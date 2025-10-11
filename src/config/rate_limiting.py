"""
Rate Limiting Configuration
File: src/config/rate_limiting.py
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import logging

logger = logging.getLogger(__name__)


def get_redis_client():
    """
    Get Redis client for rate limiting storage
    
    Returns:
        Redis client or None if not available
    """
    redis_url = os.environ.get('REDIS_URL')
    
    if not redis_url:
        logger.warning("REDIS_URL not configured. Using in-memory rate limiting.")
        return None
    
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        logger.info("Redis connected for rate limiting")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def init_rate_limiter(app):
    """
    Initialize rate limiter for Flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        Limiter instance
    """
    redis_client = get_redis_client()
    
    if redis_client:
        # Use Redis for distributed rate limiting
        storage_uri = os.environ.get('REDIS_URL')
        logger.info("Using Redis for rate limiting storage")
    else:
        # Fall back to in-memory storage (not recommended for production)
        storage_uri = "memory://"
        logger.warning("Using in-memory rate limiting (not recommended for production)")
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=[
            "1000 per day",   # Global limit per IP
            "200 per hour"    # Global limit per IP
        ],
        strategy="fixed-window-elastic-expiry",
        headers_enabled=True,
        swallow_errors=True  # Don't crash app if rate limiting fails
    )
    
    logger.info("Rate limiter initialized")
    return limiter


# Rate limit configurations for different endpoint types
RATE_LIMITS = {
    # Authentication endpoints (stricter limits)
    'auth_login': "5 per minute",
    'auth_register': "3 per minute",
    'auth_refresh': "10 per minute",
    'auth_logout': "10 per minute",
    'auth_password_reset': "3 per hour",
    'auth_password_change': "5 per hour",
    
    # API endpoints (moderate limits)
    'api_read': "100 per minute",
    'api_write': "30 per minute",
    'api_upload': "10 per minute",
    
    # Health checks (lenient limits)
    'health_check': "60 per minute",
    
    # Admin endpoints (moderate limits)
    'admin_read': "50 per minute",
    'admin_write': "20 per minute",
}


def get_rate_limit(endpoint_type: str) -> str:
    """
    Get rate limit for specific endpoint type
    
    Args:
        endpoint_type: Type of endpoint
        
    Returns:
        Rate limit string (e.g., "5 per minute")
    """
    return RATE_LIMITS.get(endpoint_type, "60 per minute")


# Decorator for custom rate limiting
def rate_limit(limit: str):
    """
    Custom rate limit decorator
    
    Args:
        limit: Rate limit string (e.g., "5 per minute")
        
    Returns:
        Decorator function
    """
    def decorator(f):
        # This will be applied by Flask-Limiter
        f._rate_limit = limit
        return f
    return decorator
