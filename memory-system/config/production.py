#!/usr/bin/env python3
"""
Production Configuration for Digital Immortality Platform
Environment variables, database pooling, logging, and security settings
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import timedelta
import json
from pathlib import Path

class Config:
    """Base configuration"""
    
    # Application settings
    APP_NAME = "Digital Immortality Platform"
    VERSION = "1.0.0"
    DEBUG = False
    TESTING = False
    
    # Environment
    ENV = os.environ.get('ENVIRONMENT', 'production')
    
    # Secret keys
    SECRET_KEY = os.environ.get('SECRET_KEY', 'CHANGE_THIS_IN_PRODUCTION_' + os.urandom(24).hex())
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'webhook_secret_' + os.urandom(16).hex())
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/memory_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Database pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 20)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 40)),
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 seconds
        }
    }
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_POOL_SIZE = int(os.environ.get('REDIS_POOL_SIZE', 10))
    
    # Session configuration
    SESSION_TYPE = 'redis' if REDIS_URL else 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else [
        'http://localhost:3000',
        'http://localhost:5000',
        'https://*.repl.co',
        'https://*.replit.dev',
        'https://*.replit.app'
    ]
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '100/hour')
    RATE_LIMIT_STORAGE_URL = REDIS_URL
    
    # Rate limit presets
    RATE_LIMITS = {
        'auth': '10/hour',
        'harvest': '10/day',
        'patterns': '100/hour',
        'insights': '100/hour',
        'review': '200/hour',
        'confidential': '20/hour',
        'secret': '10/hour',
        'ultra_secret': '5/hour'
    }
    
    # Background jobs
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = os.environ.get('SCHEDULER_TIMEZONE', 'UTC')
    
    # Job schedule (cron expressions)
    JOB_SCHEDULE = {
        'harvest': {'hour': 2, 'minute': 0},  # 2 AM
        'pattern_analysis': {'hour': 3, 'minute': 0},  # 3 AM
        'insight_generation': {'hour': 4, 'minute': 0},  # 4 AM
        'daily_digest': {'hour': 6, 'minute': 0},  # 6 AM
        'backup': {'hour': 1, 'minute': 0}  # 1 AM
    }
    
    # Security settings
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'salt_' + os.urandom(16).hex())
    SECURITY_PASSWORD_HASH = 'pbkdf2:sha256:150000'
    SECURITY_TOKEN_MAX_AGE = 3600  # 1 hour
    
    # Voice authentication
    VOICE_AUTH_ENABLED = os.environ.get('VOICE_AUTH_ENABLED', 'true').lower() == 'true'
    VOICE_AUTH_TIMEOUT = int(os.environ.get('VOICE_AUTH_TIMEOUT', 300))  # 5 minutes
    VOICE_AUTH_MAX_ATTEMPTS = int(os.environ.get('VOICE_AUTH_MAX_ATTEMPTS', 3))
    
    # API keys (for external services)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    # File storage
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'mp4'}
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10))
    
    # Performance settings
    CACHE_TYPE = 'redis' if REDIS_URL else 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'cache:'
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    METRICS_ENABLED = os.environ.get('METRICS_ENABLED', 'true').lower() == 'true'
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    
    # Relaxed rate limits for development
    RATE_LIMITS = {
        'auth': '100/hour',
        'harvest': '100/hour',
        'patterns': '1000/hour',
        'insights': '1000/hour',
        'review': '1000/hour',
        'confidential': '100/hour',
        'secret': '100/hour',
        'ultra_secret': '100/hour'
    }
    
    # Disable voice auth in development
    VOICE_AUTH_ENABLED = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Disable rate limiting in tests
    RATE_LIMIT_ENABLED = False
    
    # Disable voice auth in tests
    VOICE_AUTH_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    ENV = 'production'
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization"""
        Config.init_app(app)
        
        # Log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog = SysLogHandler()
        syslog.setLevel(logging.WARNING)
        app.logger.addHandler(syslog)
        
        # Initialize Sentry for error tracking
        if cls.SENTRY_DSN:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(
                dsn=cls.SENTRY_DSN,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,
                environment=cls.ENV
            )

class ConfigManager:
    """Configuration manager"""
    
    configs = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }
    
    @classmethod
    def get_config(cls, config_name: Optional[str] = None) -> Config:
        """Get configuration by name"""
        if not config_name:
            config_name = os.environ.get('FLASK_ENV', 'production')
        
        return cls.configs.get(config_name, ProductionConfig)
    
    @classmethod
    def load_env_file(cls, env_file: str = '.env'):
        """Load environment variables from file"""
        env_path = Path(env_file)
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            logging.info(f"Loaded environment from {env_file}")
    
    @classmethod
    def validate_config(cls, config: Config) -> bool:
        """Validate configuration"""
        required_vars = []
        
        if config.ENV == 'production':
            required_vars = [
                'SECRET_KEY',
                'DATABASE_URL',
                'ENCRYPTION_KEY',
                'JWT_SECRET_KEY'
            ]
        
        missing = [var for var in required_vars if not getattr(config, var, None)]
        
        if missing:
            logging.error(f"Missing required configuration: {', '.join(missing)}")
            return False
        
        return True

def setup_logging(config: Config):
    """Setup logging configuration"""
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Setup root logger
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT
    )
    
    # Setup file handler with rotation
    if config.LOG_FILE:
        file_handler = RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        logging.getLogger().addHandler(file_handler)

def create_app(config_name: Optional[str] = None):
    """Application factory"""
    from flask import Flask
    from flask_cors import CORS
    
    # Load environment variables
    ConfigManager.load_env_file()
    
    # Get configuration
    config = ConfigManager.get_config(config_name)
    
    # Validate configuration
    if not ConfigManager.validate_config(config):
        raise ValueError("Invalid configuration")
    
    # Setup logging
    setup_logging(config)
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize extensions
    config.init_app(app)
    
    # Setup CORS
    CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    
    # Setup security
    from security.security_manager import initialize_security
    initialize_security(app)
    
    # Setup database
    from database.models import DatabaseManager
    db_manager = DatabaseManager(config.DATABASE_URL)
    db_manager.create_tables()
    
    # Setup background jobs
    if config.SCHEDULER_API_ENABLED:
        from background_jobs import initialize_job_manager
        job_manager = initialize_job_manager(config.DATABASE_URL)
        # Note: Don't start scheduler here, start in separate thread/process
    
    # Register blueprints
    from routes.memory import memory_bp
    from routes.user import user_bp
    from routes.enhanced_memory import enhanced_memory_bp
    
    app.register_blueprint(memory_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(enhanced_memory_bp)
    
    logging.info(f"Application created with {config.ENV} configuration")
    
    return app

# Environment variable template
ENV_TEMPLATE = """
# Digital Immortality Platform - Environment Variables

# Environment
FLASK_ENV=production
ENVIRONMENT=production

# Security
SECRET_KEY=
ENCRYPTION_KEY=
JWT_SECRET_KEY=
WEBHOOK_SECRET=
SECURITY_PASSWORD_SALT=

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/memory_db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TELEGRAM_BOT_TOKEN=
STRIPE_SECRET_KEY=
SUPABASE_URL=
SUPABASE_KEY=

# CORS Origins (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/hour

# Voice Authentication
VOICE_AUTH_ENABLED=true
VOICE_AUTH_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Monitoring (optional)
SENTRY_DSN=
METRICS_ENABLED=true
"""

def generate_env_template():
    """Generate .env template file"""
    with open('.env.template', 'w') as f:
        f.write(ENV_TEMPLATE)
    print("Generated .env.template file")

# Export configuration
__all__ = [
    'Config',
    'DevelopmentConfig',
    'TestingConfig',
    'ProductionConfig',
    'ConfigManager',
    'setup_logging',
    'create_app',
    'generate_env_template'
]

if __name__ == "__main__":
    # Generate template when run directly
    generate_env_template()
    
    # Test configuration loading
    config = ConfigManager.get_config('production')
    print(f"Loaded {config.ENV} configuration")
    print(f"Database: {config.DATABASE_URL}")
    print(f"Redis: {config.REDIS_URL}")
    print(f"Rate limiting: {config.RATE_LIMIT_ENABLED}")
    print(f"Voice auth: {config.VOICE_AUTH_ENABLED}")