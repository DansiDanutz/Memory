#!/usr/bin/env python3
"""
Secure Production Configuration Manager for Memory App Platform
Handles environment validation, secret management, and security settings
"""

import os
import sys
import json
import hashlib
import secrets
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Configuration validation error"""
    pass

class SecurityLevel(Enum):
    """Security levels for configuration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    # Authentication
    jwt_secret: str
    admin_jwt_secret: str
    session_secret: str
    
    # Encryption
    master_encryption_key: str
    database_encryption_key: str
    backup_encryption_key: str
    
    # CORS
    allowed_origins: List[str]
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    allow_credentials: bool = True
    
    # Rate Limiting
    rate_limit_window_ms: int = 60000
    rate_limit_max_requests: int = 100
    rate_limit_skip_success: bool = False
    
    # Security Headers
    hsts_max_age: int = 31536000
    csp_directives: str = "default-src 'self'"
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Admin Access
    admin_ip_whitelist: List[str] = field(default_factory=list)
    admin_2fa_required: bool = True
    admin_session_timeout: int = 3600
    
    # Audit
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 90
    
    # Input Validation
    max_request_size: int = 10485760  # 10MB
    max_field_length: int = 10000
    allowed_file_types: List[str] = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".wav", ".mp3"])
    
    def validate(self) -> List[str]:
        """Validate security configuration"""
        errors = []
        
        # Check JWT secrets
        if len(self.jwt_secret) < 64:
            errors.append("JWT secret must be at least 64 characters")
        if len(self.admin_jwt_secret) < 64:
            errors.append("Admin JWT secret must be at least 64 characters")
        
        # Check encryption keys
        if len(self.master_encryption_key) < 32:
            errors.append("Master encryption key must be at least 32 characters")
        
        # Validate CORS origins
        for origin in self.allowed_origins:
            if not re.match(r'^https?://[\w\-\.]+(:\d+)?$', origin):
                errors.append(f"Invalid CORS origin: {origin}")
        
        # Validate IP whitelist
        for ip in self.admin_ip_whitelist:
            if not self._is_valid_ip(ip):
                errors.append(f"Invalid IP address in whitelist: {ip}")
        
        return errors
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Validate IP address or CIDR notation"""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$'
        return bool(re.match(ip_pattern, ip))

@dataclass
class DatabaseConfig:
    """Database configuration with pooling and security"""
    url: str
    pool_min: int = 2
    pool_max: int = 10
    ssl_enabled: bool = True
    connection_timeout: int = 30000
    idle_timeout: int = 10000
    statement_timeout: int = 30000
    
    # Security
    encrypt_at_rest: bool = True
    audit_queries: bool = True
    
    def get_pool_config(self) -> Dict[str, Any]:
        """Get connection pool configuration"""
        return {
            'min_size': self.pool_min,
            'max_size': self.pool_max,
            'timeout': self.connection_timeout / 1000,
            'idle_timeout': self.idle_timeout / 1000,
            'statement_timeout': self.statement_timeout,
            'ssl': 'require' if self.ssl_enabled else None
        }

@dataclass
class ServiceCredentials:
    """External service credentials"""
    service_name: str
    api_key: str
    api_secret: Optional[str] = None
    endpoint: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if credentials are valid"""
        return bool(self.api_key and len(self.api_key) > 10)

class ProductionConfigManager:
    """Secure production configuration manager"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or '.env'
        self.security_level = SecurityLevel(os.getenv('ENVIRONMENT', 'development'))
        self.configs: Dict[str, Any] = {}
        self.secrets: Dict[str, str] = {}
        self.validated = False
        
        # Initialize encryption
        self._init_encryption()
        
        # Load and validate configuration
        self.load_configuration()
        self.validate_configuration()
    
    def _init_encryption(self):
        """Initialize encryption for secrets"""
        master_key = os.getenv('MEMORY_MASTER_SECRET', '')
        if not master_key:
            if self.security_level == SecurityLevel.PRODUCTION:
                raise ConfigValidationError("MEMORY_MASTER_SECRET is required in production")
            master_key = 'development-key-not-for-production'
        
        # Generate encryption key using PBKDF2
        salt = b'memory-app-salt-v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher_suite = Fernet(key)
    
    def load_configuration(self):
        """Load configuration from environment"""
        # Load security configuration
        self.security_config = SecurityConfig(
            jwt_secret=self._get_required('JWT_SECRET'),
            admin_jwt_secret=self._get_required('ADMIN_JWT_SECRET'),
            session_secret=self._get_required('SESSION_SECRET'),
            master_encryption_key=self._get_required('MEMORY_MASTER_SECRET'),
            database_encryption_key=os.getenv('DATABASE_ENCRYPTION_KEY', ''),
            backup_encryption_key=os.getenv('BACKUP_ENCRYPTION_KEY', ''),
            allowed_origins=self._parse_list(os.getenv('CORS_ALLOWED_ORIGINS', '')),
            allowed_methods=self._parse_list(os.getenv('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')),
            allowed_headers=self._parse_list(os.getenv('CORS_ALLOWED_HEADERS', 'Content-Type,Authorization')),
            allow_credentials=os.getenv('CORS_CREDENTIALS', 'true').lower() == 'true',
            rate_limit_window_ms=int(os.getenv('RATE_LIMIT_WINDOW_MS', '60000')),
            rate_limit_max_requests=int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '100')),
            hsts_max_age=int(os.getenv('HSTS_MAX_AGE', '31536000')),
            csp_directives=os.getenv('CSP_DIRECTIVES', "default-src 'self'"),
            admin_ip_whitelist=self._parse_list(os.getenv('ADMIN_IP_WHITELIST', '')),
            admin_2fa_required=os.getenv('ADMIN_2FA_ENABLED', 'true').lower() == 'true'
        )
        
        # Load database configuration
        self.database_config = DatabaseConfig(
            url=self._get_required('DATABASE_URL'),
            pool_min=int(os.getenv('DATABASE_POOL_MIN', '2')),
            pool_max=int(os.getenv('DATABASE_POOL_MAX', '10')),
            ssl_enabled=os.getenv('DATABASE_SSL', 'true').lower() == 'true'
        )
        
        # Load service credentials
        self.services = {
            'openai': ServiceCredentials(
                service_name='OpenAI',
                api_key=os.getenv('OPENAI_API_KEY', ''),
                endpoint='https://api.openai.com/v1'
            ),
            'anthropic': ServiceCredentials(
                service_name='Anthropic',
                api_key=os.getenv('ANTHROPIC_API_KEY', ''),
                endpoint='https://api.anthropic.com'
            ),
            'xai': ServiceCredentials(
                service_name='xAI',
                api_key=os.getenv('XAI_API_KEY', ''),
                endpoint='https://api.x.ai/v1'
            ),
            'twilio': ServiceCredentials(
                service_name='Twilio',
                api_key=os.getenv('TWILIO_ACCOUNT_SID', ''),
                api_secret=os.getenv('TWILIO_AUTH_TOKEN', ''),
                webhook_secret=os.getenv('TWILIO_WEBHOOK_SECRET', '')
            ),
            'whatsapp': ServiceCredentials(
                service_name='WhatsApp',
                api_key=os.getenv('WHATSAPP_ACCESS_TOKEN', ''),
                webhook_secret=os.getenv('WHATSAPP_WEBHOOK_SECRET', '')
            ),
            'telegram': ServiceCredentials(
                service_name='Telegram',
                api_key=os.getenv('TELEGRAM_BOT_TOKEN', '')
            ),
            'stripe': ServiceCredentials(
                service_name='Stripe',
                api_key=os.getenv('STRIPE_SECRET_KEY', ''),
                webhook_secret=os.getenv('STRIPE_WEBHOOK_SECRET', '')
            )
        }
        
        # Load feature flags
        self.features = {
            'voice_cloning': os.getenv('FEATURE_VOICE_CLONING', 'true').lower() == 'true',
            'voice_auth': os.getenv('FEATURE_VOICE_AUTH', 'true').lower() == 'true',
            'memory_gaming': os.getenv('FEATURE_MEMORY_GAMING', 'true').lower() == 'true',
            'admin_dashboard': os.getenv('FEATURE_ADMIN_DASHBOARD', 'true').lower() == 'true',
            'mutual_connections': os.getenv('FEATURE_MUTUAL_CONNECTIONS', 'true').lower() == 'true',
            'secret_memories': os.getenv('FEATURE_SECRET_MEMORIES', 'true').lower() == 'true',
            'emergency_inheritance': os.getenv('FEATURE_EMERGENCY_INHERITANCE', 'true').lower() == 'true'
        }
        
        # Load monitoring configuration
        self.monitoring = {
            'sentry_dsn': os.getenv('SENTRY_DSN', ''),
            'log_level': os.getenv('LOG_LEVEL', 'info'),
            'prometheus_enabled': os.getenv('PROMETHEUS_ENABLED', 'false').lower() == 'true',
            'health_check_interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '30000'))
        }
    
    def _get_required(self, key: str) -> str:
        """Get required environment variable"""
        value = os.getenv(key, '')
        if not value and self.security_level == SecurityLevel.PRODUCTION:
            raise ConfigValidationError(f"Required environment variable {key} is not set")
        return value or f'demo-{key.lower()}'
    
    def _parse_list(self, value: str) -> List[str]:
        """Parse comma-separated list from environment variable"""
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def validate_configuration(self) -> bool:
        """Validate all configuration"""
        errors = []
        warnings = []
        
        # Validate security configuration
        security_errors = self.security_config.validate()
        errors.extend(security_errors)
        
        # Check database configuration
        if not self.database_config.url:
            errors.append("DATABASE_URL is required")
        elif not self.database_config.url.startswith(('postgresql://', 'postgres://')):
            warnings.append("DATABASE_URL should use PostgreSQL in production")
        
        # Check service credentials
        required_services = ['openai', 'stripe'] if self.security_level == SecurityLevel.PRODUCTION else []
        for service_name in required_services:
            service = self.services.get(service_name)
            if not service or not service.is_valid():
                errors.append(f"{service_name.upper()} credentials are required in production")
        
        # Check SSL/TLS configuration
        if self.security_level == SecurityLevel.PRODUCTION:
            if not self.database_config.ssl_enabled:
                errors.append("Database SSL must be enabled in production")
            
            for origin in self.security_config.allowed_origins:
                if origin.startswith('http://') and 'localhost' not in origin:
                    errors.append(f"HTTPS is required for origin: {origin}")
        
        # Log validation results
        if errors:
            logger.error(f"Configuration validation failed with {len(errors)} errors:")
            for error in errors:
                logger.error(f"  - {error}")
            if self.security_level == SecurityLevel.PRODUCTION:
                raise ConfigValidationError(f"Configuration validation failed: {'; '.join(errors)}")
        
        if warnings:
            logger.warning(f"Configuration has {len(warnings)} warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        self.validated = True
        logger.info("✅ Configuration validation successful")
        return True
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret value"""
        return self.cipher_suite.encrypt(secret.encode()).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value"""
        return self.cipher_suite.decrypt(encrypted_secret.encode()).decode()
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        return {
            'Strict-Transport-Security': f'max-age={self.security_config.hsts_max_age}; includeSubDomains; preload',
            'Content-Security-Policy': self.security_config.csp_directives,
            'X-Frame-Options': self.security_config.x_frame_options,
            'X-Content-Type-Options': self.security_config.x_content_type_options,
            'X-XSS-Protection': self.security_config.x_xss_protection,
            'Referrer-Policy': self.security_config.referrer_policy,
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            'origins': self.security_config.allowed_origins,
            'methods': self.security_config.allowed_methods,
            'allow_headers': self.security_config.allowed_headers,
            'supports_credentials': self.security_config.allow_credentials
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'windowMs': self.security_config.rate_limit_window_ms,
            'max': self.security_config.rate_limit_max_requests,
            'skipSuccessfulRequests': self.security_config.rate_limit_skip_success,
            'message': 'Too many requests, please try again later'
        }
    
    def is_production_ready(self) -> Tuple[bool, List[str]]:
        """Check if configuration is production ready"""
        checks = []
        
        # Security checks
        if len(self.security_config.jwt_secret) < 64:
            checks.append("JWT secret too short")
        if not self.security_config.admin_2fa_required:
            checks.append("2FA should be enabled for admin access")
        if not self.security_config.admin_ip_whitelist:
            checks.append("Admin IP whitelist not configured")
        
        # Database checks
        if not self.database_config.ssl_enabled:
            checks.append("Database SSL not enabled")
        if self.database_config.pool_max < 5:
            checks.append("Database pool size too small for production")
        
        # Service checks
        critical_services = ['openai', 'stripe', 'twilio']
        for service_name in critical_services:
            if not self.services[service_name].is_valid():
                checks.append(f"{service_name} not configured")
        
        # Monitoring checks
        if not self.monitoring['sentry_dsn']:
            checks.append("Sentry error tracking not configured")
        
        is_ready = len(checks) == 0
        return is_ready, checks
    
    def export_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration (for debugging, exclude secrets by default)"""
        config = {
            'environment': self.security_level.value,
            'validated': self.validated,
            'features': self.features,
            'monitoring': self.monitoring,
            'security': {
                'cors_origins': self.security_config.allowed_origins,
                'rate_limit_max': self.security_config.rate_limit_max_requests,
                'admin_2fa': self.security_config.admin_2fa_required,
                'admin_ip_whitelist': self.security_config.admin_ip_whitelist
            },
            'database': {
                'pool_min': self.database_config.pool_min,
                'pool_max': self.database_config.pool_max,
                'ssl_enabled': self.database_config.ssl_enabled
            },
            'services': {}
        }
        
        # Add service status (without secrets)
        for name, service in self.services.items():
            config['services'][name] = {
                'configured': service.is_valid(),
                'name': service.service_name
            }
            if include_secrets:
                config['services'][name]['has_key'] = bool(service.api_key)
                config['services'][name]['has_secret'] = bool(service.api_secret)
        
        return config

# Initialize global configuration manager
_config_manager = None

def get_config() -> ProductionConfigManager:
    """Get or create the configuration manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ProductionConfigManager()
    return _config_manager

def validate_and_start():
    """Validate configuration and start the application"""
    try:
        config = get_config()
        is_ready, issues = config.is_production_ready()
        
        if not is_ready:
            logger.warning(f"Configuration has {len(issues)} issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            
            if config.security_level == SecurityLevel.PRODUCTION:
                logger.error("Cannot start in production with configuration issues")
                sys.exit(1)
        else:
            logger.info("✅ Configuration is production ready")
        
        return config
    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during configuration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Test configuration loading
    config = validate_and_start()
    print(json.dumps(config.export_config(), indent=2))