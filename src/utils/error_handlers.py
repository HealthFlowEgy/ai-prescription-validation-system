"""
Centralized error handling for production
File: src/utils/error_handlers.py
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from datetime import datetime
import logging
import traceback
from services.monitoring_service import MonitoringService


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors"""
    
    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'API_ERROR'
        self.details = details or {}
    
    def to_dict(self):
        return {
            'status': 'error',
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': datetime.utcnow().isoformat()
        }


class ValidationError(APIError):
    """Validation error"""
    
    def __init__(self, message, details=None):
        super().__init__(message, status_code=400, error_code='VALIDATION_ERROR', details=details)


class AuthenticationError(APIError):
    """Authentication error"""
    
    def __init__(self, message='Authentication required', details=None):
        super().__init__(message, status_code=401, error_code='AUTHENTICATION_ERROR', details=details)


class AuthorizationError(APIError):
    """Authorization error"""
    
    def __init__(self, message='Insufficient permissions', details=None):
        super().__init__(message, status_code=403, error_code='AUTHORIZATION_ERROR', details=details)


class NotFoundError(APIError):
    """Resource not found error"""
    
    def __init__(self, resource='Resource', resource_id=None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, status_code=404, error_code='NOT_FOUND')


class ConflictError(APIError):
    """Resource conflict error"""
    
    def __init__(self, message='Resource conflict', details=None):
        super().__init__(message, status_code=409, error_code='CONFLICT_ERROR', details=details)


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    
    def __init__(self, message='Rate limit exceeded', retry_after=None):
        details = {'retry_after': retry_after} if retry_after else {}
        super().__init__(message, status_code=429, error_code='RATE_LIMIT_EXCEEDED', details=details)


class ServiceUnavailableError(APIError):
    """Service unavailable error"""
    
    def __init__(self, message='Service temporarily unavailable', details=None):
        super().__init__(message, status_code=503, error_code='SERVICE_UNAVAILABLE', details=details)


class DatabaseError(APIError):
    """Database operation error"""
    
    def __init__(self, message='Database operation failed', details=None):
        super().__init__(message, status_code=500, error_code='DATABASE_ERROR', details=details)


def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors"""
        response = error.to_dict()
        
        # Log the error
        logger.warning(
            f"API Error: {error.error_code} - {error.message}",
            extra={
                'error_code': error.error_code,
                'status_code': error.status_code,
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            }
        )
        
        return jsonify(response), error.status_code
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request"""
        return jsonify({
            'status': 'error',
            'message': 'Bad request',
            'error_code': 'BAD_REQUEST',
            'details': str(error.description) if hasattr(error, 'description') else str(error),
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized"""
        return jsonify({
            'status': 'error',
            'message': 'Authentication required',
            'error_code': 'UNAUTHORIZED',
            'timestamp': datetime.utcnow().isoformat()
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden"""
        return jsonify({
            'status': 'error',
            'message': 'Access forbidden',
            'error_code': 'FORBIDDEN',
            'timestamp': datetime.utcnow().isoformat()
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found"""
        return jsonify({
            'status': 'error',
            'message': 'Resource not found',
            'error_code': 'NOT_FOUND',
            'path': request.path,
            'timestamp': datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed"""
        return jsonify({
            'status': 'error',
            'message': f'Method {request.method} not allowed for this endpoint',
            'error_code': 'METHOD_NOT_ALLOWED',
            'allowed_methods': error.valid_methods if hasattr(error, 'valid_methods') else [],
            'timestamp': datetime.utcnow().isoformat()
        }), 405
    
    @app.errorhandler(413)
    def handle_request_entity_too_large(error):
        """Handle 413 Request Entity Too Large"""
        max_size_mb = app.config.get('MAX_CONTENT_LENGTH', 16777216) / (1024 * 1024)
        return jsonify({
            'status': 'error',
            'message': f'Request entity too large. Maximum size is {max_size_mb:.1f}MB',
            'error_code': 'REQUEST_TOO_LARGE',
            'max_size_bytes': app.config.get('MAX_CONTENT_LENGTH', 16777216),
            'timestamp': datetime.utcnow().isoformat()
        }), 413
    
    @app.errorhandler(415)
    def handle_unsupported_media_type(error):
        """Handle 415 Unsupported Media Type"""
        return jsonify({
            'status': 'error',
            'message': 'Unsupported media type',
            'error_code': 'UNSUPPORTED_MEDIA_TYPE',
            'timestamp': datetime.utcnow().isoformat()
        }), 415
    
    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        """Handle 429 Too Many Requests"""
        return jsonify({
            'status': 'error',
            'message': 'Rate limit exceeded',
            'error_code': 'RATE_LIMIT_EXCEEDED',
            'timestamp': datetime.utcnow().isoformat()
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle 500 Internal Server Error"""
        # Log the full error with traceback
        logger.error(
            'Internal server error occurred',
            exc_info=True,
            extra={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr
            }
        )
        
        # Capture in Sentry
        MonitoringService.capture_exception(error, {
            'request': {
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            }
        })
        
        # Don't expose internal error details in production
        response = {
            'status': 'error',
            'message': 'An internal server error occurred',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Include error details only in development
        if app.config.get('DEBUG'):
            response['details'] = str(error)
            response['traceback'] = traceback.format_exc()
        
        return jsonify(response), 500
    
    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle 503 Service Unavailable"""
        return jsonify({
            'status': 'error',
            'message': 'Service temporarily unavailable',
            'error_code': 'SERVICE_UNAVAILABLE',
            'timestamp': datetime.utcnow().isoformat()
        }), 503
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle generic HTTP exceptions"""
        return jsonify({
            'status': 'error',
            'message': error.description or 'HTTP error occurred',
            'error_code': f'HTTP_{error.code}',
            'timestamp': datetime.utcnow().isoformat()
        }), error.code
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """Handle database integrity errors"""
        logger.error(f"Database integrity error: {str(error)}", exc_info=True)
        
        # Parse common integrity errors
        error_message = 'Database integrity constraint violated'
        if 'unique constraint' in str(error).lower():
            error_message = 'A record with this value already exists'
        elif 'foreign key constraint' in str(error).lower():
            error_message = 'Referenced record does not exist'
        elif 'not null constraint' in str(error).lower():
            error_message = 'Required field is missing'
        
        return jsonify({
            'status': 'error',
            'message': error_message,
            'error_code': 'DATABASE_INTEGRITY_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(OperationalError)
    def handle_operational_error(error):
        """Handle database operational errors"""
        logger.error(f"Database operational error: {str(error)}", exc_info=True)
        
        # Capture in Sentry
        MonitoringService.capture_exception(error, {
            'error_type': 'database_operational_error',
            'request': {
                'endpoint': request.endpoint,
                'method': request.method
            }
        })
        
        return jsonify({
            'status': 'error',
            'message': 'Database connection error. Please try again.',
            'error_code': 'DATABASE_CONNECTION_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 503
    
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        """Handle generic SQLAlchemy errors"""
        logger.error(f"Database error: {str(error)}", exc_info=True)
        
        # Capture in Sentry
        MonitoringService.capture_exception(error, {
            'error_type': 'sqlalchemy_error',
            'request': {
                'endpoint': request.endpoint,
                'method': request.method
            }
        })
        
        return jsonify({
            'status': 'error',
            'message': 'A database error occurred',
            'error_code': 'DATABASE_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.critical(
            f'Unexpected error: {type(error).__name__}',
            exc_info=True,
            extra={
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr
            }
        )
        
        # Capture in Sentry
        MonitoringService.capture_exception(error, {
            'error_type': 'unexpected_error',
            'request': {
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            }
        })
        
        response = {
            'status': 'error',
            'message': 'An unexpected error occurred',
            'error_code': 'UNEXPECTED_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Include error details only in development
        if app.config.get('DEBUG'):
            response['error_type'] = type(error).__name__
            response['details'] = str(error)
            response['traceback'] = traceback.format_exc()
        
        return jsonify(response), 500
    
    # Request validation errors
    @app.before_request
    def check_maintenance_mode():
        """Check if application is in maintenance mode"""
        if app.config.get('MAINTENANCE_MODE', False):
            # Allow health checks during maintenance
            if request.path in ['/api/health', '/api/liveness', '/api/readiness']:
                return None
            
            return jsonify({
                'status': 'error',
                'message': 'System is currently under maintenance. Please try again later.',
                'error_code': 'MAINTENANCE_MODE',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    
    # After request logging
    @app.after_request
    def log_response(response):
        """Log response details"""
        if request.endpoint and not request.endpoint.startswith('static'):
            logger.info(
                f"{request.method} {request.path} - {response.status_code}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'endpoint': request.endpoint,
                    'remote_addr': request.remote_addr
                }
            )
        return response
    
    logger.info("Error handlers registered successfully")


def create_error_response(message, error_code, status_code=400, **kwargs):
    """
    Helper function to create consistent error responses
    
    Args:
        message: Error message
        error_code: Error code
        status_code: HTTP status code
        **kwargs: Additional fields to include in response
    
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'status': 'error',
        'message': message,
        'error_code': error_code,
        'timestamp': datetime.utcnow().isoformat()
    }
    response.update(kwargs)
    
    return jsonify(response), status_code


def create_success_response(data=None, message=None, **kwargs):
    """
    Helper function to create consistent success responses
    
    Args:
        data: Response data
        message: Success message
        **kwargs: Additional fields to include in response
    
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'status': 'success',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    response.update(kwargs)
    
    return jsonify(response), 200
