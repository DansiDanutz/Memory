#!/usr/bin/env python3
"""
Security Manager for Digital Immortality Platform
Handles encryption, rate limiting, audit logging, and webhook verification
"""

import os
import sys
import json
import hmac
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
except ImportError:
    PBKDF2 = None
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from flask import request, jsonify, g, session
from collections import defaultdict
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import database models
try:
    from database.models import DatabaseManager, AuditLog, SecurityLevel
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    DatabaseManager = None
    AuditLog = None
    SecurityLevel = None
    logging.warning("Database models not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, key: Optional[str] = None):
        """Initialize encryption manager with key"""
        if key:
            self.key = key.encode()
        else:
            # Generate or load key from environment
            env_key = os.environ.get('ENCRYPTION_KEY')
            if env_key:
                self.key = env_key.encode()
            else:
                # Generate new key
                self.key = Fernet.generate_key()
                logger.warning("Generated new encryption key (hidden for security)")
                logger.warning("⚠️ CRITICAL: Set ENCRYPTION_KEY environment variable for production")
        
        self.cipher = Fernet(self.key)
        logger.info("Encryption manager initialized")
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt encrypted data"""
        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt to dictionary"""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple:
        """Hash password with salt"""
        if not salt:
            salt = os.urandom(32)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.b64encode(kdf.derive(password.encode()))
        return key.decode(), base64.b64encode(salt).decode()
    
    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        salt_bytes = base64.b64decode(salt.encode())
        new_hash, _ = self.hash_password(password, salt_bytes)
        return new_hash == hashed

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter"""
        self.redis_client = redis_client
        self.memory_store = defaultdict(list)  # Fallback for when Redis not available
        
        if redis_client:
            logger.info("Rate limiter initialized with Redis")
        else:
            logger.info("Rate limiter initialized with memory store (not recommended for production)")
    
    def is_allowed(self, key: str, max_calls: int, window: int) -> bool:
        """Check if request is allowed under rate limit"""
        current_time = time.time()
        
        if self.redis_client:
            # Redis-based rate limiting
            try:
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, current_time - window)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.zcount(key, current_time - window, current_time)
                pipe.expire(key, window)
                results = pipe.execute()
                
                request_count = results[2]
                return request_count <= max_calls
            except Exception as e:
                logger.error(f"Redis rate limiting failed: {e}")
                return True  # Allow on error
        else:
            # Memory-based rate limiting
            # Clean old entries
            self.memory_store[key] = [
                timestamp for timestamp in self.memory_store[key]
                if timestamp > current_time - window
            ]
            
            # Check rate limit
            if len(self.memory_store[key]) >= max_calls:
                return False
            
            # Add current request
            self.memory_store[key].append(current_time)
            return True
    
    def decorator(self, max_calls: int = 60, window: int = 60):
        """Decorator for rate limiting Flask routes"""
        def decorator_wrapper(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # Get rate limit key
                user_id = session.get('user_id')
                ip = request.remote_addr
                endpoint = request.endpoint
                
                # Create composite key
                key = f"rate_limit:{endpoint}:{user_id or ip}"
                
                # Check rate limit
                if not self.is_allowed(key, max_calls, window):
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded',
                        'retry_after': window
                    }), 429
                
                return f(*args, **kwargs)
            return wrapper
        return decorator_wrapper

class AuditLogger:
    """Audit logging for sensitive operations"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize audit logger"""
        self.db_manager = db_manager or (DatabaseManager() if DB_AVAILABLE else None)
        logger.info("Audit logger initialized")
    
    def log(self, action: str, resource: Optional[str] = None, 
            resource_type: Optional[str] = None, success: bool = True,
            error_message: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log an audit event"""
        try:
            if self.db_manager:
                with self.db_manager.get_session() as session:
                    log_entry = AuditLog(
                        user_id=g.get('user_id') or session.get('user_id'),
                        action=action,
                        resource=resource,
                        resource_type=resource_type,
                        ip_address=request.remote_addr if request else None,
                        user_agent=request.headers.get('User-Agent') if request else None,
                        voice_verified=g.get('voice_verified', False),
                        security_level=g.get('security_level'),
                        success=success,
                        error_message=error_message,
                        extra_metadata=metadata or {},
                        duration_ms=g.get('request_duration_ms')
                    )
                    session.add(log_entry)
                    session.commit()
            else:
                # Fallback to file logging
                log_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'user_id': g.get('user_id') or (session.get('user_id') if 'session' in globals() else None),
                    'action': action,
                    'resource': resource,
                    'resource_type': resource_type,
                    'ip_address': request.remote_addr if request else None,
                    'success': success,
                    'error_message': error_message,
                    'metadata': metadata
                }
                logger.info(f"AUDIT: {json.dumps(log_data)}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def decorator(self, action: str, resource_type: Optional[str] = None):
        """Decorator for automatic audit logging"""
        def decorator_wrapper(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                resource = kwargs.get('memory_id') or kwargs.get('job_id') or kwargs.get('id')
                
                try:
                    result = f(*args, **kwargs)
                    
                    # Calculate duration
                    duration_ms = int((time.time() - start_time) * 1000)
                    g.request_duration_ms = duration_ms
                    
                    # Log success
                    self.log(
                        action=action,
                        resource=resource,
                        resource_type=resource_type,
                        success=True
                    )
                    
                    return result
                    
                except Exception as e:
                    # Calculate duration
                    duration_ms = int((time.time() - start_time) * 1000)
                    g.request_duration_ms = duration_ms
                    
                    # Log failure
                    self.log(
                        action=action,
                        resource=resource,
                        resource_type=resource_type,
                        success=False,
                        error_message=str(e)
                    )
                    
                    raise
            return wrapper
        return decorator_wrapper

class WebhookVerifier:
    """Verify webhook signatures for secure communication"""
    
    def __init__(self, secret: Optional[str] = None):
        """Initialize webhook verifier"""
        self.secret = secret or os.environ.get('WEBHOOK_SECRET', 'default_secret')
        logger.info("Webhook verifier initialized")
    
    def generate_signature(self, payload: bytes) -> str:
        """Generate HMAC signature for payload"""
        signature = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        expected_signature = self.generate_signature(payload)
        return hmac.compare_digest(expected_signature, signature)
    
    def decorator(self):
        """Decorator for webhook endpoint verification"""
        def decorator_wrapper(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # Get signature from headers
                signature = request.headers.get('X-Signature') or request.headers.get('X-Hub-Signature-256')
                
                if not signature:
                    return jsonify({
                        'success': False,
                        'error': 'Missing signature'
                    }), 401
                
                # Verify signature
                if not self.verify_signature(request.data, signature):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid signature'
                    }), 401
                
                return f(*args, **kwargs)
            return wrapper
        return decorator_wrapper

class CORSManager:
    """CORS configuration for production"""
    
    @staticmethod
    def configure_cors(app, origins: Optional[list] = None):
        """Configure CORS for Flask app"""
        from flask_cors import CORS
        
        allowed_origins = origins or [
            'http://localhost:3000',
            'http://localhost:5000',
            'https://*.repl.co',
            'https://*.replit.dev',
            'https://*.replit.app'
        ]
        
        # Get additional origins from environment
        env_origins = os.environ.get('CORS_ORIGINS', '').split(',')
        if env_origins:
            allowed_origins.extend([o.strip() for o in env_origins if o.strip()])
        
        CORS(app, 
             origins=allowed_origins,
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Voice-Token', 'X-Signature'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             max_age=3600)
        
        logger.info(f"CORS configured with origins: {allowed_origins}")
        return app

class SecurityManager:
    """Main security manager combining all security features"""
    
    def __init__(self, app=None, redis_client=None):
        """Initialize security manager"""
        self.encryption = EncryptionManager()
        self.rate_limiter = RateLimiter(redis_client)
        self.audit_logger = AuditLogger()
        self.webhook_verifier = WebhookVerifier()
        
        if app:
            self.init_app(app)
        
        logger.info("Security Manager initialized with all components")
    
    def init_app(self, app):
        """Initialize Flask app with security features"""
        # Configure CORS
        CORSManager.configure_cors(app)
        
        # Add before_request handler for request tracking
        @app.before_request
        def before_request():
            g.request_start_time = time.time()
        
        # Add after_request handler for security headers
        @app.after_request
        def after_request(response):
            # Add security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # Add CSP header
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' http://localhost:* ws://localhost:*"
            )
            
            return response
        
        logger.info("Flask app configured with security features")
    
    def encrypt_sensitive_data(self, data: Any) -> str:
        """Encrypt sensitive data"""
        if isinstance(data, dict):
            return self.encryption.encrypt_dict(data)
        return self.encryption.encrypt(str(data))
    
    def decrypt_sensitive_data(self, encrypted_data: str, as_dict: bool = False) -> Any:
        """Decrypt sensitive data"""
        if as_dict:
            return self.encryption.decrypt_dict(encrypted_data)
        return self.encryption.decrypt(encrypted_data)
    
    def check_rate_limit(self, key: str, max_calls: int = 60, window: int = 60) -> bool:
        """Check if request is within rate limit"""
        return self.rate_limiter.is_allowed(key, max_calls, window)
    
    def audit_log(self, action: str, **kwargs):
        """Log audit event"""
        self.audit_logger.log(action, **kwargs)
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        return self.webhook_verifier.verify_signature(payload, signature)

# Global security manager instance
security_manager = None

def initialize_security(app=None, redis_client=None):
    """Initialize global security manager"""
    global security_manager
    security_manager = SecurityManager(app, redis_client)
    return security_manager

def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global security_manager
    if not security_manager:
        security_manager = SecurityManager()
    return security_manager

# Export decorators for easy use
def rate_limit(max_calls: int = 60, window: int = 60):
    """Rate limiting decorator"""
    manager = get_security_manager()
    return manager.rate_limiter.decorator(max_calls, window)

def audit_log(action: str, resource_type: Optional[str] = None):
    """Audit logging decorator"""
    manager = get_security_manager()
    return manager.audit_logger.decorator(action, resource_type)

def verify_webhook():
    """Webhook verification decorator"""
    manager = get_security_manager()
    return manager.webhook_verifier.decorator()

# For testing
if __name__ == "__main__":
    # Test encryption
    manager = SecurityManager()
    
    # Test string encryption
    original = "This is sensitive data"
    encrypted = manager.encrypt_sensitive_data(original)
    decrypted = manager.decrypt_sensitive_data(encrypted)
    print(f"Original: {original}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    assert original == decrypted
    
    # Test dict encryption
    original_dict = {"user": "test", "password": "secret123"}
    encrypted_dict = manager.encrypt_sensitive_data(original_dict)
    decrypted_dict = manager.decrypt_sensitive_data(encrypted_dict, as_dict=True)
    print(f"\nOriginal dict: {original_dict}")
    print(f"Encrypted dict: {encrypted_dict}")
    print(f"Decrypted dict: {decrypted_dict}")
    assert original_dict == decrypted_dict
    
    # Test password hashing
    password = "mySecurePassword123"
    hashed, salt = manager.encryption.hash_password(password)
    print(f"\nPassword: {password}")
    print(f"Hashed: {hashed}")
    print(f"Salt: {salt}")
    assert manager.encryption.verify_password(password, hashed, salt)
    assert not manager.encryption.verify_password("wrongPassword", hashed, salt)
    
    print("\n✅ All security tests passed!")