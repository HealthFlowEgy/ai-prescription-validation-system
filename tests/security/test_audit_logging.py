"""
Security Tests: Audit Logging

Tests HIPAA-compliant audit logging functionality.

Author: HealthFlow Security Team
Date: 2025-10-14
"""

from datetime import datetime, timedelta

import pytest

from src.services.audit_service import (
    AuditAction,
    AuditLogModel,
    AuditService,
    AuditSeverity,
)


class TestAuditLogging:
    """Test suite for HIPAA-compliant audit logging"""

    def test_audit_log_creation(self, session):
        """Test basic audit log creation"""
        audit_service = AuditService()

        log = audit_service.log_event(
            action=AuditAction.READ,
            user_id=1,
            resource_type="Prescription",
            resource_id="RX-001",
            description="Test audit log",
        )

        assert log is not None
        assert log.action == AuditAction.READ.value
        assert log.user_id == 1
        assert log.resource_type == "Prescription"
        assert log.resource_id == "RX-001"
        assert log.event_id.startswith("AUD-")

    def test_phi_access_logging(self, session):
        """Test PHI access creates detailed audit log"""
        audit_service = AuditService()

        log = audit_service.log_phi_access(
            user_id=1,
            action=AuditAction.READ,
            resource_type="Prescription",
            resource_id="RX-001",
            phi_fields=["patient_name", "patient_dob", "diagnosis"],
            access_justification="Patient care",
        )

        assert log is not None
        assert log.phi_accessed is True
        assert "patient_name" in log.phi_fields_accessed
        assert log.access_justification == "Patient care"

    def test_audit_log_immutability(self, session):
        """Test that audit logs cannot be modified"""
        audit_service = AuditService()

        log = audit_service.log_event(
            action=AuditAction.READ, user_id=1, resource_type="Test", resource_id="001"
        )

        # Attempt to modify should raise exception
        with pytest.raises(Exception) as exc_info:
            log.action = AuditAction.DELETE.value
            session.commit()

        assert "immutable" in str(exc_info.value).lower()

    def test_audit_log_cannot_be_deleted(self, session):
        """Test that audit logs cannot be deleted"""
        audit_service = AuditService()

        log = audit_service.log_event(action=AuditAction.READ, user_id=1)

        # Attempt to delete should raise exception
        with pytest.raises(Exception) as exc_info:
            session.delete(log)
            session.commit()

        assert "cannot be deleted" in str(exc_info.value).lower()

    def test_audit_log_integrity_hash(self, session):
        """Test audit log integrity verification"""
        audit_service = AuditService()

        log = audit_service.log_event(
            action=AuditAction.READ,
            user_id=1,
            resource_type="Prescription",
            resource_id="RX-001",
        )

        # Verify integrity
        assert audit_service.verify_log_integrity(log) is True
        assert log.record_hash is not None
        assert len(log.record_hash) == 64  # SHA-256 hash

    def test_authentication_logging(self, session):
        """Test authentication events are logged"""
        audit_service = AuditService()

        # Successful login
        log = audit_service.log_authentication(
            action=AuditAction.LOGIN, user_id=1, username="testuser", success=True
        )

        assert log.action == AuditAction.LOGIN.value
        assert log.severity == AuditSeverity.INFO.value
        assert "successful" in log.description.lower()

    def test_failed_authentication_logging(self, session):
        """Test failed authentication creates warning log"""
        audit_service = AuditService()

        log = audit_service.log_authentication(
            action=AuditAction.LOGIN_FAILED,
            user_id=None,
            username="testuser",
            success=False,
            failure_reason="Invalid password",
        )

        assert log.action == AuditAction.LOGIN_FAILED.value
        assert log.severity == AuditSeverity.WARNING.value
        assert "failed" in log.description.lower()

    def test_get_user_activity(self, session):
        """Test retrieving user activity logs"""
        audit_service = AuditService()

        # Create multiple logs for user
        for i in range(5):
            audit_service.log_event(
                action=AuditAction.READ, user_id=1, resource_id=f"RX-{i:03d}"
            )

        # Retrieve activity
        logs = audit_service.get_user_activity(user_id=1, limit=10)

        assert len(logs) >= 5
        assert all(log.user_id == 1 for log in logs)

    def test_get_phi_access_logs(self, session):
        """Test retrieving PHI access logs"""
        audit_service = AuditService()

        # Create PHI access logs
        audit_service.log_phi_access(
            user_id=1,
            action=AuditAction.READ,
            resource_type="Prescription",
            resource_id="RX-001",
            phi_fields=["patient_name"],
        )

        # Retrieve PHI logs
        logs = audit_service.get_phi_access_logs(resource_type="Prescription", limit=10)

        assert len(logs) >= 1
        assert all(log.phi_accessed for log in logs)

    def test_audit_log_retention_policy(self, session):
        """Test audit log retention policy application"""
        audit_service = AuditService()

        # Retention should be 7 years (2557 days)
        assert audit_service.RETENTION_DAYS == 2557

    def test_emergency_access_flagging(self, session):
        """Test emergency access is properly flagged"""
        audit_service = AuditService()

        log = audit_service.log_event(
            action=AuditAction.READ,
            user_id=1,
            resource_type="Prescription",
            resource_id="RX-001",
            emergency_access=True,
            access_justification="Emergency treatment",
        )

        assert log.emergency_access is True
        assert log.access_justification == "Emergency treatment"

    def test_audit_log_timestamps(self, session):
        """Test audit logs have accurate timestamps"""
        audit_service = AuditService()

        before = datetime.utcnow()
        log = audit_service.log_event(action=AuditAction.READ, user_id=1)
        after = datetime.utcnow()

        assert before <= log.timestamp <= after

    def test_audit_log_to_dict(self, session):
        """Test audit log serialization"""
        audit_service = AuditService()

        log = audit_service.log_event(
            action=AuditAction.READ,
            user_id=1,
            resource_type="Prescription",
            resource_id="RX-001",
        )

        log_dict = log.to_dict()

        assert "event_id" in log_dict
        assert "action" in log_dict
        assert "timestamp" in log_dict
        assert log_dict["user_id"] == 1
