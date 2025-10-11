# Production Integration Guide

**Version:** 2.1.0  
**Date:** October 7, 2025  
**Status:** Ready for Integration

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Integration Steps](#detailed-integration-steps)
4. [Database Migration](#database-migration)
5. [Testing](#testing)
6. [Deployment](#deployment)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Python 3.11+
- PostgreSQL 15+
- Docker 20.10+
- Git 2.30+

### Required Environment Variables
```bash
# Core
FLASK_ENV=production
SECRET_KEY=<generate-with-openssl>
JWT_SECRET_KEY=<generate-with-openssl>

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Monitoring (Optional but Recommended)
SENTRY_DSN=https://your-key@sentry.io/project-id

# Redis (Optional)
REDIS_URL=redis://localhost:6379/0

# OpenAI (Existing)
OPENAI_API_KEY=<your-key>
```

### Generate Secure Keys
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32
```

---

## Quick Start

### Option 1: Local Development

```bash
# 1. Clone repository
git clone https://github.com/HealthFlowEgy/ai-prescription-validation-system.git
cd ai-prescription-validation-system

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Set up environment
cp .env.production.example .env
# Edit .env with your values

# 5. Set up PostgreSQL
createdb prescription_validator_dev

# 6. Run migrations
alembic upgrade head

# 7. Create admin user
python -c "
from src.main_integrated import app, db
from src.models.user_updated import User
from src.services.auth_service import AuthService

with app.app_context():
    admin = User(
        username='admin',
        email='admin@healthflow.com',
        name='System Administrator',
        role='admin',
        is_active=True,
        is_verified=True
    )
    admin.password_hash = AuthService.hash_password('Admin123!')
    db.session.add(admin)
    db.session.commit()
    print('✅ Admin user created: admin@healthflow.com / Admin123!')
"

# 8. Run application
python src/main_integrated.py
```

### Option 2: Docker

```bash
# 1. Build image
docker build -f Dockerfile.production -t prescription-validator:latest .

# 2. Run with docker-compose
docker-compose up -d

# 3. Check health
curl http://localhost:5000/api/health
```

---

## Detailed Integration Steps

### Step 1: Update User Model

**File:** `src/models/user.py`

**Action:** Replace the existing user model with the enhanced version.

```bash
# Backup current model
cp src/models/user.py src/models/user.py.backup

# Use updated model
cp src/models/user_updated.py src/models/user.py
```

**What Changed:**
- Added `password_hash` field for authentication
- Added `role`, `is_active`, `is_verified` for authorization
- Added `created_at`, `updated_at`, `last_login` for auditing
- Added helper methods: `set_password()`, `check_password()`, `has_role()`

### Step 2: Update Main Application

**File:** `src/main.py`

**Action:** Integrate production-ready components.

```bash
# Backup current main.py
cp src/main.py src/main.py.backup

# Option A: Use integrated version (recommended for new setup)
cp src/main_integrated.py src/main.py

# Option B: Manually integrate (for existing customizations)
# Follow the integration pattern in main_integrated.py
```

**Key Changes:**
```python
# Add these imports
from services.auth_service import AuthService
from services.monitoring_service import MonitoringService, monitor_request
from utils.error_handlers import register_error_handlers
from routes.auth_routes import auth_bp
from routes.health_routes import health_bp

# In create_app():
# 1. Initialize monitoring
MonitoringService.initialize_sentry(app)

# 2. Register error handlers
register_error_handlers(app)

# 3. Register new blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(health_bp)

# 4. Add monitoring decorator
@app.before_request
@monitor_request
def before_request_monitoring():
    pass
```

### Step 3: Update Existing Routes

**Files:** `src/routes/prescription.py`, `src/routes/user.py`, etc.

**Action:** Add authentication to protect endpoints.

**Example:**

```python
# Before
@prescription_bp.route('/api/prescriptions', methods=['GET'])
def get_prescriptions():
    prescriptions = Prescription.query.all()
    return jsonify([p.to_dict() for p in prescriptions])

# After
from services.auth_service import token_required, role_required

@prescription_bp.route('/api/prescriptions', methods=['GET'])
@token_required
def get_prescriptions(current_user):
    # Filter by current user
    prescriptions = Prescription.query.filter_by(
        user_id=current_user.id
    ).all()
    return jsonify([p.to_dict() for p in prescriptions])

# Admin-only endpoint
@prescription_bp.route('/api/prescriptions/all', methods=['GET'])
@token_required
@role_required('admin')
def get_all_prescriptions(current_user):
    prescriptions = Prescription.query.all()
    return jsonify([p.to_dict() for p in prescriptions])
```

### Step 4: Create Database Migration

**Action:** Create Alembic migration for new fields.

```bash
# Generate migration
alembic revision --autogenerate -m "Add authentication fields to users"

# Review migration file
# Edit migrations/versions/XXXXX_add_authentication_fields.py if needed

# Apply migration
alembic upgrade head

# Verify
alembic current
```

### Step 5: Update Configuration

**File:** `.env` or `.env.production`

**Action:** Add new environment variables.

```bash
# Copy template
cp .env.production.example .env.production

# Edit with your values
nano .env.production
```

**Required Variables:**
```bash
# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/prescription_validator

# Monitoring
SENTRY_DSN=https://your-key@sentry.io/project-id

# Security
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60

# Features
ENABLE_SWAGGER=false
ENABLE_METRICS=true
```

### Step 6: Update Docker Configuration

**Action:** Use production Dockerfile.

```bash
# Build production image
docker build -f Dockerfile.production \
  --build-arg APP_VERSION=2.1.0 \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  -t prescription-validator:2.1.0 .

# Test locally
docker run -d \
  --name prescription-validator-test \
  -p 5000:5000 \
  --env-file .env.production \
  prescription-validator:2.1.0

# Check health
curl http://localhost:5000/api/health
```

---

## Database Migration

### Migrate from SQLite to PostgreSQL

**Script:** `scripts/migrate_sqlite_to_postgres.py`

```bash
# 1. Set up PostgreSQL database
createdb prescription_validator_prod

# 2. Run migration script
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-db data/prescriptions.db \
  --postgres-url postgresql://user:password@localhost:5432/prescription_validator_prod

# 3. Verify migration
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-db data/prescriptions.db \
  --postgres-url postgresql://user:password@localhost:5432/prescription_validator_prod \
  --verify-only
```

**What the Script Does:**
1. Creates backup of SQLite database
2. Connects to both databases
3. Migrates all tables with data
4. Verifies row counts match
5. Provides detailed progress logs

### Manual Migration (Alternative)

```bash
# 1. Export data from SQLite
sqlite3 data/prescriptions.db .dump > backup.sql

# 2. Convert SQLite SQL to PostgreSQL SQL
# (Manual editing required for data types)

# 3. Import to PostgreSQL
psql -U user -d prescription_validator_prod < backup_converted.sql
```

---

## Testing

### 1. Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 2. Integration Tests

```bash
# Test authentication
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123!",
    "role": "pharmacist"
  }'

# Login
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!"}' \
  | jq -r '.access_token')

# Test protected endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/prescriptions
```

### 3. Health Checks

```bash
# Basic health
curl http://localhost:5000/api/health

# Detailed health (requires admin token)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:5000/api/health/detailed

# Metrics
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:5000/api/metrics

# Kubernetes probes
curl http://localhost:5000/api/readiness
curl http://localhost:5000/api/liveness
```

### 4. Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Run load test
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/health

# Or use Locust
pip install locust
locust -f tests/load_test.py --host=http://localhost:5000
```

---

## Deployment

### Production Deployment Checklist

- [ ] PostgreSQL database configured
- [ ] Environment variables set
- [ ] Database migrations applied
- [ ] Admin user created
- [ ] SSL/TLS certificates installed
- [ ] Nginx reverse proxy configured
- [ ] Firewall rules configured
- [ ] Monitoring (Sentry) configured
- [ ] Backup system configured
- [ ] Health checks passing
- [ ] Load testing completed

### Deploy to Digital Ocean

```bash
# 1. SSH into droplet
ssh root@your-droplet-ip

# 2. Clone repository
cd /opt
git clone https://github.com/HealthFlowEgy/ai-prescription-validation-system.git
cd ai-prescription-validation-system

# 3. Set up environment
cp .env.production.example .env.production
nano .env.production

# 4. Build and run
docker-compose -f docker-compose.prod.yml up -d

# 5. Run migrations
docker exec prescription-validation-system alembic upgrade head

# 6. Create admin user
docker exec -it prescription-validation-system python -c "
from src.main_integrated import app, db
from src.models.user import User
from src.services.auth_service import AuthService

with app.app_context():
    admin = User(
        username='admin',
        email='admin@healthflow.com',
        name='Admin',
        role='admin',
        is_active=True
    )
    admin.password_hash = AuthService.hash_password('ChangeMe123!')
    db.session.add(admin)
    db.session.commit()
"

# 7. Verify deployment
curl http://localhost:5000/api/health
```

### CI/CD Deployment

The GitHub Actions workflow (`.github/workflows/deploy-production.yml`) automatically:

1. Runs tests
2. Builds Docker image
3. Deploys to production
4. Runs database migrations
5. Performs health checks
6. Sends notifications

**Trigger deployment:**
```bash
git push origin main
```

---

## Rollback Procedures

### Rollback Application

```bash
# 1. Stop current container
docker stop prescription-validation-system

# 2. Start previous version
docker run -d \
  --name prescription-validation-system \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env.production \
  prescription-validator:previous

# 3. Verify
curl http://localhost:5000/api/health
```

### Rollback Database

```bash
# Downgrade one migration
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Restore from backup
psql -U user -d prescription_validator_prod < backup.sql
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

#### 2. Authentication Not Working

**Symptoms:**
```
401 Unauthorized
```

**Solutions:**
```bash
# Check JWT_SECRET_KEY is set
echo $JWT_SECRET_KEY

# Verify user exists
docker exec -it prescription-validation-system python -c "
from src.main_integrated import app, db
from src.models.user import User
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f'{u.email} - {u.role}')
"

# Reset password
docker exec -it prescription-validation-system python -c "
from src.main_integrated import app, db
from src.models.user import User
from src.services.auth_service import AuthService
with app.app_context():
    user = User.find_by_email('admin@healthflow.com')
    user.password_hash = AuthService.hash_password('NewPassword123!')
    db.session.commit()
"
```

#### 3. Migration Failed

**Symptoms:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```

**Solutions:**
```bash
# Check current revision
alembic current

# Check migration history
alembic history

# Stamp database with current revision
alembic stamp head

# Try migration again
alembic upgrade head
```

#### 4. Docker Container Won't Start

**Symptoms:**
Container exits immediately after starting.

**Solutions:**
```bash
# Check logs
docker logs prescription-validation-system

# Run interactively
docker run -it --rm \
  --env-file .env.production \
  prescription-validator:latest \
  /bin/bash

# Check environment variables
docker exec prescription-validation-system env | grep -E "DATABASE|SECRET|JWT"
```

---

## Support

For issues or questions:

1. Check this guide
2. Review logs: `docker logs prescription-validation-system`
3. Check Sentry for errors
4. Review GitHub Issues
5. Contact development team

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2025  
**Maintained By:** HealthFlow Development Team
