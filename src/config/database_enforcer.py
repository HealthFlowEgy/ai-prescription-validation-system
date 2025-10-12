"""
Database Configuration Enforcer
Ensures proper database is used in each environment
File: src/config/database_enforcer.py
"""

import logging
import os
import sys
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DatabaseConfigurationError(Exception):
    """Raised when database configuration is invalid for environment"""


class DatabaseEnforcer:
    """
    Enforce database requirements based on environment

    Rules:
    - Production: MUST use PostgreSQL
    - Staging: MUST use PostgreSQL
    - Development: Can use SQLite or PostgreSQL
    - Testing: Can use SQLite or PostgreSQL
    """

    ALLOWED_DATABASES = {
        "production": {"postgresql", "postgres"},
        "staging": {"postgresql", "postgres"},
        "development": {"sqlite", "postgresql", "postgres"},
        "testing": {"sqlite", "postgresql", "postgres"},
    }

    @classmethod
    def validate_database_config(
        cls, database_url: str = None, environment: str = None
    ) -> None:
        """
        Validate database configuration for current environment

        Args:
            database_url: Database URL to validate (default: from DATABASE_URL env var)
            environment: Environment name (default: from FLASK_ENV env var)

        Raises:
            DatabaseConfigurationError: If configuration is invalid
        """
        # Get database URL
        if database_url is None:
            database_url = os.environ.get("DATABASE_URL")

        if not database_url:
            raise DatabaseConfigurationError(
                "DATABASE_URL environment variable is not set. "
                "Please configure your database connection."
            )

        # Get environment
        if environment is None:
            environment = os.environ.get("FLASK_ENV", "production").lower()

        # Parse database URL
        parsed = urlparse(database_url)
        db_scheme = parsed.scheme.lower()

        # Handle special cases
        if db_scheme.startswith("sqlite"):
            db_type = "sqlite"
        elif db_scheme in ("postgresql", "postgres"):
            db_type = "postgresql"
        else:
            db_type = db_scheme

        # Get allowed databases for environment
        allowed = cls.ALLOWED_DATABASES.get(environment, {"postgresql", "postgres"})

        # Validate
        if db_type not in allowed:
            error_msg = (
                f"❌ CRITICAL: Invalid database for {environment} environment!\n"
                f"\n"
                f"Current database: {db_type}\n"
                f"Allowed databases: {', '.join(allowed)}\n"
                f"\n"
                f"{'='*60}\n"
                f"PRODUCTION ENVIRONMENTS REQUIRE POSTGRESQL\n"
                f"{'='*60}\n"
                f"\n"
                f"SQLite is NOT suitable for production because:\n"
                f"  ❌ No concurrent write support\n"
                f"  ❌ No connection pooling\n"
                f"  ❌ No replication\n"
                f"  ❌ File-based (difficult to scale)\n"
                f"  ❌ Limited data types\n"
                f"  ❌ No user management\n"
                f"\n"
                f"To fix this:\n"
                f"  1. Set up PostgreSQL database\n"
                f"  2. Update DATABASE_URL environment variable:\n"
                f"     export DATABASE_URL='postgresql://user:pass@host:5432/dbname'\n"
                f"  3. Run migrations: alembic upgrade head\n"
                f"\n"
                f"For development, set FLASK_ENV=development to use SQLite.\n"
            )

            logger.critical(error_msg)
            raise DatabaseConfigurationError(error_msg)

        # Log success
        logger.info(f"✅ Database configuration valid: {db_type} for {environment}")

    @classmethod
    def get_database_info(cls, database_url: str = None) -> dict:
        """
        Get information about configured database

        Args:
            database_url: Database URL (default: from DATABASE_URL env var)

        Returns:
            Dictionary with database information
        """
        if database_url is None:
            database_url = os.environ.get("DATABASE_URL", "")

        if not database_url:
            return {"type": "none", "configured": False, "production_ready": False}

        parsed = urlparse(database_url)

        # Determine database type
        if parsed.scheme.startswith("sqlite"):
            db_type = "sqlite"
            production_ready = False
        elif parsed.scheme in ("postgresql", "postgres"):
            db_type = "postgresql"
            production_ready = True
        else:
            db_type = parsed.scheme
            production_ready = False

        return {
            "type": db_type,
            "scheme": parsed.scheme,
            "host": parsed.hostname or "file",
            "port": parsed.port,
            "database": parsed.path.lstrip("/") if parsed.path else None,
            "configured": True,
            "production_ready": production_ready,
        }

    @classmethod
    def check_production_readiness(cls) -> dict:
        """
        Check if system is ready for production deployment

        Returns:
            Dictionary with readiness status
        """
        environment = os.environ.get("FLASK_ENV", "production").lower()
        database_url = os.environ.get("DATABASE_URL")

        checks = {
            "environment": environment,
            "database_configured": bool(database_url),
            "database_info": cls.get_database_info(database_url),
            "production_ready": False,
            "issues": [],
        }

        # Check database configuration
        if not database_url:
            checks["issues"].append("DATABASE_URL not configured")
        elif (
            checks["database_info"]["type"] == "sqlite" and environment == "production"
        ):
            checks["issues"].append("SQLite not allowed in production")

        # Check other critical settings
        if not os.environ.get("SECRET_KEY"):
            checks["issues"].append("SECRET_KEY not configured")

        if not os.environ.get("JWT_SECRET_KEY"):
            checks["issues"].append("JWT_SECRET_KEY not configured")

        # Determine overall readiness
        checks["production_ready"] = len(checks["issues"]) == 0

        return checks

    @classmethod
    def enforce_on_startup(cls) -> None:
        """
        Enforce database requirements on application startup

        This should be called early in application initialization.
        Will exit the application if requirements are not met in production.
        """
        try:
            cls.validate_database_config()
            logger.info("✅ Database configuration validated successfully")
        except DatabaseConfigurationError as e:
            # In production, this is fatal
            environment = os.environ.get("FLASK_ENV", "production").lower()
            if environment == "production":
                logger.critical(
                    "FATAL: Cannot start application with invalid database configuration"
                )
                sys.exit(1)
            else:
                # In development, just warn
                logger.warning(str(e))
                logger.warning("Continuing in development mode...")


def validate_database_on_startup():
    """
    Convenience function to validate database on startup
    Call this in your main application initialization
    """
    DatabaseEnforcer.enforce_on_startup()


def get_database_status() -> dict:
    """
    Get current database status

    Returns:
        Dictionary with database status information
    """
    return {
        "info": DatabaseEnforcer.get_database_info(),
        "readiness": DatabaseEnforcer.check_production_readiness(),
    }
