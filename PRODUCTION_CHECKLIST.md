# Production Deployment Checklist

This checklist ensures your application is properly configured for production deployment.

## ✅ Critical Requirements (MUST)

### 1. Database Configuration
- [ ] PostgreSQL database provisioned
- [ ] `DATABASE_URL` environment variable set to PostgreSQL connection string
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Database backups configured
- [ ] Connection pooling configured (recommended: 20-50 connections)

**Example:**
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/prescription_db"
```

### 2. Security Configuration
- [ ] `SECRET_KEY` set to strong random value (min 32 characters)
- [ ] `JWT_SECRET_KEY` set to strong random value (min 32 characters)
- [ ] `FLASK_ENV` set to `production`
- [ ] Debug mode disabled (`DEBUG=False`)
- [ ] CORS origins restricted to your domains

**Generate secrets:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Redis Configuration (Recommended)
- [ ] Redis instance provisioned
- [ ] `REDIS_URL` environment variable set
- [ ] Redis used for rate limiting
- [ ] Redis used for token blacklisting
- [ ] Redis persistence configured

**Example:**
```bash
export REDIS_URL="redis://localhost:6379/0"
```

### 4. Monitoring & Logging
- [ ] Sentry DSN configured (`SENTRY_DSN`)
- [ ] Log level set appropriately (`LOG_LEVEL=INFO`)
- [ ] Log aggregation configured (e.g., CloudWatch, ELK)
- [ ] Application metrics enabled
- [ ] Health check endpoints accessible

### 5. SSL/TLS
- [ ] SSL certificate installed
- [ ] HTTPS enforced
- [ ] HTTP redirects to HTTPS
- [ ] HSTS header configured

## 🔒 Security Checklist

### Authentication & Authorization
- [ ] Password minimum length: 12 characters
- [ ] Password complexity enforced
- [ ] Common passwords blocked
- [ ] JWT tokens use HS256 algorithm
- [ ] Token expiration configured (access: 1h, refresh: 7d)
- [ ] Token blacklisting enabled
- [ ] Rate limiting configured

### Input Validation
- [ ] File upload validation enabled
- [ ] File size limits enforced
- [ ] MIME type verification enabled
- [ ] SQL injection prevention active
- [ ] XSS prevention active
- [ ] CSRF protection enabled (if using forms)

### Network Security
- [ ] Firewall configured
- [ ] Only necessary ports open (80, 443)
- [ ] Database not publicly accessible
- [ ] Redis not publicly accessible
- [ ] VPC/Security groups configured

## 📊 Performance Checklist

### Application
- [ ] Gunicorn workers configured (recommended: 2-4 × CPU cores)
- [ ] Worker timeout configured (recommended: 30-60s)
- [ ] Keep-alive configured
- [ ] Static files served via CDN or nginx

### Database
- [ ] Database indexes created
- [ ] Query optimization done
- [ ] Connection pooling configured
- [ ] Slow query logging enabled

### Caching
- [ ] Redis caching enabled
- [ ] Cache invalidation strategy defined
- [ ] CDN configured for static assets

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code review completed
- [ ] Security audit completed
- [ ] Load testing completed
- [ ] Backup strategy defined
- [ ] Rollback plan documented

### Deployment
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Static files collected/deployed
- [ ] Health checks passing
- [ ] Smoke tests passing

### Post-Deployment
- [ ] Application accessible
- [ ] Authentication working
- [ ] File uploads working
- [ ] Database queries working
- [ ] Monitoring active
- [ ] Logs flowing
- [ ] Alerts configured

## 📝 Environment Variables Reference

### Required
```bash
# Flask
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
DEBUG=False

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# JWT
JWT_SECRET_KEY=<strong-random-key>
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Recommended
```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=True

# File Uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=/var/app/uploads
```

### Optional
```bash
# Email (if using)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# AWS (if using)
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=your-bucket
```

## 🔍 Validation Commands

### Check Database
```bash
# Test database connection
python -c "from src.config.database_enforcer import get_database_status; import json; print(json.dumps(get_database_status(), indent=2))"

# Run migrations
alembic upgrade head

# Verify tables
psql $DATABASE_URL -c "\dt"
```

### Check Application
```bash
# Start application
gunicorn --config gunicorn_config.py src.main:app

# Test health endpoint
curl http://localhost:8000/api/health

# Test authentication
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","password":"TestPassword123!","role":"pharmacist"}'
```

### Check Security
```bash
# Verify HTTPS
curl -I https://yourdomain.com

# Check security headers
curl -I https://yourdomain.com | grep -E "(Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options)"

# Test rate limiting
for i in {1..10}; do curl -X POST http://localhost:8000/api/auth/login; done
```

## 🆘 Troubleshooting

### Application Won't Start
1. Check DATABASE_URL is set and correct
2. Check SECRET_KEY and JWT_SECRET_KEY are set
3. Check database is accessible
4. Check migrations are up to date
5. Check logs for errors

### Database Errors
1. Verify PostgreSQL is running
2. Check connection string format
3. Verify database exists
4. Check user permissions
5. Run migrations

### Authentication Errors
1. Verify JWT_SECRET_KEY is set
2. Check token expiration settings
3. Verify Redis is running (if using token blacklisting)
4. Check password validation settings

### Performance Issues
1. Check database query performance
2. Verify connection pooling
3. Check Gunicorn worker count
4. Monitor Redis performance
5. Review application logs

## 📚 Additional Resources

- [Flask Production Best Practices](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [OWASP Security Guidelines](https://owasp.org/www-project-web-security-testing-guide/)

---

**Last Updated:** 2025-10-07  
**Version:** 2.1.0
