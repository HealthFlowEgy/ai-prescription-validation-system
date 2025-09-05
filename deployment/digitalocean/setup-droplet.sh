#!/bin/bash

# Digital Ocean Droplet Setup Script for Prescription Validation System
# This script sets up a fresh Ubuntu droplet for deployment

set -e

echo "🚀 Setting up Digital Ocean Droplet for Prescription Validation System"

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop \
    nginx \
    tesseract-ocr \
    tesseract-ocr-eng

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
echo "🔗 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install doctl (DigitalOcean CLI)
echo "⚙️ Installing doctl..."
cd /tmp
wget https://github.com/digitalocean/doctl/releases/download/v1.104.0/doctl-1.104.0-linux-amd64.tar.gz
tar xf doctl-1.104.0-linux-amd64.tar.gz
sudo mv doctl /usr/local/bin
cd -

# Create application directories
echo "📁 Creating application directories..."
sudo mkdir -p /opt/prescription-validator/{uploads,data,logs,backups}
sudo mkdir -p /opt/prescription-validator-staging/{uploads,data,logs,backups}

# Set proper permissions
sudo chown -R $USER:$USER /opt/prescription-validator*

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp  # For staging
sudo ufw --force enable

# Configure fail2ban
echo "🛡️ Configuring fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Create systemd service for the application
echo "⚡ Creating systemd service..."
sudo tee /etc/systemd/system/prescription-validator.service > /dev/null <<EOF
[Unit]
Description=Prescription Validation System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/prescription-validator
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable prescription-validator.service

# Create backup script
echo "💾 Creating backup script..."
sudo tee /usr/local/bin/backup-prescription-validator.sh > /dev/null <<'EOF'
#!/bin/bash

BACKUP_DIR="/opt/prescription-validator/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_$DATE"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup database
if [ -f "/opt/prescription-validator/data/production.db" ]; then
    cp /opt/prescription-validator/data/production.db $BACKUP_DIR/production_$DATE.db
fi

# Backup uploads
if [ -d "/opt/prescription-validator/uploads" ]; then
    tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/prescription-validator uploads/
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_NAME"
EOF

sudo chmod +x /usr/local/bin/backup-prescription-validator.sh

# Create cron job for daily backups
echo "⏰ Setting up daily backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-prescription-validator.sh") | crontab -

# Create log rotation configuration
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/prescription-validator > /dev/null <<EOF
/opt/prescription-validator/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER $USER
}
EOF

# Create monitoring script
echo "📊 Creating monitoring script..."
sudo tee /usr/local/bin/monitor-prescription-validator.sh > /dev/null <<'EOF'
#!/bin/bash

CONTAINER_NAME="prescription-validation-system"
HEALTH_URL="http://localhost/api/health"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "$(date): Container $CONTAINER_NAME is not running" >> /var/log/prescription-validator-monitor.log
    # Restart the service
    systemctl restart prescription-validator.service
fi

# Check health endpoint
if ! curl -f $HEALTH_URL > /dev/null 2>&1; then
    echo "$(date): Health check failed for $HEALTH_URL" >> /var/log/prescription-validator-monitor.log
    # Restart the service
    systemctl restart prescription-validator.service
fi
EOF

sudo chmod +x /usr/local/bin/monitor-prescription-validator.sh

# Add monitoring to cron (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/monitor-prescription-validator.sh") | crontab -

# Create SSL certificate directory
echo "🔒 Creating SSL certificate directory..."
sudo mkdir -p /etc/nginx/ssl

# Generate self-signed certificate (replace with real certificate in production)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set proper permissions for SSL certificates
sudo chmod 600 /etc/nginx/ssl/key.pem
sudo chmod 644 /etc/nginx/ssl/cert.pem

# Create environment file template
echo "🔧 Creating environment file template..."
tee /opt/prescription-validator/.env.template > /dev/null <<EOF
# Production Environment Variables
FLASK_ENV=production
SECRET_KEY=your-production-secret-key-here
DATABASE_URL=sqlite:///data/production.db

# Optional: PostgreSQL configuration
# DATABASE_URL=postgresql://username:password@localhost:5432/prescription_validator

# Optional: Redis configuration
# REDIS_URL=redis://localhost:6379/0

# Optional: Monitoring
# SENTRY_DSN=your-sentry-dsn-here

# Optional: Email configuration
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password

# File upload limits
MAX_CONTENT_LENGTH=16777216

# OCR Configuration
TESSERACT_CMD=/usr/bin/tesseract
OCR_LANGUAGE=eng
EOF

echo "✅ Droplet setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy your application code to /opt/prescription-validator/"
echo "2. Configure environment variables in /opt/prescription-validator/.env"
echo "3. Set up your DigitalOcean Container Registry credentials"
echo "4. Configure your domain and SSL certificates"
echo "5. Start the application: sudo systemctl start prescription-validator"
echo ""
echo "Useful commands:"
echo "- Check application status: sudo systemctl status prescription-validator"
echo "- View application logs: docker logs prescription-validation-system"
echo "- Run backup manually: /usr/local/bin/backup-prescription-validator.sh"
echo "- Monitor application: /usr/local/bin/monitor-prescription-validator.sh"
echo ""
echo "🎉 Your droplet is ready for deployment!"

