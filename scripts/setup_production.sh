#!/bin/bash
#
# Production Setup Script
# Configures remaining production requirements
#

set -e

echo "🚀 Production Setup Script"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating from template..."
    cp .env.production.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your actual values${NC}"
    echo ""
fi

# Generate secrets if not set
echo "🔐 Checking secrets..."

if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=your-secret-key-here" .env; then
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    echo -e "${GREEN}✅ Generated SECRET_KEY${NC}"
fi

if ! grep -q "JWT_SECRET_KEY=" .env || grep -q "JWT_SECRET_KEY=your-jwt-secret-here" .env; then
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" .env
    echo -e "${GREEN}✅ Generated JWT_SECRET_KEY${NC}"
fi

echo ""

# Check PostgreSQL
echo "🗄️  Checking PostgreSQL..."

if command -v psql &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL client installed${NC}"
    
    # Test connection if DATABASE_URL is set
    if grep -q "DATABASE_URL=postgresql://" .env; then
        DATABASE_URL=$(grep "DATABASE_URL=" .env | cut -d '=' -f2-)
        if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
            echo -e "${GREEN}✅ PostgreSQL connection successful${NC}"
        else
            echo -e "${YELLOW}⚠️  Cannot connect to PostgreSQL${NC}"
            echo "   Please verify DATABASE_URL in .env"
        fi
    else
        echo -e "${YELLOW}⚠️  DATABASE_URL not configured${NC}"
        echo "   Currently using SQLite (development only)"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL client not installed${NC}"
    echo "   Install with: sudo apt-get install postgresql-client"
fi

echo ""

# Check Redis
echo "🔴 Checking Redis..."

if command -v redis-cli &> /dev/null; then
    echo -e "${GREEN}✅ Redis client installed${NC}"
    
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis server running${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis server not running${NC}"
        echo "   Start with: sudo systemctl start redis"
    fi
else
    echo -e "${YELLOW}⚠️  Redis not installed${NC}"
    echo "   Install with: sudo apt-get install redis-server"
fi

echo ""

# Check Python dependencies
echo "🐍 Checking Python dependencies..."

if python3 -c "import flask" &> /dev/null; then
    echo -e "${GREEN}✅ Flask installed${NC}"
else
    echo -e "${RED}❌ Flask not installed${NC}"
    echo "   Install with: pip install -r requirements.txt"
fi

if python3 -c "import pytest" &> /dev/null; then
    echo -e "${GREEN}✅ pytest installed${NC}"
else
    echo -e "${YELLOW}⚠️  pytest not installed${NC}"
    echo "   Install with: pip install pytest"
fi

echo ""

# Check migrations
echo "📦 Checking database migrations..."

if [ -d "migrations/versions" ]; then
    migration_count=$(ls -1 migrations/versions/*.py 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Found $migration_count migration(s)${NC}"
else
    echo -e "${YELLOW}⚠️  No migrations directory${NC}"
    echo "   Initialize with: alembic init migrations"
fi

echo ""

# Run migrations if PostgreSQL is configured
if grep -q "DATABASE_URL=postgresql://" .env; then
    echo "🔄 Running database migrations..."
    if alembic upgrade head 2>&1 | tee /tmp/alembic.log; then
        echo -e "${GREEN}✅ Migrations applied successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  Migration warnings (check /tmp/alembic.log)${NC}"
    fi
    echo ""
fi

# Check Sentry configuration
echo "📊 Checking Sentry configuration..."

if grep -q "SENTRY_DSN=https://" .env; then
    echo -e "${GREEN}✅ Sentry DSN configured${NC}"
else
    echo -e "${YELLOW}⚠️  Sentry DSN not configured${NC}"
    echo "   Add your Sentry DSN to .env for error tracking"
fi

echo ""

# Rate limiting check
echo "⏱️  Checking rate limiting..."

if grep -q "REDIS_URL=" .env && redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅ Rate limiting ready (Redis available)${NC}"
else
    echo -e "${YELLOW}⚠️  Rate limiting not configured${NC}"
    echo "   Configure REDIS_URL in .env for rate limiting"
fi

echo ""

# Summary
echo "📋 Setup Summary"
echo "================"

READY_COUNT=0
TOTAL_COUNT=7

# Check each requirement
if [ -f .env ]; then ((READY_COUNT++)); fi
if grep -q "SECRET_KEY=" .env && ! grep -q "your-secret-key-here" .env; then ((READY_COUNT++)); fi
if grep -q "JWT_SECRET_KEY=" .env && ! grep -q "your-jwt-secret-here" .env; then ((READY_COUNT++)); fi
if command -v psql &> /dev/null; then ((READY_COUNT++)); fi
if python3 -c "import flask" &> /dev/null; then ((READY_COUNT++)); fi
if [ -d "migrations/versions" ]; then ((READY_COUNT++)); fi

echo "Ready: $READY_COUNT/$TOTAL_COUNT components"
echo ""

if [ $READY_COUNT -eq $TOTAL_COUNT ]; then
    echo -e "${GREEN}🎉 Production setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review .env configuration"
    echo "2. Run tests: pytest tests/ -v"
    echo "3. Start application: python src/main.py"
    echo "4. Or deploy with Docker: docker-compose -f docker-compose.prod.yml up -d"
else
    echo -e "${YELLOW}⚠️  Some components need attention${NC}"
    echo ""
    echo "Please address the warnings above before deploying to production."
fi

echo ""
echo "For detailed deployment instructions, see:"
echo "  - PRODUCTION_DEPLOYMENT.md"
echo "  - DEPLOYMENT_GUIDE.md"
echo ""
