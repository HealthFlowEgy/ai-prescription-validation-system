"""
Security Middleware for Flask Application
Implements security headers, rate limiting, and input validation
"""
import re
from functools import wraps
from flask import request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

logger = logging.getLogger(__name__)


def configure_security_headers(app):
    """
    Configure security headers for all responses.
    
    Implements OWASP security best practices.
    """
    @app.after_request
    def add_security_headers(response):
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Force HTTPS
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # Remove server header
        response.headers.pop('Server', None)
        
        return response
    
    logger.info("Security headers configured")


def configure_rate_limiting(app):
    """
    Configure rate limiting for API endpoints.
    
    Uses Redis for distributed rate limiting.
    """
    # Get user ID from JWT token if available, otherwise use IP
    def get_rate_limit_key():
        if hasattr(g, 'current_user') and g.current_user:
            return f"user:{g.current_user.id}"
        return f"ip:{get_remote_address()}"
    
    limiter = Limiter(
        app=app,
        key_func=get_rate_limit_key,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri=app.config.get('REDIS_URL', 'redis://localhost:6379/1'),
        strategy="fixed-window"
    )
    
    # Custom rate limit exceeded handler
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        logger.warning(f"Rate limit exceeded for {get_rate_limit_key()}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'retry_after': e.description
        }), 429
    
    logger.info("Rate limiting configured")
    
    return limiter


# Rate limit decorators for different endpoint types
def rate_limit_strict(limiter):
    """Strict rate limit for sensitive operations (5/min, 50/hour)."""
    return limiter.limit("5 per minute;50 per hour")


def rate_limit_upload(limiter):
    """Rate limit for file uploads (10/min, 100/hour)."""
    return limiter.limit("10 per minute;100 per hour")


def rate_limit_auth(limiter):
    """Rate limit for authentication endpoints (5/min, 20/hour)."""
    return limiter.limit("5 per minute;20 per hour")


class InputValidator:
    """Input validation utilities."""
    
    # Validation patterns
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'phone': re.compile(r'^\+?1?\d{10,15}$'),
        'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.,]+$'),
    }
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/|xp_|sp_)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(\bAND\b.*=.*\bAND\b)",
        r"('|\"|`)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format."""
        if not email or len(email) > 255:
            return False
        return bool(cls.PATTERNS['email'].match(email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validate phone number format."""
        if not phone:
            return False
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        return bool(cls.PATTERNS['phone'].match(cleaned))
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format."""
        if not uuid_str:
            return False
        return bool(cls.PATTERNS['uuid'].match(str(uuid_str)))
    
    @classmethod
    def sanitize_string(cls, text: str, max_length: int = 1000) -> str:
        """
        Sanitize user input string.
        
        Removes potentially dangerous characters and limits length.
        """
        if not text:
            return ""
        
        # Truncate to max length
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newline and tab
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    @classmethod
    def check_sql_injection(cls, text: str) -> bool:
        """
        Check if text contains SQL injection patterns.
        
        Returns True if suspicious patterns found.
        """
        if not text:
            return False
        
        text_upper = text.upper()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def check_xss(cls, text: str) -> bool:
        """
        Check if text contains XSS patterns.
        
        Returns True if suspicious patterns found.
        """
        if not text:
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def validate_and_sanitize(cls, text: str, max_length: int = 1000) -> str:
        """
        Validate and sanitize user input.
        
        Raises ValueError if malicious patterns detected.
        """
        if cls.check_sql_injection(text):
            raise ValueError("Potential SQL injection detected")
        
        if cls.check_xss(text):
            raise ValueError("Potential XSS attack detected")
        
        return cls.sanitize_string(text, max_length)


def validate_request_data(required_fields=None, optional_fields=None):
    """
    Decorator to validate request JSON data.
    
    Usage:
        @validate_request_data(required_fields=['name', 'email'])
        def create_user():
            data = request.json
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.json
            if not data:
                return jsonify({'error': 'Request body is empty'}), 400
            
            # Check required fields
            if required_fields:
                missing = [field for field in required_fields if field not in data]
                if missing:
                    return jsonify({
                        'error': 'Missing required fields',
                        'missing_fields': missing
                    }), 400
            
            # Validate and sanitize all string fields
            for key, value in data.items():
                if isinstance(value, str):
                    try:
                        data[key] = InputValidator.validate_and_sanitize(value)
                    except ValueError as e:
                        return jsonify({
                            'error': 'Invalid input',
                            'field': key,
                            'message': str(e)
                        }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_https(f):
    """Decorator to require HTTPS for sensitive endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
            return jsonify({'error': 'HTTPS required'}), 403
        return f(*args, **kwargs)
    return decorated_function

