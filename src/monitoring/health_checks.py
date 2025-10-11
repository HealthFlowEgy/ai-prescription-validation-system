"""
Production Health Checks and Monitoring
Provides detailed system health status for monitoring and alerting
"""
import time
import psutil
from datetime import datetime
from typing import Dict, Any, List
from flask import jsonify
import logging

from src.models.database import db
import redis

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Individual health check result."""
    
    def __init__(self, name: str, status: str, message: str = "", details: Dict[str, Any] = None):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self):
        return {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class HealthCheckService:
    """Service for performing system health checks."""
    
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
        # Initialize Redis client for health checks
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        try:
            self.redis_client = redis.from_url(redis_url)
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    def check_database(self) -> HealthCheck:
        """Check database connectivity and responsiveness."""
        try:
            start = time.time()
            
            # Execute simple query
            db.session.execute('SELECT 1')
            db.session.commit()
            
            response_time = (time.time() - start) * 1000  # Convert to ms
            
            if response_time < 100:
                status = HealthStatus.HEALTHY
                message = "Database responsive"
            elif response_time < 500:
                status = HealthStatus.DEGRADED
                message = "Database slow"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Database very slow"
            
            return HealthCheck(
                name="database",
                status=status,
                message=message,
                details={'response_time_ms': round(response_time, 2)}
            )
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}"
            )
    
    def check_redis(self) -> HealthCheck:
        """Check Redis connectivity and responsiveness."""
        if not self.redis_client:
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message="Redis client not initialized"
            )
        
        try:
            start = time.time()
            
            # Ping Redis
            self.redis_client.ping()
            
            response_time = (time.time() - start) * 1000
            
            # Get Redis info
            info = self.redis_client.info()
            memory_used_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            if response_time < 50:
                status = HealthStatus.HEALTHY
                message = "Redis responsive"
            elif response_time < 200:
                status = HealthStatus.DEGRADED
                message = "Redis slow"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Redis very slow"
            
            return HealthCheck(
                name="redis",
                status=status,
                message=message,
                details={
                    'response_time_ms': round(response_time, 2),
                    'memory_used_mb': round(memory_used_mb, 2),
                    'connected_clients': info.get('connected_clients', 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}"
            )
    
    def check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        try:
            disk = psutil.disk_usage('/')
            percent_used = disk.percent
            free_gb = disk.free / (1024 ** 3)
            
            if percent_used < 80:
                status = HealthStatus.HEALTHY
                message = "Sufficient disk space"
            elif percent_used < 90:
                status = HealthStatus.DEGRADED
                message = "Disk space running low"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Critical: Disk space very low"
            
            return HealthCheck(
                name="disk_space",
                status=status,
                message=message,
                details={
                    'percent_used': percent_used,
                    'free_gb': round(free_gb, 2),
                    'total_gb': round(disk.total / (1024 ** 3), 2)
                }
            )
            
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check disk space: {str(e)}"
            )
    
    def check_memory(self) -> HealthCheck:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            percent_used = memory.percent
            available_gb = memory.available / (1024 ** 3)
            
            if percent_used < 80:
                status = HealthStatus.HEALTHY
                message = "Sufficient memory"
            elif percent_used < 90:
                status = HealthStatus.DEGRADED
                message = "Memory usage high"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Critical: Memory usage very high"
            
            return HealthCheck(
                name="memory",
                status=status,
                message=message,
                details={
                    'percent_used': percent_used,
                    'available_gb': round(available_gb, 2),
                    'total_gb': round(memory.total / (1024 ** 3), 2)
                }
            )
            
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check memory: {str(e)}"
            )
    
    def check_cpu(self) -> HealthCheck:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = "CPU usage normal"
            elif cpu_percent < 90:
                status = HealthStatus.DEGRADED
                message = "CPU usage high"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Critical: CPU usage very high"
            
            return HealthCheck(
                name="cpu",
                status=status,
                message=message,
                details={
                    'percent_used': cpu_percent,
                    'cpu_count': cpu_count
                }
            )
            
        except Exception as e:
            logger.error(f"CPU check failed: {e}")
            return HealthCheck(
                name="cpu",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check CPU: {str(e)}"
            )
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        checks = [
            self.check_database(),
            self.check_redis(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu()
        ]
        
        # Determine overall status
        if any(check.status == HealthStatus.UNHEALTHY for check in checks):
            overall_status = HealthStatus.UNHEALTHY
        elif any(check.status == HealthStatus.DEGRADED for check in checks):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': [check.to_dict() for check in checks]
        }


# Flask route handlers
def create_health_check_routes(app):
    """Create health check routes for the Flask app."""
    
    health_service = HealthCheckService(app)
    
    @app.route('/health')
    def health_check():
        """Basic health check endpoint."""
        return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with all component statuses."""
        result = health_service.run_all_checks()
        
        # Return 503 if unhealthy
        status_code = 200 if result['status'] != HealthStatus.UNHEALTHY else 503
        
        return jsonify(result), status_code
    
    @app.route('/health/ready')
    def readiness_check():
        """Kubernetes readiness probe."""
        # Check if app can serve traffic
        db_check = health_service.check_database()
        redis_check = health_service.check_redis()
        
        if db_check.status == HealthStatus.UNHEALTHY or redis_check.status == HealthStatus.UNHEALTHY:
            return jsonify({
                'ready': False,
                'checks': [db_check.to_dict(), redis_check.to_dict()]
            }), 503
        
        return jsonify({'ready': True})
    
    @app.route('/health/live')
    def liveness_check():
        """Kubernetes liveness probe."""
        # Simple check that app is running
        return jsonify({'alive': True})
    
    logger.info("Health check routes configured")


# Metrics collection
class MetricsCollector:
    """Collect application metrics for monitoring."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.request_durations = []
    
    def record_request(self, duration_ms: float, status_code: int):
        """Record a request."""
        self.request_count += 1
        self.request_durations.append(duration_ms)
        
        if status_code >= 500:
            self.error_count += 1
        
        # Keep only last 1000 durations
        if len(self.request_durations) > 1000:
            self.request_durations = self.request_durations[-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if not self.request_durations:
            avg_duration = 0
            p95_duration = 0
            p99_duration = 0
        else:
            sorted_durations = sorted(self.request_durations)
            avg_duration = sum(sorted_durations) / len(sorted_durations)
            p95_index = int(len(sorted_durations) * 0.95)
            p99_index = int(len(sorted_durations) * 0.99)
            p95_duration = sorted_durations[p95_index] if p95_index < len(sorted_durations) else 0
            p99_duration = sorted_durations[p99_index] if p99_index < len(sorted_durations) else 0
        
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate_percent': round(error_rate, 2),
            'avg_response_time_ms': round(avg_duration, 2),
            'p95_response_time_ms': round(p95_duration, 2),
            'p99_response_time_ms': round(p99_duration, 2)
        }


# Global metrics collector
metrics_collector = MetricsCollector()


def create_metrics_routes(app):
    """Create metrics routes for the Flask app."""
    
    @app.route('/metrics')
    def metrics():
        """Prometheus-compatible metrics endpoint."""
        metrics_data = metrics_collector.get_metrics()
        
        # Prometheus format
        output = []
        output.append(f'# HELP http_requests_total Total number of HTTP requests')
        output.append(f'# TYPE http_requests_total counter')
        output.append(f'http_requests_total {metrics_data["request_count"]}')
        output.append(f'')
        output.append(f'# HELP http_errors_total Total number of HTTP errors (5xx)')
        output.append(f'# TYPE http_errors_total counter')
        output.append(f'http_errors_total {metrics_data["error_count"]}')
        output.append(f'')
        output.append(f'# HELP http_request_duration_milliseconds HTTP request duration in milliseconds')
        output.append(f'# TYPE http_request_duration_milliseconds summary')
        output.append(f'http_request_duration_milliseconds{{quantile="0.95"}} {metrics_data["p95_response_time_ms"]}')
        output.append(f'http_request_duration_milliseconds{{quantile="0.99"}} {metrics_data["p99_response_time_ms"]}')
        output.append(f'http_request_duration_milliseconds_sum {metrics_data["avg_response_time_ms"] * metrics_data["request_count"]}')
        output.append(f'http_request_duration_milliseconds_count {metrics_data["request_count"]}')
        
        return '\n'.join(output), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    @app.route('/metrics/json')
    def metrics_json():
        """JSON metrics endpoint."""
        return jsonify(metrics_collector.get_metrics())
    
    logger.info("Metrics routes configured")

