"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set test environment variables before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
os.environ['SKIP_DB_VALIDATION'] = 'true'

from flask import Flask
from models.database import db as _db
from models.user import User
from models.prescription import Prescription, ValidationStatus, ProcessingStatus, InputFormat


@pytest.fixture(scope='session')
def app():
    """Create minimal Flask application for testing"""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'WTF_CSRF_ENABLED': False,
    })
    
    # Initialize database
    _db.init_app(app)
    
    # Create application context
    ctx = app.app_context()
    ctx.push()
    
    # Create all tables
    _db.create_all()
    
    yield app
    
    # Cleanup
    _db.session.remove()
    _db.drop_all()
    ctx.pop()


@pytest.fixture(scope='session')
def db(app):
    """Get database instance"""
    return _db


@pytest.fixture(scope='function')
def session(db):
    """Create a new database session for a test"""
    # Create all tables fresh for each test
    db.create_all()
    
    yield db.session
    
    # Rollback any changes and remove session
    db.session.rollback()
    db.session.remove()
    
    # Drop all tables to ensure clean state
    db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


# User fixtures
@pytest.fixture
def test_user(session):
    """Create a test user"""
    user = User(
        username='testuser',
        email='test@example.com',
        name='Test User',
        role='pharmacist',
        is_active=True,
        is_verified=True
    )
    user.set_password('TestPassword123!')
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def admin_user(session):
    """Create an admin user"""
    user = User(
        username='admin',
        email='admin@example.com',
        name='Admin User',
        role='admin',
        is_active=True,
        is_verified=True
    )
    user.set_password('AdminPassword123!')
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def doctor_user(session):
    """Create a doctor user"""
    user = User(
        username='doctor',
        email='doctor@example.com',
        name='Dr. Smith',
        role='doctor',
        is_active=True,
        is_verified=True
    )
    user.set_password('DoctorPassword123!')
    session.add(user)
    session.commit()
    return user


# Prescription fixtures
@pytest.fixture
def test_prescription(session, test_user):
    """Create a test prescription"""
    prescription = Prescription(
        prescription_id='RX-TEST-001',
        input_format=InputFormat.HANDWRITTEN_IMAGE,
        processing_status=ProcessingStatus.UPLOADED,
        validation_status=ValidationStatus.PENDING,
        patient_name='John Doe',
        patient_age=35,
        patient_gender='M',
        doctor_name='Dr. Smith',
        doctor_license='DOC123456',
        created_by=test_user.id
    )
    session.add(prescription)
    session.commit()
    return prescription


@pytest.fixture
def valid_prescription(session, test_user):
    """Create a valid prescription"""
    prescription = Prescription(
        prescription_id='RX-VALID-001',
        input_format=InputFormat.DIGITAL_DATA,
        processing_status=ProcessingStatus.COMPLETED,
        validation_status=ValidationStatus.VALID,
        patient_name='Jane Doe',
        patient_age=28,
        patient_gender='F',
        doctor_name='Dr. Johnson',
        doctor_license='DOC789012',
        created_by=test_user.id
    )
    session.add(prescription)
    session.commit()
    return prescription


# Mock data fixtures
@pytest.fixture
def mock_ocr_result():
    """Mock OCR extraction result"""
    return {
        'raw_text': 'Amoxicillin 500mg TID for 7 days',
        'structured_data': {
            'medications': [
                {
                    'drug_name': 'Amoxicillin',
                    'dosage': '500mg',
                    'frequency': 'TID',
                    'duration': '7 days'
                }
            ],
            'patient_info': {
                'name': 'John Doe',
                'age': 35,
                'gender': 'M'
            },
            'doctor_info': {
                'name': 'Dr. Smith',
                'license': 'DOC123456'
            }
        },
        'confidence': 0.92
    }


@pytest.fixture
def mock_prescription_image():
    """Mock prescription image file"""
    from io import BytesIO
    try:
        from PIL import Image
        # Create a simple test image
        img = Image.new('RGB', (800, 600), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    except ImportError:
        # If PIL not available, return empty bytes
        return BytesIO(b'fake image data')

