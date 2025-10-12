"""
Simplified production configuration
"""

import os
from datetime import timedelta


class ProductionConfig:
    """Production environment configuration"""

    # Flask Core Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = False
    TESTING = False
    ENV = "production"

    # Database - will be set at runtime
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///data/production.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Sentry
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # App Info
    APP_VERSION = os.environ.get("APP_VERSION", "2.1.0")
    APP_NAME = "AI Prescription Validation System"


class DevelopmentConfig:
    """Development environment configuration"""

    DEBUG = True
    TESTING = False
    ENV = "development"

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///data/development.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True

    JWT_ACCESS_TOKEN_EXPIRES = 3600
    JWT_REFRESH_TOKEN_EXPIRES = 86400

    CORS_ORIGINS = ["*"]
    LOG_LEVEL = "DEBUG"
    SENTRY_DSN = None

    APP_VERSION = "dev"
    APP_NAME = "AI Prescription Validation System (Development)"


def get_config(environment=None):
    """Get configuration for specified environment"""
    if environment is None:
        environment = os.environ.get("FLASK_ENV", "development")

    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "default": DevelopmentConfig,
    }

    return configs.get(environment, DevelopmentConfig)
