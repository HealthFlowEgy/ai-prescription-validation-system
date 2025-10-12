"""
Unit tests for Prescription model
"""

import pytest
from datetime import datetime, date
from models.prescription import (
    Prescription,
    ValidationStatus,
    ProcessingStatus,
    InputFormat,
)


class TestPrescriptionModel:
    """Test cases for Prescription model"""

    def test_prescription_creation(self, session):
        """Test creating a prescription"""
        prescription = Prescription(
            prescription_id="RX-2025-001",
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            patient_name="John Doe",
            prescriber_name="Dr. Smith",
        )
        session.add(prescription)
        session.commit()

        assert prescription.id is not None
        assert prescription.prescription_id == "RX-2025-001"
        assert prescription.input_format == InputFormat.HANDWRITTEN_IMAGE
        assert prescription.processing_status == ProcessingStatus.UPLOADED
        assert prescription.validation_status == ValidationStatus.PENDING

    def test_prescription_unique_id(self, session):
        """Test that prescription IDs must be unique"""
        prescription1 = Prescription(
            prescription_id="RX-2025-001", input_format=InputFormat.HANDWRITTEN_IMAGE
        )
        session.add(prescription1)
        session.commit()

        prescription2 = Prescription(
            prescription_id="RX-2025-001", input_format=InputFormat.DIGITAL_DATA
        )
        session.add(prescription2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_prescription_enums(self, session):
        """Test prescription enum values"""
        prescription = Prescription(
            prescription_id="RX-2025-002",
            input_format=InputFormat.VOICE_AUDIO,
            processing_status=ProcessingStatus.PROCESSING,
            validation_status=ValidationStatus.REQUIRES_REVIEW,
        )
        session.add(prescription)
        session.commit()

        assert prescription.input_format == InputFormat.VOICE_AUDIO
        assert prescription.processing_status == ProcessingStatus.PROCESSING
        assert prescription.validation_status == ValidationStatus.REQUIRES_REVIEW

    def test_prescription_patient_info(self, session):
        """Test prescription patient information"""
        prescription = Prescription(
            prescription_id="RX-2025-003",
            input_format=InputFormat.DIGITAL_DATA,
            patient_name="Jane Doe",
            patient_dob=date(1995, 5, 15),
            patient_id="PAT-12345",
        )
        session.add(prescription)
        session.commit()

        assert prescription.patient_name == "Jane Doe"
        assert prescription.patient_dob == date(1995, 5, 15)
        assert prescription.patient_id == "PAT-12345"

    def test_prescription_prescriber_info(self, session):
        """Test prescription prescriber information"""
        prescription = Prescription(
            prescription_id="RX-2025-004",
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            prescriber_name="Dr. Johnson",
            prescriber_license="DOC-789012",
            prescriber_specialty="Cardiology",
        )
        session.add(prescription)
        session.commit()

        assert prescription.prescriber_name == "Dr. Johnson"
        assert prescription.prescriber_license == "DOC-789012"
        assert prescription.prescriber_specialty == "Cardiology"

    def test_prescription_timestamps(self, session):
        """Test prescription timestamps"""
        prescription = Prescription(
            prescription_id="RX-2025-005", input_format=InputFormat.HANDWRITTEN_IMAGE
        )
        session.add(prescription)
        session.commit()

        assert prescription.created_at is not None
        assert prescription.updated_at is not None
        assert isinstance(prescription.created_at, datetime)
        assert isinstance(prescription.updated_at, datetime)

    def test_prescription_file_info(self, session):
        """Test prescription file information"""
        prescription = Prescription(
            prescription_id="RX-2025-006",
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            original_filename="prescription.pdf",
            file_path="/uploads/RX-2025-006/prescription.pdf",
            file_size=1024000,
        )
        session.add(prescription)
        session.commit()

        assert prescription.original_filename == "prescription.pdf"
        assert prescription.file_path == "/uploads/RX-2025-006/prescription.pdf"
        assert prescription.file_size == 1024000

    def test_prescription_ocr_data(self, session):
        """Test prescription OCR data"""
        prescription = Prescription(
            prescription_id="RX-2025-007",
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            ocr_text="Amoxicillin 500mg TID for 7 days",
        )
        session.add(prescription)
        session.commit()

        assert prescription.ocr_text == "Amoxicillin 500mg TID for 7 days"

    def test_prescription_default_values(self, session):
        """Test default values for prescription fields"""
        prescription = Prescription(
            prescription_id="RX-2025-009", input_format=InputFormat.HANDWRITTEN_IMAGE
        )
        session.add(prescription)
        session.commit()

        assert prescription.processing_status == ProcessingStatus.UPLOADED
        assert prescription.validation_status == ValidationStatus.PENDING
        assert prescription.created_at is not None
        assert prescription.updated_at is not None

    def test_prescription_status_transitions(self, session):
        """Test prescription status transitions"""
        prescription = Prescription(
            prescription_id="RX-2025-011",
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            processing_status=ProcessingStatus.UPLOADED,
            validation_status=ValidationStatus.PENDING,
        )
        session.add(prescription)
        session.commit()

        # Transition to processing
        prescription.processing_status = ProcessingStatus.PROCESSING
        session.commit()
        assert prescription.processing_status == ProcessingStatus.PROCESSING

        # Transition to completed
        prescription.processing_status = ProcessingStatus.COMPLETED
        prescription.validation_status = ValidationStatus.VALID
        session.commit()
        assert prescription.processing_status == ProcessingStatus.COMPLETED
        assert prescription.validation_status == ValidationStatus.VALID

    def test_prescription_input_formats(self, session):
        """Test all input format types"""
        formats = [
            InputFormat.HANDWRITTEN_IMAGE,
            InputFormat.DIGITAL_DATA,
            InputFormat.VOICE_AUDIO,
        ]

        for idx, input_format in enumerate(formats):
            prescription = Prescription(
                prescription_id=f"RX-2025-{100+idx}", input_format=input_format
            )
            session.add(prescription)
            session.commit()

            assert prescription.input_format == input_format
            session.delete(prescription)
            session.commit()

    def test_prescription_processing_statuses(self, session):
        """Test all processing status types"""
        statuses = [
            ProcessingStatus.UPLOADED,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ]

        for idx, status in enumerate(statuses):
            prescription = Prescription(
                prescription_id=f"RX-2025-{200+idx}",
                input_format=InputFormat.HANDWRITTEN_IMAGE,
                processing_status=status,
            )
            session.add(prescription)
            session.commit()

            assert prescription.processing_status == status
            session.delete(prescription)
            session.commit()

    def test_prescription_validation_statuses(self, session):
        """Test all validation status types"""
        statuses = [
            ValidationStatus.PENDING,
            ValidationStatus.VALID,
            ValidationStatus.INVALID,
            ValidationStatus.REQUIRES_REVIEW,
        ]

        for idx, status in enumerate(statuses):
            prescription = Prescription(
                prescription_id=f"RX-2025-{300+idx}",
                input_format=InputFormat.HANDWRITTEN_IMAGE,
                validation_status=status,
            )
            session.add(prescription)
            session.commit()

            assert prescription.validation_status == status
            session.delete(prescription)
            session.commit()

    def test_prescription_to_dict(self, session):
        """Test prescription to_dict method"""
        prescription = Prescription(
            prescription_id="RX-2025-400",
            input_format=InputFormat.DIGITAL_DATA,
            patient_name="Test Patient",
            prescriber_name="Dr. Test",
        )
        session.add(prescription)
        session.commit()

        prescription_dict = prescription.to_dict()

        assert "id" in prescription_dict
        assert "prescription_id" in prescription_dict
        assert "input_format" in prescription_dict
        assert "patient_info" in prescription_dict
        assert "prescriber_info" in prescription_dict
        assert prescription_dict["prescription_id"] == "RX-2025-400"

    def test_prescription_repr(self, session):
        """Test prescription __repr__ method"""
        prescription = Prescription(
            prescription_id="RX-2025-500", input_format=InputFormat.HANDWRITTEN_IMAGE
        )
        session.add(prescription)
        session.commit()

        repr_str = repr(prescription)
        assert "RX-2025-500" in repr_str

    def test_prescription_with_date(self, session):
        """Test prescription with prescription date"""
        prescription_date = datetime(2025, 10, 11, 10, 30)
        prescription = Prescription(
            prescription_id="RX-2025-600",
            input_format=InputFormat.DIGITAL_DATA,
            prescription_date=prescription_date,
        )
        session.add(prescription)
        session.commit()

        assert prescription.prescription_date == prescription_date

    def test_prescription_json_fields(self, session):
        """Test prescription JSON fields"""
        import json

        allergies = json.dumps(["Penicillin", "Aspirin"])
        conditions = json.dumps(["Hypertension", "Diabetes"])

        prescription = Prescription(
            prescription_id="RX-2025-700",
            input_format=InputFormat.DIGITAL_DATA,
            patient_allergies=allergies,
            patient_conditions=conditions,
        )
        session.add(prescription)
        session.commit()

        assert prescription.patient_allergies == allergies
        assert prescription.patient_conditions == conditions

        # Test to_dict properly parses JSON
        prescription_dict = prescription.to_dict()
        assert isinstance(prescription_dict["patient_info"]["allergies"], list)
        assert isinstance(prescription_dict["patient_info"]["conditions"], list)
