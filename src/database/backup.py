#!/usr/bin/env python3
"""
Database backup and migration utilities for AI-Based Digital Prescription Validation System
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from models.database import db
from models.user import User
from models.prescription import Prescription, Medication, ValidationResult, AuditLog


class DatabaseBackup:
    """Database backup and restore utilities"""

    def __init__(self):
        self.backup_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self, backup_name: str = None) -> str:
        """Create a backup of the database"""
        if not backup_name:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_file = os.path.join(self.backup_dir, f"{backup_name}.json")

        with app.app_context():
            try:
                backup_data = {
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0.0",
                        "database_uri": app.config.get(
                            "SQLALCHEMY_DATABASE_URI", "sqlite:///app.db"
                        ),
                    },
                    "users": [],
                    "prescriptions": [],
                    "medications": [],
                    "validation_results": [],
                    "audit_logs": [],
                }

                # Backup users
                users = User.query.all()
                for user in users:
                    backup_data["users"].append(
                        {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role,
                            "is_active": user.is_active,
                            "created_at": (
                                user.created_at.isoformat() if user.created_at else None
                            ),
                            "updated_at": (
                                user.updated_at.isoformat() if user.updated_at else None
                            ),
                        }
                    )

                # Backup prescriptions
                prescriptions = Prescription.query.all()
                for prescription in prescriptions:
                    backup_data["prescriptions"].append(
                        {
                            "id": prescription.id,
                            "prescription_id": prescription.prescription_id,
                            "user_id": prescription.user_id,
                            "patient_name": prescription.patient_name,
                            "patient_address": prescription.patient_address,
                            "prescriber_name": prescription.prescriber_name,
                            "prescriber_license": prescription.prescriber_license,
                            "prescription_date": (
                                prescription.prescription_date.isoformat()
                                if prescription.prescription_date
                                else None
                            ),
                            "input_format": (
                                prescription.input_format.value
                                if prescription.input_format
                                else None
                            ),
                            "file_path": prescription.file_path,
                            "original_filename": prescription.original_filename,
                            "file_size": prescription.file_size,
                            "processing_status": (
                                prescription.processing_status.value
                                if prescription.processing_status
                                else None
                            ),
                            "validation_status": (
                                prescription.validation_status.value
                                if prescription.validation_status
                                else None
                            ),
                            "ocr_text": prescription.ocr_text,
                            "ocr_confidence": prescription.ocr_confidence,
                            "created_at": (
                                prescription.created_at.isoformat()
                                if prescription.created_at
                                else None
                            ),
                            "updated_at": (
                                prescription.updated_at.isoformat()
                                if prescription.updated_at
                                else None
                            ),
                        }
                    )

                # Backup medications
                medications = Medication.query.all()
                for medication in medications:
                    backup_data["medications"].append(
                        {
                            "id": medication.id,
                            "prescription_id": medication.prescription_id,
                            "drug_name": medication.drug_name,
                            "dosage": medication.dosage,
                            "frequency": medication.frequency,
                            "quantity": medication.quantity,
                            "route": medication.route,
                            "duration": medication.duration,
                            "instructions": medication.instructions,
                            "refills": medication.refills,
                            "created_at": (
                                medication.created_at.isoformat()
                                if medication.created_at
                                else None
                            ),
                        }
                    )

                # Backup validation results
                validation_results = ValidationResult.query.all()
                for result in validation_results:
                    backup_data["validation_results"].append(
                        {
                            "id": result.id,
                            "prescription_id": result.prescription_id,
                            "validation_type": result.validation_type,
                            "status": result.status.value if result.status else None,
                            "confidence": result.confidence,
                            "issue_type": result.issue_type,
                            "severity": result.severity,
                            "description": result.description,
                            "affected_fields": result.affected_fields,
                            "recommendations": result.recommendations,
                            "drug1": result.drug1,
                            "drug2": result.drug2,
                            "interaction_type": result.interaction_type,
                            "clinical_recommendation": result.clinical_recommendation,
                            "validator_version": result.validator_version,
                            "created_at": (
                                result.created_at.isoformat()
                                if result.created_at
                                else None
                            ),
                        }
                    )

                # Backup audit logs
                audit_logs = AuditLog.query.all()
                for log in audit_logs:
                    backup_data["audit_logs"].append(
                        {
                            "id": log.id,
                            "user_id": log.user_id,
                            "prescription_id": log.prescription_id,
                            "action": log.action,
                            "description": log.description,
                            "old_values": log.old_values,
                            "new_values": log.new_values,
                            "ip_address": log.ip_address,
                            "user_agent": log.user_agent,
                            "created_at": (
                                log.created_at.isoformat() if log.created_at else None
                            ),
                        }
                    )

                # Write backup file
                with open(backup_file, "w") as f:
                    json.dump(backup_data, f, indent=2, default=str)

                print(f"✓ Backup created successfully: {backup_file}")
                print(f"  - Users: {len(backup_data['users'])}")
                print(f"  - Prescriptions: {len(backup_data['prescriptions'])}")
                print(f"  - Medications: {len(backup_data['medications'])}")
                print(
                    f"  - Validation Results: {len(backup_data['validation_results'])}"
                )
                print(f"  - Audit Logs: {len(backup_data['audit_logs'])}")

                return backup_file

            except Exception as e:
                print(f"✗ Error creating backup: {str(e)}")
                return None

    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from backup file"""
        if not os.path.exists(backup_file):
            print(f"✗ Backup file not found: {backup_file}")
            return False

        with app.app_context():
            try:
                with open(backup_file, "r") as f:
                    backup_data = json.load(f)

                print(f"Restoring backup from: {backup_file}")
                print(f"Backup created: {backup_data['metadata']['created_at']}")

                # Clear existing data
                db.drop_all()
                db.create_all()

                # Restore users
                for user_data in backup_data["users"]:
                    user = User(
                        name=user_data["name"],
                        email=user_data["email"],
                        role=user_data["role"],
                        is_active=user_data["is_active"],
                    )
                    if user_data["created_at"]:
                        user.created_at = datetime.fromisoformat(
                            user_data["created_at"]
                        )
                    if user_data["updated_at"]:
                        user.updated_at = datetime.fromisoformat(
                            user_data["updated_at"]
                        )

                    db.session.add(user)

                db.session.commit()
                print(f"✓ Restored {len(backup_data['users'])} users")

                # Note: For a complete restore, you would need to restore all other tables
                # This is a simplified version focusing on users

                return True

            except Exception as e:
                print(f"✗ Error restoring backup: {str(e)}")
                return False

    def list_backups(self) -> List[str]:
        """List available backup files"""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.endswith(".json"):
                backups.append(os.path.join(self.backup_dir, file))
        return sorted(backups)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Database backup utilities")
    parser.add_argument(
        "action", choices=["backup", "restore", "list"], help="Action to perform"
    )
    parser.add_argument("--name", help="Backup name (for backup action)")
    parser.add_argument("--file", help="Backup file path (for restore action)")

    args = parser.parse_args()

    backup_manager = DatabaseBackup()

    if args.action == "backup":
        backup_manager.create_backup(args.name)
    elif args.action == "restore":
        if not args.file:
            print("✗ Please specify backup file with --file")
            return
        backup_manager.restore_backup(args.file)
    elif args.action == "list":
        backups = backup_manager.list_backups()
        if backups:
            print("Available backups:")
            for backup in backups:
                print(f"  - {backup}")
        else:
            print("No backups found")


if __name__ == "__main__":
    main()
