#!/usr/bin/env python3
"""
API tests for AI-Based Digital Prescription Validation System
"""

import json
import os
import sys
import unittest
from io import BytesIO

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app
from models.user import User, db


class APITestCase(unittest.TestCase):
    """Test cases for API endpoints"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Create test user
            test_user = User(
                name="Test User", email="test@example.com", role="user", is_active=True
            )
            db.session.add(test_user)
            db.session.commit()
            self.test_user_id = test_user.id

    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(
            data["service"], "AI-Based Digital Prescription Validation System"
        )

    def test_prescription_upload(self):
        """Test prescription upload endpoint"""
        # Create a test image file
        test_image = BytesIO(b"fake image data")
        test_image.name = "test_prescription.png"

        response = self.client.post(
            "/api/prescriptions/upload",
            data={
                "file": (test_image, "test_prescription.png"),
                "input_format": "handwritten_image",
                "user_id": self.test_user_id,
            },
        )

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data["status"], "uploaded")
        self.assertIn("prescription_id", data)
        self.assertEqual(data["file_info"]["filename"], "test_prescription.png")

    def test_prescription_upload_no_file(self):
        """Test prescription upload without file"""
        response = self.client.post(
            "/api/prescriptions/upload",
            data={"input_format": "handwritten_image", "user_id": self.test_user_id},
        )

        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertEqual(data["error"], "No file provided")

    def test_prescription_upload_invalid_format(self):
        """Test prescription upload with invalid file format"""
        test_file = BytesIO(b"fake file data")
        test_file.name = "test.txt"

        response = self.client.post(
            "/api/prescriptions/upload",
            data={
                "file": (test_file, "test.txt"),
                "input_format": "handwritten_image",
                "user_id": self.test_user_id,
            },
        )

        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertEqual(
            data["error"],
            "Invalid file format. Allowed formats: pdf, png, jpg, jpeg, tiff, bmp",
        )

    def test_get_prescriptions(self):
        """Test get prescriptions endpoint"""
        response = self.client.get(f"/api/prescriptions?user_id={self.test_user_id}")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIsInstance(data["prescriptions"], list)
        self.assertEqual(data["total"], 0)  # No prescriptions initially

    def test_get_prescription_not_found(self):
        """Test get prescription with invalid ID"""
        response = self.client.get("/api/prescriptions/invalid-id")
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual(data["error"], "Prescription not found")


class ValidationServiceTestCase(unittest.TestCase):
    """Test cases for validation service"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_drug_interaction_checker(self):
        """Test drug interaction checking"""
        from models.prescription import Medication
        from services.validation_service import DrugInteractionChecker

        checker = DrugInteractionChecker()

        # Create test medications
        med1 = Medication(drug_name="warfarin", dosage="5mg", frequency="daily")
        med2 = Medication(drug_name="aspirin", dosage="81mg", frequency="daily")

        interactions = checker.check_interactions([med1, med2])

        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].severity, "severe")
        self.assertIn("bleeding", interactions[0].description.lower())

    def test_dosage_validator(self):
        """Test dosage validation"""
        from models.prescription import Medication
        from services.validation_service import DosageValidator

        validator = DosageValidator()

        # Test normal dosage
        med_normal = Medication(
            drug_name="lisinopril", dosage="10mg", frequency="daily"
        )
        issues_normal = validator.validate_dosage(med_normal)
        self.assertEqual(len(issues_normal), 0)

        # Test high dosage
        med_high = Medication(drug_name="lisinopril", dosage="100mg", frequency="daily")
        issues_high = validator.validate_dosage(med_high)
        self.assertEqual(len(issues_high), 1)
        self.assertEqual(issues_high[0].issue_type, "dosage_too_high")


class OCRServiceTestCase(unittest.TestCase):
    """Test cases for OCR service"""

    def test_text_preprocessing(self):
        """Test text preprocessing functions"""
        from services.ocr_service import OCRService

        ocr_service = OCRService()

        # Test text cleaning
        dirty_text = "  Dr.  John   Smith  \n\n  Prescription  "
        clean_text = ocr_service.clean_extracted_text(dirty_text)

        self.assertNotIn("\n\n", clean_text)
        self.assertNotIn("   ", clean_text)  # Multiple spaces should be reduced


class NLPServiceTestCase(unittest.TestCase):
    """Test cases for NLP service"""

    def test_medication_extraction(self):
        """Test medication extraction from text"""
        from services.nlp_service import NLPService

        nlp_service = NLPService()

        test_text = """
        Rx:
        1. Lisinopril 10mg tablets
           Take 1 tablet by mouth once daily
           Quantity: 30 tablets
           Refills: 2
        
        2. Metformin 500mg tablets
           Take 1 tablet by mouth twice daily with meals
           Quantity: 60 tablets
           Refills: 3
        """

        extracted_data = nlp_service.extract_prescription_data(test_text)

        self.assertIn("medications", extracted_data)
        medications = extracted_data["medications"]

        # Should extract at least 2 medications
        self.assertGreaterEqual(len(medications), 2)

        # Check if Lisinopril was extracted
        lisinopril_found = any(
            "lisinopril" in med["drug_name"].lower() for med in medications
        )
        self.assertTrue(lisinopril_found)


def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTest(unittest.makeSuite(APITestCase))
    test_suite.addTest(unittest.makeSuite(ValidationServiceTestCase))
    test_suite.addTest(unittest.makeSuite(OCRServiceTestCase))
    test_suite.addTest(unittest.makeSuite(NLPServiceTestCase))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
