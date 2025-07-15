# Deployment Guide - AI-Based Digital Prescription Validation System

This guide provides comprehensive instructions for deploying the AI-Based Digital Prescription Validation System in various environments.

## Quick Start Deployment

### Local Development

1. **Prerequisites**
   ```bash
   # Install Python 3.11+
   python3 --version
   
   # Install Tesseract OCR
   sudo apt-get install tesseract-ocr  # Ubuntu/Debian
   brew install tesseract              # macOS
   ```

2. **Setup Application**
   ```bash
   cd prescription_validation_system
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python src/database/init_db.py init
   python src/main.py
   ```

3. **Access Application**
   - Open browser to `http://localhost:5000`
   - Upload a prescription image to test functionality

### Production Deployment

#### Using Gunicorn (Recommended)

1. **Install Gunicorn**
   ```bash
   pip install gunicorn
   ```

2. **Create Gunicorn Configuration**
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:5000"
   workers = 4
   worker_class = "sync"
   worker_connections = 1000
   timeout = 30
   keepalive = 2
   max_requests = 1000
   max_requests_jitter = 100
   preload_app = True
   ```

3. **Start Application**
   ```bash
   gunicorn -c gunicorn.conf.py src.main:app
   ```

#### Using Docker

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       tesseract-ocr \
       tesseract-ocr-eng \
       && rm -rf /var/lib/apt/lists/*
   
   WORKDIR /app
   
   # Install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create uploads directory
   RUN mkdir -p uploads
   
   # Initialize database
   RUN python src/database/init_db.py init
   
   EXPOSE 5000
   
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.main:app"]
   ```

2. **Build and Run**
   ```bash
   docker build -t prescription-validator .
   docker run -p 5000:5000 -v $(pwd)/uploads:/app/uploads prescription-validator
   ```

#### Using Docker Compose

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "5000:5000"
       volumes:
         - ./uploads:/app/uploads
         - ./data:/app/data
       environment:
         - FLASK_ENV=production
         - DATABASE_URL=sqlite:///data/production.db
       restart: unless-stopped
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
       depends_on:
         - app
       restart: unless-stopped
   ```

2. **Create Nginx Configuration**
   ```nginx
   # nginx.conf
   events {
       worker_connections 1024;
   }
   
   http {
       upstream app {
           server app:5000;
       }
   
       server {
           listen 80;
           client_max_body_size 10M;
   
           location / {
               proxy_pass http://app;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }
   }
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

## Cloud Deployment

### AWS Deployment

#### Using Elastic Beanstalk

1. **Install EB CLI**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB Application**
   ```bash
   eb init prescription-validator
   eb create production
   ```

3. **Deploy**
   ```bash
   eb deploy
   ```

#### Using ECS

1. **Create Task Definition**
   ```json
   {
     "family": "prescription-validator",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "app",
         "image": "your-account.dkr.ecr.region.amazonaws.com/prescription-validator:latest",
         "portMappings": [
           {
             "containerPort": 5000,
             "protocol": "tcp"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/prescription-validator",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

### Google Cloud Platform

#### Using Cloud Run

1. **Build and Push Image**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/prescription-validator
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy prescription-validator \
     --image gcr.io/PROJECT_ID/prescription-validator \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Azure Deployment

#### Using Container Instances

1. **Create Resource Group**
   ```bash
   az group create --name prescription-validator-rg --location eastus
   ```

2. **Deploy Container**
   ```bash
   az container create \
     --resource-group prescription-validator-rg \
     --name prescription-validator \
     --image your-registry/prescription-validator:latest \
     --dns-name-label prescription-validator \
     --ports 5000
   ```

## Environment Configuration

### Environment Variables

Set these environment variables for production:

```bash
# Application Configuration
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
export DEBUG=False

# Database Configuration
export DATABASE_URL=sqlite:///data/production.db

# File Upload Configuration
export UPLOAD_FOLDER=/app/uploads
export MAX_CONTENT_LENGTH=16777216  # 16MB

# OCR Configuration
export TESSERACT_CMD=/usr/bin/tesseract
export OCR_LANGUAGE=eng

# Logging Configuration
export LOG_LEVEL=INFO
export LOG_FILE=/app/logs/app.log
```

### Configuration Files

Create `src/config/production.py`:

```python
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///production.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    
    # OCR settings
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD') or 'tesseract'
    OCR_LANGUAGE = os.environ.get('OCR_LANGUAGE') or 'eng'
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
```

## Security Considerations

### SSL/TLS Configuration

1. **Obtain SSL Certificate**
   ```bash
   # Using Let's Encrypt
   sudo certbot --nginx -d yourdomain.com
   ```

2. **Update Nginx Configuration**
   ```nginx
   server {
       listen 443 ssl;
       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/private.key;
       
       location / {
           proxy_pass http://app:5000;
           proxy_set_header X-Forwarded-Proto https;
       }
   }
   ```

### Firewall Configuration

```bash
# Allow HTTP and HTTPS traffic
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow 22

# Enable firewall
sudo ufw enable
```

### Application Security

1. **Input Validation**: All user inputs are validated
2. **File Upload Security**: File types and sizes are restricted
3. **SQL Injection Prevention**: Using SQLAlchemy ORM
4. **XSS Protection**: Input sanitization implemented
5. **CSRF Protection**: Consider implementing CSRF tokens

## Monitoring and Logging

### Application Monitoring

1. **Health Check Endpoint**
   ```bash
   curl http://localhost:5000/api/health
   ```

2. **Log Monitoring**
   ```bash
   tail -f /app/logs/app.log
   ```

### System Monitoring

1. **Resource Usage**
   ```bash
   docker stats prescription-validator
   ```

2. **Application Metrics**
   - Response times
   - Error rates
   - Upload success rates
   - Validation accuracy

### Alerting

Set up alerts for:
- Application downtime
- High error rates
- Resource exhaustion
- Failed validations

## Backup and Recovery

### Database Backup

1. **Automated Backup**
   ```bash
   # Create backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   python src/database/backup.py backup --name "backup_$DATE"
   ```

2. **Schedule Backups**
   ```bash
   # Add to crontab
   0 2 * * * /path/to/backup_script.sh
   ```

### File Backup

```bash
# Backup uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

### Recovery Procedures

1. **Database Recovery**
   ```bash
   python src/database/backup.py restore --file backup_file.json
   ```

2. **File Recovery**
   ```bash
   tar -xzf uploads_backup.tar.gz
   ```

## Performance Optimization

### Application Optimization

1. **Database Indexing**
   - Add indexes on frequently queried fields
   - Optimize query patterns

2. **Caching**
   - Implement Redis for session storage
   - Cache OCR results for duplicate images

3. **Async Processing**
   - Use Celery for background tasks
   - Queue prescription processing

### Infrastructure Optimization

1. **Load Balancing**
   ```nginx
   upstream app_servers {
       server app1:5000;
       server app2:5000;
       server app3:5000;
   }
   ```

2. **CDN Configuration**
   - Serve static files from CDN
   - Cache API responses where appropriate

## Troubleshooting

### Common Issues

1. **Tesseract Not Found**
   ```bash
   # Check installation
   which tesseract
   tesseract --version
   
   # Install if missing
   sudo apt-get install tesseract-ocr
   ```

2. **Database Connection Issues**
   ```bash
   # Check database file permissions
   ls -la data/
   
   # Reinitialize if needed
   python src/database/init_db.py reset
   ```

3. **File Upload Failures**
   ```bash
   # Check upload directory permissions
   chmod 755 uploads/
   
   # Check disk space
   df -h
   ```

### Log Analysis

```bash
# Check application logs
grep ERROR /app/logs/app.log

# Check system logs
journalctl -u prescription-validator

# Check Docker logs
docker logs prescription-validator
```

## Maintenance

### Regular Maintenance Tasks

1. **Log Rotation**
   ```bash
   # Configure logrotate
   /app/logs/app.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

2. **Database Maintenance**
   ```bash
   # Vacuum SQLite database
   sqlite3 data/production.db "VACUUM;"
   ```

3. **Security Updates**
   ```bash
   # Update system packages
   sudo apt-get update && sudo apt-get upgrade
   
   # Update Python packages
   pip install --upgrade -r requirements.txt
   ```

### Scaling Considerations

1. **Horizontal Scaling**
   - Deploy multiple application instances
   - Use load balancer for distribution
   - Implement session storage (Redis)

2. **Database Scaling**
   - Consider PostgreSQL for production
   - Implement read replicas
   - Database connection pooling

3. **File Storage Scaling**
   - Use cloud storage (S3, GCS, Azure Blob)
   - Implement file cleanup policies
   - Consider CDN for file delivery

This deployment guide provides comprehensive instructions for deploying the AI-Based Digital Prescription Validation System in various environments. Choose the deployment method that best fits your infrastructure requirements and security needs.

