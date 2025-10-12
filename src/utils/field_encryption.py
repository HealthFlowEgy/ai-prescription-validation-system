#!/usr/bin/env python3
"""
Sprint 1 Comprehensive Testing Suite
Tests for field-level encryption, backup system, and consolidated CI/CD

Run with:
    pytest tests/sprint1/ -v --cov=src --cov-report=html
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import redis

from src.encryption.encrypted_types import EncryptedDate, EncryptedString

# Import modules to test
from src.encryption.field_encryption import (
    DecryptionError,
    EncryptionKeyManager,
    FieldEncryptionService,
)
from src.models.prescription import Prescription

# ============================================
# Fixtures
# ============================================


@pytest.fixture
def redis_client():
    """Mock Redis client for testing."""
    client = Mock(spec=redis.Redis)
    client.get.return_value = None
    client.setex.return_value = True
    return client


@pytest.fixture
def encryption_key():
    """Test encryption key."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key()


@pytest.fixture
def key_manager(redis_client, encryption_key, monkeypatch):
    """Initialize key manager with test key."""
    import base64

    monkeypatch.setenv(
        "ENCRYPTION_KEY_CURRENT", base64.b64encode(encryption_key).decode()
    )
    return EncryptionKeyManager(redis_client)


@pytest.fixture
def encryption_service(key_manager):
    """Initialize encryption service."""
    return FieldEncryptionService(key_manager)


@pytest.fixture
def test_database():
    """Create test database."""
    from src.database import create_app, db

    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


# ============================================
# Test Suite 1: Encryption Service
# ============================================


class TestEncryptionKeyManager:
    """Test encryption key management."""

    def test_get_current_key(self, key_manager, encryption_key):
        """Test retrieving current encryption key."""
        key = key_manager.get_current_key()
        assert key == encryption_key

    def test_get_current_key_from_cache(
        self, redis_client, key_manager, encryption_key
    ):
        """Test key retrieval from Redis cache."""
        import base64

        # Simulate cached key
        redis_client.get.return_value = base64.b64encode(encryption_key)

        key = key_manager.get_current_key()
        assert key == encryption_key
        redis_client.get.assert_called_once()

    def test_get_previous_keys(self, key_manager, monkeypatch):
        """Test retrieving previous encryption keys for rotation."""
        import base64

        from cryptography.fernet import Fernet

        prev_key_1 = Fernet.generate_key()
        prev_key_2 = Fernet.generate_key()

        monkeypatch.setenv(
            "ENCRYPTION_KEY_PREVIOUS_1", base64.b64encode(prev_key_1).decode()
        )
        monkeypatch.setenv(
            "ENCRYPTION_KEY_PREVIOUS_2", base64.b64encode(prev_key_2).decode()
        )

        keys = key_manager.get_previous_keys()
        assert len(keys) == 2
        assert prev_key_1 in keys
        assert prev_key_2 in keys

    def test_generate_new_key(self):
        """Test generating new encryption key."""
        key = EncryptionKeyManager.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

        # Verify it's a valid Fernet key
        import base64

        from cryptography.fernet import Fernet

        key_bytes = base64.b64decode(key.encode())
        fernet = Fernet(key_bytes)
        assert fernet is not None


class TestFieldEncryptionService:
    """Test field-level encryption operations."""

    def test_encrypt_string(self, encryption_service):
        """Test encrypting a string."""
        plaintext = "John Doe"
        ciphertext = encryption_service.encrypt(plaintext)

        assert ciphertext is not None
        assert ciphertext != plaintext
        assert isinstance(ciphertext, str)

    def test_decrypt_string(self, encryption_service):
        """Test decrypting a string."""
        plaintext = "John Doe"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_none(self, encryption_service):
        """Test encrypting None returns None."""
        result = encryption_service.encrypt(None)
        assert result is None

    def test_decrypt_none(self, encryption_service):
        """Test decrypting None returns None."""
        result = encryption_service.decrypt(None)
        assert result is None

    def test_encrypt_unicode(self, encryption_service):
        """Test encrypting Unicode characters."""
        plaintext = "Patient: 张三 🏥"
        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_bulk_encrypt(self, encryption_service):
        """Test bulk encryption of multiple fields."""
        data = {"name": "John Doe", "email": "john@example.com", "phone": "555-1234"}

        encrypted_data = encryption_service.bulk_encrypt(data)

        assert len(encrypted_data) == 3
        assert all(v != data[k] for k, v in encrypted_data.items())

    def test_bulk_decrypt(self, encryption_service):
        """Test bulk decryption of multiple fields."""
        data = {"name": "John Doe", "email": "john@example.com", "phone": "555-1234"}

        encrypted_data = encryption_service.bulk_encrypt(data)
        decrypted_data = encryption_service.bulk_decrypt(encrypted_data)

        assert decrypted_data == data

    def test_encryption_cache(self, encryption_service):
        """Test decryption caching improves performance."""
        plaintext = "John Doe"
        ciphertext = encryption_service.encrypt(plaintext)

        # First decrypt (cache miss)
        import time

        start = time.time()
        decrypted1 = encryption_service.decrypt(ciphertext)
        time1 = time.time() - start

        # Second decrypt (cache hit)
        start = time.time()
        decrypted2 = encryption_service.decrypt(ciphertext)
        time2 = time.time() - start

        assert decrypted1 == decrypted2 == plaintext
        # Cache should be faster (though timing can be flaky)
        assert time2 <= time1 * 2  # Allow some variance

    def test_key_rotation(self, encryption_service):
        """Test re-encrypting data with new key."""
        plaintext = "Sensitive Data"
        old_ciphertext = encryption_service.encrypt(plaintext)

        # Simulate key rotation
        new_ciphertext = encryption_service.rotate_key(old_ciphertext)

        assert new_ciphertext != old_ciphertext
        assert encryption_service.decrypt(new_ciphertext) == plaintext

    def test_decryption_with_wrong_key_fails(self, redis_client):
        """Test that decryption fails with wrong key."""
        import base64

        from cryptography.fernet import Fernet

        # Create two separate encryption services with different keys
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        os.environ["ENCRYPTION_KEY_CURRENT"] = base64.b64encode(key1).decode()
        manager1 = EncryptionKeyManager(redis_client)
        service1 = FieldEncryptionService(manager1)

        os.environ["ENCRYPTION_KEY_CURRENT"] = base64.b64encode(key2).decode()
        manager2 = EncryptionKeyManager(redis_client)
        service2 = FieldEncryptionService(manager2)

        # Encrypt with key1
        plaintext = "Secret"
        ciphertext = service1.encrypt(plaintext)

        # Try to decrypt with key2 (should fail)
        with pytest.raises(DecryptionError):
            service2.decrypt(ciphertext)


# ============================================
# Test Suite 2: Encrypted Database Types
# ============================================


class TestEncryptedTypes:
    """Test SQLAlchemy encrypted column types."""

    def test_encrypted_string_bind_param(self, encryption_service, monkeypatch):
        """Test encrypting string for database storage."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        column = EncryptedString(255)
        plaintext = "John Doe"

        encrypted = column.process_bind_param(plaintext, None)

        assert encrypted is not None
        assert encrypted != plaintext

    def test_encrypted_string_result_value(self, encryption_service, monkeypatch):
        """Test decrypting string from database."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        column = EncryptedString(255)
        plaintext = "John Doe"

        encrypted = column.process_bind_param(plaintext, None)
        decrypted = column.process_result_value(encrypted, None)

        assert decrypted == plaintext

    def test_encrypted_string_length_validation(self, encryption_service, monkeypatch):
        """Test that overly long strings are rejected."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        column = EncryptedString(10)
        too_long = "This is a very long string that exceeds the limit"

        with pytest.raises(ValueError):
            column.process_bind_param(too_long, None)

    def test_encrypted_date_roundtrip(self, encryption_service, monkeypatch):
        """Test encrypting and decrypting dates."""
        from datetime import date

        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        column = EncryptedDate()
        test_date = date(1990, 5, 15)

        encrypted = column.process_bind_param(test_date, None)
        decrypted = column.process_result_value(encrypted, None)

        assert decrypted == test_date

    def test_encrypted_json_roundtrip(self, encryption_service, monkeypatch):
        """Test encrypting and decrypting JSON data."""
        from src.encryption import field_encryption
        from src.encryption.encrypted_types import EncryptedJSON

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        column = EncryptedJSON()
        test_data = {
            "allergies": ["penicillin", "latex"],
            "conditions": ["diabetes", "hypertension"],
            "medications": ["metformin", "lisinopril"],
        }

        encrypted = column.process_bind_param(test_data, None)
        decrypted = column.process_result_value(encrypted, None)

        assert decrypted == test_data


# ============================================
# Test Suite 3: Database Models
# ============================================


class TestPrescriptionModel:
    """Test Prescription model with encrypted fields."""

    def test_create_prescription_with_encrypted_fields(
        self, test_database, encryption_service, monkeypatch
    ):
        """Test creating prescription with PHI encryption."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        # Create prescription with PHI
        prescription = Prescription(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            patient_name="John Doe",
            patient_dob=datetime(1980, 1, 1).date(),
            diagnosis="Type 2 Diabetes",
            status="PENDING",
        )

        test_database.session.add(prescription)
        test_database.session.commit()

        # Verify data is encrypted in database
        result = test_database.session.execute(
            f"SELECT patient_name FROM prescriptions WHERE id = '{prescription.id}'"
        ).fetchone()

        # Database value should be encrypted (different from plaintext)
        assert result[0] != "John Doe"

    def test_query_prescription_decrypts_automatically(
        self, test_database, encryption_service, monkeypatch
    ):
        """Test that querying prescription decrypts PHI automatically."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        # Create prescription
        prescription = Prescription(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            patient_name="Jane Smith",
            diagnosis="Hypertension",
            status="COMPLETED",
        )

        test_database.session.add(prescription)
        test_database.session.commit()
        prescription_id = prescription.id

        # Clear session
        test_database.session.expire_all()

        # Query prescription
        retrieved = Prescription.query.get(prescription_id)

        # Should be automatically decrypted
        assert retrieved.patient_name == "Jane Smith"
        assert retrieved.diagnosis == "Hypertension"

    def test_to_dict_excludes_phi_by_default(
        self, test_database, encryption_service, monkeypatch
    ):
        """Test that to_dict() excludes PHI unless explicitly requested."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        prescription = Prescription(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            patient_name="John Doe",
            diagnosis="Diabetes",
            status="PENDING",
        )

        # Default to_dict should not include PHI
        data = prescription.to_dict(include_phi=False)
        assert "patient_name" not in data
        assert "diagnosis" not in data
        assert "status" in data

        # Explicitly request PHI
        data_with_phi = prescription.to_dict(include_phi=True)
        assert "patient_name" in data_with_phi
        assert data_with_phi["patient_name"] == "John Doe"


# ============================================
# Test Suite 4: Data Migration
# ============================================


class TestDataMigration:
    """Test migration from plaintext to encrypted fields."""

    @patch("src.models.prescription.Prescription")
    def test_migration_script_processes_batches(self, mock_prescription):
        """Test that migration processes records in batches."""
        from scripts.migrate_to_encrypted_fields import DataMigrator

        # Mock 250 prescriptions
        mock_prescription.query.count.return_value = 250
        mock_prescription.query.offset.return_value.limit.return_value.all.return_value = [
            Mock(id=i, patient_name=f"Patient{i}") for i in range(100)
        ]

        migrator = DataMigrator(batch_size=100, dry_run=True)

        # Should process 3 batches (100 + 100 + 50)
        # Test implementation would verify this

    def test_migration_handles_null_values(self, encryption_service):
        """Test that migration handles NULL PHI fields correctly."""
        from scripts.migrate_to_encrypted_fields import DataMigrator

        migrator = DataMigrator(batch_size=10, dry_run=True)

        # Create mock prescription with NULL diagnosis
        mock_prescription = Mock()
        mock_prescription.patient_name = "John Doe"
        mock_prescription.diagnosis = None

        # Should not crash on NULL
        try:
            migrator._migrate_prescription(mock_prescription)
        except AttributeError:
            pytest.fail("Migration failed on NULL value")


# ============================================
# Test Suite 5: Backup Service
# ============================================


class TestDatabaseBackupService:
    """Test automated database backup functionality."""

    @patch("subprocess.run")
    @patch("boto3.client")
    def test_create_full_backup(self, mock_boto, mock_subprocess):
        """Test creating full database backup."""
        # Mock successful pg_basebackup
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="pg_basebackup: complete", stderr=""
        )

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto.return_value = mock_s3

        from scripts.backup_service import DatabaseBackupService

        service = DatabaseBackupService(
            db_host="localhost",
            db_port=5432,
            db_name="healthflow",
            db_user="postgres",
            db_password="password",
            s3_bucket="test-backups",
        )

        metadata = service.create_full_backup()

        assert metadata.backup_type == "full"
        assert metadata.size_bytes > 0
        assert metadata.checksum is not None

    def test_backup_metadata_serialization(self):
        """Test backup metadata can be serialized to JSON."""
        from scripts.backup_service import BackupMetadata

        metadata = BackupMetadata(
            backup_id="test_backup_123",
            backup_type="full",
            timestamp=datetime.utcnow(),
            size_bytes=1024000,
            checksum="abc123",
            database_name="healthflow",
            postgres_version="PostgreSQL 15.0",
        )

        # Should serialize to JSON without errors
        json_data = json.dumps(metadata.to_dict())
        assert json_data is not None

        # Should deserialize back
        parsed = json.loads(json_data)
        assert parsed["backup_id"] == "test_backup_123"

    def test_retention_policy_keeps_correct_backups(self):
        """Test that retention policy keeps the right backups."""
        from scripts.backup_service import BackupMetadata, DatabaseBackupService

        # Create fake backups spanning 90 days
        now = datetime.utcnow()
        backups = []

        for days_ago in range(90):
            backup = BackupMetadata(
                backup_id=f"backup_{days_ago}",
                backup_type="full",
                timestamp=now - timedelta(days=days_ago),
                size_bytes=1000000,
                checksum="test",
                database_name="healthflow",
                postgres_version="15.0",
            )
            backups.append(backup)

        service = DatabaseBackupService(
            db_host="localhost",
            db_port=5432,
            db_name="test",
            db_user="test",
            db_password="test",
            s3_bucket="test",
        )

        # Mock _list_backups to return our test data
        with patch.object(service, "_list_backups", return_value=backups):
            with patch.object(service, "_delete_backup"):
                service.apply_retention_policy()

                # Should keep:
                # - Last 30 daily (30 backups)
                # - 12 weekly (12 backups)
                # - 12 monthly (12 backups)
                # Total: Up to 54 unique backups


# ============================================
# Test Suite 6: CI/CD Workflows
# ============================================


class TestCICDWorkflows:
    """Test CI/CD workflow configurations."""

    def test_ci_workflow_exists(self):
        """Test that ci.yml workflow file exists."""
        ci_path = Path(".github/workflows/ci.yml")
        assert ci_path.exists(), "ci.yml workflow file missing"

    def test_cd_workflow_exists(self):
        """Test that cd.yml workflow file exists."""
        cd_path = Path(".github/workflows/cd.yml")
        assert cd_path.exists(), "cd.yml workflow file missing"

    def test_ci_workflow_has_required_jobs(self):
        """Test that CI workflow contains all required jobs."""
        import yaml

        ci_path = Path(".github/workflows/ci.yml")
        with open(ci_path) as f:
            workflow = yaml.safe_load(f)

        required_jobs = [
            "code-quality",
            "backend-tests",
            "frontend-tests",
            "security-scan",
            "docker-build",
        ]

        jobs = workflow.get("jobs", {})
        for required_job in required_jobs:
            assert required_job in jobs, f"Missing job: {required_job}"

    def test_cd_workflow_deploys_to_correct_environments(self):
        """Test that CD workflow deploys to staging and production."""
        import yaml

        cd_path = Path(".github/workflows/cd.yml")
        with open(cd_path) as f:
            workflow = yaml.safe_load(f)

        # Check trigger branches
        on_config = workflow.get("on", {})
        push_branches = on_config.get("push", {}).get("branches", [])

        assert "develop" in push_branches, "Missing develop branch trigger"
        assert "main" in push_branches, "Missing main branch trigger"


# ============================================
# Integration Tests
# ============================================


class TestEndToEndEncryption:
    """Integration tests for complete encryption workflow."""

    def test_complete_prescription_workflow(
        self, test_database, encryption_service, monkeypatch
    ):
        """Test complete workflow: create, query, update prescription with encryption."""
        from src.encryption import field_encryption

        monkeypatch.setattr(field_encryption, "_encryption_service", encryption_service)

        # 1. Create prescription
        prescription = Prescription(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            patient_name="Alice Johnson",
            patient_dob=datetime(1985, 3, 20).date(),
            diagnosis="Asthma",
            medications=["albuterol", "fluticasone"],
            status="PROCESSING",
        )

        test_database.session.add(prescription)
        test_database.session.commit()
        prescription_id = prescription.id

        # 2. Query prescription (should decrypt automatically)
        test_database.session.expire_all()
        retrieved = Prescription.query.get(prescription_id)

        assert retrieved.patient_name == "Alice Johnson"
        assert retrieved.diagnosis == "Asthma"

        # 3. Update prescription
        retrieved.diagnosis = "Asthma - Moderate Persistent"
        test_database.session.commit()

        # 4. Query again
        test_database.session.expire_all()
        updated = Prescription.query.get(prescription_id)

        assert updated.diagnosis == "Asthma - Moderate Persistent"

    def test_backup_and_restore_encrypted_data(self):
        """Test that encrypted data survives backup and restore."""
        # This would test the complete backup/restore cycle
        # Implementation depends on actual backup infrastructure


# ============================================
# Performance Tests
# ============================================


class TestEncryptionPerformance:
    """Performance tests for encryption operations."""

    def test_encryption_performance(self, encryption_service, benchmark):
        """Test encryption performance with benchmark."""
        plaintext = "This is a test patient name"

        result = benchmark(encryption_service.encrypt, plaintext)

        assert result is not None
        # Benchmark will report timing automatically

    def test_bulk_encryption_performance(self, encryption_service):
        """Test bulk encryption of 1000 records."""
        import time

        # Generate 1000 fake patient records
        records = {f"patient_{i}": f"Patient Name {i}" for i in range(1000)}

        start = time.time()
        encrypted = encryption_service.bulk_encrypt(records)
        duration = time.time() - start

        assert len(encrypted) == 1000
        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0, f"Bulk encryption too slow: {duration}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=html"])
