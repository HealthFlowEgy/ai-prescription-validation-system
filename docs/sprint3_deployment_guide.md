# Sprint 3 Deployment Guide
## HealthFlow AI - Model Governance & Clinical Safety

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Service Installation](#service-installation)
4. [Configuration](#configuration)
5. [Deployment Steps](#deployment-steps)
6. [Verification](#verification)
7. [Monitoring Setup](#monitoring-setup)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **Python** >= 3.10
- **PostgreSQL** >= 15
- **Redis** >= 7.0
- **MLflow** >= 2.8

### Required Credentials
- AWS credentials (for S3 artifact storage)
- Encryption key for PHI
- JWT secret key
- Database passwords

### Hardware Requirements

**Minimum (Development):**
- 8 GB RAM
- 4 CPU cores
- 50 GB disk space

**Recommended (Production):**
- 32 GB RAM
- 16 CPU cores
- 500 GB SSD storage
- Multiple availability zones

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/HealthFlowEgy/ai-prescription-validation-system.git
cd ai-prescription-validation-system
git checkout sprint-3-model-governance
```

### 2. Create Environment File

Create `.env` file in project root:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=healthflow_user
POSTGRES_DB=healthflow

# Redis Configuration
REDIS_PASSWORD=your_redis_password_here

# RabbitMQ Configuration
RABBITMQ_USER=healthflow
RABBITMQ_PASSWORD=your_rabbitmq_password_here

# Security Keys
PHI_ENCRYPTION_KEY=generate_with_fernet
JWT_SECRET_KEY=your_jwt_secret_key_here

# AWS Configuration (for MLflow artifacts)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET=healthflow-mlflow-artifacts

# Monitoring
GRAFANA_PASSWORD=your_grafana_password

# Application
FLASK_ENV=production
LOG_LEVEL=INFO
```

### 3. Generate Encryption Keys

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `PHI_ENCRYPTION_KEY` in `.env`

### 4. Set Up AWS S3 Bucket

```bash
# Create S3 bucket for MLflow artifacts
aws s3 mb s3://healthflow-mlflow-artifacts --region us-east-1

# Set lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket healthflow-mlflow-artifacts \
  --lifecycle-configuration file://s3-lifecycle.json
```

---

## Service Installation

### 1. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Build Docker Images

```bash
# Build all images
docker-compose build

# Or build specific services
docker-compose build api
docker-compose build celery-worker
```

### 3. Initialize Database

```bash
# Start PostgreSQL
docker-compose up -d postgres-primary

# Wait for database to be ready
sleep 10

# Run migrations
docker-compose exec postgres-primary psql -U healthflow_user -d healthflow -f /docker-entrypoint-initdb.d/init.sql
```

---

## Configuration

### 1. MLflow Configuration

Create `mlflow/config.yml`:

```yaml
tracking_uri: http://mlflow:5000
artifact_location: s3://healthflow-mlflow-artifacts
experiment_name: prescription-ocr-validation

models:
  ocr:
    name: prescription-ocr-v1
    production_version: 1
    staging_version: 2
  
  nlp:
    name: prescription-nlp-v1
    production_version: 1
    staging_version: 2
```

### 2. Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
upstream api_backend {
    least_conn;
    server api:5000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name healthflow.ai;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name healthflow.ai;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/healthflow.crt;
    ssl_certificate_key /etc/nginx/ssl/healthflow.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API Proxy
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://api_backend/health;
        access_log off;
    }

    # MLflow UI
    location /mlflow/ {
        proxy_pass http://mlflow:5000/;
        proxy_set_header Host $host;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://grafana:3000/;
        proxy_set_header Host $host;
    }
}
```

### 3. Prometheus Configuration

Create `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'healthflow-api'
    static_configs:
      - targets: ['api:5000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/alerts.yml'
```

### 4. Grafana Dashboards

Create `grafana/dashboards/healthflow.json` with dashboards for:
- API performance metrics
- Model inference metrics
- Database performance
- System resources
- Clinical validation metrics

---

## Deployment Steps

### Step 1: Start Infrastructure Services

```bash
# Start databases and message queue
docker-compose up -d postgres-primary postgres-replica redis-master redis-replica rabbitmq

# Wait for services to be healthy
docker-compose ps
```

### Step 2: Initialize MLflow

```bash
# Start MLflow
docker-compose up -d mlflow

# Wait for MLflow to be ready
sleep 10

# Register initial models
python scripts/register_models.py
```

### Step 3: Start Application Services

```bash
# Start API and workers
docker-compose up -d api celery-worker

# Verify services are running
docker-compose logs -f api
```

### Step 4: Start Monitoring Stack

```bash
# Start monitoring services
docker-compose up -d prometheus grafana jaeger elasticsearch logstash kibana

# Wait for services
sleep 30

# Access Grafana
open http://localhost:3000
```

### Step 5: Configure Load Balancer

```bash
# Start Nginx
docker-compose up -d nginx

# Test configuration
docker-compose exec nginx nginx -t

# Reload if needed
docker-compose exec nginx nginx -s reload
```

### Step 6: Start Backup Service

```bash
# Start backup service
docker-compose up -d backup

# Test backup immediately
docker-compose exec backup /scripts/backup-now.sh
```

---

## Verification

### 1. Health Checks

```bash
# Basic health check
curl http://localhost/health

# Detailed health check (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost/api/health/detailed
```

### 2. Test API Endpoints

```bash
# Upload test prescription
curl -X POST http://localhost/api/prescriptions/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_prescription.jpg" \
  -F "patient_context={\"current_medications\":[]}"

# Get metrics
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost/api/metrics/current

# Check model versions
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost/api/models/prescription-ocr-v1/versions
```

### 3. Verify Database

```bash
# Connect to database
docker-compose exec postgres-primary psql -U healthflow_user -d healthflow

# Check tables
\dt

# Check encryption
SELECT prescription_id, patient_name FROM prescriptions LIMIT 1;
# patient_name should be encrypted
```

### 4. Verify Replication

```bash
# Check replication status
docker-compose exec postgres-primary psql -U healthflow_user -c "SELECT * FROM pg_stat_replication;"

# Verify replica
docker-compose exec postgres-replica psql -U healthflow_user -d healthflow -c "SELECT count(*) FROM prescriptions;"
```

### 5. Test Monitoring

```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Check Grafana dashboards
open http://localhost:3000/dashboards

# Check Jaeger traces
open http://localhost:16686
```

---

## Monitoring Setup

### 1. Configure Grafana Dashboards

1. Login to Grafana (admin/your_grafana_password)
2. Import dashboards from `grafana/dashboards/`
3. Configure alert notifications:
   - Email
   - Slack
   - PagerDuty

### 2. Set Up Alerts

Create `prometheus/alerts.yml`:

```yaml
groups:
  - name: healthflow_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"
      
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times"
          description: "P95 latency is {{ $value }}s"
      
      - alert: ModelDriftDetected
        expr: model_drift_detected == 1
        for: 1m
        labels:
          severity: high
        annotations:
          summary: "Model performance drift detected"
          description: "Model drift detected - retraining recommended"
      
      - alert: LowModelConfidence
        expr: avg_over_time(model_confidence[10m]) < 0.80
        for: 10m
        labels:
          severity: medium
        annotations:
          summary: "Low model confidence"
          description: "Average confidence is {{ $value }}"
```

### 3. Configure Log Aggregation

1. Access Kibana: http://localhost:5601
2. Create index patterns for application logs
3. Set up log parsing rules
4. Create dashboards for:
   - Error logs
   - PHI access logs
   - API request logs

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

#### 2. Database Connection Issues

```bash
# Check database logs
docker-compose logs postgres-primary

# Verify connection
docker-compose exec postgres-primary pg_isready

# Check connections
docker-compose exec postgres-primary psql -U healthflow_user -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 3. MLflow Not Loading Models

```bash
# Check MLflow logs
docker-compose logs mlflow

# Verify S3 connection
docker-compose exec mlflow aws s3 ls s3://healthflow-mlflow-artifacts/

# Re-register models
python scripts/register_models.py
```

#### 4. High Memory Usage

```bash
# Check resource usage
docker stats

# Adjust limits in docker-compose.yml
# For each service:
deploy:
  resources:
    limits:
      memory: 2G
```

#### 5. Encryption Errors

```bash
# Verify encryption key is set
docker-compose exec api env | grep PHI_ENCRYPTION_KEY

# Test encryption
docker-compose exec api python -c "from phi_encryption import EncryptionService; EncryptionService()"
```

### Performance Tuning

#### 1. PostgreSQL

```sql
-- Tune PostgreSQL settings
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
SELECT pg_reload_conf();
```

#### 2. Redis

```bash
# Update redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru
```

#### 3. API Workers

```bash
# Adjust Gunicorn workers in docker-compose.yml
command: gunicorn -w 8 -b 0.0.0.0:5000 --timeout 120 enhanced_api:app
```

---

## Security Checklist

- [ ] All passwords changed from defaults
- [ ] PHI encryption key generated and secured
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Database backup enabled
- [ ] Audit logging enabled
- [ ] Access controls configured
- [ ] Vulnerability scan completed
- [ ] Penetration testing completed

---

## Maintenance

### Daily Tasks
- Monitor alerts
- Review error logs
- Check system health

### Weekly Tasks
- Review audit logs
- Check backup integrity
- Review performance metrics
- Update security patches

### Monthly Tasks
- Review and rotate logs
- Test disaster recovery
- Update dependencies
- Review access permissions

---

## Rollback Procedure

If deployment fails:

```bash
# Stop new services
docker-compose down

# Restore from backup
./scripts/restore-backup.sh [backup-date]

# Start previous version
git checkout [previous-tag]
docker-compose up -d

# Verify
curl http://localhost/health
```

---

## Support

For issues or questions:
- Email: support@healthflow.ai
- Slack: #healthflow-support
- Documentation: https://docs.healthflow.ai

---

## Next Steps

After successful deployment:

1. **Week 1-2**: Monitor closely, tune performance
2. **Week 3-4**: Gradual traffic increase (10% → 50% → 100%)
3. **Month 2**: Clinical validation study
4. **Month 3**: Full production rollout

**Remember**: This is healthcare software. Patient safety is paramount. When in doubt, require human review.