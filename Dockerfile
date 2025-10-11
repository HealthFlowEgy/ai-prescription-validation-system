# Enhanced HealthFlow AI Digital Prescription System v2.0
# Multi-stage Docker Build
# International Best Practices Implementation

# ============================================================================
# BASE STAGE - Common dependencies
# ============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    zlib1g-dev \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r healthflow && useradd -r -g healthflow healthflow

# Set work directory
WORKDIR /app

# ============================================================================
# DEPENDENCIES STAGE - Install Python dependencies
# ============================================================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================================
# DEVELOPMENT STAGE - Development environment
# ============================================================================
FROM dependencies as development

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Copy source code
COPY . .

# Change ownership to app user
RUN chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Create necessary directories
RUN mkdir -p logs uploads backups

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command
CMD ["python", "src/main.py"]

# ============================================================================
# PRODUCTION STAGE - Production environment
# ============================================================================
FROM dependencies as production

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY gunicorn.conf.py .

# Copy static files and templates
COPY static/ ./static/
COPY templates/ ./templates/

# Create necessary directories and set permissions
RUN mkdir -p logs uploads backups && \
    chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Production command with Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "src.main:create_app()"]

# ============================================================================
# TESTING STAGE - Testing environment
# ============================================================================
FROM dependencies as testing

# Install testing dependencies
COPY requirements-test.txt .
RUN pip install -r requirements-test.txt

# Copy source code and tests
COPY . .

# Change ownership
RUN chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Run tests
CMD ["python", "-m", "pytest", "src/tests/", "-v", "--cov=src", "--cov-report=html"]

# ============================================================================
# WORKER STAGE - Celery worker
# ============================================================================
FROM dependencies as worker

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Change ownership
RUN chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Create necessary directories
RUN mkdir -p logs uploads

# Health check for worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD celery -A src.main.celery inspect ping || exit 1

# Worker command
CMD ["celery", "-A", "src.main.celery", "worker", "--loglevel=info", "--concurrency=4"]

# ============================================================================
# SCHEDULER STAGE - Celery beat scheduler
# ============================================================================
FROM dependencies as scheduler

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Change ownership
RUN chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Create necessary directories
RUN mkdir -p logs

# Scheduler command
CMD ["celery", "-A", "src.main.celery", "beat", "--loglevel=info"]

# ============================================================================
# MIGRATION STAGE - Database migrations
# ============================================================================
FROM dependencies as migration

# Copy source code and migration files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Change ownership
RUN chown -R healthflow:healthflow /app

# Switch to app user
USER healthflow

# Migration command
CMD ["python", "-m", "alembic", "upgrade", "head"]

# ============================================================================
# BUILD ARGUMENTS AND LABELS
# ============================================================================

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

# Labels for metadata
LABEL maintainer="HealthFlow Development Team <dev@healthflow.egypt.gov>" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="Enhanced HealthFlow" \
      org.label-schema.description="AI Digital Prescription System" \
      org.label-schema.url="https://healthflow.egypt.gov" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/HealthFlowEgy/ai-prescription-validation-system" \
      org.label-schema.vendor="HealthFlow Egypt" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

# Build development image:
# docker build --target development -t healthflow:dev .

# Build production image:
# docker build --target production -t healthflow:prod .

# Build worker image:
# docker build --target worker -t healthflow:worker .

# Build scheduler image:
# docker build --target scheduler -t healthflow:scheduler .

# Build testing image:
# docker build --target testing -t healthflow:test .

# Run development container:
# docker run -p 5000:5000 -v $(pwd):/app healthflow:dev

# Run production container:
# docker run -p 5000:5000 healthflow:prod

# Run with environment file:
# docker run --env-file .env -p 5000:5000 healthflow:prod

# ============================================================================
# SECURITY CONSIDERATIONS
# ============================================================================

# 1. Non-root user execution
# 2. Minimal base image (slim)
# 3. Multi-stage builds to reduce image size
# 4. No sensitive data in image layers
# 5. Health checks for container monitoring
# 6. Proper file permissions
# 7. Security scanning with tools like Trivy
# 8. Regular base image updates
# 9. Secrets management via environment variables
# 10. Network security with proper firewall rules

