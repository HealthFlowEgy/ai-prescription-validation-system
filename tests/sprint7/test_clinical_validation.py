"""
Tests for Enhanced Clinical Validation Service
"""

from unittest.mock import Mock, patch

import pytest

from src.services.clinical_validation_enhanced import (
    ClinicalValidationService,
    DrugInteractionService,
    ValidationConfig,
    ValidationFlag,
)


class TestDrugInteractionService:
    """Test drug interaction checking."""

    def setup_method(self):
        self.service = DrugInteractionService()

    def test_warfarin_aspirin_interaction(self):
        """Test detection of warfarin + aspirin interaction."""
        medications = [
            {"name": "Warfarin", "dosage": {"value": 5, "unit": "mg"}},
            {"name": "Aspirin", "dosage": {"value": 81, "unit": "mg"}},
        ]

        interactions = self.service.check_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["severity"] == "SEVERE"
        assert "bleeding" in interactions[0]["description"].lower()

    def test_warfarin_ibuprofen_interaction(self):
        """Test detection of warfarin + ibuprofen interaction."""
        medications = [
            {"name": "Warfarin", "dosage": {"value": 5, "unit": "mg"}},
            {"name": "Ibuprofen", "dosage": {"value": 400, "unit": "mg"}},
        ]

        interactions = self.service.check_interactions(medications)

        assert len(interactions) == 1
        assert interactions[0]["severity"] == "SEVERE"

    def test_no_interaction(self):
        """Test medications with no known interactions."""
        medications = [
            {"name": "Metformin", "dosage": {"value": 500, "unit": "mg"}},
            {"name": "Lisinopril", "dosage": {"value": 10, "unit": "mg"}},
        ]

        interactions = self.service.check_interactions(medications)

        assert len(interactions) == 0

    def test_single_medication(self):
        """Test single medication (no interactions possible)."""
        medications = [{"name": "Metformin", "dosage": {"value": 500, "unit": "mg"}}]

        interactions = self.service.check_interactions(medications)

        assert len(interactions) == 0


class TestClinicalValidationService:
    """Test clinical validation service."""

    def setup_method(self):
        self.service = ClinicalValidationService()
        self.mock_prescription = Mock()
        self.mock_prescription.id = "test-123"
        self.mock_prescription.status = "PENDING"
        self.mock_prescription.patient_notes = ""
        self.mock_prescription.save = Mock()

    def test_low_ocr_confidence_flagged(self):
        """Test that low OCR confidence is flagged."""
        ocr_result = {
            "confidence": 0.70,  # Below threshold of 0.85
            "field_confidences": {},
        }
        nlp_result = {
            "medications": [],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "LOW_OCR_CONFIDENCE" for f in result["flags"])
        assert self.mock_prescription.status == "REQUIRES_MANUAL_REVIEW"

    def test_critical_medication_flagged(self):
        """Test that critical medications are flagged."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [{"name": "Warfarin", "dosage": {"value": 5, "unit": "mg"}}],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "CRITICAL_MEDICATION" for f in result["flags"])

    def test_unusual_dosage_flagged(self):
        """Test that unusual dosages are flagged."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [
                {
                    "name": "Warfarin",
                    "dosage": {"value": 50, "unit": "mg"},
                }  # Way too high
            ],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "UNUSUAL_DOSAGE" for f in result["flags"])

    def test_drug_interaction_flagged(self):
        """Test that drug interactions are flagged."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [
                {"name": "Warfarin", "dosage": {"value": 5, "unit": "mg"}},
                {"name": "Aspirin", "dosage": {"value": 81, "unit": "mg"}},
            ],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "DRUG_INTERACTION" for f in result["flags"])

    def test_missing_information_flagged(self):
        """Test that missing required information is flagged."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [
                {"name": "Metformin", "dosage": {"value": 500, "unit": "mg"}}
            ],
            "patient_name": None,  # Missing
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "MISSING_INFORMATION" for f in result["flags"])

    def test_missing_dosage_flagged(self):
        """Test that missing dosage is flagged."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [{"name": "Metformin"}],  # No dosage
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "MISSING_DOSAGE" for f in result["flags"])

    def test_high_risk_patient_flagged(self):
        """Test that high-risk patient conditions are flagged."""
        self.mock_prescription.patient_notes = "Patient is pregnant"

        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [
                {"name": "Metformin", "dosage": {"value": 500, "unit": "mg"}}
            ],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
            "diagnosis": "",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == True
        assert any(f["type"] == "HIGH_RISK_PATIENT" for f in result["flags"])

    def test_clean_prescription_auto_approved(self):
        """Test that clean prescription is auto-approved."""
        ocr_result = {"confidence": 0.95, "field_confidences": {}}
        nlp_result = {
            "medications": [
                {"name": "Metformin", "dosage": {"value": 500, "unit": "mg"}}
            ],
            "patient_name": "Test Patient",
            "prescriber_name": "Dr. Test",
        }

        result = self.service.validate_prescription(
            self.mock_prescription, ocr_result, nlp_result
        )

        assert result["requires_review"] == False
        assert result["auto_approved"] == True
        assert len(result["flags"]) == 0
        assert self.mock_prescription.status == "AUTO_APPROVED"


class TestValidationFlag:
    """Test ValidationFlag class."""

    def test_flag_creation(self):
        """Test creating a validation flag."""
        flag = ValidationFlag(
            flag_type="TEST_FLAG",
            severity="HIGH",
            message="Test message",
            details={"key": "value"},
        )

        assert flag.type == "TEST_FLAG"
        assert flag.severity == "HIGH"
        assert flag.message == "Test message"
        assert flag.details == {"key": "value"}

    def test_flag_to_dict(self):
        """Test converting flag to dictionary."""
        flag = ValidationFlag(
            flag_type="TEST_FLAG", severity="HIGH", message="Test message"
        )

        result = flag.to_dict()

        assert result["type"] == "TEST_FLAG"
        assert result["severity"] == "HIGH"
        assert result["message"] == "Test message"
        assert "timestamp" in result
