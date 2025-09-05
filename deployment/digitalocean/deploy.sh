#!/bin/bash

# Deployment script for Prescription Validation System on Digital Ocean
# This script handles the deployment process

set -e

# Configuration
CONTAINER_NAME="prescription-validation-system"
REGISTRY="registry.digitalocean.com"
IMAGE_NAME="prescription-validator"
BACKUP_DIR="/opt/prescription-validator/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service to be ready at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            print_success "Service is ready!"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts - Service not ready yet, waiting..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    print_error "Service failed to become ready after $max_attempts attempts"
    return 1
}

# Function to create backup
create_backup() {
    print_status "Creating backup before deployment..."
    
    local backup_name="pre_deploy_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database if it exists
    if [ -f "/opt/prescription-validator/data/production.db" ]; then
        cp "/opt/prescription-validator/data/production.db" "$BACKUP_DIR/production_$backup_name.db"
        print_success "Database backup created: production_$backup_name.db"
    fi
    
    # Backup current container if it exists
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        docker commit "$CONTAINER_NAME" "$CONTAINER_NAME-backup-$backup_name" || true
        print_success "Container backup created: $CONTAINER_NAME-backup-$backup_name"
    fi
}

# Function to rollback deployment
rollback_deployment() {
    print_warning "Rolling back deployment..."
    
    # Find the latest backup container
    local backup_container=$(docker images --format "table {{.Repository}}\t{{.Tag}}" | grep "$CONTAINER_NAME-backup" | head -1 | awk '{print $1":"$2}')
    
    if [ -n "$backup_container" ]; then
        print_status "Rolling back to: $backup_container"
        
        # Stop current container
        docker stop "$CONTAINER_NAME" || true
        docker rm "$CONTAINER_NAME" || true
        
        # Start backup container
        docker run -d \
            --name "$CONTAINER_NAME" \
            --restart unless-stopped \
            -p 80:5000 \
            -v /opt/prescription-validator/uploads:/app/uploads \
            -v /opt/prescription-validator/data:/app/data \
            -v /opt/prescription-validator/logs:/app/logs \
            "$backup_container"
        
        print_success "Rollback completed"
    else
        print_error "No backup container found for rollback"
        return 1
    fi
}

# Function to deploy application
deploy_application() {
    local image_tag=${1:-latest}
    local registry_name=${2:-$DIGITALOCEAN_REGISTRY_NAME}
    
    if [ -z "$registry_name" ]; then
        print_error "Registry name not provided. Set DIGITALOCEAN_REGISTRY_NAME environment variable."
        exit 1
    fi
    
    local full_image_name="$REGISTRY/$registry_name/$IMAGE_NAME:$image_tag"
    
    print_status "Deploying application with image: $full_image_name"
    
    # Login to Digital Ocean Container Registry
    print_status "Logging in to Digital Ocean Container Registry..."
    if ! doctl registry login --expiry-seconds 1200; then
        print_error "Failed to login to Digital Ocean Container Registry"
        exit 1
    fi
    
    # Pull the latest image
    print_status "Pulling image: $full_image_name"
    if ! docker pull "$full_image_name"; then
        print_error "Failed to pull image: $full_image_name"
        exit 1
    fi
    
    # Create backup before deployment
    create_backup
    
    # Stop and remove existing container
    print_status "Stopping existing container..."
    docker stop "$CONTAINER_NAME" || true
    docker rm "$CONTAINER_NAME" || true
    
    # Run new container
    print_status "Starting new container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 80:5000 \
        -v /opt/prescription-validator/uploads:/app/uploads \
        -v /opt/prescription-validator/data:/app/data \
        -v /opt/prescription-validator/logs:/app/logs \
        --env-file /opt/prescription-validator/.env \
        "$full_image_name"
    
    # Wait for service to be ready
    if wait_for_service "http://localhost/api/health"; then
        print_success "Deployment completed successfully!"
        
        # Clean up old images (keep last 3 versions)
        print_status "Cleaning up old images..."
        docker images "$REGISTRY/$registry_name/$IMAGE_NAME" --format "table {{.Tag}}\t{{.ID}}" | tail -n +4 | awk '{print $2}' | xargs -r docker rmi || true
        
        # Clean up old backup containers (keep last 5)
        docker images --format "table {{.Repository}}\t{{.Tag}}" | grep "$CONTAINER_NAME-backup" | tail -n +6 | awk '{print $1":"$2}' | xargs -r docker rmi || true
        
        print_success "Cleanup completed"
        
        # Show deployment information
        print_status "Deployment Information:"
        echo "  - Container Name: $CONTAINER_NAME"
        echo "  - Image: $full_image_name"
        echo "  - Health Check: http://localhost/api/health"
        echo "  - Logs: docker logs $CONTAINER_NAME"
        
    else
        print_error "Deployment failed - service not ready"
        print_warning "Attempting rollback..."
        rollback_deployment
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --tag TAG          Image tag to deploy (default: latest)"
    echo "  -r, --registry NAME    Registry name"
    echo "  -b, --backup           Create backup only"
    echo "  -R, --rollback         Rollback to previous version"
    echo "  -s, --status           Show deployment status"
    echo "  -l, --logs             Show application logs"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Deploy latest version"
    echo "  $0 -t v1.2.3                        # Deploy specific version"
    echo "  $0 -r my-registry -t latest         # Deploy from specific registry"
    echo "  $0 --backup                         # Create backup only"
    echo "  $0 --rollback                       # Rollback deployment"
    echo "  $0 --status                         # Show status"
}

# Function to show deployment status
show_status() {
    print_status "Deployment Status:"
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container is running"
        echo "  - Container ID: $(docker ps --filter name=$CONTAINER_NAME --format '{{.ID}}')"
        echo "  - Image: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Image}}')"
        echo "  - Status: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Status}}')"
        echo "  - Ports: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Ports}}')"
        
        # Check health
        if curl -f -s "http://localhost/api/health" > /dev/null 2>&1; then
            print_success "Health check: PASSED"
        else
            print_error "Health check: FAILED"
        fi
    else
        print_error "Container is not running"
    fi
    
    # Show recent logs
    print_status "Recent logs:"
    docker logs --tail 10 "$CONTAINER_NAME" 2>/dev/null || echo "No logs available"
}

# Function to show logs
show_logs() {
    local lines=${1:-50}
    print_status "Showing last $lines lines of logs:"
    docker logs --tail "$lines" -f "$CONTAINER_NAME"
}

# Main script logic
main() {
    # Check if required commands exist
    if ! command_exists docker; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command_exists doctl; then
        print_error "doctl is not installed"
        exit 1
    fi
    
    if ! command_exists curl; then
        print_error "curl is not installed"
        exit 1
    fi
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY_NAME="$2"
                shift 2
                ;;
            -b|--backup)
                create_backup
                exit 0
                ;;
            -R|--rollback)
                rollback_deployment
                exit 0
                ;;
            -s|--status)
                show_status
                exit 0
                ;;
            -l|--logs)
                show_logs
                exit 0
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Deploy application
    deploy_application "${IMAGE_TAG:-latest}" "${REGISTRY_NAME:-$DIGITALOCEAN_REGISTRY_NAME}"
}

# Run main function
main "$@"

