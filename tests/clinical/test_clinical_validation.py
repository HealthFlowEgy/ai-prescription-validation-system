"""
Clinical Validation Test Suite

Comprehensive tests for clinical validation service, pharmacist review workflow,
and safety alert system.

Author: HealthFlow QA Team
Date: 2025-10-14
"""

import pytest
from datetime import datetime, timedelta
from src.services.clinical_validation_service import (
    ClinicalValidationService,
    PharmacistReview,
    SafetyAlert,
    ReviewStatus,
    ReviewPriority,
    ValidationFlag,
    SafetySeverity
)
from src.models.prescription import Prescription
from src.models.user import User
from src.models.database import db


@pytest.fixture
def clinical_service():
    """Create clinical validation service instance"""
    return ClinicalValidationService()


@pytest.fixture
def test_prescription(db_session):
    """Create test prescription"""
    prescription = Prescription(
        prescription_id='RX-TEST-001',
        patient_name='John Doe',
        patient_dob='1975-05-15',
        input_format='HANDWRITTEN_IMAGE'
    )
    db_session.add(prescription)
    db_session.commit()
    return prescription


@pytest.fixture
def test_pharmacist(db_session):
    """Create test pharmacist user"""
    pharmacist = User(
        username='pharmacist@test.com',
        email='pharmacist@test.com',
        role='pharmacist'
    )
    pharmacist.set_password('test123')
    db_session.add(pharmacist)
    db_session.commit()
    return pharmacist


# ============================================================================
# Validation Flag Tests
# ============================================================================

class TestValidationFlags:
    """Test validation flag generation"""
    
    def test_low_confidence_ocr_flag(self, clinical_service, test_prescription):
        """Test that low OCR confidence generates appropriate flag"""
        confidence_scores = {
            'ocr_confidence': 0.72,  # Below threshold
            'nlp_confidence': 0.95
        }
        extracted_data = {
            'medications': []
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should have low confidence flag
        flags = review.validation_flags
        assert any(flag['flag_type'] == 'LOW_CONFIDENCE_OCR' for flag in flags)
        
        # Should require review
        low_conf_flag = next(f for f in flags if f['flag_type'] == 'LOW_CONFIDENCE_OCR')
        assert low_conf_flag['requires_review'] is True
    
    def test_critical_medication_flag(self, clinical_service, test_prescription):
        """Test that critical medications are flagged"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'medications': [
                {'name': 'Warfarin', 'dosage': '5mg', 'frequency': 'once daily'}
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should have critical medication flag
        flags = review.validation_flags
        assert any(flag['flag_type'] == 'CRITICAL_MEDICATION' for flag in flags)
        
        # Should be blocking
        crit_flag = next(f for f in flags if f['flag_type'] == 'CRITICAL_MEDICATION')
        assert crit_flag['blocking'] is True
    
    def test_drug_interaction_detection(self, clinical_service, test_prescription):
        """Test drug interaction detection"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'medications': [
                {'name': 'Warfarin', 'dosage': '5mg'},
                {'name': 'Aspirin', 'dosage': '81mg'}
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should detect Warfarin + Aspirin interaction
        flags = review.validation_flags
        interaction_flags = [f for f in flags if f['flag_type'] == 'DRUG_INTERACTION']
        assert len(interaction_flags) > 0
        
        # Should be severe
        assert interaction_flags[0]['severity'] == 'SEVERE'
    
    def test_missing_information_flag(self, clinical_service, test_prescription):
        """Test missing required information detection"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'medications': [{'name': 'Metformin'}],
            # Missing patient_name, patient_dob, prescriber info
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should have missing information flag
        flags = review.validation_flags
        assert any(flag['flag_type'] == 'MISSING_INFORMATION' for flag in flags)
    
    def test_age_inappropriate_medication_pediatric(self, clinical_service, test_prescription):
        """Test age-inappropriate medication detection for pediatric patients"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'patient_age': 10,  # Pediatric
            'medications': [
                {'name': 'Aspirin', 'dosage': '81mg'}  # Contraindicated in children
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should flag age inappropriateness
        flags = review.validation_flags
        assert any(flag['flag_type'] == 'AGE_INAPPROPRIATE' for flag in flags)
    
    def test_age_inappropriate_medication_geriatric(self, clinical_service, test_prescription):
        """Test age-inappropriate medication detection for elderly patients"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'patient_age': 75,  # Geriatric
            'medications': [
                {'name': 'Benzodiazepine', 'dosage': '5mg'}  # Beers Criteria
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Should flag potential inappropriateness
        flags = review.validation_flags
        assert any(flag['flag_type'] == 'AGE_INAPPROPRIATE' for flag in flags)


# ============================================================================
# Priority Determination Tests
# ============================================================================

class TestPriorityDetermination:
    """Test review priority determination"""
    
    def test_critical_priority_for_critical_medication(self, clinical_service, test_prescription):
        """Test that critical medications get CRITICAL priority"""
        confidence_scores = {'ocr_confidence': 0.95, 'nlp_confidence': 0.95}
        extracted_data = {
            'medications': [
                {'name': 'Insulin', 'dosage': '10 units'}
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        assert review.priority == ReviewPriority.CRITICAL.value
    
    def test_high_priority_for_severe_issues(self, clinical_service, test_prescription):
        """Test HIGH priority for severe validation issues"""
        confidence_scores = {
            'ocr_confidence': 0.70,  # Low confidence
            'nlp_confidence': 0.95
        }
        extracted_data = {
            'medications': [{'name': 'Metformin', 'dosage': '500mg'}]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        # Low confidence should trigger HIGH or MEDIUM priority
        assert review.priority in [ReviewPriority.HIGH.value, ReviewPriority.MEDIUM.value]
    
    def test_routine_priority_for_clean_prescription(self, clinical_service, test_prescription):
        """Test ROUTINE priority for clean prescriptions"""
        confidence_scores = {'ocr_confidence': 0.98, 'nlp_confidence': 0.97}
        extracted_data = {
            'patient_name': 'John Doe',
            'patient_dob': '1975-05-15',
            'patient_age': 49,
            'prescriber_name': 'Dr. Smith',
            'prescriber_license': 'MD12345',
            'date_prescribed': '2025-10-14',
            'medications': [
                {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'}
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        assert review.priority == ReviewPriority.ROUTINE.value


# ============================================================================
# Pharmacist Review Workflow Tests
# ============================================================================

class TestPharmacistReviewWorkflow:
    """Test complete pharmacist review workflow"""
    
    def test_create_review(self, clinical_service, test_prescription):
        """Test review creation"""
        confidence_scores = {'ocr_confidence': 0.90, 'nlp_confidence': 0.92}
        extracted_data = {
            'medications': [{'name': 'Metformin', 'dosage': '500mg'}]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        
        assert review is not None
        assert review.review_id.startswith('REV-')
        assert review.status == ReviewStatus.PENDING.value
        assert review.prescription_id == test_prescription.id
    
    def test_assign_review(self, clinical_service, test_prescription, test_pharmacist):
        """Test assigning review to pharmacist"""
        # Create review
        review = clinical_service.create_review(
            test_prescription,
            {'ocr_confidence': 0.90, 'nlp_confidence': 0.92},
            {'medications': []}
        )
        
        # Assign to pharmacist
        updated_review = clinical_service.assign_review(review, test_pharmacist.id)
        
        assert updated_review.assigned_to == test_pharmacist.id
        assert updated_review.status == ReviewStatus.IN_REVIEW.value
        assert updated_review.assigned_at is not None
        assert updated_review.started_at is not None
    
    def test_submit_approved_review(self, clinical_service, test_prescription, test_pharmacist, db_session):
        """Test submitting approved review"""
        # Create and assign review
        review = clinical_service.create_review(
            test_prescription,
            {'ocr_confidence': 0.90, 'nlp_confidence': 0.92},
            {'medications': [{'name': 'Metformin', 'dosage': '500mg'}]}
        )
        clinical_service.assign_review(review, test_pharmacist.id)
        
        # Submit approval
        updated_review = clinical_service.submit_review(
            review=review,
            pharmacist_id=test_pharmacist.id,
            status=ReviewStatus.APPROVED,
            notes='Prescription verified and approved'
        )
        
        assert updated_review.status == ReviewStatus.APPROVED.value
        assert updated_review.reviewed_by == test_pharmacist.id
        assert updated_review.completed_at is not None
        assert updated_review.approval_notes == 'Prescription verified and approved'
        assert updated_review.time_to_review_seconds is not None
    
    def test_submit_review_with_corrections(self, clinical_service, test_prescription, test_pharmacist):
        """Test submitting review with corrections"""
        original_data = {
            'medications': [
                {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'once daily'}
            ]
        }
        
        review = clinical_service.create_review(
            test_prescription,
            {'ocr_confidence': 0.85, 'nlp_confidence': 0.90},
            original_data
        )
        clinical_service.assign_review(review, test_pharmacist.id)
        
        # Submit with corrections
        corrected_data = {
            'medications': [
                {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'}  # Corrected
            ]
        }
        
        updated_review = clinical_service.submit_review(
            review=review,
            pharmacist_id=test_pharmacist.id,
            status=ReviewStatus.APPROVED_WITH_CHANGES,
            corrected_data=corrected_data,
            notes='Corrected frequency'
        )
        
        assert updated_review.num_corrections > 0
        assert updated_review.corrected_data is not None
        assert updated_review.accuracy_score < 1.0
    
    def test_submit_rejected_review(self, clinical_service, test_prescription, test_pharmacist):
        """Test submitting rejected review"""
        review = clinical_service.create_review(
            test_prescription,
            {'ocr_confidence': 0.60, 'nlp_confidence': 0.65},
            {'medications': []}
        )
        clinical_service.assign_review(review, test_pharmacist.id)
        
        # Submit rejection
        updated_review = clinical_service.submit_review(
            review=review,
            pharmacist_id=test_pharmacist.id,
            status=ReviewStatus.REJECTED,
            rejection_reason='Prescription illegible, cannot verify'
        )
        
        assert updated_review.status == ReviewStatus.REJECTED.value
        assert updated_review.rejection_reason is not None
    
    def test_get_pending_reviews(self, clinical_service, test_prescription, test_pharmacist):
        """Test fetching pending reviews"""
        # Create multiple reviews
        for i in range(3):
            prescription = Prescription(
                prescription_id=f'RX-TEST-{i:03d}',
                patient_name=f'Patient {i}'
            )
            db.session.add(prescription)
            db.session.commit()
            
            clinical_service.create_review(
                prescription,
                {'ocr_confidence': 0.90, 'nlp_confidence': 0.92},
                {'medications': []}
            )
        
        # Get pending reviews
        pending = clinical_service.get_pending_reviews(limit=10)
        
        assert len(pending) >= 3
        assert all(r.status == ReviewStatus.PENDING.value for r in pending)
    
    def test_get_pending_reviews_by_priority(self, clinical_service):
        """Test fetching pending reviews filtered by priority"""
        # Create critical review
        prescription = Prescription(
            prescription_id='RX-CRITICAL-001',
            patient_name='Critical Patient'
        )
        db.session.add(prescription)
        db.session.commit()
        
        clinical_service.create_review(
            prescription,
            {'ocr_confidence': 0.95, 'nlp_confidence': 0.95},
            {'medications': [{'name': 'Insulin', 'dosage': '10 units'}]}
        )
        
        # Get critical reviews
        critical_reviews = clinical_service.get_pending_reviews(
            priority=ReviewPriority.CRITICAL
        )
        
        assert len(critical_reviews) > 0
        assert all(r.priority == ReviewPriority.CRITICAL.value for r in critical_reviews)


# ============================================================================
# Safety Alert Tests
# ============================================================================

class TestSafetyAlerts:
    """Test safety alert system"""
    
    def test_create_safety_alert(self, clinical_service, test_prescription):
        """Test creating safety alert"""
        alert = clinical_service.create_safety_alert(
            prescription_id=test_prescription.id,
            alert_type='DRUG_INTERACTION',
            severity=SafetySeverity.SEVERE,
            description='Warfarin + Aspirin interaction detected',
            detected_by='AI'
        )
        
        assert alert is not None
        assert alert.alert_id.startswith('ALR-')
        assert alert.severity == SafetySeverity.SEVERE.value
        assert alert.status == 'OPEN'
    
    def test_safety_alert_fda_reporting(self, clinical_service, test_prescription):
        """Test FDA reporting flag for critical safety alerts"""
        alert = clinical_service.create_safety_alert(
            prescription_id=test_prescription.id,
            alert_type='ADVERSE_EVENT',
            severity=SafetySeverity.LIFE_THREATENING,
            description='Severe adverse reaction reported',
            detected_by='PHARMACIST',
            requires_fda_report=True
        )
        
        assert alert.requires_fda_report is True
        assert alert.fda_report_filed is False


# ============================================================================
# Metrics Tests
# ============================================================================

class TestClinicalMetrics:
    """Test clinical metrics calculation"""
    
    def test_get_review_metrics(self, clinical_service, test_prescription, test_pharmacist):
        """Test fetching review metrics"""
        # Create and complete some reviews
        for i in range(5):
            prescription = Prescription(
                prescription_id=f'RX-METRICS-{i:03d}',
                patient_name=f'Patient {i}'
            )
            db.session.add(prescription)
            db.session.commit()
            
            review = clinical_service.create_review(
                prescription,
                {'ocr_confidence': 0.90 + (i * 0.01), 'nlp_confidence': 0.92},
                {'medications': [{'name': 'Metformin', 'dosage': '500mg'}]}
            )
            
            # Complete review
            clinical_service.assign_review(review, test_pharmacist.id)
            clinical_service.submit_review(
                review, test_pharmacist.id, ReviewStatus.APPROVED
            )
        
        # Get metrics
        metrics = clinical_service.get_review_metrics()
        
        assert metrics['total_reviews'] >= 5
        assert metrics['completed_reviews'] >= 5
        assert 0 <= metrics['approval_rate'] <= 1
        assert metrics['avg_time_to_review_minutes'] >= 0
    
    def test_metrics_date_filtering(self, clinical_service):
        """Test metrics with date range filtering"""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        metrics = clinical_service.get_review_metrics(
            start_date=start_date,
            end_date=end_date
        )
        
        # Should return metrics (even if empty)
        assert isinstance(metrics, dict)


# ============================================================================
# Accuracy Calculation Tests
# ============================================================================

class TestAccuracyCalculation:
    """Test AI accuracy calculation"""
    
    def test_perfect_accuracy(self, clinical_service):
        """Test accuracy calculation with no corrections"""
        original = {
            'patient_name': 'John Doe',
            'medication': 'Metformin',
            'dosage': '500mg'
        }
        corrected = original.copy()
        
        accuracy = clinical_service._calculate_accuracy(original, corrected)
        assert accuracy == 1.0
    
    def test_partial_accuracy(self, clinical_service):
        """Test accuracy calculation with some corrections"""
        original = {
            'patient_name': 'John Doe',
            'medication': 'Metformin',
            'dosage': '500mg',
            'frequency': 'once daily'
        }
        corrected = {
            'patient_name': 'John Doe',
            'medication': 'Metformin',
            'dosage': '500mg',
            'frequency': 'twice daily'  # Corrected
        }
        
        accuracy = clinical_service._calculate_accuracy(original, corrected)
        assert accuracy == 0.75  # 3 out of 4 correct


# ============================================================================
# Integration Tests
# ============================================================================

class TestClinicalValidationIntegration:
    """Integration tests for complete workflow"""
    
    def test_complete_review_workflow(self, clinical_service, test_prescription, test_pharmacist):
        """Test complete end-to-end review workflow"""
        # Step 1: AI processes prescription
        confidence_scores = {'ocr_confidence': 0.92, 'nlp_confidence': 0.94}
        extracted_data = {
            'patient_name': 'John Doe',
            'patient_dob': '1975-05-15',
            'medications': [
                {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'}
            ]
        }
        
        # Step 2: Create review
        review = clinical_service.create_review(
            test_prescription,
            confidence_scores,
            extracted_data
        )
        assert review.status == ReviewStatus.PENDING.value
        
        # Step 3: Pharmacist takes review
        review = clinical_service.assign_review(review, test_pharmacist.id)
        assert review.status == ReviewStatus.IN_REVIEW.value
        
        # Step 4: Pharmacist approves
        review = clinical_service.submit_review(
            review,
            test_pharmacist.id,
            ReviewStatus.APPROVED,
            notes='Verified and approved'
        )
        assert review.status == ReviewStatus.APPROVED.value
        assert review.completed_at is not None
        
        # Step 5: Verify prescription updated
        db.session.refresh(test_prescription)
        from src.models.prescription import ValidationStatus
        assert test_prescription.validation_status == ValidationStatus.VALID


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])