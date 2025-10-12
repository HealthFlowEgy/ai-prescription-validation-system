#!/usr/bin/env python3
"""
Database initialization script for AI-Based Digital Prescription Validation System
"""

import os
import sys
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from models.database import db
from models.prescription import (
    Prescription,
    ValidationResult,
)
from models.user import User


def create_tables():
    """Create all database tables"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✓ Database tables created successfully")

            # Create default admin user if it doesn't exist
            admin_user = User.query.filter_by(
                email="admin@prescriptionvalidator.com"
            ).first()
            if not admin_user:
                admin_user = User(
                    name="System Administrator",
                    email="admin@prescriptionvalidator.com",
                    role="admin",
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✓ Default admin user created")
            else:
                print("✓ Admin user already exists")

            # Create test user if it doesn't exist
            test_user = User.query.filter_by(
                email="test@prescriptionvalidator.com"
            ).first()
            if not test_user:
                test_user = User(
                    name="Test User",
                    email="test@prescriptionvalidator.com",
                    role="user",
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.session.add(test_user)
                db.session.commit()
                print("✓ Test user created")
            else:
                print("✓ Test user already exists")

            print("\n✓ Database initialization completed successfully!")

        except Exception as e:
            print(f"✗ Error initializing database: {str(e)}")
            return False

    return True


def drop_tables():
    """Drop all database tables (use with caution!)"""
    with app.app_context():
        try:
            db.drop_all()
            print("✓ All database tables dropped")
            return True
        except Exception as e:
            print(f"✗ Error dropping tables: {str(e)}")
            return False


def reset_database():
    """Reset database by dropping and recreating all tables"""
    print("Resetting database...")
    if drop_tables():
        return create_tables()
    return False


def show_database_info():
    """Show database information"""
    with app.app_context():
        try:
            # Get table information
            tables = db.engine.table_names()
            print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"Tables: {', '.join(tables)}")

            # Get user count
            user_count = User.query.count()
            print(f"Users: {user_count}")

            # Get prescription count
            prescription_count = Prescription.query.count()
            print(f"Prescriptions: {prescription_count}")

            # Get validation results count
            validation_count = ValidationResult.query.count()
            print(f"Validation Results: {validation_count}")

        except Exception as e:
            print(f"✗ Error getting database info: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Database management for Prescription Validation System"
    )
    parser.add_argument(
        "action", choices=["init", "reset", "drop", "info"], help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "init":
        create_tables()
    elif args.action == "reset":
        reset_database()
    elif args.action == "drop":
        drop_tables()
    elif args.action == "info":
        show_database_info()
