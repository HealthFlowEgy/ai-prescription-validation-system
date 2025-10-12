#!/usr/bin/env python3
"""
Enhanced HealthFlow AI Digital Prescription System v2.1
Production-Ready with Integrated Security & Monitoring

Main Application Entry Point:
- Production-ready JWT authentication
- Comprehensive monitoring and observability
- Centralized error handling
- PostgreSQL with migrations
- Health checks and metrics
- International best practices

Version: 2.1.0
Author: HealthFlow Development Team
License: MIT
"""

import logging
import os
import sys
from datetime import datetime, timezone

# Flask and extensions
from flask import Flask, g, request
from flask_caching import Cache
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate


# Production-ready configuration
from config.production import get_config

# Production services
from services.auth_service import AuthService
from services.monitoring_service import MonitoringService, monitor_request
from utils.error_handlers import register_error_handlers

# Existing services (preserved)
try:
    from services.identity_service import IdentityService
except ImportError as e:
    logging.warning(f"Some services not available: {e}")

# Routes - Production
from routes.auth_routes import auth_bp as production_auth_bp
from routes.health_routes import health_bp

# Routes - Existing (preserved)
try:
    from routes.admin import admin_bp
    from routes.analytics import analytics_bp
    from routes.fhir import fhir_bp
    from routes.prescription import prescription_bp
except ImportError as e:
    logging.warning(f"Some routes not available: {e}")
    prescription_bp = None
    fhir_bp = None
    analytics_bp = None
    admin_bp = None

# Models
from models.database import db
from models.user import User

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================

# Extensions
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()

# Service instances
monitoring_service = None
auth_service = None

# Logger
logger = logging.getLogger(__name__)

# ============================================================================
# APPLICATION FACTORY (PRODUCTION-READY)
# ============================================================================


def create_app(environment: str = None) -> Flask:
    """
    Production-Ready Application Factory

    Features:
    - JWT authentication with bcrypt
    - Sentry error tracking
    - Prometheus metrics
    - PostgreSQL with connection pooling
    - Comprehensive error handling
    - Health checks and readiness probes
    - CORS and security headers
    - Rate limiting
    """

    # Initialize Flask application
    app = Flask(__name__)

    # Load production configuration
    env = environment or os.getenv("FLASK_ENV", "development")
    config_class = get_config(env)
    app.config.from_object(config_class)

    # Setup logging
    setup_logging(app)
    logger.info(f"Starting HealthFlow v2.1 in {env} mode")

    # Initialize database
    init_database(app)

    # Initialize monitoring (Sentry)
    init_monitoring(app)

    # Initialize extensions
    init_extensions(app)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    register_blueprints(app)

    # Setup middleware
    setup_middleware(app)

    # Initialize services
    init_services(app)

    # Store app start time
    app.start_time = datetime.now(timezone.utc)

    logger.info("HealthFlow v2.1 initialized successfully")
    return app


# ============================================================================
# LOGGING SETUP
# ============================================================================


def setup_logging(app: Flask) -> None:
    """Configure production logging"""

    log_level = app.config.get("LOG_LEVEL", "INFO")
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            (
                logging.FileHandler("logs/app.log")
                if os.path.exists("logs")
                else logging.StreamHandler()
            ),
        ],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================


def init_database(app: Flask) -> None:
    """Initialize database with production configuration"""

    try:
        # Initialize SQLAlchemy
        db.init_app(app)
        migrate.init_app(app, db)

        with app.app_context():
            # Test database connection
            db.session.execute("SELECT 1")
            logger.info(
                f"Database connected: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')[:50]}..."
            )

            # Create tables if they don't exist
            db.create_all()
            logger.info("Database tables verified")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# ============================================================================
# MONITORING INITIALIZATION
# ============================================================================


def init_monitoring(app: Flask) -> None:
    """Initialize Sentry and metrics collection"""

    global monitoring_service

    try:
        # Initialize Sentry
        MonitoringService.initialize_sentry(app)

        # Create monitoring service instance
        monitoring_service = MonitoringService()
        app.monitoring_service = monitoring_service

        logger.info("Monitoring initialized successfully")

    except Exception as e:
        logger.warning(f"Monitoring initialization failed: {e}")


# ============================================================================
# EXTENSIONS INITIALIZATION
# ============================================================================


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions"""

    # CORS
    cors_origins = app.config.get("CORS_ORIGINS", ["*"])
    cors.init_app(
        app,
        origins=cors_origins,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        expose_headers=["X-Total-Count", "X-Page-Count"],
        supports_credentials=True,
    )

    # Rate limiting
    limiter.init_app(app)

    # Caching
    cache_config = {
        "CACHE_TYPE": app.config.get("CACHE_TYPE", "simple"),
        "CACHE_DEFAULT_TIMEOUT": app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
    }
    if app.config.get("REDIS_URL"):
        cache_config["CACHE_REDIS_URL"] = app.config["REDIS_URL"]

    cache.init_app(app, config=cache_config)

    logger.info("Extensions initialized")


# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================


def register_blueprints(app: Flask) -> None:
    """Register application blueprints"""

    # Production authentication routes (new)
    app.register_blueprint(production_auth_bp)
    logger.info("Registered: Production Auth Routes")

    # Health check routes (new)
    app.register_blueprint(health_bp)
    logger.info("Registered: Health Check Routes")

    # Existing routes (if available)
    if prescription_bp:
        app.register_blueprint(prescription_bp, url_prefix="/api/v1/prescriptions")
        logger.info("Registered: Prescription Routes")

    if fhir_bp:
        app.register_blueprint(fhir_bp, url_prefix="/fhir/r4")
        logger.info("Registered: FHIR Routes")

    if analytics_bp:
        app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
        logger.info("Registered: Analytics Routes")

    if admin_bp:
        app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")
        logger.info("Registered: Admin Routes")


# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================


def setup_middleware(app: Flask) -> None:
    """Setup request/response middleware"""

    @app.before_request
    @monitor_request
    def before_request_handler():
        """Pre-request processing with monitoring"""
        g.start_time = datetime.now(timezone.utc)
        g.request_id = request.headers.get(
            "X-Request-ID", f"req_{datetime.now().timestamp()}"
        )

        # Log request
        logger.debug(
            f"Request: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"[{g.request_id}]"
        )

    @app.after_request
    def after_request_handler(response):
        """Post-request processing with security headers"""

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Request-ID"] = g.get("request_id", "unknown")

        if app.config.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Calculate request duration
        if hasattr(g, "start_time"):
            duration = (datetime.now(timezone.utc) - g.start_time).total_seconds()
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

        # Log response
        logger.debug(
            f"Response: {response.status_code} for {request.method} {request.path} "
            f"[{g.get('request_id', 'unknown')}]"
        )

        return response

    logger.info("Middleware configured")


# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================


def init_services(app: Flask) -> None:
    """Initialize application services"""

    global auth_service

    try:
        with app.app_context():
            # Initialize auth service
            auth_service = AuthService()
            app.auth_service = auth_service

            # Initialize existing services if available
            try:
                # Identity service
                if "IdentityService" in dir():
                    app.identity_service = IdentityService(
                        config=app.config,
                        security_service=None,  # Use our auth_service instead
                    )

                # Other services...
                logger.info("Legacy services initialized")

            except Exception as e:
                logger.warning(f"Some legacy services not initialized: {e}")

            logger.info("Services initialized successfully")

    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise


# ============================================================================
# CLI COMMANDS
# ============================================================================


def register_cli_commands(app: Flask) -> None:
    """Register CLI commands"""

    @app.cli.command()
    def init_db():
        """Initialize database"""
        db.create_all()
        logger.info("Database initialized")
        print("✅ Database initialized successfully")

    @app.cli.command()
    def create_admin():
        """Create admin user"""
        admin = User(
            name="System Administrator",
            email="admin@healthflow.com",
            role="admin",
            is_active=True,
        )
        admin.password_hash = AuthService.hash_password("Admin123!")

        db.session.add(admin)
        db.session.commit()

        logger.info("Admin user created")
        print("✅ Admin user created: admin@healthflow.com / Admin123!")

    @app.cli.command()
    def test_db():
        """Test database connection"""
        try:
            result = db.session.execute("SELECT 1").scalar()
            print(f"✅ Database connection successful: {result}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

# Create application instance
app = create_app()

# Register CLI commands
register_cli_commands(app)


def main():
    """Main application entry point"""

    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    env = os.getenv("FLASK_ENV", "development")

    logger.info(
        f"Starting HealthFlow v2.1: "
        f"host={host}, port={port}, debug={debug}, env={env}"
    )

    if env == "production":
        logger.info("Production mode: Use Gunicorn")
        logger.info("Command: gunicorn -c gunicorn_config.py 'src.main_integrated:app'")
    else:
        app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
