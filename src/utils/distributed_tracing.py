"""
Centralized Logging & Monitoring Configuration
Implements ELK Stack integration and Prometheus metrics
"""

import json
import logging
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info
from pythonjsonlogger import jsonlogger

# ============================================
# Structured Logging Configuration
# ============================================


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.
    Adds standard fields for ELK Stack indexing.
    """

    def add_fields(
        self, log_record: Dict, record: logging.LogRecord, message_dict: Dict
    ):
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = os.getenv("SERVICE_NAME", "healthflow-backend")
        log_record["environment"] = os.getenv("ENVIRONMENT", "production")
        log_record["pod_name"] = os.getenv("HOSTNAME", "unknown")
        log_record["namespace"] = os.getenv("NAMESPACE", "healthflow-production")

        # Add trace context if available
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            log_record["trace_id"] = format(span_context.trace_id, "032x")
            log_record["span_id"] = format(span_context.span_id, "016x")

        # Sanitize PHI from logs (critical for HIPAA)
        if "message" in log_record:
            log_record["message"] = self._sanitize_phi(log_record["message"])

        # Move exception info to dedicated field
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stacktrace": self.formatException(record.exc_info),
            }

    def _sanitize_phi(self, message: str) -> str:
        """Remove PHI from log messages."""
        import re

        # Redact common PHI patterns
        patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN-REDACTED]"),  # SSN
            (
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "[EMAIL-REDACTED]",
            ),  # Email
            (r"\b\d{10}\b", "[PHONE-REDACTED]"),  # Phone
            (r"\b\d{1,2}/\d{1,2}/\d{4}\b", "[DATE-REDACTED]"),  # Date
        ]

        for pattern, replacement in patterns:
            message = re.sub(pattern, replacement, message)

        return message


def configure_logging():
    """
    Configure application logging with JSON output for ELK Stack.
    """

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # JSON handler for structured logs
    json_handler = logging.StreamHandler()
    json_formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    json_handler.setFormatter(json_formatter)
    root_logger.addHandler(json_handler)

    # Configure library loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Structured logging configured for ELK Stack")


# ============================================
# Request Logging Middleware
# ============================================


def log_request_middleware(app):
    """
    Flask middleware for comprehensive request/response logging.
    """

    @app.before_request
    def log_request():
        import time

        from flask import g, request

        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-ID", os.urandom(16).hex())

        # Log incoming request
        logging.info(
            "Request started",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "query_string": request.query_string.decode(),
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get("User-Agent"),
                "content_length": request.content_length,
                "user_id": getattr(g, "current_user", {}).get("id"),
            },
        )

    @app.after_request
    def log_response(response):
        from flask import g

        if hasattr(g, "start_time"):
            duration = time.time() - g.start_time

            # Log response
            logging.info(
                "Request completed",
                extra={
                    "request_id": getattr(g, "request_id", "unknown"),
                    "status_code": response.status_code,
                    "duration_ms": duration * 1000,
                    "response_size": response.content_length,
                },
            )

            # Update Prometheus metrics
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.endpoint,
                status_code=response.status_code,
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint,
                status_code=response.status_code,
            ).inc()

        return response

    @app.errorhandler(Exception)
    def log_exception(error):
        from flask import g

        logging.error(
            "Unhandled exception",
            extra={
                "request_id": getattr(g, "request_id", "unknown"),
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            exc_info=True,
        )

        return {"error": "Internal server error"}, 500


# ============================================
# Prometheus Metrics
# ============================================

# HTTP Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Business Metrics
PRESCRIPTION_PROCESSED = Counter(
    "prescriptions_processed_total",
    "Total prescriptions processed",
    ["status", "requires_review"],
)

PRESCRIPTION_PROCESSING_TIME = Histogram(
    "prescription_processing_seconds",
    "Time to process a prescription",
    ["stage"],  # ocr, nlp, validation
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

OCR_CONFIDENCE = Histogram(
    "ocr_confidence_score",
    "OCR confidence scores",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
)

# Database Metrics
DB_QUERY_COUNT = Counter(
    "database_queries_total", "Total database queries", ["operation", "table", "status"]
)

DB_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

DB_CONNECTION_POOL = Gauge(
    "database_connection_pool_size",
    "Current database connection pool size",
    ["state"],  # idle, active, waiting
)

# Celery Metrics
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total", "Total Celery tasks", ["task_name", "status"]
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration",
    ["task_name"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length", "Current Celery queue length", ["queue_name"]
)

# ML Model Metrics
ML_MODEL_PREDICTIONS = Counter(
    "ml_model_predictions_total",
    "Total ML model predictions",
    ["model_name", "model_version"],
)

ML_MODEL_LATENCY = Histogram(
    "ml_model_inference_seconds",
    "ML model inference latency",
    ["model_name", "model_version"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

ML_MODEL_CONFIDENCE = Histogram(
    "ml_model_confidence_score",
    "ML model confidence scores",
    ["model_name", "model_version"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
)

# System Metrics
SYSTEM_INFO = Info("system", "System information")
SYSTEM_INFO.info(
    {
        "version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "python_version": os.sys.version,
    }
)


# ============================================
# Metrics Decorators
# ============================================


def track_time(metric: Histogram, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to track function execution time in Prometheus.

    Usage:
        @track_time(PRESCRIPTION_PROCESSING_TIME, {'stage': 'ocr'})
        def extract_text(image):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        return wrapper

    return decorator


def count_calls(metric: Counter, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to count function calls in Prometheus.

    Usage:
        @count_calls(PRESCRIPTION_PROCESSED, {'status': 'success'})
        def process_prescription(prescription_id):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                return result
            except Exception as e:
                if labels:
                    error_labels = labels.copy()
                    error_labels["status"] = "error"
                    metric.labels(**error_labels).inc()
                raise

        return wrapper

    return decorator


# ============================================
# Custom Metrics Collection
# ============================================


def collect_database_metrics(db_engine):
    """
    Collect database connection pool metrics.
    Should be called periodically (e.g., every 30 seconds).
    """
    pool = db_engine.pool

    DB_CONNECTION_POOL.labels(state="idle").set(pool.size() - pool.checkedout())
    DB_CONNECTION_POOL.labels(state="active").set(pool.checkedout())
    DB_CONNECTION_POOL.labels(state="waiting").set(pool.overflow())


def collect_celery_metrics(celery_app):
    """
    Collect Celery queue metrics.
    Should be called periodically (e.g., every 30 seconds).
    """
    from celery import current_app

    inspect = current_app.control.inspect()

    # Get queue lengths
    active_queues = inspect.active_queues()
    if active_queues:
        for worker, queues in active_queues.items():
            for queue in queues:
                # Get queue length from Redis
                queue_key = f"celery:{queue['name']}"
                length = redis_client.llen(queue_key)
                CELERY_QUEUE_LENGTH.labels(queue_name=queue["name"]).set(length)


# ============================================
# Health Check Metrics
# ============================================

HEALTH_CHECK = Gauge(
    "service_health",
    "Service health status (1 = healthy, 0 = unhealthy)",
    ["component"],
)


def update_health_metrics(health_checks: Dict[str, bool]):
    """
    Update health check metrics based on health check results.

    Args:
        health_checks: Dict of component name to health status
    """
    for component, is_healthy in health_checks.items():
        HEALTH_CHECK.labels(component=component).set(1 if is_healthy else 0)


# ============================================
# Metrics Endpoint
# ============================================


def setup_metrics_endpoint(app):
    """
    Set up Prometheus metrics endpoint.
    """
    from flask import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    @app.route("/metrics")
    def metrics():
        """
        Prometheus metrics endpoint.
        Should be scraped by Prometheus every 15-30 seconds.
        """
        # Collect latest metrics before exposing
        from src.database import db

        collect_database_metrics(db.engine)

        # Generate metrics in Prometheus format
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ============================================
# Alert Rules (Prometheus)
# ============================================

PROMETHEUS_ALERT_RULES = """
# prometheus-alerts.yml
groups:
  - name: healthflow_alerts
    interval: 30s
    rules:
    
    # High Error Rate
    - alert: HighErrorRate
      expr: |
        (
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
        ) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
    
    # Slow Requests
    - alert: SlowRequests
      expr: |
        histogram_quantile(0.95, 
          rate(http_request_duration_seconds_bucket[5m])
        ) > 2.0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Slow requests detected"
        description: "P95 latency is {{ $value }}s (threshold: 2s)"
    
    # Database Connection Pool Exhausted
    - alert: DatabaseConnectionPoolExhausted
      expr: |
        database_connection_pool_size{state="waiting"} > 10
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Database connection pool exhausted"
        description: "{{ $value }} connections waiting for pool"
    
    # Low OCR Confidence
    - alert: LowOCRConfidence
      expr: |
        histogram_quantile(0.50,
          rate(ocr_confidence_score_bucket[10m])
        ) < 0.80
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Low OCR confidence scores"
        description: "Median OCR confidence is {{ $value }} (threshold: 0.80)"
    
    # High Celery Queue Length
    - alert: HighCeleryQueueLength
      expr: |
        celery_queue_length > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High Celery queue length"
        description: "Queue {{ $labels.queue_name }} has {{ $value }} pending tasks"
    
    # Service Unhealthy
    - alert: ServiceUnhealthy
      expr: |
        service_health == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Service component unhealthy"
        description: "Component {{ $labels.component }} is unhealthy"
    
    # High Memory Usage
    - alert: HighMemoryUsage
      expr: |
        (
          process_resident_memory_bytes 
          / 
          node_memory_MemTotal_bytes
        ) > 0.90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage"
        description: "Memory usage is {{ $value | humanizePercentage }}"
"""


# ============================================
# Usage Example
# ============================================

"""
# In main Flask app initialization:

from src.logging_monitoring import (
    configure_logging,
    log_request_middleware,
    setup_metrics_endpoint,
    track_time,
    PRESCRIPTION_PROCESSING_TIME,
    OCR_CONFIDENCE
)

# Configure logging
configure_logging()

# Add request logging
log_request_middleware(app)

# Expose metrics endpoint
setup_metrics_endpoint(app)

# Use metrics in services
@track_time(PRESCRIPTION_PROCESSING_TIME, {'stage': 'ocr'})
def extract_text(image_path):
    result = ocr_model.predict(image_path)
    OCR_CONFIDENCE.observe(result.confidence)
    return result
"""
