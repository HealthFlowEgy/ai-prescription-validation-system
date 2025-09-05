# CI/CD Deployment Guide for Digital Ocean

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [GitHub Repository Setup](#github-repository-setup)
- [Digital Ocean Configuration](#digital-ocean-configuration)
- [CI/CD Pipeline Configuration](#cicd-pipeline-configuration)
- [Deployment Workflows](#deployment-workflows)
- [Infrastructure as Code](#infrastructure-as-code)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Overview

This guide provides comprehensive instructions for setting up a complete CI/CD pipeline for the AI-Based Digital Prescription Validation System using GitHub Actions and Digital Ocean. The pipeline includes automated testing, building, and deployment to production and staging environments.

### Architecture Overview

The CI/CD pipeline follows modern DevOps practices with the following components:

- **Source Control**: GitHub repository with branch-based workflows
- **Continuous Integration**: Automated testing, linting, and security scanning
- **Container Registry**: Digital Ocean Container Registry for Docker images
- **Deployment Target**: Digital Ocean Droplets with Docker containers
- **Infrastructure**: Terraform for infrastructure as code
- **Monitoring**: Health checks, logging, and alerting

### Deployment Environments

The system supports multiple deployment environments:

1. **Development**: Feature branch deployments for testing
2. **Staging**: Automated deployment from develop branch
3. **Production**: Tagged releases with manual approval gates

## Prerequisites

Before setting up the CI/CD pipeline, ensure you have the following:

### Required Accounts and Tools

1. **GitHub Account**: With repository access and Actions enabled
2. **Digital Ocean Account**: With API access and billing configured
3. **Domain Name** (optional): For custom domain configuration
4. **Local Development Environment**: 
   - Git
   - Docker
   - Terraform (optional)
   - doctl (Digital Ocean CLI)

### Required Permissions

- GitHub repository admin access
- Digital Ocean project owner or admin access
- SSH key pair for server access
- SSL certificates (for production HTTPS)

## GitHub Repository Setup

### Step 1: Repository Creation and Initial Setup

First, create a new GitHub repository or use an existing one for the prescription validation system. The repository should contain all the application code, Docker configuration, and CI/CD workflows.

```bash
# Clone the repository
git clone https://github.com/your-username/prescription-validation-system.git
cd prescription-validation-system

# Ensure all CI/CD files are present
ls -la .github/workflows/
ls -la deployment/digitalocean/
```

### Step 2: Branch Strategy Configuration

The CI/CD pipeline uses a GitFlow-inspired branching strategy:

- **main**: Production-ready code, triggers production deployments
- **develop**: Integration branch, triggers staging deployments  
- **feature/***: Feature branches, triggers development testing
- **hotfix/***: Emergency fixes, can trigger direct production deployment

Configure branch protection rules in GitHub:

1. Navigate to Settings → Branches
2. Add protection rule for `main` branch:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date
   - Include administrators

### Step 3: Repository Secrets Configuration

Configure the following secrets in GitHub repository settings (Settings → Secrets and variables → Actions):

#### Digital Ocean Secrets
```
DIGITALOCEAN_ACCESS_TOKEN=your_do_api_token
DIGITALOCEAN_REGISTRY_NAME=your_registry_name
```

#### Server Access Secrets
```
DROPLET_HOST=your_production_server_ip
STAGING_DROPLET_HOST=your_staging_server_ip
DROPLET_USERNAME=deploy
DROPLET_SSH_KEY=your_private_ssh_key
DROPLET_PORT=22
```

#### Application Secrets
```
PRODUCTION_SECRET_KEY=your_production_secret_key
STAGING_SECRET_KEY=your_staging_secret_key
```

#### Optional Notification Secrets
```
SLACK_WEBHOOK=your_slack_webhook_url
```

## Digital Ocean Configuration

### Step 1: Account Setup and API Token

1. **Create Digital Ocean Account**: Sign up at digitalocean.com
2. **Generate API Token**:
   - Go to API → Tokens/Keys
   - Generate New Token with read/write scope
   - Save the token securely (add to GitHub secrets)

### Step 2: Container Registry Setup

Create a container registry to store Docker images:

```bash
# Using doctl CLI
doctl registry create prescription-validator-registry

# Or via web interface:
# Navigate to Container Registry → Create Registry
```

### Step 3: SSH Key Configuration

Generate and configure SSH keys for server access:

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "deployment@prescription-validator"

# Add public key to Digital Ocean
doctl compute ssh-key create deployment-key --public-key-file ~/.ssh/id_rsa.pub

# Add private key to GitHub secrets as DROPLET_SSH_KEY
```

### Step 4: Droplet Creation (Manual Method)

Create droplets for production and staging:

```bash
# Create production droplet
doctl compute droplet create prescription-validator-prod \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys deployment-key

# Create staging droplet  
doctl compute droplet create prescription-validator-staging \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-2gb \
  --region nyc3 \
  --ssh-keys deployment-key
```

### Step 5: Server Preparation

Run the setup script on each droplet:

```bash
# Copy setup script to server
scp deployment/digitalocean/setup-droplet.sh root@your_server_ip:/tmp/

# SSH to server and run setup
ssh root@your_server_ip
chmod +x /tmp/setup-droplet.sh
/tmp/setup-droplet.sh
```

## CI/CD Pipeline Configuration

### Workflow Overview

The CI/CD pipeline consists of three main workflows:

1. **Test Workflow** (`test.yml`): Runs on pull requests and develop branch
2. **Staging Deployment** (`staging.yml`): Deploys to staging environment
3. **Production Deployment** (`deploy.yml`): Deploys to production on main branch
4. **Release Workflow** (`release.yml`): Handles tagged releases

### Test Workflow Details

The test workflow performs comprehensive quality checks:

```yaml
# Key features of test.yml:
- Code linting with Black, isort, flake8
- Type checking with mypy
- Security scanning with Bandit and Safety
- Unit tests with pytest
- Integration tests
- Multi-Python version testing (3.9, 3.10, 3.11)
```

### Staging Deployment Workflow

Staging deployment provides a production-like environment for testing:

```yaml
# Key features of staging.yml:
- Triggered on develop branch pushes
- Builds and pushes staging Docker images
- Deploys to staging droplet on port 8080
- Runs integration tests against staging
- Notifies team of deployment status
```

### Production Deployment Workflow

Production deployment ensures reliable releases:

```yaml
# Key features of deploy.yml:
- Triggered on main branch pushes
- Comprehensive testing before deployment
- Blue-green deployment strategy
- Health checks and rollback capability
- Production monitoring integration
```

### Release Workflow

Release workflow handles versioned deployments:

```yaml
# Key features of release.yml:
- Triggered on git tags (v*)
- Security vulnerability scanning
- Creates GitHub releases
- Deploys specific versions to production
- Generates deployment artifacts
```

## Deployment Workflows

### Development Deployment

For feature development and testing:

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/new-validation-rule
   # Make changes
   git commit -m "Add new validation rule"
   git push origin feature/new-validation-rule
   ```

2. **Create Pull Request**: 
   - Triggers test workflow automatically
   - All tests must pass before merge
   - Code review required

3. **Merge to Develop**:
   - Triggers staging deployment
   - Available at staging URL for testing

### Staging Deployment

Staging deployment happens automatically when code is pushed to the develop branch:

1. **Automatic Trigger**: Push to develop branch
2. **Build Process**: 
   - Run tests
   - Build Docker image with staging tag
   - Push to container registry
3. **Deployment**:
   - Deploy to staging droplet
   - Run health checks
   - Notify team of status

### Production Deployment

Production deployment requires careful coordination:

1. **Merge to Main**: 
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

2. **Automatic Process**:
   - Comprehensive testing
   - Build production Docker image
   - Deploy with zero-downtime strategy
   - Health checks and monitoring

3. **Manual Verification**:
   - Verify application functionality
   - Monitor logs and metrics
   - Confirm deployment success

### Release Deployment

For versioned releases:

1. **Create Release Tag**:
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```

2. **Automated Process**:
   - Security scanning
   - Build versioned images
   - Deploy to production
   - Create GitHub release
   - Generate deployment artifacts

## Infrastructure as Code

### Terraform Configuration

The system includes Terraform configuration for infrastructure automation:

```bash
# Navigate to Terraform directory
cd deployment/digitalocean/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="do_token=your_token" -var="ssh_key_name=your_key"

# Apply configuration
terraform apply
```

### Terraform Resources

The Terraform configuration creates:

- **VPC**: Isolated network for resources
- **Droplets**: Web servers for application hosting
- **Firewall**: Security rules for network access
- **Container Registry**: Docker image storage
- **Load Balancer**: Traffic distribution (production)
- **Database**: PostgreSQL cluster (optional)
- **Domain**: DNS configuration (optional)

### Infrastructure Management

Managing infrastructure with Terraform:

```bash
# View current state
terraform show

# Update infrastructure
terraform plan
terraform apply

# Destroy infrastructure (careful!)
terraform destroy
```

## Monitoring and Maintenance

### Health Monitoring

The system includes comprehensive health monitoring:

1. **Application Health Checks**:
   - `/api/health` endpoint monitoring
   - Container health checks
   - Service availability monitoring

2. **Infrastructure Monitoring**:
   - Server resource usage
   - Docker container status
   - Network connectivity

3. **Automated Recovery**:
   - Container restart on failure
   - Service recovery scripts
   - Automated backup creation

### Logging and Debugging

Centralized logging for troubleshooting:

```bash
# View application logs
docker logs prescription-validation-system

# View system logs
journalctl -u prescription-validator

# View deployment logs
tail -f /opt/prescription-validator/logs/app.log
```

### Backup and Recovery

Automated backup system:

1. **Daily Backups**:
   - Database snapshots
   - File uploads backup
   - Configuration backup

2. **Backup Retention**:
   - 7 days of daily backups
   - 4 weeks of weekly backups
   - 12 months of monthly backups

3. **Recovery Procedures**:
   - Database restoration
   - File recovery
   - Full system recovery

### Performance Optimization

Continuous performance monitoring and optimization:

1. **Application Performance**:
   - Response time monitoring
   - Resource usage tracking
   - Error rate monitoring

2. **Infrastructure Optimization**:
   - Server scaling recommendations
   - Resource allocation tuning
   - Cost optimization

## Troubleshooting

### Common Issues and Solutions

#### Deployment Failures

**Issue**: Docker image build fails
```bash
# Solution: Check Dockerfile and dependencies
docker build -t test-image .
docker run --rm test-image python -c "import src.main"
```

**Issue**: Container registry authentication fails
```bash
# Solution: Refresh registry login
doctl registry login --expiry-seconds 1200
```

**Issue**: Health check failures
```bash
# Solution: Check application logs and configuration
curl -v http://localhost:5000/api/health
docker logs prescription-validation-system
```

#### GitHub Actions Issues

**Issue**: Workflow fails on secrets
```bash
# Solution: Verify secrets are configured correctly
# Check GitHub repository settings → Secrets
```

**Issue**: SSH connection failures
```bash
# Solution: Verify SSH key configuration
ssh -i ~/.ssh/deployment_key deploy@server_ip
```

#### Server Issues

**Issue**: Out of disk space
```bash
# Solution: Clean up old Docker images and logs
docker system prune -f
find /opt/prescription-validator/logs -name "*.log" -mtime +30 -delete
```

**Issue**: Memory issues
```bash
# Solution: Monitor and optimize resource usage
htop
docker stats
```

### Debugging Workflows

Step-by-step debugging process:

1. **Check Workflow Status**: Review GitHub Actions logs
2. **Verify Secrets**: Ensure all required secrets are configured
3. **Test Locally**: Reproduce issues in local environment
4. **Check Server Status**: Verify server health and resources
5. **Review Logs**: Examine application and system logs
6. **Rollback if Necessary**: Use deployment rollback procedures

## Security Considerations

### Security Best Practices

The CI/CD pipeline implements multiple security layers:

1. **Code Security**:
   - Automated security scanning with Bandit
   - Dependency vulnerability checks with Safety
   - Code quality enforcement with linting

2. **Infrastructure Security**:
   - Firewall configuration
   - SSH key-based authentication
   - Regular security updates

3. **Deployment Security**:
   - Secrets management with GitHub Secrets
   - Container image scanning
   - Network isolation with VPC

4. **Runtime Security**:
   - Non-root container execution
   - Resource limits and quotas
   - Regular backup and recovery testing

### Security Monitoring

Continuous security monitoring includes:

1. **Vulnerability Scanning**: Regular scans of dependencies and containers
2. **Access Monitoring**: SSH access logging and monitoring
3. **Network Security**: Firewall logs and intrusion detection
4. **Application Security**: Input validation and error handling

### Incident Response

Security incident response procedures:

1. **Detection**: Automated alerts and monitoring
2. **Assessment**: Rapid security assessment
3. **Containment**: Immediate threat containment
4. **Recovery**: System recovery and hardening
5. **Documentation**: Incident documentation and lessons learned

This comprehensive CI/CD deployment guide provides all the necessary information to set up, deploy, and maintain the AI-Based Digital Prescription Validation System on Digital Ocean with automated CI/CD pipelines. The system is designed for reliability, security, and scalability in production environments.

