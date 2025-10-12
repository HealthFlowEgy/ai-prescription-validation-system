#!/usr/bin/env python3
"""
Enhanced HealthFlow Configuration Management
International Best Practices Implementation

Configuration System:
- Multi-environment support (development, staging, production)
- Security-first configuration
- Environment variable integration
- Validation and type checking
- International compliance settings

Version: 2.0.0
"""

import os
import secrets
from datetime import timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseSettings, Field, validator
from pydantic_settings import SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration with common settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ========================================================================
    # APPLICATION SETTINGS
    # ========================================================================

    APP_NAME: str = Field(default="Enhanced HealthFlow", description="Application name")
    APP_VERSION: str = Field(default="2.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=False, description="Debug mode")
    TESTING: bool = Field(default=False, description="Testing mode")

    # ========================================================================
    # SECURITY SETTINGS
    # ========================================================================

    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = Field(default=timedelta(hours=1))
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = Field(default=timedelta(days=30))

    # Encryption
    ENCRYPTION_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    PASSWORD_SALT_ROUNDS: int = Field(default=12, description="BCrypt salt rounds")

    # Session management
    SESSION_TIMEOUT: int = Field(default=3600, description="Session timeout in seconds")
    PERMANENT_SESSION_LIFETIME: timedelta = Field(default=timedelta(hours=8))

    # ========================================================================
    # DATABASE SETTINGS
    # ========================================================================

    DATABASE_URL: str = Field(
        default="postgresql://healthflow:healthflow@localhost:5432/healthflow",
        description="Primary database URL",
    )
    DATABASE_POOL_SIZE: int = Field(
        default=20, description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=30, description="Database max overflow connections"
    )
    DATABASE_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout")
    DATABASE_POOL_RECYCLE: int = Field(
        default=3600, description="Database pool recycle time"
    )

    # Read replica (for analytics)
    DATABASE_REPLICA_URL: Optional[str] = Field(
        default=None, description="Read replica database URL"
    )

    # ========================================================================
    # REDIS SETTINGS
    # ========================================================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    REDIS_CACHE_DB: int = Field(default=1, description="Redis cache database")
    REDIS_SESSION_DB: int = Field(default=2, description="Redis session database")
    REDIS_CELERY_DB: int = Field(default=3, description="Redis Celery database")

    # ========================================================================
    # EXTERNAL SERVICES
    # ========================================================================

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_API_BASE: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API base URL"
    )
    AI_MODEL: str = Field(default="gpt-4", description="AI model to use")
    AI_MAX_TOKENS: int = Field(default=2000, description="Maximum AI response tokens")
    AI_TEMPERATURE: float = Field(default=0.1, description="AI temperature setting")

    # FHIR Server
    FHIR_SERVER_URL: str = Field(
        default="http://localhost:8080/fhir", description="FHIR R4 server URL"
    )
    FHIR_CLIENT_ID: str = Field(default="", description="FHIR client ID")
    FHIR_CLIENT_SECRET: str = Field(default="", description="FHIR client secret")

    # ========================================================================
    # INTERNATIONAL INTEGRATION
    # ========================================================================

    # Estonia X-Road Integration
    XROAD_SECURITY_SERVER: str = Field(
        default="", description="X-Road security server URL"
    )
    XROAD_CLIENT_ID: str = Field(default="", description="X-Road client identifier")
    XROAD_SERVICE_ID: str = Field(default="", description="X-Road service identifier")

    # NHS CIS2 Integration
    NHS_CIS2_ENDPOINT: str = Field(
        default="", description="NHS CIS2 authentication endpoint"
    )
    NHS_CIS2_CLIENT_ID: str = Field(default="", description="NHS CIS2 client ID")
    NHS_CIS2_CLIENT_SECRET: str = Field(
        default="", description="NHS CIS2 client secret"
    )

    # Netherlands MedCom Integration
    MEDCOM_ENDPOINT: str = Field(default="", description="MedCom service endpoint")
    MEDCOM_API_KEY: str = Field(default="", description="MedCom API key")

    # Egyptian Health Services
    UHIS_ENDPOINT: str = Field(
        default="", description="Universal Health Insurance System endpoint"
    )
    UHIS_API_KEY: str = Field(default="", description="UHIS API key")
    MEDICAL_SYNDICATE_API: str = Field(
        default="", description="Egyptian Medical Syndicate API"
    )

    # ========================================================================
    # EMAIL SETTINGS
    # ========================================================================

    MAIL_SERVER: str = Field(default="localhost", description="SMTP server")
    MAIL_PORT: int = Field(default=587, description="SMTP port")
    MAIL_USE_TLS: bool = Field(default=True, description="Use TLS for email")
    MAIL_USE_SSL: bool = Field(default=False, description="Use SSL for email")
    MAIL_USERNAME: str = Field(default="", description="SMTP username")
    MAIL_PASSWORD: str = Field(default="", description="SMTP password")
    MAIL_DEFAULT_SENDER: str = Field(
        default="noreply@healthflow.egypt.gov", description="Default email sender"
    )

    # ========================================================================
    # FILE STORAGE
    # ========================================================================

    UPLOAD_FOLDER: str = Field(default="uploads", description="File upload directory")
    MAX_CONTENT_LENGTH: int = Field(
        default=16 * 1024 * 1024, description="Max file size (16MB)"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=["pdf", "png", "jpg", "jpeg", "gif", "doc", "docx"],
        description="Allowed file extensions",
    )

    # Cloud storage (optional)
    AWS_ACCESS_KEY_ID: str = Field(default="", description="AWS access key")
    AWS_SECRET_ACCESS_KEY: str = Field(default="", description="AWS secret key")
    AWS_S3_BUCKET: str = Field(default="", description="AWS S3 bucket name")
    AWS_S3_REGION: str = Field(default="us-east-1", description="AWS S3 region")

    # ========================================================================
    # MONITORING & LOGGING
    # ========================================================================

    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    LOG_FILE: str = Field(default="logs/healthflow.log", description="Log file path")
    LOG_MAX_BYTES: int = Field(default=10485760, description="Max log file size (10MB)")
    LOG_BACKUP_COUNT: int = Field(default=5, description="Number of log backups")

    # Sentry (Error tracking)
    SENTRY_DSN: str = Field(default="", description="Sentry DSN for error tracking")

    # Prometheus metrics
    METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    RATELIMIT_STORAGE_URL: str = Field(default="redis://localhost:6379/4")
    RATELIMIT_DEFAULT: str = Field(
        default="1000 per hour", description="Default rate limit"
    )
    RATELIMIT_HEADERS_ENABLED: bool = Field(default=True)

    # API-specific rate limits
    API_RATE_LIMIT: str = Field(default="100 per minute", description="API rate limit")
    AUTH_RATE_LIMIT: str = Field(
        default="5 per minute", description="Authentication rate limit"
    )
    UPLOAD_RATE_LIMIT: str = Field(
        default="10 per minute", description="File upload rate limit"
    )

    # ========================================================================
    # CACHING
    # ========================================================================

    CACHE_TYPE: str = Field(default="redis", description="Cache backend type")
    CACHE_DEFAULT_TIMEOUT: int = Field(default=300, description="Default cache timeout")
    CACHE_KEY_PREFIX: str = Field(default="healthflow:", description="Cache key prefix")

    # ========================================================================
    # CELERY TASK QUEUE
    # ========================================================================

    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/3")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/3")
    CELERY_TASK_SERIALIZER: str = Field(default="json")
    CELERY_RESULT_SERIALIZER: str = Field(default="json")
    CELERY_ACCEPT_CONTENT: List[str] = Field(default=["json"])
    CELERY_TIMEZONE: str = Field(default="Africa/Cairo")
    CELERY_ENABLE_UTC: bool = Field(default=True)

    # ========================================================================
    # INTERNATIONALIZATION
    # ========================================================================

    LANGUAGES: Dict[str, str] = Field(
        default={"en": "English", "ar": "العربية", "fr": "Français"},
        description="Supported languages",
    )
    DEFAULT_LANGUAGE: str = Field(default="en", description="Default language")
    BABEL_DEFAULT_LOCALE: str = Field(default="en", description="Babel default locale")
    BABEL_DEFAULT_TIMEZONE: str = Field(
        default="Africa/Cairo", description="Default timezone"
    )

    # ========================================================================
    # CORS SETTINGS
    # ========================================================================

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://healthflow.egypt.gov"],
        description="Allowed CORS origins",
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization", "X-Requested-With"],
        description="Allowed CORS headers",
    )

    # ========================================================================
    # HEALTH CHECKS
    # ========================================================================

    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Enable health checks")
    HEALTH_CHECK_TIMEOUT: int = Field(default=30, description="Health check timeout")

    # ========================================================================
    # COMPLIANCE & AUDIT
    # ========================================================================

    AUDIT_ENABLED: bool = Field(default=True, description="Enable audit logging")
    AUDIT_RETENTION_DAYS: int = Field(
        default=2555, description="Audit log retention (7 years)"
    )
    GDPR_COMPLIANCE: bool = Field(default=True, description="GDPR compliance mode")
    HIPAA_COMPLIANCE: bool = Field(default=True, description="HIPAA compliance mode")

    # Data retention
    DATA_RETENTION_DAYS: int = Field(
        default=2555, description="Data retention period (7 years)"
    )
    BACKUP_RETENTION_DAYS: int = Field(
        default=90, description="Backup retention period"
    )

    # ========================================================================
    # VALIDATORS
    # ========================================================================

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v.startswith(("postgresql://", "sqlite:///")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")
        return v

    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a valid Redis URL")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    @validator("AI_TEMPERATURE")
    def validate_ai_temperature(cls, v):
        """Validate AI temperature range"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("AI_TEMPERATURE must be between 0.0 and 2.0")
        return v

    @validator("PASSWORD_SALT_ROUNDS")
    def validate_salt_rounds(cls, v):
        """Validate BCrypt salt rounds"""
        if not 10 <= v <= 15:
            raise ValueError("PASSWORD_SALT_ROUNDS must be between 10 and 15")
        return v


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    TESTING: bool = False

    # Development database
    DATABASE_URL: str = (
        "postgresql://healthflow:healthflow@localhost:5432/healthflow_dev"
    )

    # Relaxed security for development
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=24)
    SESSION_TIMEOUT: int = 86400  # 24 hours

    # Development-specific settings
    MAIL_SUPPRESS_SEND: bool = True
    WTF_CSRF_ENABLED: bool = False

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # CORS - allow all origins in development
    CORS_ORIGINS: List[str] = ["*"]


class TestingConfig(BaseConfig):
    """Testing environment configuration"""

    ENVIRONMENT: str = "testing"
    DEBUG: bool = False
    TESTING: bool = True

    # In-memory database for testing
    DATABASE_URL: str = "sqlite:///:memory:"

    # Disable external services in testing
    MAIL_SUPPRESS_SEND: bool = True
    WTF_CSRF_ENABLED: bool = False
    CELERY_TASK_ALWAYS_EAGER: bool = True

    # Fast password hashing for tests
    PASSWORD_SALT_ROUNDS: int = 4

    # Disable rate limiting in tests
    RATELIMIT_ENABLED: bool = False

    # Logging
    LOG_LEVEL: str = "WARNING"


class StagingConfig(BaseConfig):
    """Staging environment configuration"""

    ENVIRONMENT: str = "staging"
    DEBUG: bool = False
    TESTING: bool = False

    # Staging database
    DATABASE_URL: str = Field(
        default="postgresql://healthflow:healthflow@localhost:5432/healthflow_staging"
    )

    # Production-like security
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
    SESSION_TIMEOUT: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    # Limited CORS origins
    CORS_ORIGINS: List[str] = [
        "https://staging.healthflow.egypt.gov",
        "https://staging-api.healthflow.egypt.gov",
    ]


class ProductionConfig(BaseConfig):
    """Production environment configuration"""

    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    TESTING: bool = False

    # Production database (must be set via environment variables)
    DATABASE_URL: str = Field(default="", description="Production database URL")

    # Strict security settings
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(minutes=30)
    SESSION_TIMEOUT: int = 1800  # 30 minutes

    # Production logging
    LOG_LEVEL: str = "WARNING"

    # Strict CORS
    CORS_ORIGINS: List[str] = [
        "https://healthflow.egypt.gov",
        "https://api.healthflow.egypt.gov",
    ]

    # Enable all monitoring
    METRICS_ENABLED: bool = True
    AUDIT_ENABLED: bool = True

    # Production-specific validators
    @validator("DATABASE_URL")
    def validate_production_database(cls, v):
        """Ensure production database is properly configured"""
        if not v or v == "":
            raise ValueError("DATABASE_URL must be set in production")
        if "localhost" in v:
            raise ValueError("Production DATABASE_URL cannot use localhost")
        return v

    @validator("SECRET_KEY")
    def validate_production_secret(cls, v):
        """Ensure production secret key is secure"""
        if len(v) < 32:
            raise ValueError("Production SECRET_KEY must be at least 32 characters")
        return v


# ============================================================================
# CONFIGURATION FACTORY
# ============================================================================

config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}


def get_config(environment: str = None) -> BaseConfig:
    """
    Get configuration instance based on environment

    Args:
        environment: Environment name (development, testing, staging, production)

    Returns:
        Configuration instance
    """

    if environment is None:
        environment = os.getenv("FLASK_ENV", "development")

    config_class = config_map.get(environment, DevelopmentConfig)
    return config_class()


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================


def validate_config(config: BaseConfig) -> List[str]:
    """
    Validate configuration and return list of issues

    Args:
        config: Configuration instance to validate

    Returns:
        List of validation issues (empty if valid)
    """

    issues = []

    # Check required production settings
    if config.ENVIRONMENT == "production":
        required_fields = [
            "DATABASE_URL",
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "ENCRYPTION_KEY",
        ]

        for field in required_fields:
            if not getattr(config, field, None):
                issues.append(f"Production environment requires {field}")

    # Check database connectivity
    try:
        parsed_db = urlparse(config.DATABASE_URL)
        if not parsed_db.scheme:
            issues.append("Invalid DATABASE_URL format")
    except Exception as e:
        issues.append(f"DATABASE_URL validation failed: {str(e)}")

    # Check Redis connectivity
    try:
        parsed_redis = urlparse(config.REDIS_URL)
        if not parsed_redis.scheme:
            issues.append("Invalid REDIS_URL format")
    except Exception as e:
        issues.append(f"REDIS_URL validation failed: {str(e)}")

    return issues


# ============================================================================
# EXPORT CONFIGURATION
# ============================================================================

# Default configuration instance
Config = get_config()

__all__ = [
    "BaseConfig",
    "DevelopmentConfig",
    "TestingConfig",
    "StagingConfig",
    "ProductionConfig",
    "get_config",
    "validate_config",
    "Config",
]
