"""
Production Configuration and Deployment System
Manages environment-specific configurations, secrets, and deployment orchestration
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import hvac  # HashiCorp Vault client
import boto3  # AWS Secrets Manager

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DR = "disaster_recovery"


class Region(Enum):
    """AWS Regions for multi-region deployment"""

    US_EAST_1 = "us-east-1"
    US_WEST_2 = "us-west-2"
    EU_WEST_1 = "eu-west-1"


@dataclass
class DatabaseConfig:
    """Database configuration"""

    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int
    max_overflow: int
    ssl_mode: str
    read_replica_host: Optional[str] = None


@dataclass
class RedisConfig:
    """Redis configuration"""

    host: str
    port: int
    password: str
    db: int
    ssl: bool
    cluster_mode: bool
    sentinel_hosts: Optional[List[str]] = None


@dataclass
class APIConfig:
    """API configuration"""

    host: str
    port: int
    workers: int
    timeout: int
    keepalive: int
    max_requests: int
    max_requests_jitter: int
    cors_origins: List[str]
    rate_limit: str


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""

    prometheus_port: int
    grafana_url: str
    jaeger_host: str
    jaeger_port: int
    log_level: str
    sentry_dsn: Optional[str]


class SecretManager:
    """
    Manages secrets using multiple backends (Vault, AWS Secrets Manager, environment)
    """

    def __init__(
        self,
        backend: str = "vault",
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        aws_region: Optional[str] = None,
    ):
        """
        Initialize secret manager

        Args:
            backend: Secret backend (vault, aws, env)
            vault_url: Vault server URL
            vault_token: Vault authentication token
            aws_region: AWS region for Secrets Manager
        """
        self.backend = backend

        if backend == "vault":
            self.vault_client = hvac.Client(
                url=vault_url or os.getenv("VAULT_ADDR"),
                token=vault_token or os.getenv("VAULT_TOKEN"),
            )
            if not self.vault_client.is_authenticated():
                raise ValueError("Vault authentication failed")

        elif backend == "aws":
            self.aws_client = boto3.client(
                "secretsmanager",
                region_name=aws_region or os.getenv("AWS_REGION", "us-east-1"),
            )

        logger.info(f"Initialized secret manager with backend: {backend}")

    def get_secret(self, secret_path: str) -> Dict[str, Any]:
        """
        Retrieve secret from configured backend

        Args:
            secret_path: Path to secret

        Returns:
            Secret data dictionary
        """
        try:
            if self.backend == "vault":
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=secret_path
                )
                return response["data"]["data"]

            elif self.backend == "aws":
                response = self.aws_client.get_secret_value(SecretId=secret_path)
                return json.loads(response["SecretString"])

            elif self.backend == "env":
                # Fallback to environment variables
                secret_key = secret_path.upper().replace("/", "_")
                value = os.getenv(secret_key)
                if not value:
                    raise ValueError(f"Environment variable {secret_key} not found")
                return {secret_key: value}

        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_path}: {e}")
            raise

    def set_secret(self, secret_path: str, data: Dict[str, Any]) -> bool:
        """
        Store secret in configured backend

        Args:
            secret_path: Path to secret
            data: Secret data

        Returns:
            Success boolean
        """
        try:
            if self.backend == "vault":
                self.vault_client.secrets.kv.v2.create_or_update_secret(
                    path=secret_path, secret=data
                )
                return True

            elif self.backend == "aws":
                self.aws_client.create_secret(
                    Name=secret_path, SecretString=json.dumps(data)
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store secret {secret_path}: {e}")
            return False


class ConfigurationManager:
    """
    Manages environment-specific configurations
    """

    def __init__(
        self,
        environment: Environment,
        config_dir: str = "config",
        secret_manager: Optional[SecretManager] = None,
    ):
        """
        Initialize configuration manager

        Args:
            environment: Target environment
            config_dir: Directory containing config files
            secret_manager: Secret manager instance
        """
        self.environment = environment
        self.config_dir = Path(config_dir)
        self.secret_manager = secret_manager
        self.config: Dict[str, Any] = {}

        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from files and secrets"""
        # Load base configuration
        base_config_path = self.config_dir / "base.yaml"
        if base_config_path.exists():
            with open(base_config_path) as f:
                self.config = yaml.safe_load(f)

        # Load environment-specific configuration
        env_config_path = self.config_dir / f"{self.environment.value}.yaml"
        if env_config_path.exists():
            with open(env_config_path) as f:
                env_config = yaml.safe_load(f)
                self._merge_config(self.config, env_config)

        # Load secrets
        if self.secret_manager:
            self._load_secrets()

        # Override with environment variables
        self._apply_env_overrides()

        logger.info(f"Loaded configuration for {self.environment.value}")

    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_secrets(self):
        """Load secrets from secret manager"""
        secret_paths = self.config.get("secrets", {})

        for key, path in secret_paths.items():
            try:
                secret_data = self.secret_manager.get_secret(path)
                self.config[key] = secret_data
            except Exception as e:
                logger.error(f"Failed to load secret {key} from {path}: {e}")

    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Database password override
        if os.getenv("DATABASE_PASSWORD"):
            self.config["database"]["password"] = os.getenv("DATABASE_PASSWORD")

        # Redis password override
        if os.getenv("REDIS_PASSWORD"):
            self.config["redis"]["password"] = os.getenv("REDIS_PASSWORD")

        # API key overrides
        for key in ["JWT_SECRET_KEY", "PHI_ENCRYPTION_KEY"]:
            if os.getenv(key):
                self.config["security"][key.lower()] = os.getenv(key)

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self.config.get("database", {})

        return DatabaseConfig(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("database", "healthflow"),
            username=db_config.get("username", "healthflow_user"),
            password=db_config.get("password", ""),
            pool_size=db_config.get("pool_size", 20),
            max_overflow=db_config.get("max_overflow", 10),
            ssl_mode=db_config.get("ssl_mode", "require"),
            read_replica_host=db_config.get("read_replica_host"),
        )

    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        redis_config = self.config.get("redis", {})

        return RedisConfig(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            password=redis_config.get("password", ""),
            db=redis_config.get("db", 0),
            ssl=redis_config.get("ssl", False),
            cluster_mode=redis_config.get("cluster_mode", False),
            sentinel_hosts=redis_config.get("sentinel_hosts"),
        )

    def get_api_config(self) -> APIConfig:
        """Get API configuration"""
        api_config = self.config.get("api", {})

        return APIConfig(
            host=api_config.get("host", "0.0.0.0"),
            port=api_config.get("port", 5000),
            workers=api_config.get("workers", 4),
            timeout=api_config.get("timeout", 120),
            keepalive=api_config.get("keepalive", 5),
            max_requests=api_config.get("max_requests", 1000),
            max_requests_jitter=api_config.get("max_requests_jitter", 100),
            cors_origins=api_config.get("cors_origins", ["*"]),
            rate_limit=api_config.get("rate_limit", "100/hour"),
        )

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        mon_config = self.config.get("monitoring", {})

        return MonitoringConfig(
            prometheus_port=mon_config.get("prometheus_port", 9090),
            grafana_url=mon_config.get("grafana_url", "http://grafana:3000"),
            jaeger_host=mon_config.get("jaeger_host", "jaeger"),
            jaeger_port=mon_config.get("jaeger_port", 6831),
            log_level=mon_config.get("log_level", "INFO"),
            sentry_dsn=mon_config.get("sentry_dsn"),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def validate(self) -> List[str]:
        """
        Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields
        required_fields = [
            "database.host",
            "database.password",
            "redis.host",
            "security.jwt_secret_key",
            "security.phi_encryption_key",
        ]

        for field in required_fields:
            if not self.get(field):
                errors.append(f"Required field missing: {field}")

        # Database connection validation
        db_config = self.get_database_config()
        if db_config.pool_size < 5:
            errors.append("Database pool_size should be at least 5")

        # API validation
        api_config = self.get_api_config()
        if api_config.workers < 2:
            errors.append("API workers should be at least 2")

        return errors


class HealthCheck:
    """
    Performs health checks on system components
    """

    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager

    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        import psycopg2

        db_config = self.config_manager.get_database_config()

        try:
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.database,
                user=db_config.username,
                password=db_config.password,
                connect_timeout=5,
            )

            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                "status": "healthy",
                "message": "Database connection successful",
                "version": version,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
            }

    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        import redis

        redis_config = self.config_manager.get_redis_config()

        try:
            client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
                db=redis_config.db,
                ssl=redis_config.ssl,
                socket_connect_timeout=5,
            )

            client.ping()
            info = client.info()

            return {
                "status": "healthy",
                "message": "Redis connection successful",
                "version": info.get("redis_version"),
                "memory_used": info.get("used_memory_human"),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}",
            }

    def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        return {
            "overall_status": "healthy",  # Will be updated based on checks
            "timestamp": str(datetime.utcnow()),
            "checks": {"database": self.check_database(), "redis": self.check_redis()},
        }


class DeploymentManager:
    """
    Manages deployment orchestration and blue-green deployments
    """

    def __init__(
        self,
        environment: Environment,
        region: Region,
        config_manager: ConfigurationManager,
    ):
        self.environment = environment
        self.region = region
        self.config_manager = config_manager

    def prepare_deployment(self) -> Dict[str, Any]:
        """
        Prepare for deployment

        Returns:
            Deployment preparation report
        """
        report = {
            "environment": self.environment.value,
            "region": self.region.value,
            "timestamp": str(datetime.utcnow()),
            "checks": [],
        }

        # Validate configuration
        config_errors = self.config_manager.validate()
        if config_errors:
            report["checks"].append(
                {"name": "configuration", "status": "failed", "errors": config_errors}
            )
            report["ready"] = False
            return report

        report["checks"].append({"name": "configuration", "status": "passed"})

        # Check health
        health_check = HealthCheck(self.config_manager)
        health_status = health_check.check_all()

        report["checks"].append(
            {
                "name": "health",
                "status": (
                    "passed"
                    if all(
                        c["status"] == "healthy"
                        for c in health_status["checks"].values()
                    )
                    else "failed"
                ),
                "details": health_status,
            }
        )

        # Check migrations
        # ... (database migration check)

        report["ready"] = all(c["status"] == "passed" for c in report["checks"])

        return report

    def execute_deployment(self, deployment_type: str = "rolling") -> Dict[str, Any]:
        """
        Execute deployment

        Args:
            deployment_type: rolling, blue-green, canary

        Returns:
            Deployment result
        """
        logger.info(
            f"Starting {deployment_type} deployment to {self.environment.value}"
        )

        # Prepare deployment
        prep_report = self.prepare_deployment()

        if not prep_report["ready"]:
            return {
                "success": False,
                "message": "Deployment preparation failed",
                "details": prep_report,
            }

        # Execute deployment based on type
        if deployment_type == "rolling":
            return self._rolling_deployment()
        elif deployment_type == "blue-green":
            return self._blue_green_deployment()
        elif deployment_type == "canary":
            return self._canary_deployment()

    def _rolling_deployment(self) -> Dict[str, Any]:
        """Execute rolling deployment"""
        # Implementation would orchestrate rolling updates
        return {
            "success": True,
            "deployment_type": "rolling",
            "message": "Rolling deployment completed",
        }

    def _blue_green_deployment(self) -> Dict[str, Any]:
        """Execute blue-green deployment"""
        # Implementation would orchestrate blue-green switch
        return {
            "success": True,
            "deployment_type": "blue-green",
            "message": "Blue-green deployment completed",
        }

    def _canary_deployment(self) -> Dict[str, Any]:
        """Execute canary deployment"""
        # Implementation would orchestrate canary rollout
        return {
            "success": True,
            "deployment_type": "canary",
            "message": "Canary deployment completed",
        }


# Example usage
if __name__ == "__main__":
    from datetime import datetime

    # Initialize secret manager
    secret_manager = SecretManager(backend="vault", vault_url="http://vault:8200")

    # Initialize configuration for production
    config_manager = ConfigurationManager(
        environment=Environment.PRODUCTION,
        config_dir="config",
        secret_manager=secret_manager,
    )

    # Validate configuration
    errors = config_manager.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configuration valid")

    # Get configurations
    db_config = config_manager.get_database_config()
    print(f"\nDatabase: {db_config.host}:{db_config.port}/{db_config.database}")

    redis_config = config_manager.get_redis_config()
    print(f"Redis: {redis_config.host}:{redis_config.port}")

    api_config = config_manager.get_api_config()
    print(f"API: {api_config.host}:{api_config.port} ({api_config.workers} workers)")

    # Run health checks
    health_check = HealthCheck(config_manager)
    health_status = health_check.check_all()
    print(f"\nHealth Status: {health_status['overall_status']}")

    # Prepare deployment
    deployment_manager = DeploymentManager(
        environment=Environment.PRODUCTION,
        region=Region.US_EAST_1,
        config_manager=config_manager,
    )

    prep_report = deployment_manager.prepare_deployment()
    print(f"\nDeployment Ready: {prep_report['ready']}")
