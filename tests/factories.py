"""
Test data factories using factory_boy
"""
import factory
from factory import fuzzy
from datetime import datetime, timedelta
import random

from models.user import User
from models.prescription import (
    Prescription, 
    ValidationStatus, 
    ProcessingStatus, 
    InputFormat
)


class UserFactory(factory.Factory):
    """Factory for creating test users"""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    name = factory.Faker('name')
    role = fuzzy.FuzzyChoice(['pharmacist', 'doctor', 'admin', 'auditor'])
    is_active = True
    is_verified = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password after user creation"""
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password('TestPassword123!')


class PharmacistFactory(UserFactory):
    """Factory for pharmacist users"""
    role = 'pharmacist'


class DoctorFactory(UserFactory):
    """Factory for doctor users"""
    role = 'doctor'


class AdminFactory(UserFactory):
    """Factory for admin users"""
    role = 'admin'


class PrescriptionFactory(factory.Factory):
    """Factory for creating test prescriptions"""
    
    class Meta:
        model = Prescription
    
    prescription_id = factory.Sequence(lambda n: f'RX-{datetime.now().year}-{n:06d}')
    input_format = fuzzy.FuzzyChoice([
        InputFormat.HANDWRITTEN_IMAGE,
        InputFormat.DIGITAL_DATA,
        InputFormat.VOICE_AUDIO
    ])
    processing_status = fuzzy.FuzzyChoice([
        ProcessingStatus.UPLOADED,
        ProcessingStatus.PROCESSING,
        ProcessingStatus.COMPLETED,
        ProcessingStatus.FAILED
    ])
    validation_status = fuzzy.FuzzyChoice([
        ValidationStatus.PENDING,
        ValidationStatus.VALID,
        ValidationStatus.INVALID,
        ValidationStatus.REQUIRES_REVIEW
    ])
    
    # Patient information
    patient_name = factory.Faker('name')
    patient_age = fuzzy.FuzzyInteger(1, 100)
    patient_gender = fuzzy.FuzzyChoice(['M', 'F', 'O'])
    patient_id = factory.Sequence(lambda n: f'PAT-{n:08d}')
    
    # Doctor information
    doctor_name = factory.Faker('name')
    doctor_license = factory.Sequence(lambda n: f'DOC-{n:06d}')
    doctor_signature = None
    
    # Prescription content
    diagnosis = factory.Faker('sentence', nb_words=5)
    notes = factory.Faker('text', max_nb_chars=200)
    
    # Timestamps
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    
    # File information
    original_filename = factory.LazyAttribute(
        lambda obj: f'prescription_{obj.prescription_id}.pdf'
    )
    file_path = factory.LazyAttribute(
        lambda obj: f'/uploads/{obj.prescription_id}/{obj.original_filename}'
    )
    file_size = fuzzy.FuzzyInteger(100000, 5000000)  # 100KB to 5MB
    
    # OCR and processing
    ocr_text = factory.Faker('text', max_nb_chars=500)
    ocr_confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    processing_time = fuzzy.FuzzyFloat(1.0, 30.0)
    
    # Validation
    validation_errors = factory.LazyFunction(lambda: [])
    validation_warnings = factory.LazyFunction(lambda: [])


class ValidPrescriptionFactory(PrescriptionFactory):
    """Factory for valid prescriptions"""
    processing_status = ProcessingStatus.COMPLETED
    validation_status = ValidationStatus.VALID
    validation_errors = factory.LazyFunction(lambda: [])
    ocr_confidence = fuzzy.FuzzyFloat(0.85, 1.0)


class InvalidPrescriptionFactory(PrescriptionFactory):
    """Factory for invalid prescriptions"""
    processing_status = ProcessingStatus.COMPLETED
    validation_status = ValidationStatus.INVALID
    validation_errors = factory.LazyFunction(lambda: [
        {'field': 'doctor_license', 'message': 'Invalid license number'},
        {'field': 'medications', 'message': 'No medications found'}
    ])


class PendingPrescriptionFactory(PrescriptionFactory):
    """Factory for pending prescriptions"""
    processing_status = ProcessingStatus.UPLOADED
    validation_status = ValidationStatus.PENDING
    ocr_text = None
    ocr_confidence = None


# Helper functions for creating test data

def create_user(**kwargs):
    """Create a user with custom attributes"""
    return UserFactory(**kwargs)


def create_prescription(**kwargs):
    """Create a prescription with custom attributes"""
    return PrescriptionFactory(**kwargs)


def create_batch_users(count=10, **kwargs):
    """Create multiple users"""
    return [UserFactory(**kwargs) for _ in range(count)]


def create_batch_prescriptions(count=10, **kwargs):
    """Create multiple prescriptions"""
    return [PrescriptionFactory(**kwargs) for _ in range(count)]


def create_realistic_prescription():
    """Create a realistic prescription with proper medical data"""
    medications = [
        {
            'drug_name': random.choice([
                'Amoxicillin', 'Ibuprofen', 'Metformin', 
                'Lisinopril', 'Atorvastatin', 'Omeprazole'
            ]),
            'dosage': random.choice(['250mg', '500mg', '1000mg', '10mg', '20mg']),
            'frequency': random.choice(['Once daily', 'Twice daily', 'Three times daily']),
            'duration': random.choice(['7 days', '14 days', '30 days', '90 days'])
        }
        for _ in range(random.randint(1, 4))
    ]
    
    return PrescriptionFactory(
        processing_status=ProcessingStatus.COMPLETED,
        validation_status=ValidationStatus.VALID,
        medications_json=str(medications),
        ocr_confidence=random.uniform(0.85, 0.98)
    )

