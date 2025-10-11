"""
Unit tests for Prescription model
"""
import pytest
from datetime import datetime
from models.prescription import (
    Prescription,
    ValidationStatus,
    ProcessingStatus,
    InputFormat
)


class TestPrescriptionModel:
    """Test cases for Prescription model"""
    
    def test_prescription_creation(self, session, test_user):
        """Test creating a prescription"""
        prescription = Prescription(
            prescription_id='RX-2025-001',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            patient_name='John Doe',
            patient_age=35,
            doctor_name='Dr. Smith',
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.id is not None
        assert prescription.prescription_id == 'RX-2025-001'
        assert prescription.input_format == InputFormat.HANDWRITTEN_IMAGE
        assert prescription.processing_status == ProcessingStatus.UPLOADED
        assert prescription.validation_status == ValidationStatus.PENDING
    
    def test_prescription_unique_id(self, session, test_user):
        """Test that prescription IDs must be unique"""
        prescription1 = Prescription(
            prescription_id='RX-2025-001',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            created_by=test_user.id
        )
        session.add(prescription1)
        session.commit()
        
        prescription2 = Prescription(
            prescription_id='RX-2025-001',
            input_format=InputFormat.DIGITAL_DATA,
            created_by=test_user.id
        )
        session.add(prescription2)
        
        with pytest.raises(Exception):  # IntegrityError
            session.commit()
    
    def test_prescription_enums(self, session, test_user):
        """Test prescription enum values"""
        prescription = Prescription(
            prescription_id='RX-2025-002',
            input_format=InputFormat.VOICE_AUDIO,
            processing_status=ProcessingStatus.PROCESSING,
            validation_status=ValidationStatus.REQUIRES_REVIEW,
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.input_format == InputFormat.VOICE_AUDIO
        assert prescription.processing_status == ProcessingStatus.PROCESSING
        assert prescription.validation_status == ValidationStatus.REQUIRES_REVIEW
    
    def test_prescription_patient_info(self, session, test_user):
        """Test prescription patient information"""
        prescription = Prescription(
            prescription_id='RX-2025-003',
            input_format=InputFormat.DIGITAL_DATA,
            patient_name='Jane Doe',
            patient_age=28,
            patient_gender='F',
            patient_id='PAT-12345',
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.patient_name == 'Jane Doe'
        assert prescription.patient_age == 28
        assert prescription.patient_gender == 'F'
        assert prescription.patient_id == 'PAT-12345'
    
    def test_prescription_doctor_info(self, session, test_user):
        """Test prescription doctor information"""
        prescription = Prescription(
            prescription_id='RX-2025-004',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            doctor_name='Dr. Johnson',
            doctor_license='DOC-789012',
            doctor_signature='signature_data',
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.doctor_name == 'Dr. Johnson'
        assert prescription.doctor_license == 'DOC-789012'
        assert prescription.doctor_signature == 'signature_data'
    
    def test_prescription_timestamps(self, session, test_user):
        """Test prescription timestamps"""
        prescription = Prescription(
            prescription_id='RX-2025-005',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.created_at is not None
        assert prescription.updated_at is not None
        assert isinstance(prescription.created_at, datetime)
        assert isinstance(prescription.updated_at, datetime)
    
    def test_prescription_file_info(self, session, test_user):
        """Test prescription file information"""
        prescription = Prescription(
            prescription_id='RX-2025-006',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            original_filename='prescription.pdf',
            file_path='/uploads/RX-2025-006/prescription.pdf',
            file_size=1024000,
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.original_filename == 'prescription.pdf'
        assert prescription.file_path == '/uploads/RX-2025-006/prescription.pdf'
        assert prescription.file_size == 1024000
    
    def test_prescription_ocr_data(self, session, test_user):
        """Test prescription OCR data"""
        prescription = Prescription(
            prescription_id='RX-2025-007',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            ocr_text='Amoxicillin 500mg TID for 7 days',
            ocr_confidence=0.92,
            processing_time=5.3,
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.ocr_text == 'Amoxicillin 500mg TID for 7 days'
        assert prescription.ocr_confidence == 0.92
        assert prescription.processing_time == 5.3
    
    def test_prescription_validation_data(self, session, test_user):
        """Test prescription validation data"""
        errors = [
            {'field': 'doctor_license', 'message': 'Invalid license'},
            {'field': 'medications', 'message': 'No medications found'}
        ]
        warnings = [
            {'field': 'dosage', 'message': 'High dosage detected'}
        ]
        
        prescription = Prescription(
            prescription_id='RX-2025-008',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            validation_status=ValidationStatus.INVALID,
            validation_errors=str(errors),
            validation_warnings=str(warnings),
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.validation_status == ValidationStatus.INVALID
        assert prescription.validation_errors is not None
        assert prescription.validation_warnings is not None
    
    def test_prescription_default_values(self, session, test_user):
        """Test default values for prescription fields"""
        prescription = Prescription(
            prescription_id='RX-2025-009',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.processing_status == ProcessingStatus.UPLOADED
        assert prescription.validation_status == ValidationStatus.PENDING
        assert prescription.created_at is not None
        assert prescription.updated_at is not None
    
    def test_prescription_diagnosis_and_notes(self, session, test_user):
        """Test prescription diagnosis and notes"""
        prescription = Prescription(
            prescription_id='RX-2025-010',
            input_format=InputFormat.DIGITAL_DATA,
            diagnosis='Bacterial infection',
            notes='Patient allergic to penicillin',
            created_by=test_user.id
        )
        session.add(prescription)
        session.commit()
        
        assert prescription.diagnosis == 'Bacterial infection'
        assert prescription.notes == 'Patient allergic to penicillin'
    
    def test_prescription_status_transitions(self, session, test_user):
        """Test prescription status transitions"""
        prescription = Prescription(
            prescription_id='RX-2025-011',
            input_format=InputFormat.HANDWRITTEN_IMAGE,
            processing_status=ProcessingStatus.UPLOADED,
            validation_status=ValidationStatus.PENDING,
            created_by=test_user.id
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
    
    def test_prescription_input_formats(self, session, test_user):
        """Test all input format types"""
        formats = [
            InputFormat.HANDWRITTEN_IMAGE,
            InputFormat.DIGITAL_DATA,
            InputFormat.VOICE_AUDIO
        ]
        
        for idx, input_format in enumerate(formats):
            prescription = Prescription(
                prescription_id=f'RX-2025-{100+idx}',
                input_format=input_format,
                created_by=test_user.id
            )
            session.add(prescription)
            session.commit()
            
            assert prescription.input_format == input_format
            session.delete(prescription)
            session.commit()
    
    def test_prescription_processing_statuses(self, session, test_user):
        """Test all processing status types"""
        statuses = [
            ProcessingStatus.UPLOADED,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED
        ]
        
        for idx, status in enumerate(statuses):
            prescription = Prescription(
                prescription_id=f'RX-2025-{200+idx}',
                input_format=InputFormat.HANDWRITTEN_IMAGE,
                processing_status=status,
                created_by=test_user.id
            )
            session.add(prescription)
            session.commit()
            
            assert prescription.processing_status == status
            session.delete(prescription)
            session.commit()
    
    def test_prescription_validation_statuses(self, session, test_user):
        """Test all validation status types"""
        statuses = [
            ValidationStatus.PENDING,
            ValidationStatus.VALID,
            ValidationStatus.INVALID,
            ValidationStatus.REQUIRES_REVIEW
        ]
        
        for idx, status in enumerate(statuses):
            prescription = Prescription(
                prescription_id=f'RX-2025-{300+idx}',
                input_format=InputFormat.HANDWRITTEN_IMAGE,
                validation_status=status,
                created_by=test_user.id
            )
            session.add(prescription)
            session.commit()
            
            assert prescription.validation_status == status
            session.delete(prescription)
            session.commit()

