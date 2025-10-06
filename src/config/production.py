"""
Production configuration with security hardening
File: src/config/production.py
"""

import os
from datetime import timedelta
from config.database import DatabaseConfig, PostgreSQLConfig


class ProductionConfig:
    """Production environment configuration"""
    
    # Flask Core Settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = PostgreSQLConfig.get_engine_options('production')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'prescription_session'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Security Headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    JWT_ALGORITHM = 'HS256'
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'bmp'}
    
    # OCR Configuration
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', '/usr/bin/tesseract')
    OCR_LANGUAGE = os.environ.get('OCR_LANGUAGE', 'eng')
    OCR_CONFIG = '--oem 3 --psm 6'
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Default rate limits (can be overridden per route)
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_LOGIN = "5/minute"
    RATELIMIT_UPLOAD = "10/minute"
    RATELIMIT_API = "1000/hour"
    
    # CORS Configuration
    CORS_ENABLED = True
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_EXPOSE_HEADERS = ['Content-Range', 'X-Content-Range']
    CORS_MAX_AGE = 3600
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', '/app/logs/app.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Monitoring Configuration
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.1'))
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@prescriptionvalidator.com')
    
    # Cache Configuration (Redis)
    CACHE_TYPE = 'redis' if os.environ.get('REDIS_URL') else 'simple'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'prescription_'
    
    # Celery Configuration (for async tasks)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL'))
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL'))
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # Application Specific
    APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
    APP_NAME = 'AI Prescription Validation System'
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'false').lower() == 'true'
    
    # Validation Settings
    VALIDATION_TIMEOUT = int(os.environ.get('VALIDATION_TIMEOUT', 30))  # seconds
    MAX_MEDICATIONS_PER_PRESCRIPTION = int(os.environ.get('MAX_MEDICATIONS_PER_PRESCRIPTION', 20))
    
    # Feature Flags
    FEATURE_VOICE_INPUT = os.environ.get('FEATURE_VOICE_INPUT', 'true').lower() == 'true'
    FEATURE_FHIR_INTEGRATION = os.environ.get('FEATURE_FHIR_INTEGRATION', 'true').lower() == 'true'
    FEATURE_SNOMED_LOOKUP = os.environ.get('FEATURE_SNOMED_LOOKUP', 'true').lower() == 'true'
    
    # External API Configuration
    SNOWSTORM_URL = os.environ.get('SNOWSTORM_URL', 'https://snowstorm.app.evidium.com')
    SNOWSTORM_TIMEOUT = int(os.environ.get('SNOWSTORM_TIMEOUT', 10))
    
    # Security Settings
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Audit Settings
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 365))
    
    # Backup Settings
    BACKUP_ENABLED = os.environ.get('BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_SCHEDULE = os.environ.get('BACKUP_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    @staticmethod
    def validate():
        """Validate that all required production settings are configured"""
        required_vars = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'DATABASE_URL',
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables for production: {', '.join(missing_vars)}"
            )
        
        # Warn about optional but recommended settings
        recommended_vars = [
            'SENTRY_DSN',
            'REDIS_URL',
            'MAIL_SERVER',
        ]
        
        missing_recommended = []
        for var in recommended_vars:
            if not os.environ.get(var):
                missing_recommended.append(var)
        
        if missing_recommended:
            import logging
            logging.warning(
                f"Missing recommended environment variables: {', '.join(missing_recommended)}"
            )
        
        return True


class StagingConfig(ProductionConfig):
    """Staging environment configuration (similar to production but with relaxed settings)"""
    
    ENV = 'staging'
    DEBUG = False
    TESTING = False
    
    # Use staging database
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('staging')
    
    # More verbose logging in staging
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_ECHO = True
    
    # Higher sample rates for monitoring
    SENTRY_TRACES_SAMPLE_RATE = 1.0
    SENTRY_PROFILES_SAMPLE_RATE = 1.0
    
    # Relaxed rate limits for testing
    RATELIMIT_DEFAULT = "1000/hour"
    RATELIMIT_LOGIN = "20/minute"
    RATELIMIT_UPLOAD = "50/minute"


class DevelopmentConfig:
    """Development environment configuration"""
    
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # Use simpler secret for development
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    
    # Database - can use SQLite for local dev
    SQLALCHEMY_DATABASE_URI = DatabaseConfig.get_database_uri('development')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_ENGINE_OPTIONS = PostgreSQLConfig.get_engine_options('development')
    
    # Relaxed security for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 86400  # 1 day
    
    # File uploads
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'bmp'}
    
    # OCR
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', 'tesseract')
    OCR_LANGUAGE = 'eng'
    
    # No rate limiting in development
    RATELIMIT_ENABLED = False
    
    # CORS - allow all in development
    CORS_ENABLED = True
    CORS_ORIGINS = ['*']
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'logs/dev.log'
    
    # No Sentry in development
    SENTRY_DSN = None
    
    # Cache - simple in-memory cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # App version
    APP_VERSION = 'dev'
    APP_NAME = 'AI Prescription Validation System (Development)'
    
    # Feature flags - all enabled in dev
    FEATURE_VOICE_INPUT = True
    FEATURE_FHIR_INTEGRATION = True
    FEATURE_SNOMED_LOOKUP = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(environment=None):
    """Get configuration for specified environment"""
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config.get(environment, config['default'])
    
    # Validate production config
    if environment == 'production':
        config_class.validate()
    
    return config_class
