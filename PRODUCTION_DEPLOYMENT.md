# 🚀 Production Deployment Guide

Complete guide for deploying the AI-Based Digital Prescription Validation System to production servers (non-Vercel).

**For Vercel deployment, see `DEPLOYMENT_GUIDE.md`**

---

## 📋 Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/HealthFlowEgy/ai-prescription-validation-system.git
cd ai-prescription-validation-system

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.production.example .env
# Edit .env with your values

# 4. Setup database
alembic upgrade head

# 5. Run with Gunicorn
gunicorn --config gunicorn_config.py src.main:app
```

---

## 🗄️ Database Setup

### **PostgreSQL (Recommended)**

```bash
# Create database
sudo -u postgres psql
CREATE DATABASE prescription_db;
CREATE USER prescription_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE prescription_db TO prescription_user;
\q

# Set DATABASE_URL in .env
DATABASE_URL=postgresql://prescription_user:secure-password@localhost:5432/prescription_db

# Run migrations
alembic upgrade head
```

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -f Dockerfile.production -t prescription-validator:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose logs -f
```

---

## 🔒 Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure JWT_SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall
- [ ] Set up fail2ban
- [ ] Enable Sentry error tracking
- [ ] Configure backup strategy

---

## 📊 Monitoring

```bash
# Health check
curl https://yourdomain.com/api/health

# Metrics
curl https://yourdomain.com/api/metrics

# Detailed health
curl https://yourdomain.com/api/health/detailed
```

---

## 🔧 Troubleshooting

**App won't start:**
```bash
# Check logs
journalctl -u prescription-validator -n 100

# Verify environment
env | grep -E "(FLASK|DATABASE|JWT)"
```

**Database errors:**
```bash
# Test connection
psql $DATABASE_URL

# Check migrations
alembic current
```

---

For complete deployment instructions, see the full documentation in the repository.

**Version:** 2.1.0  
**Last Updated:** October 7, 2025
