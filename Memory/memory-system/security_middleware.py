#!/usr/bin/env python3
"""
Security Middleware for Memory App Platform
Provides comprehensive security measures including input validation,
sanitization, rate limiting, and secure headers
"""

import re
import json
import html
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import jwt
from flask import Flask, request, jsonify, g, Response
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden
import bleach
from collections import defaultdict
import ipaddress
import time

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Main security middleware class"""
    
    def __init__(self, app: Optional[Flask] = None, config: Optional[Dict] = None):
        self.app = app
        self.config = config or {}
        self.rate_limiters = defaultdict(lambda: defaultdict(list))
        self.blocked_ips = set()
        self.failed_attempts = defaultdict(int)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize middleware with Flask app"""
        self.app = app
        
        # Register before_request handlers
        app.before_request(self.check_blocked_ip)
        app.before_request(self.validate_request_size)
        app.before_request(self.check_rate_limit)
        app.before_request(self.validate_content_type)
        app.before_request(self.sanitize_inputs)
        
        # Register after_request handlers
        app.after_request(self.add_security_headers)
        app.after_request(self.log_request)
        
        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(500, self.handle_internal_error)
        
        logger.info("✅ Security middleware initialized")
    
    # ============================================
    # Request Validation
    # ============================================
    
    def check_blocked_ip(self):
        """Check if IP is blocked"""
        client_ip = self.get_client_ip()
        
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return jsonify({'error': 'Access denied'}), 403
        
        # Check failed attempts
        if self.failed_attempts.get(client_ip, 0) > 10:
            self.blocked_ips.add(client_ip)
            logger.warning(f"IP blocked due to failed attempts: {client_ip}")
            return jsonify({'error': 'Too many failed attempts'}), 403
    
    def validate_request_size(self):
        """Validate request size"""
        max_size = self.config.get('max_request_size', 10485760)  # 10MB default
        
        if request.content_length and request.content_length > max_size:
            logger.warning(f"Request too large: {request.content_length} bytes")
            return jsonify({'error': 'Request too large'}), 413
    
    def check_rate_limit(self):
        """Check rate limiting"""
        if request.path.startswith('/health') or request.path.startswith('/metrics'):
            return  # Skip rate limiting for health checks
        
        client_ip = self.get_client_ip()
        endpoint = request.endpoint or request.path
        
        # Get rate limit config
        window_ms = self.config.get('rate_limit_window_ms', 60000)
        max_requests = self.config.get('rate_limit_max_requests', 100)
        
        # Clean old requests
        now = time.time() * 1000
        cutoff = now - window_ms
        
        requests = self.rate_limiters[client_ip][endpoint]
        self.rate_limiters[client_ip][endpoint] = [t for t in requests if t > cutoff]
        
        # Check limit
        if len(self.rate_limiters[client_ip][endpoint]) >= max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Add current request
        self.rate_limiters[client_ip][endpoint].append(now)
    
    def validate_content_type(self):
        """Validate content type for POST/PUT requests"""
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type
            
            if not content_type:
                return jsonify({'error': 'Content-Type header required'}), 400
            
            # Allow common content types
            allowed_types = [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
                'text/plain',
                'text/xml',
                'application/xml'
            ]
            
            base_type = content_type.split(';')[0].strip()
            if not any(base_type.startswith(allowed) for allowed in allowed_types):
                logger.warning(f"Invalid content type: {content_type}")
                return jsonify({'error': 'Invalid content type'}), 400
    
    def sanitize_inputs(self):
        """Sanitize all input data"""
        # Sanitize query parameters
        if request.args:
            g.sanitized_args = self._sanitize_dict(request.args.to_dict())
        
        # Sanitize form data
        if request.form:
            g.sanitized_form = self._sanitize_dict(request.form.to_dict())
        
        # Sanitize JSON data
        if request.is_json:
            try:
                json_data = request.get_json()
                if json_data:
                    g.sanitized_json = self._sanitize_data(json_data)
            except Exception as e:
                logger.error(f"Invalid JSON data: {e}")
                return jsonify({'error': 'Invalid JSON data'}), 400
    
    def _sanitize_dict(self, data: Dict) -> Dict:
        """Sanitize dictionary data"""
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            clean_key = self._sanitize_string(key)[:100]  # Limit key length
            
            # Sanitize value
            if isinstance(value, str):
                sanitized[clean_key] = self._sanitize_string(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [self._sanitize_string(str(v)) for v in value]
            else:
                sanitized[clean_key] = value
        
        return sanitized
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data"""
        if isinstance(data, dict):
            return {self._sanitize_string(k): self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            return data
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string input"""
        if not text:
            return text
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # HTML escape
        text = html.escape(text)
        
        # Remove dangerous HTML/JS using bleach
        text = bleach.clean(text, tags=[], strip=True)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        max_length = self.config.get('max_field_length', 10000)
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    # ============================================
    # Input Validation Helpers
    # ============================================
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number"""
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        # Check if it's a valid phone number (10-15 digits)
        return 10 <= len(digits) <= 15
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """Validate UUID"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_str.lower()))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_alphanumeric(text: str, allow_spaces: bool = False) -> bool:
        """Validate alphanumeric text"""
        if allow_spaces:
            pattern = r'^[a-zA-Z0-9\s]+$'
        else:
            pattern = r'^[a-zA-Z0-9]+$'
        return bool(re.match(pattern, text))
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    # ============================================
    # Security Headers
    # ============================================
    
    def add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        # Basic security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS (only in production)
        if self.config.get('environment') == 'production':
            max_age = self.config.get('hsts_max_age', 31536000)
            response.headers['Strict-Transport-Security'] = f'max-age={max_age}; includeSubDomains; preload'
        
        # CSP
        csp = self.config.get('csp_directives', "default-src 'self'")
        response.headers['Content-Security-Policy'] = csp
        
        # Permissions Policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server header
        response.headers.pop('Server', None)
        
        # Add custom security header
        response.headers['X-Memory-App-Version'] = self.config.get('app_version', '1.0.0')
        
        return response
    
    # ============================================
    # Error Handlers
    # ============================================
    
    def handle_bad_request(self, error):
        """Handle 400 errors"""
        logger.warning(f"Bad request: {error}")
        return jsonify({
            'error': 'Bad request',
            'message': 'The request could not be understood or was missing required parameters'
        }), 400
    
    def handle_unauthorized(self, error):
        """Handle 401 errors"""
        client_ip = self.get_client_ip()
        self.failed_attempts[client_ip] += 1
        logger.warning(f"Unauthorized access attempt from {client_ip}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    def handle_forbidden(self, error):
        """Handle 403 errors"""
        logger.warning(f"Forbidden access: {error}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    def handle_not_found(self, error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource could not be found'
        }), 404
    
    def handle_internal_error(self, error):
        """Handle 500 errors"""
        # Log full error internally
        logger.error(f"Internal server error: {error}", exc_info=True)
        
        # Return generic error to client (no stack traces)
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        # Check for proxy headers
        if 'X-Forwarded-For' in request.headers:
            ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        elif 'X-Real-IP' in request.headers:
            ip = request.headers['X-Real-IP']
        else:
            ip = request.remote_addr
        
        # Validate IP
        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            return request.remote_addr or '0.0.0.0'
    
    def log_request(self, response: Response) -> Response:
        """Log request for audit"""
        if self.config.get('enable_audit_logging', True):
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'ip': self.get_client_ip(),
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'user_agent': request.headers.get('User-Agent', ''),
                'duration_ms': g.get('request_start_time', 0)
            }
            
            # Log based on status code
            if response.status_code >= 500:
                logger.error(f"Request audit: {json.dumps(log_data)}")
            elif response.status_code >= 400:
                logger.warning(f"Request audit: {json.dumps(log_data)}")
            else:
                logger.info(f"Request audit: {json.dumps(log_data)}")
        
        return response

# ============================================
# Decorator Functions
# ============================================

def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header'}), 401
        
        if not token:
            return jsonify({'error': 'Authorization required'}), 401
        
        try:
            # Verify token (use your JWT secret)
            jwt_secret = os.getenv('JWT_SECRET', 'your-jwt-secret')
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            g.user_id = payload.get('user_id')
            g.user_role = payload.get('role')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f: Callable) -> Callable:
    """Decorator to require admin authentication"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        if g.get('user_role') not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

def validate_input(schema: Dict[str, Any]) -> Callable:
    """Decorator to validate input against schema"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json() if request.is_json else request.form.to_dict()
            
            # Validate against schema
            errors = []
            for field, rules in schema.items():
                value = data.get(field)
                
                # Check required
                if rules.get('required') and not value:
                    errors.append(f"{field} is required")
                    continue
                
                if value:
                    # Check type
                    expected_type = rules.get('type')
                    if expected_type and not isinstance(value, expected_type):
                        errors.append(f"{field} must be of type {expected_type.__name__}")
                    
                    # Check pattern
                    pattern = rules.get('pattern')
                    if pattern and isinstance(value, str) and not re.match(pattern, value):
                        errors.append(f"{field} has invalid format")
                    
                    # Check length
                    min_length = rules.get('min_length')
                    max_length = rules.get('max_length')
                    if isinstance(value, str):
                        if min_length and len(value) < min_length:
                            errors.append(f"{field} must be at least {min_length} characters")
                        if max_length and len(value) > max_length:
                            errors.append(f"{field} must be at most {max_length} characters")
                    
                    # Check range
                    min_value = rules.get('min')
                    max_value = rules.get('max')
                    if isinstance(value, (int, float)):
                        if min_value is not None and value < min_value:
                            errors.append(f"{field} must be at least {min_value}")
                        if max_value is not None and value > max_value:
                            errors.append(f"{field} must be at most {max_value}")
            
            if errors:
                return jsonify({'error': 'Validation failed', 'details': errors}), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def rate_limit(max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """Decorator for custom rate limiting"""
    def decorator(f: Callable) -> Callable:
        request_times = defaultdict(list)
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_id = request.remote_addr
            now = time.time()
            
            # Clean old requests
            cutoff = now - window_seconds
            request_times[client_id] = [t for t in request_times[client_id] if t > cutoff]
            
            # Check limit
            if len(request_times[client_id]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            request_times[client_id].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# ============================================
# SQL Injection Prevention
# ============================================

class SQLSanitizer:
    """SQL injection prevention utilities"""
    
    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """Sanitize SQL identifier (table/column name)"""
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier}")
        return identifier
    
    @staticmethod
    def sanitize_value(value: Any) -> Any:
        """Sanitize SQL value (use parameterized queries instead when possible)"""
        if isinstance(value, str):
            # Escape special characters
            value = value.replace("'", "''")
            value = value.replace("\\", "\\\\")
            value = value.replace("\n", "\\n")
            value = value.replace("\r", "\\r")
            value = value.replace("\t", "\\t")
            value = value.replace("\x00", "")
        return value
    
    @staticmethod
    def validate_order_by(column: str, allowed_columns: List[str]) -> str:
        """Validate ORDER BY column"""
        if column not in allowed_columns:
            raise ValueError(f"Invalid sort column: {column}")
        return column

# ============================================
# CSRF Protection
# ============================================

class CSRFProtection:
    """CSRF protection utilities"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        timestamp = str(int(time.time()))
        data = f"{session_id}:{timestamp}"
        signature = hashlib.sha256(f"{data}:{self.secret_key}".encode()).hexdigest()
        return f"{data}:{signature}"
    
    def validate_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """Validate CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            token_session, timestamp, signature = parts
            
            # Check session match
            if token_session != session_id:
                return False
            
            # Check age
            token_age = int(time.time()) - int(timestamp)
            if token_age > max_age:
                return False
            
            # Check signature
            expected_signature = hashlib.sha256(
                f"{token_session}:{timestamp}:{self.secret_key}".encode()
            ).hexdigest()
            
            return secrets.compare_digest(signature, expected_signature)
        except Exception:
            return False

# Export main components
__all__ = [
    'SecurityMiddleware',
    'require_auth',
    'require_admin',
    'validate_input',
    'rate_limit',
    'SQLSanitizer',
    'CSRFProtection'
]