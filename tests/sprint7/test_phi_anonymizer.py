"""
Tests for PHI Anonymization Filter
"""

import logging

from src.utils.phi_anonymizer import PHIAnonymizer, redact_phi


class TestPHIAnonymizer:
    """Test PHI anonymization functionality."""

    def test_ssn_redaction(self):
        """Test SSN redaction."""
        text = "Patient SSN is 123-45-6789"
        result = redact_phi(text)
        assert "[SSN-REDACTED]" in result
        assert "123-45-6789" not in result

    def test_email_redaction(self):
        """Test email redaction."""
        text = "Contact: patient@example.com"
        result = redact_phi(text)
        assert "[EMAIL-REDACTED]" in result
        assert "patient@example.com" not in result

    def test_phone_redaction(self):
        """Test phone number redaction."""
        text = "Phone: 555-123-4567"
        result = redact_phi(text)
        assert "[PHONE-REDACTED]" in result
        assert "555-123-4567" not in result

    def test_date_redaction(self):
        """Test date redaction."""
        text = "DOB: 01/15/1980"
        result = redact_phi(text)
        assert "[DATE-REDACTED]" in result
        assert "01/15/1980" not in result

    def test_mrn_redaction(self):
        """Test medical record number redaction."""
        text = "MRN-1234567"
        result = redact_phi(text)
        assert "[MRN-REDACTED]" in result
        assert "MRN-1234567" not in result

    def test_ip_address_redaction(self):
        """Test IP address redaction."""
        text = "IP: 192.168.1.1"
        result = redact_phi(text)
        assert "[IP-REDACTED]" in result
        assert "192.168.1.1" not in result

    def test_credit_card_redaction(self):
        """Test credit card redaction."""
        text = "Card: 1234-5678-9012-3456"
        result = redact_phi(text)
        assert "[CC-REDACTED]" in result
        assert "1234-5678-9012-3456" not in result

    def test_name_redaction(self):
        """Test patient name redaction."""
        text = "Patient: John Smith"
        result = redact_phi(text)
        assert "[NAME-REDACTED]" in result
        assert "John Smith" not in result

    def test_address_redaction(self):
        """Test address redaction."""
        text = "Address: 123 Main Street"
        result = redact_phi(text)
        assert "[ADDRESS-REDACTED]" in result
        assert "123 Main Street" not in result

    def test_zip_code_redaction(self):
        """Test ZIP code redaction."""
        text = "ZIP: 12345"
        result = redact_phi(text)
        assert "[ZIP-REDACTED]" in result
        assert "12345" not in result

    def test_multiple_phi_redaction(self):
        """Test multiple PHI elements in one string."""
        text = "Patient John Smith, SSN 123-45-6789, DOB 01/15/1980, email patient@example.com"
        result = redact_phi(text)
        assert "[NAME-REDACTED]" in result
        assert "[SSN-REDACTED]" in result
        assert "[DATE-REDACTED]" in result
        assert "[EMAIL-REDACTED]" in result

    def test_logging_filter(self):
        """Test PHI anonymizer as logging filter."""
        anonymizer = PHIAnonymizer()

        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Patient SSN: 123-45-6789",
            args=(),
            exc_info=None,
        )

        # Apply filter
        anonymizer.filter(record)

        # Check redaction
        assert "[SSN-REDACTED]" in record.msg
        assert "123-45-6789" not in record.msg
        assert anonymizer.get_redaction_count() == 1
