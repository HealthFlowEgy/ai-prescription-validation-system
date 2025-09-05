# Quick Start Deployment Guide

## 🚀 Deploy to Digital Ocean in 15 Minutes

This guide will get your AI-Based Digital Prescription Validation System deployed to Digital Ocean with CI/CD in under 15 minutes.

## Prerequisites Checklist

- [ ] GitHub account with repository access
- [ ] Digital Ocean account with billing configured
- [ ] Domain name (optional but recommended)
- [ ] SSH key pair generated

## Step 1: Digital Ocean Setup (5 minutes)

### 1.1 Create API Token
```bash
# Go to: https://cloud.digitalocean.com/account/api/tokens
# Click "Generate New Token"
# Name: "prescription-validator-cicd"
# Scopes: Read and Write
# Save the token securely
```

### 1.2 Create Container Registry
```bash
# Install doctl if not already installed
curl -sL https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz | tar -xzv
sudo mv doctl /usr/local/bin

# Authenticate with Digital Ocean
doctl auth init

# Create container registry
doctl registry create prescription-validator-registry
```

### 1.3 Create SSH Key
```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/prescription_validator_deploy

# Add public key to Digital Ocean
doctl compute ssh-key create prescription-validator-deploy \
  --public-key-file ~/.ssh/prescription_validator_deploy.pub
```

## Step 2: GitHub Repository Setup (3 minutes)

### 2.1 Fork or Create Repository
```bash
# Option 1: Fork the repository
# Go to GitHub and fork the repository

# Option 2: Create new repository and push code
git clone <your-repo-url>
cd prescription-validation-system
git remote set-url origin <your-github-repo-url>
git push -u origin main
```

### 2.2 Configure Repository Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
```
DIGITALOCEAN_ACCESS_TOKEN=your_do_api_token_here
DIGITALOCEAN_REGISTRY_NAME=prescription-validator-registry
DROPLET_USERNAME=root
DROPLET_SSH_KEY=contents_of_private_key_file
PRODUCTION_SECRET_KEY=your_random_secret_key_here
STAGING_SECRET_KEY=your_random_staging_secret_key_here
```

## Step 3: Infrastructure Deployment (5 minutes)

### 3.1 Deploy with Terraform (Recommended)
```bash
cd deployment/digitalocean/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars file
cat > terraform.tfvars << EOF
do_token = "your_digitalocean_api_token"
ssh_key_name = "prescription-validator-deploy"
project_name = "prescription-validator"
environment = "production"
region = "nyc3"
droplet_size = "s-2vcpu-4gb"
domain_name = "yourdomain.com"  # Optional
EOF

# Deploy infrastructure
terraform plan
terraform apply -auto-approve
```

### 3.2 Manual Droplet Creation (Alternative)
```bash
# Create production droplet
doctl compute droplet create prescription-validator-prod \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3 \
  --ssh-keys prescription-validator-deploy \
  --wait

# Get droplet IP
DROPLET_IP=$(doctl compute droplet get prescription-validator-prod --format PublicIPv4 --no-header)
echo "Droplet IP: $DROPLET_IP"
```

## Step 4: Server Setup (2 minutes)

### 4.1 Run Setup Script
```bash
# Get droplet IP (if using Terraform)
DROPLET_IP=$(terraform output -raw web_droplet_ip)

# Copy and run setup script
scp -i ~/.ssh/prescription_validator_deploy deployment/digitalocean/setup-droplet.sh root@$DROPLET_IP:/tmp/
ssh -i ~/.ssh/prescription_validator_deploy root@$DROPLET_IP "chmod +x /tmp/setup-droplet.sh && /tmp/setup-droplet.sh"
```

### 4.2 Update GitHub Secrets
Add the droplet IP to GitHub secrets:
```
DROPLET_HOST=your_droplet_ip_here
DROPLET_PORT=22
```

## Step 5: Deploy Application (1 minute)

### 5.1 Trigger Deployment
```bash
# Push to main branch to trigger production deployment
git add .
git commit -m "Initial deployment setup"
git push origin main
```

### 5.2 Monitor Deployment
- Go to GitHub → Actions tab
- Watch the "CI/CD Pipeline for Digital Ocean Deployment" workflow
- Deployment typically takes 3-5 minutes

## Step 6: Verify Deployment

### 6.1 Check Application Health
```bash
# Test health endpoint
curl http://$DROPLET_IP/api/health

# Expected response:
# {"status": "healthy", "service": "AI-Based Digital Prescription Validation System"}
```

### 6.2 Access Web Interface
```bash
# Open in browser
open http://$DROPLET_IP
# Or visit: http://your-droplet-ip
```

## Step 7: Configure Domain (Optional)

### 7.1 DNS Configuration
If you have a domain name:
```bash
# Add A record pointing to your droplet IP
# Example: prescription-validator.yourdomain.com → your_droplet_ip
```

### 7.2 SSL Certificate
```bash
# SSH to server
ssh -i ~/.ssh/prescription_validator_deploy root@$DROPLET_IP

# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

## Troubleshooting Quick Fixes

### Issue: GitHub Actions Failing
```bash
# Check secrets are configured correctly
# Verify SSH key format (no extra spaces/newlines)
# Ensure API token has correct permissions
```

### Issue: Container Registry Authentication
```bash
# Re-authenticate with registry
doctl registry login --expiry-seconds 1200
```

### Issue: Application Not Starting
```bash
# Check container logs
ssh -i ~/.ssh/prescription_validator_deploy root@$DROPLET_IP
docker logs prescription-validation-system

# Restart container
docker restart prescription-validation-system
```

### Issue: Health Check Failing
```bash
# Check if Tesseract is installed
ssh -i ~/.ssh/prescription_validator_deploy root@$DROPLET_IP
tesseract --version

# Check application logs
docker logs prescription-validation-system | tail -50
```

## Next Steps

### Set Up Staging Environment
```bash
# Create staging droplet
doctl compute droplet create prescription-validator-staging \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-2gb \
  --region nyc3 \
  --ssh-keys prescription-validator-deploy

# Add staging IP to GitHub secrets as STAGING_DROPLET_HOST
```

### Configure Monitoring
```bash
# Set up Slack notifications (optional)
# Add SLACK_WEBHOOK to GitHub secrets

# Set up log monitoring
# Configure log aggregation service
```

### Enable Automatic Backups
```bash
# Backups are automatically configured
# Check backup status
ssh -i ~/.ssh/prescription_validator_deploy root@$DROPLET_IP
ls -la /opt/prescription-validator/backups/
```

## Success Checklist

- [ ] Application accessible at http://your-droplet-ip
- [ ] Health check returns "healthy" status
- [ ] File upload functionality works
- [ ] GitHub Actions workflow completes successfully
- [ ] SSL certificate configured (if using domain)
- [ ] Monitoring and backups configured

## Support and Resources

- **GitHub Repository**: Your forked repository with all code
- **Digital Ocean Dashboard**: Monitor droplets and resources
- **Application Logs**: `docker logs prescription-validation-system`
- **System Logs**: `journalctl -u prescription-validator`
- **Backup Location**: `/opt/prescription-validator/backups/`

## Cost Estimation

**Monthly Costs (USD)**:
- Production Droplet (2 vCPU, 4GB): ~$24/month
- Staging Droplet (1 vCPU, 2GB): ~$12/month
- Container Registry: ~$5/month
- Load Balancer (optional): ~$12/month
- **Total**: ~$41-53/month

**Cost Optimization Tips**:
- Use smaller droplets for staging
- Enable droplet monitoring to optimize resources
- Set up automatic scaling for production traffic
- Use snapshots for backup instead of additional storage

🎉 **Congratulations!** Your AI-Based Digital Prescription Validation System is now deployed with full CI/CD pipeline on Digital Ocean!

