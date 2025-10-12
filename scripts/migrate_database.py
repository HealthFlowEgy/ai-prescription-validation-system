#!/usr/bin/env python3
"""
Comprehensive database migration script
Handles migration from SQLite to PostgreSQL and schema updates
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import logging
from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handle database migrations"""

    def __init__(self, source_url: str, target_url: str):
        """
        Initialize migrator

        Args:
            source_url: Source database URL (SQLite)
            target_url: Target database URL (PostgreSQL)
        """
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine = None
        self.target_engine = None

    def connect(self):
        """Establish database connections"""
        logger.info("Connecting to source database...")
        self.source_engine = create_engine(self.source_url)

        logger.info("Connecting to target database...")
        self.target_engine = create_engine(self.target_url)

        logger.info("✅ Database connections established")

    def verify_source(self) -> bool:
        """Verify source database exists and has data"""
        try:
            inspector = inspect(self.source_engine)
            tables = inspector.get_table_names()

            if not tables:
                logger.error("❌ Source database has no tables")
                return False

            logger.info(
                f"✅ Source database has {len(tables)} tables: {', '.join(tables)}"
            )

            # Check for data
            with self.source_engine.connect() as conn:
                for table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    logger.info(f"   - {table}: {count} rows")

            return True

        except Exception as e:
            logger.error(f"❌ Error verifying source database: {e}")
            return False

    def create_target_schema(self):
        """Create target database schema"""
        logger.info("Creating target database schema...")

        try:
            # Import models to create schema
            # Create all tables
            from main import app
            from models.prescription import (
                AuditLog,
                Medication,
                Prescription,
                ValidationResult,
            )
            from models.user import User, db

            with app.app_context():
                db.create_all()

            logger.info("✅ Target schema created successfully")

        except Exception as e:
            logger.error(f"❌ Error creating target schema: {e}")
            raise

    def migrate_table(self, table_name: str) -> int:
        """
        Migrate a single table

        Args:
            table_name: Name of table to migrate

        Returns:
            Number of rows migrated
        """
        logger.info(f"Migrating table: {table_name}")

        try:
            # Get source data
            with self.source_engine.connect() as source_conn:
                result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                columns = result.keys()

                if not rows:
                    logger.info(f"   ⚠️  Table {table_name} is empty, skipping")
                    return 0

                logger.info(f"   Found {len(rows)} rows to migrate")

                # Insert into target
                with self.target_engine.connect() as target_conn:
                    # Build insert statement
                    cols = ", ".join(columns)
                    placeholders = ", ".join([f":{col}" for col in columns])
                    insert_sql = (
                        f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                    )

                    # Insert rows
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        target_conn.execute(text(insert_sql), row_dict)

                    target_conn.commit()

                logger.info(f"   ✅ Migrated {len(rows)} rows")
                return len(rows)

        except Exception as e:
            logger.error(f"   ❌ Error migrating table {table_name}: {e}")
            raise

    def migrate_all_tables(self):
        """Migrate all tables from source to target"""
        logger.info("Starting full database migration...")

        inspector = inspect(self.source_engine)
        tables = inspector.get_table_names()

        total_rows = 0
        migrated_tables = []

        for table in tables:
            try:
                rows = self.migrate_table(table)
                total_rows += rows
                migrated_tables.append(table)
            except Exception as e:
                logger.error(f"Failed to migrate table {table}: {e}")
                logger.warning("Continuing with next table...")

        logger.info(f"\n✅ Migration complete!")
        logger.info(f"   Tables migrated: {len(migrated_tables)}/{len(tables)}")
        logger.info(f"   Total rows migrated: {total_rows}")
        logger.info(f"   Migrated tables: {', '.join(migrated_tables)}")

    def verify_migration(self) -> bool:
        """Verify migration was successful"""
        logger.info("\nVerifying migration...")

        try:
            source_inspector = inspect(self.source_engine)
            target_inspector = inspect(self.target_engine)

            source_tables = set(source_inspector.get_table_names())
            target_tables = set(target_inspector.get_table_names())

            # Check all source tables exist in target
            missing_tables = source_tables - target_tables
            if missing_tables:
                logger.error(f"❌ Missing tables in target: {missing_tables}")
                return False

            # Check row counts match
            all_match = True
            with self.source_engine.connect() as source_conn, self.target_engine.connect() as target_conn:

                for table in source_tables:
                    source_count = source_conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()
                    target_count = target_conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    ).scalar()

                    if source_count == target_count:
                        logger.info(f"   ✅ {table}: {source_count} rows (match)")
                    else:
                        logger.error(
                            f"   ❌ {table}: source={source_count}, target={target_count} (mismatch)"
                        )
                        all_match = False

            if all_match:
                logger.info("\n✅ Migration verification passed!")
                return True
            else:
                logger.error("\n❌ Migration verification failed!")
                return False

        except Exception as e:
            logger.error(f"❌ Error verifying migration: {e}")
            return False

    def close(self):
        """Close database connections"""
        if self.source_engine:
            self.source_engine.dispose()
        if self.target_engine:
            self.target_engine.dispose()
        logger.info("Database connections closed")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description="Migrate database from SQLite to PostgreSQL"
    )
    parser.add_argument("--source", required=True, help="Source database URL (SQLite)")
    parser.add_argument(
        "--target", required=True, help="Target database URL (PostgreSQL)"
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify, do not migrate"
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip post-migration verification",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("DATABASE MIGRATION TOOL")
    logger.info("=" * 60)
    logger.info(f"Source: {args.source}")
    logger.info(f"Target: {args.target}")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    migrator = DatabaseMigrator(args.source, args.target)

    try:
        # Connect to databases
        migrator.connect()

        # Verify source
        if not migrator.verify_source():
            logger.error("Source database verification failed")
            return 1

        if args.verify_only:
            logger.info("\nVerify-only mode: Skipping migration")
            return 0

        # Create target schema
        migrator.create_target_schema()

        # Migrate data
        migrator.migrate_all_tables()

        # Verify migration
        if not args.skip_verification:
            if not migrator.verify_migration():
                logger.error("Migration verification failed")
                return 1

        logger.info("\n" + "=" * 60)
        logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        migrator.close()


if __name__ == "__main__":
    sys.exit(main())
