#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

This script safely migrates data from SQLite to PostgreSQL while preserving all data.

Usage:
    python scripts/migrate_sqlite_to_postgres.py --sqlite-db data/prescriptions.db --postgres-url postgresql://user:pass@host/db

Features:
- Data validation
- Rollback on error
- Progress tracking
- Backup creation
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handle database migration from SQLite to PostgreSQL"""

    def __init__(self, sqlite_url: str, postgres_url: str):
        self.sqlite_url = sqlite_url
        self.postgres_url = postgres_url
        self.sqlite_engine = None
        self.postgres_engine = None
        self.tables_migrated = []

    def connect(self):
        """Establish database connections"""
        try:
            logger.info("Connecting to SQLite database...")
            self.sqlite_engine = create_engine(self.sqlite_url)

            logger.info("Connecting to PostgreSQL database...")
            self.postgres_engine = create_engine(self.postgres_url)

            # Test connections
            self.sqlite_engine.connect()
            self.postgres_engine.connect()

            logger.info("✅ Database connections established")
            return True

        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False

    def backup_sqlite(self):
        """Create backup of SQLite database"""
        try:
            # Extract database path from URL
            db_path = self.sqlite_url.replace("sqlite:///", "")

            if not os.path.exists(db_path):
                logger.warning(f"SQLite database not found: {db_path}")
                return False

            # Create backup
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_path)

            logger.info(f"✅ Backup created: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False

    def get_tables(self):
        """Get list of tables from SQLite"""
        try:
            inspector = inspect(self.sqlite_engine)
            tables = inspector.get_table_names()
            logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
            return tables

        except Exception as e:
            logger.error(f"❌ Failed to get tables: {e}")
            return []

    def migrate_table(self, table_name: str):
        """Migrate a single table"""
        try:
            logger.info(f"Migrating table: {table_name}")

            # Reflect table structure
            metadata = MetaData()
            table = Table(table_name, metadata, autoload_with=self.sqlite_engine)

            # Create table in PostgreSQL
            metadata.create_all(self.postgres_engine)

            # Create sessions
            SQLiteSession = sessionmaker(bind=self.sqlite_engine)
            PostgresSession = sessionmaker(bind=self.postgres_engine)

            sqlite_session = SQLiteSession()
            postgres_session = PostgresSession()

            try:
                # Read data from SQLite
                rows = sqlite_session.execute(table.select()).fetchall()
                row_count = len(rows)

                if row_count == 0:
                    logger.info(f"  ⚠️  Table {table_name} is empty")
                    return True

                logger.info(f"  Copying {row_count} rows...")

                # Insert data into PostgreSQL
                for i, row in enumerate(rows, 1):
                    # Convert row to dict
                    row_dict = dict(row._mapping)

                    # Insert into PostgreSQL
                    postgres_session.execute(table.insert().values(**row_dict))

                    # Progress indicator
                    if i % 100 == 0 or i == row_count:
                        logger.info(f"  Progress: {i}/{row_count} rows")

                # Commit transaction
                postgres_session.commit()

                # Verify migration
                postgres_count = postgres_session.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                ).scalar()

                if postgres_count == row_count:
                    logger.info(
                        f"  ✅ Table {table_name} migrated successfully ({postgres_count} rows)"
                    )
                    self.tables_migrated.append(table_name)
                    return True
                else:
                    logger.error(
                        f"  ❌ Row count mismatch: SQLite={row_count}, PostgreSQL={postgres_count}"
                    )
                    postgres_session.rollback()
                    return False

            except Exception as e:
                postgres_session.rollback()
                logger.error(f"  ❌ Migration failed: {e}")
                return False

            finally:
                sqlite_session.close()
                postgres_session.close()

        except Exception as e:
            logger.error(f"❌ Table migration failed: {e}")
            return False

    def migrate_all(self):
        """Migrate all tables"""
        try:
            # Get tables
            tables = self.get_tables()

            if not tables:
                logger.warning("No tables to migrate")
                return False

            # Migrate each table
            success_count = 0
            for table in tables:
                if self.migrate_table(table):
                    success_count += 1

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info(f"Migration Summary:")
            logger.info(f"  Total tables: {len(tables)}")
            logger.info(f"  Migrated successfully: {success_count}")
            logger.info(f"  Failed: {len(tables) - success_count}")
            logger.info("=" * 60)

            return success_count == len(tables)

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

    def verify_migration(self):
        """Verify migration integrity"""
        try:
            logger.info("\nVerifying migration...")

            sqlite_inspector = inspect(self.sqlite_engine)
            postgres_inspector = inspect(self.postgres_engine)

            sqlite_tables = set(sqlite_inspector.get_table_names())
            postgres_tables = set(postgres_inspector.get_table_names())

            # Check if all tables exist
            missing_tables = sqlite_tables - postgres_tables
            if missing_tables:
                logger.warning(f"  ⚠️  Missing tables in PostgreSQL: {missing_tables}")
                return False

            # Check row counts
            all_match = True
            for table in sqlite_tables:
                sqlite_count = self.sqlite_engine.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).scalar()

                postgres_count = self.postgres_engine.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).scalar()

                if sqlite_count == postgres_count:
                    logger.info(f"  ✅ {table}: {postgres_count} rows")
                else:
                    logger.error(
                        f"  ❌ {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}"
                    )
                    all_match = False

            if all_match:
                logger.info("\n✅ Migration verified successfully!")
            else:
                logger.error("\n❌ Migration verification failed!")

            return all_match

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False


def main():
    """Main migration function"""

    parser = argparse.ArgumentParser(
        description="Migrate SQLite database to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-db", required=True, help="Path to SQLite database file"
    )
    parser.add_argument(
        "--postgres-url", required=True, help="PostgreSQL connection URL"
    )
    parser.add_argument("--skip-backup", action="store_true", help="Skip SQLite backup")
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify existing migration"
    )

    args = parser.parse_args()

    # Construct SQLite URL
    sqlite_url = f"sqlite:///{args.sqlite_db}"

    # Create migrator
    migrator = DatabaseMigrator(sqlite_url, args.postgres_url)

    # Connect to databases
    if not migrator.connect():
        logger.error("Failed to connect to databases")
        sys.exit(1)

    # Verify only mode
    if args.verify_only:
        success = migrator.verify_migration()
        sys.exit(0 if success else 1)

    # Create backup
    if not args.skip_backup:
        if not migrator.backup_sqlite():
            logger.error("Failed to create backup")
            response = input("Continue without backup? (yes/no): ")
            if response.lower() != "yes":
                sys.exit(1)

    # Run migration
    logger.info("\n" + "=" * 60)
    logger.info("Starting migration...")
    logger.info("=" * 60 + "\n")

    success = migrator.migrate_all()

    if success:
        # Verify migration
        migrator.verify_migration()
        logger.info("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
