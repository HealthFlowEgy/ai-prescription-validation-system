#!/bin/bash
# Docker entrypoint script for production
# File: docker-entrypoint.sh

set -e

echo "🚀 Starting AI Prescription Validation System..."
echo "Environment: ${FLASK_ENV}"
echo "Version: ${APP_VERSION}"

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database to be ready..."
    
    # Extract database host from DATABASE_URL or use DB_HOST
    if [ -n "$DATABASE_URL" ]; then
        DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*@([^:/]+).*|\1|')
        DB_PORT=$(echo $DATABASE_URL | sed -E 's|.*:([0-9]+)/.*|\1|')
    else
        DB_HOST=${DB_HOST:-localhost}
        DB_PORT=${DB_PORT:-5432}
    fi
    
    # Wait for PostgreSQL (skip if using SQLite)
    if [[ "$DATABASE_URL" == *"postgresql"* ]] || [[ "$DATABASE_URL" == postgres* ]]; then
        max_tries=30
        tries=0
        
        while ! nc -z $DB_HOST $DB_PORT 2>/dev/null; do
            tries=$((tries + 1))
            if [ $tries -eq $max_tries ]; then
                echo "❌ Database is not available after ${max_tries} attempts"
                exit 1
            fi
            echo "Waiting for database... (${tries}/${max_tries})"
            sleep 2
        done
        
        echo "✅ Database is ready!"
    else
        echo "ℹ️  Using SQLite, skipping database wait"
    fi
}

# Function to run database migrations
run_migrations() {
    echo "🔄 Running database migrations..."
    
    # Check if alembic is initialized
    if [ ! -d "migrations/versions" ]; then
        echo "Initializing Alembic migrations..."
        alembic init migrations 2>/dev/null || true
    fi
    
    # Run migrations
    if alembic upgrade head; then
        echo "✅ Database migrations completed successfully"
    else
        echo "⚠️  Database migration failed, but continuing..."
    fi
}

# Function to create necessary directories
create_directories() {
    echo "📁 Creating necessary directories..."
    mkdir -p /app/uploads /app/data /app/logs /app/backups
    echo "✅ Directories created"
}

# Function to download spaCy model if not present
download_spacy_model() {
    echo "🔍 Checking spaCy model..."
    python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || {
        echo "📥 Downloading spaCy model..."
        python -m spacy download en_core_web_sm
        echo "✅ spaCy model downloaded"
    }
}

# Function to check environment variables
check_environment() {
    echo "🔍 Checking environment configuration..."
    
    if [ "$FLASK_ENV" = "production" ]; then
        # Check critical environment variables for production
        critical_vars=("SECRET_KEY" "JWT_SECRET_KEY")
        missing_vars=()
        
        for var in "${critical_vars[@]}"; do
            if [ -z "${!var}" ]; then
                missing_vars+=("$var")
            fi
        done
        
        if [ ${#missing_vars[@]} -ne 0 ]; then
            echo "❌ Missing critical environment variables: ${missing_vars[*]}"
            exit 1
        fi
        
        echo "✅ Environment configuration is valid"
    else
        echo "ℹ️  Running in ${FLASK_ENV} mode"
    fi
}

# Function to initialize database if needed
init_database() {
    echo "🗄️  Checking database initialization..."
    
    python << END
import sys
sys.path.insert(0, '/app/src')

try:
    from main import app, db
    with app.app_context():
        # Check if database exists and has tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("📝 Initializing database tables...")
            db.create_all()
            print("✅ Database initialized")
        else:
            print(f"✅ Database already initialized ({len(tables)} tables found)")
except Exception as e:
    print(f"⚠️  Database check failed: {str(e)}")
    sys.exit(1)
END
}

# Main execution flow
main() {
    # Step 1: Check environment
    check_environment
    
    # Step 2: Create directories
    create_directories
    
    # Step 3: Wait for database
    wait_for_db
    
    # Step 4: Run migrations
    run_migrations
    
    # Step 5: Initialize database if needed
    init_database
    
    # Step 6: Download spaCy model (optional, uncomment if needed)
    # download_spacy_model
    
    echo "✅ Initialization complete!"
    echo "🌐 Starting application server..."
    echo ""
    
    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"
