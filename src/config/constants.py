"""
Configuration constants to replace magic numbers throughout codebase.
All hardcoded values should reference these constants.
"""

from datetime import timedelta


class SecurityConstants:
    """Security-related constants."""

    # Password requirements
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_MIN_UPPERCASE = 1
    PASSWORD_MIN_LOWERCASE = 1
    PASSWORD_MIN_DIGITS = 1
    PASSWORD_MIN_SPECIAL = 1

    # Authentication
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)
    JWT_ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRY = timedelta(days=7)
    JWT_ALGORITHM = "HS256"

    # MFA
    MFA_TOKEN_LENGTH = 6
    MFA_TOKEN_VALIDITY_WINDOW = 1  # 30 seconds on each side
    MFA_BACKUP_CODE_COUNT = 10
    MFA_BACKUP_CODE_LENGTH = 8

    # Session
    SESSION_TIMEOUT = timedelta(minutes=30)
    SESSION_REFRESH_THRESHOLD = timedelta(minutes=5)

    # Rate Limiting
    RATE_LIMIT_LOGIN = "5 per minute"
    RATE_LIMIT_API = "100 per hour"
    RATE_LIMIT_UPLOAD = "10 per hour"


class DatabaseConstants:
    """Database-related constants."""

    # Connection Pool
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 10
    DB_POOL_TIMEOUT = 30  # seconds
    DB_POOL_RECYCLE = 3600  # 1 hour

    # Query Limits
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MAX_QUERY_RESULTS = 10000

    # Timeouts
    QUERY_TIMEOUT = 30  # seconds
    TRANSACTION_TIMEOUT = 60  # seconds

    # Retry
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_FACTOR = 2
    RETRY_MAX_DELAY = 32  # seconds


class CacheConstants:
    """Cache-related constants."""

    # TTL (Time To Live)
    CACHE_TTL_SHORT = 300  # 5 minutes
    CACHE_TTL_MEDIUM = 3600  # 1 hour
    CACHE_TTL_LONG = 86400  # 24 hours

    # Redis
    REDIS_MAX_CONNECTIONS = 50
    REDIS_SOCKET_TIMEOUT = 5  # seconds
    REDIS_SOCKET_CONNECT_TIMEOUT = 5  # seconds


class FileConstants:
    """File upload constants."""

    # File Size Limits (bytes)
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_UPLOAD_SIZE_ADMIN = 50 * 1024 * 1024  # 50 MB

    # Allowed Extensions
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx"}
    ALLOWED_ALL_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

    # Image Processing
    MAX_IMAGE_DIMENSION = 4096  # pixels
    THUMBNAIL_SIZE = (200, 200)  # pixels
    COMPRESSION_QUALITY = 85  # 0-100


class ValidationConstants:
    """Validation constants."""

    # Prescription Validation
    MIN_CONFIDENCE_THRESHOLD = 0.85
    HIGH_CONFIDENCE_THRESHOLD = 0.95
    AUTO_APPROVE_THRESHOLD = 0.90

    # Text Length Limits
    MAX_MEDICATION_NAME_LENGTH = 255
    MAX_DIAGNOSIS_LENGTH = 500
    MAX_NOTES_LENGTH = 2000
    MAX_EMAIL_LENGTH = 255
    MAX_PHONE_LENGTH = 20

    # Numeric Limits
    MIN_AGE = 0
    MAX_AGE = 150
    MIN_DOSAGE = 0.01
    MAX_DOSAGE = 10000


class APIConstants:
    """API-related constants."""

    # Timeouts
    EXTERNAL_API_TIMEOUT = 10  # seconds
    LONG_RUNNING_API_TIMEOUT = 60  # seconds

    # Retry
    API_MAX_RETRIES = 3
    API_RETRY_DELAY = 1  # seconds
    API_RETRY_BACKOFF = 2

    # Pagination
    DEFAULT_API_PAGE_SIZE = 20
    MAX_API_PAGE_SIZE = 100


class MonitoringConstants:
    """Monitoring and observability constants."""

    # Tracing
    TRACE_SAMPLE_RATE = 0.1  # 10% sampling
    TRACE_RETENTION_DAYS = 7

    # Metrics
    METRICS_SCRAPE_INTERVAL = 15  # seconds
    METRICS_RETENTION_DAYS = 30

    # Logging
    LOG_ROTATION_SIZE = 100 * 1024 * 1024  # 100 MB
    LOG_RETENTION_DAYS = 30
    AUDIT_LOG_RETENTION_DAYS = 2555  # 7 years for HIPAA

    # Health Checks
    HEALTH_CHECK_INTERVAL = 10  # seconds
    HEALTH_CHECK_TIMEOUT = 5  # seconds


class CeleryConstants:
    """Celery task constants."""

    # Task Timeouts
    TASK_SOFT_TIME_LIMIT = 300  # 5 minutes
    TASK_HARD_TIME_LIMIT = 600  # 10 minutes

    # Retry
    TASK_MAX_RETRIES = 3
    TASK_RETRY_BACKOFF = True
    TASK_RETRY_BACKOFF_MAX = 600  # seconds
    TASK_RETRY_JITTER = True

    # Queue Limits
    MAX_QUEUE_LENGTH = 10000
    QUEUE_ALERT_THRESHOLD = 5000
