"""
PostgreSQL database configuration for production
File: src/config/database.py
"""

import os
from typing import Optional


class DatabaseConfig:
    """Database configuration for different environments"""

    @staticmethod
    def get_database_uri(environment: str = None) -> str:
        """
        Get database URI based on environment

        Args:
            environment: Environment name (production, staging, development)

        Returns:
            Database connection URI
        """
        if environment is None:
            environment = os.environ.get("FLASK_ENV", "development")

        if environment == "production":
            return DatabaseConfig._get_production_uri()
        elif environment == "staging":
            return DatabaseConfig._get_staging_uri()
        else:
            return DatabaseConfig._get_development_uri()

    @staticmethod
    def _get_production_uri() -> str:
        """Get production PostgreSQL URI"""
        # Primary: Use DATABASE_URL if provided (for managed services)
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            # Fix for Heroku/some platforms using 'postgres://' instead of 'postgresql://'
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            return database_url

        # Secondary: Build from individual components
        user = os.environ.get("DB_USER", "prescription_user")
        password = os.environ.get("DB_PASSWORD", "")
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        database = os.environ.get("DB_NAME", "prescription_validator_prod")

        if not password:
            raise ValueError("DB_PASSWORD must be set for production database")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    @staticmethod
    def _get_staging_uri() -> str:
        """Get staging PostgreSQL URI"""
        database_url = os.environ.get("STAGING_DATABASE_URL")
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            return database_url

        user = os.environ.get("STAGING_DB_USER", "prescription_user")
        password = os.environ.get("STAGING_DB_PASSWORD", "")
        host = os.environ.get("STAGING_DB_HOST", "localhost")
        port = os.environ.get("STAGING_DB_PORT", "5432")
        database = os.environ.get("STAGING_DB_NAME", "prescription_validator_staging")

        if not password:
            raise ValueError("STAGING_DB_PASSWORD must be set for staging database")

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    @staticmethod
    def _get_development_uri() -> str:
        """Get development database URI (can use SQLite or PostgreSQL)"""
        # Allow developers to use PostgreSQL locally if they want
        dev_database_url = os.environ.get("DEV_DATABASE_URL")
        if dev_database_url:
            return dev_database_url

        # Default to SQLite for local development
        db_path = os.environ.get("DEV_DB_PATH", "data/development.db")
        return f"sqlite:///{db_path}"


class PostgreSQLConfig:
    """PostgreSQL-specific configuration"""

    # Connection pool settings
    SQLALCHEMY_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", 10))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", 30))
    SQLALCHEMY_POOL_RECYCLE = int(os.environ.get("DB_POOL_RECYCLE", 1800))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", 20))

    # Additional PostgreSQL options
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connections before using
        "pool_size": SQLALCHEMY_POOL_SIZE,
        "pool_timeout": SQLALCHEMY_POOL_TIMEOUT,
        "pool_recycle": SQLALCHEMY_POOL_RECYCLE,
        "max_overflow": SQLALCHEMY_MAX_OVERFLOW,
        "connect_args": {"connect_timeout": 10, "options": "-c timezone=utc"},
    }

    @staticmethod
    def get_engine_options(environment: str = None) -> dict:
        """Get SQLAlchemy engine options for the environment"""
        if environment is None:
            environment = os.environ.get("FLASK_ENV", "development")

        if (
            environment == "development"
            and "sqlite" in DatabaseConfig.get_database_uri(environment)
        ):
            # SQLite-specific options
            return {"pool_pre_ping": True, "connect_args": {"check_same_thread": False}}

        # PostgreSQL options for staging/production
        return PostgreSQLConfig.SQLALCHEMY_ENGINE_OPTIONS


# Database URL helper for backwards compatibility
def get_database_url(environment: str = None) -> str:
    """Legacy function for getting database URL"""
    return DatabaseConfig.get_database_uri(environment)
