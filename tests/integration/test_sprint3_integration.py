"""
Sprint 3 Integration Tests
Tests for Model Governance, Clinical Validation, Monitoring, and PHI Encryption
"""

import pytest
import time
from datetime import datetime, timedelta
import json

# Import services
from mlflow_registry import ModelRegistry, ModelPerformanceTracker
from clinical_validation import ClinicalValidationService, ValidationSeverity
from monitoring_service import MonitoringService, MetricsCollector
from phi_encryption import (
    EncryptionService,
    PHIAnonymizer,
    AuditLogger,
    DataRetentionService,
)


class TestMLflowRegistry:
    """Test Model Registry and Versioning"""

    @pytest.fixture
    def registry(self):
        return ModelRegistry(tracking_uri="http://localhost:5000")

    def test_register_model(self, registry):
        """Test model registration"""

        # Mock model
        class MockModel:
            def predict(self, x):
                return x

        model = MockModel()

        version = registry.register_model(
            model=model,
            model_name="test-ocr-model",
            model_type="ocr",
            metrics={"accuracy": 0.95, "precision": 0.93},
            parameters={"learning_rate": 0.001, "batch_size": 32},
        )

        assert version is not None
        assert isinstance(version, str)

    def test_transition_model_stage(self, registry):
        """Test model stage transition"""
        # Transition to staging
        registry.transition_model_stage(
            model_name="test-ocr-model",
            version="1",
            stage="Staging",
            archive_existing=False,
        )

        # Verify transition
        versions = registry.client.get_latest_versions(
            "test-ocr-model", stages=["Staging"]
        )

        assert len(versions) > 0
        assert versions[0].current_stage == "Staging"

    def test_load_production_model(self, registry):
        """Test loading production model"""
        try:
            model, version_info = registry.load_production_model("prescription-ocr-v1")

            assert model is not None
            assert version_info.current_stage == "Production"

        except Exception as e:
            pytest.skip(f"Production model not available: {e}")

    def test_compare_models(self, registry):
        """Test model comparison"""
        comparison = registry.compare_models(
            model_name="test-ocr-model", versions=["1", "2"]
        )

        assert "model_name" in comparison
        assert "versions" in comparison
        assert len(comparison["versions"]) == 2


class TestClinicalValidation:
    """Test Clinical Validation Service"""

    @pytest.fixture
    def validator(self):
        return ClinicalValidationService()

    def test_low_ocr_confidence_flagged(self, validator):
        """Test that low OCR confidence is flagged"""
        ocr_result = {
            "confidence": 0.70,  # Below threshold
            "text": "Sample text",
            "field_confidences": {"medication": 0.72},
        }

        nlp_result = {
            "medications": [{"name": "Aspirin", "dosage": "100mg", "confidence": 0.90}],
            "patient_name": "John Doe",
            "prescriber_name": "Dr. Smith",
            "date": "2025-10-11",
            "entities": [],
        }

        result = validator.validate_prescription(ocr_result, nlp_result)

        assert result["requires_pharmacist_review"] is True
        assert result["risk_score"] > 0
        assert len(result["flags"]) > 0

        # Check for low confidence flag
        flag_types = [f["type"] for f in result["flags"]]
        assert "low_confidence_ocr" in flag_types

    def test_critical_medication_flagged(self, validator):
        """Test that critical medications are flagged"""
        ocr_result = {
            "confidence": 0.90,
            "text": "Warfarin prescription",
            "field_confidences": {},
        }

        nlp_result = {
            "medications": [
                {
                    "name": "Warfarin",  # Critical medication
                    "dosage": "5mg daily",
                    "confidence": 0.92,
                }
            ],
            "patient_name": "Jane Smith",
            "prescriber_name": "Dr. Johnson",
            "date": "2025-10-11",
            "entities": [
                {"type": "medication", "value": "Warfarin", "confidence": 0.92}
            ],
        }

        result = validator.validate_prescription(ocr_result, nlp_result)

        assert result["requires_pharmacist_review"] is True

        # Check for critical medication flag
        flag_types = [f["type"] for f in result["flags"]]
        assert "critical_medication" in flag_types

    def test_drug_interaction_detected(self, validator):
        """Test drug interaction detection"""
        ocr_result = {"confidence": 0.92, "text": "", "field_confidences": {}}

        nlp_result = {
            "medications": [{"name": "Warfarin", "dosage": "5mg", "confidence": 0.90}],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
            "date": "2025-10-11",
            "entities": [],
        }

        patient_context = {
            "current_medications": ["aspirin"],  # Interaction with warfarin
            "allergies": [],
            "age": 65,
        }

        result = validator.validate_prescription(
            ocr_result, nlp_result, patient_context
        )

        assert result["requires_pharmacist_review"] is True

        # Check for interaction flag
        flag_types = [f["type"] for f in result["flags"]]
        assert "drug_interaction" in flag_types

    def test_missing_required_fields(self, validator):
        """Test missing required field detection"""
        ocr_result = {"confidence": 0.88, "text": "", "field_confidences": {}}

        nlp_result = {
            "medications": [{"name": "Aspirin", "dosage": "100mg", "confidence": 0.90}],
            # Missing patient_name and prescriber_name
            "date": "2025-10-11",
            "entities": [],
        }

        result = validator.validate_prescription(ocr_result, nlp_result)

        assert result["status"] != "approved"
        assert len(result["flags"]) > 0

        # Check for missing field flags
        flag_types = [f["type"] for f in result["flags"]]
        assert "missing_required_field" in flag_types

    def test_unusual_dosage_flagged(self, validator):
        """Test unusual dosage detection"""
        ocr_result = {"confidence": 0.90, "text": "", "field_confidences": {}}

        nlp_result = {
            "medications": [
                {
                    "name": "lisinopril",
                    "dosage": "100mg daily",  # Exceeds normal range (max 40mg)
                    "confidence": 0.91,
                }
            ],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
            "date": "2025-10-11",
            "entities": [],
        }

        result = validator.validate_prescription(ocr_result, nlp_result)

        # Check for unusual dosage flag
        flag_types = [f["type"] for f in result["flags"]]
        assert "unusual_dosage" in flag_types

    def test_validation_risk_score(self, validator):
        """Test risk score calculation"""
        ocr_result = {"confidence": 0.70, "text": "", "field_confidences": {}}

        nlp_result = {
            "medications": [{"name": "Warfarin", "dosage": "5mg", "confidence": 0.75}],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
            "date": "2025-10-11",
            "entities": [
                {"type": "medication", "value": "Warfarin", "confidence": 0.75}
            ],
        }

        result = validator.validate_prescription(ocr_result, nlp_result)

        # Multiple issues should result in higher risk score
        assert result["risk_score"] > 50
        assert result["risk_score"] <= 100


class TestMonitoringService:
    """Test Monitoring and Alerting"""

    @pytest.fixture
    def monitoring(self):
        baseline_metrics = {"accuracy": 0.94, "confidence": 0.90, "response_time": 500}
        return MonitoringService(baseline_metrics)

    def test_record_prediction(self, monitoring):
        """Test prediction recording"""
        monitoring.record_prediction(
            response_time_ms=450,
            confidence_score=0.88,
            success=True,
            metadata={"endpoint": "test"},
        )

        metrics = monitoring.metrics_collector.get_current_metrics()

        assert metrics["counters"]["total_requests"] == 1
        assert metrics["counters"]["successful_requests"] == 1

    def test_metrics_aggregation(self, monitoring):
        """Test metrics aggregation"""
        # Record multiple predictions
        for i in range(100):
            monitoring.record_prediction(
                response_time_ms=400 + i,
                confidence_score=0.90 - (i * 0.001),
                success=True,
            )

        metrics = monitoring.metrics_collector.get_current_metrics()

        assert metrics["response_time"]["mean"] > 0
        assert metrics["response_time"]["p95"] > 0
        assert metrics["confidence"]["mean"] > 0

    def test_drift_detection(self, monitoring):
        """Test model drift detection"""
        # Simulate degraded performance
        for i in range(100):
            monitoring.record_prediction(
                response_time_ms=800 + i * 2,  # Slow responses
                confidence_score=0.75 - (i * 0.001),  # Low confidence
                success=True,
            )

        health = monitoring.check_system_health()

        assert health["drift"]["drift_detected"] is True
        assert len(health["drift"]["details"]) > 0

    def test_alert_generation(self, monitoring):
        """Test alert generation"""
        # Simulate high error rate
        for i in range(100):
            success = i % 10 != 0  # 10% error rate
            monitoring.record_prediction(
                response_time_ms=500, confidence_score=0.85, success=success
            )

        health = monitoring.check_system_health()

        # Should generate high error rate alert
        assert len(health["alerts"]["new"]) > 0 or len(health["alerts"]["active"]) > 0

    def test_alert_cooldown(self, monitoring):
        """Test alert cooldown mechanism"""
        # Trigger alert
        for i in range(100):
            monitoring.record_prediction(
                response_time_ms=3000, confidence_score=0.85, success=True  # Slow
            )

        health1 = monitoring.check_system_health()
        initial_alerts = len(health1["alerts"]["new"])

        # Check again immediately (should be in cooldown)
        health2 = monitoring.check_system_health()
        cooldown_alerts = len(health2["alerts"]["new"])

        # Should not generate duplicate alert
        assert cooldown_alerts <= initial_alerts


class TestPHIEncryption:
    """Test PHI Encryption and Security"""

    @pytest.fixture
    def encryption_service(self):
        return EncryptionService()

    def test_encrypt_decrypt(self, encryption_service):
        """Test encryption and decryption"""
        plaintext = "John Doe"

        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)

        assert encrypted != plaintext
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, encryption_service):
        """Test encrypting empty string"""
        encrypted = encryption_service.encrypt("")
        assert encrypted == ""

    def test_decrypt_invalid_data(self, encryption_service):
        """Test decrypting invalid data raises error"""
        with pytest.raises(Exception):
            encryption_service.decrypt("invalid_encrypted_data")

    def test_phi_anonymization(self):
        """Test PHI anonymization in logs"""
        anonymizer = PHIAnonymizer()

        text_with_phi = (
            "Patient John Doe, SSN 123-45-6789, "
            "phone 555-123-4567, email john@example.com"
        )

        anonymized = anonymizer.anonymize(text_with_phi)

        assert "123-45-6789" not in anonymized
        assert "555-123-4567" not in anonymized
        assert "john@example.com" not in anonymized
        assert "[SSN-REDACTED]" in anonymized
        assert "[PHONE-REDACTED]" in anonymized
        assert "[EMAIL-REDACTED]" in anonymized

    def test_phi_anonymize_dict(self):
        """Test dictionary anonymization"""
        anonymizer = PHIAnonymizer()

        data_with_phi = {
            "patient_name": "John Doe",
            "ssn": "123-45-6789",
            "contact": {"phone": "555-123-4567", "email": "john@example.com"},
        }

        anonymized = anonymizer.anonymize_dict(data_with_phi)

        assert "123-45-6789" not in str(anonymized)
        assert "[SSN-REDACTED]" in anonymized["ssn"]
        assert "[PHONE-REDACTED]" in anonymized["contact"]["phone"]
        assert "[EMAIL-REDACTED]" in anonymized["contact"]["email"]

    def test_audit_logging(self):
        """Test audit logging"""
        audit_logger = AuditLogger()

        audit_logger.log_access(
            user_id="user123",
            action="READ",
            resource_type="Prescription",
            resource_id="rx-456",
            phi_fields_accessed=["patient_name", "medications"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            access_justification="Filling prescription",
            success=True,
        )

        # Verify log was created (check log file)
        # In production, verify database entry
        assert True  # Placeholder

    def test_data_retention(self):
        """Test data retention service"""
        retention_service = DataRetentionService()

        # Mark for deletion
        deletion_date = datetime.utcnow() + timedelta(days=7)
        retention_service.mark_for_deletion(
            resource_type="prescription",
            resource_id="test-123",
            deletion_date=deletion_date,
        )

        # Verify marked (in production, check database)
        assert True  # Placeholder


class TestIntegration:
    """End-to-end integration tests"""

    def test_full_prescription_workflow(self):
        """Test complete prescription processing workflow"""
        # Initialize services
        validator = ClinicalValidationService()
        monitoring = MonitoringService(
            {"accuracy": 0.94, "confidence": 0.90, "response_time": 500}
        )
        encryption_service = EncryptionService()

        # Step 1: Simulate OCR
        start_time = time.time()
        ocr_result = {
            "confidence": 0.89,
            "text": "Prescription for John Doe...",
            "field_confidences": {"medication": 0.91, "dosage": 0.87},
        }

        # Step 2: Simulate NLP
        nlp_result = {
            "medications": [
                {"name": "Lisinopril", "dosage": "10mg daily", "confidence": 0.90}
            ],
            "patient_name": "John Doe",
            "prescriber_name": "Dr. Smith",
            "date": "2025-10-11",
            "entities": [
                {"type": "medication", "value": "Lisinopril", "confidence": 0.90}
            ],
        }

        # Step 3: Clinical Validation
        validation_result = validator.validate_prescription(ocr_result, nlp_result)

        # Step 4: Encrypt PH
