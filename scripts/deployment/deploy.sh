#!/bin/bash

###############################################################################
# Production Deployment Script
# HealthFlow AI Prescription Validation System
#
# Usage: ./deploy.sh [environment] [version]
# Example: ./deploy.sh production v1.0.0
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="healthflow-${ENVIRONMENT}"
REGISTRY="healthflow"

# Logging
LOG_FILE="deployment_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Confirm deployment
confirm_deployment() {
    echo ""
    echo "=========================================="
    echo "  DEPLOYMENT CONFIRMATION"
    echo "=========================================="
    echo "  Environment: $ENVIRONMENT"
    echo "  Version: $VERSION"
    echo "  Namespace: $NAMESPACE"
    echo "=========================================="
    echo ""
    
    if [ "$ENVIRONMENT" == "production" ]; then
        warning "You are about to deploy to PRODUCTION!"
        read -p "Are you absolutely sure? (type 'yes' to continue): " -r
        if [ "$REPLY" != "yes" ]; then
            error "Deployment cancelled"
            exit 1
        fi
    else
        read -p "Continue with deployment? (y/n): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Deployment cancelled"
            exit 1
        fi
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log "✓ Kubernetes cluster accessible"
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        warning "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace "$NAMESPACE"
    fi
    log "✓ Namespace exists"
    
    # Check Docker images exist
    for service in api frontend celery; do
        if ! docker pull "${REGISTRY}/${service}:${VERSION}" &> /dev/null; then
            error "Docker image ${REGISTRY}/${service}:${VERSION} not found"
            exit 1
        fi
        log "✓ Docker image ${service}:${VERSION} exists"
    done
    
    # Check database connectivity
    info "Checking database connectivity..."
    if kubectl exec -n "$NAMESPACE" deployment/api -- python -c "from src.database import db; db.engine.connect()" &> /dev/null; then
        log "✓ Database connectivity verified"
    else
        warning "Database connectivity check failed (may be expected if first deployment)"
    fi
}

# Backup database
backup_database() {
    log "Creating database backup..."
    
    BACKUP_NAME="backup_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S)"
    
    kubectl exec -n "$NAMESPACE" deployment/api -- \
        python scripts/backup_database.py --output "/backups/${BACKUP_NAME}.sql"
    
    if [ $? -eq 0 ]; then
        log "✓ Database backup created: ${BACKUP_NAME}"
        echo "$BACKUP_NAME" > .last_backup
    else
        error "Database backup failed"
        exit 1
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    kubectl exec -n "$NAMESPACE" deployment/api -- \
        python manage.py migrate
    
    if [ $? -eq 0 ]; then
        log "✓ Database migrations completed"
    else
        error "Database migrations failed"
        exit 1
    fi
}

# Deploy application
deploy_application() {
    log "Deploying application version ${VERSION}..."
    
    # Update API deployment
    info "Deploying API..."
    kubectl set image deployment/api -n "$NAMESPACE" \
        api="${REGISTRY}/api:${VERSION}"
    kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=5m
    log "✓ API deployed"
    
    # Update Frontend deployment
    info "Deploying Frontend..."
    kubectl set image deployment/frontend -n "$NAMESPACE" \
        frontend="${REGISTRY}/frontend:${VERSION}"
    kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=5m
    log "✓ Frontend deployed"
    
    # Update Celery deployment
    info "Deploying Celery workers..."
    kubectl set image deployment/celery -n "$NAMESPACE" \
        celery="${REGISTRY}/celery:${VERSION}"
    kubectl rollout status deployment/celery -n "$NAMESPACE" --timeout=5m
    log "✓ Celery deployed"
}

# Run smoke tests
run_smoke_tests() {
    log "Running smoke tests..."
    
    # Get API endpoint
    API_URL=$(kubectl get service api -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    # Health check
    info "Testing health endpoint..."
    if curl -f "https://${API_URL}/health" &> /dev/null; then
        log "✓ Health check passed"
    else
        error "Health check failed"
        return 1
    fi
    
    # Authentication test
    info "Testing authentication..."
    RESPONSE=$(curl -s -X POST "https://${API_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@healthflow.com","password":"TestPassword123!"}')
    
    if echo "$RESPONSE" | grep -q "access_token"; then
        log "✓ Authentication test passed"
    else
        error "Authentication test failed"
        return 1
    fi
    
    log "✓ All smoke tests passed"
}

# Monitor deployment
monitor_deployment() {
    log "Monitoring deployment for 5 minutes..."
    
    for i in {1..10}; do
        sleep 30
        
        # Check pod status
        PODS_READY=$(kubectl get pods -n "$NAMESPACE" -o json | \
            jq '[.items[] | select(.status.phase=="Running")] | length')
        PODS_TOTAL=$(kubectl get pods -n "$NAMESPACE" -o json | jq '.items | length')
        
        info "Pods ready: ${PODS_READY}/${PODS_TOTAL}"
        
        # Check for errors in logs
        ERROR_COUNT=$(kubectl logs -n "$NAMESPACE" deployment/api --since=30s 2>/dev/null | \
            grep -i "error" | wc -l)
        
        if [ "$ERROR_COUNT" -gt 10 ]; then
            warning "High error count detected: $ERROR_COUNT errors in last 30s"
        fi
    done
    
    log "✓ Monitoring complete"
}

# Rollback deployment
rollback_deployment() {
    error "Rolling back deployment..."
    
    kubectl rollout undo deployment/api -n "$NAMESPACE"
    kubectl rollout undo deployment/frontend -n "$NAMESPACE"
    kubectl rollout undo deployment/celery -n "$NAMESPACE"
    
    log "Rollback initiated. Waiting for completion..."
    
    kubectl rollout status deployment/api -n "$NAMESPACE" --timeout=5m
    kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout=5m
    kubectl rollout status deployment/celery -n "$NAMESPACE" --timeout=5m
    
    log "✓ Rollback complete"
    
    # Restore database if backup exists
    if [ -f .last_backup ]; then
        BACKUP_NAME=$(cat .last_backup)
        warning "Restoring database from backup: $BACKUP_NAME"
        kubectl exec -n "$NAMESPACE" deployment/api -- \
            python scripts/restore_database.py --input "/backups/${BACKUP_NAME}.sql"
        log "✓ Database restored"
    fi
}

# Main deployment flow
main() {
    log "=========================================="
    log "  HealthFlow Deployment Script"
    log "=========================================="
    log "Environment: $ENVIRONMENT"
    log "Version: $VERSION"
    log "=========================================="
    
    # Confirm deployment
    confirm_deployment
    
    # Pre-deployment checks
    pre_deployment_checks
    
    # Backup database (production only)
    if [ "$ENVIRONMENT" == "production" ]; then
        backup_database
    fi
    
    # Run migrations
    run_migrations
    
    # Deploy application
    deploy_application
    
    # Run smoke tests
    if run_smoke_tests; then
        log "✓ Smoke tests passed"
    else
        error "Smoke tests failed!"
        read -p "Rollback deployment? (y/n): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback_deployment
            exit 1
        fi
    fi
    
    # Monitor deployment
    monitor_deployment
    
    log "=========================================="
    log "  DEPLOYMENT SUCCESSFUL"
    log "=========================================="
    log "Environment: $ENVIRONMENT"
    log "Version: $VERSION"
    log "Deployment log: $LOG_FILE"
    log "=========================================="
}

# Trap errors and rollback
trap 'error "Deployment failed at line $LINENO"; rollback_deployment; exit 1' ERR

# Run main function
main

