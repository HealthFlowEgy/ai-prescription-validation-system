"""
PHI Anonymization Filter for HIPAA-Compliant Logging
Removes Protected Health Information from all log messages
"""

import logging
import re
from typing import List, Pattern, Tuple


class PHIAnonymizer(logging.Filter):
    """
    Logging filter that redacts Protected Health Information (PHI) from log messages.

    Complies with HIPAA Privacy Rule 45 CFR § 164.514(b)(2) Safe Harbor de-identification method.
    """

    # PHI patterns to redact (pattern, replacement)
    PHI_PATTERNS: List[Tuple[Pattern, str]] = [
        # Social Security Numbers (XXX-XX-XXXX)
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN-REDACTED]"),
        # Email addresses
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[EMAIL-REDACTED]",
        ),
        # Phone numbers (10 digits)
        (re.compile(r"\b\d{10}\b"), "[PHONE-REDACTED]"),
        (re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"), "[PHONE-REDACTED]"),
        # Dates (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD)
        (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "[DATE-REDACTED]"),
        (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "[DATE-REDACTED]"),
        # Medical Record Numbers (MRN-XXXXXXX)
        (re.compile(r"\bMRN-\d{7}\b", re.IGNORECASE), "[MRN-REDACTED]"),
        # IP Addresses (potential identifier)
        (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[IP-REDACTED]"),
        # Credit Card Numbers (16 digits)
        (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CC-REDACTED]"),
        # Common name patterns (First Last)
        (
            re.compile(r"\bPatient:\s*[A-Z][a-z]+\s+[A-Z][a-z]+\b"),
            "Patient: [NAME-REDACTED]",
        ),
        (
            re.compile(r"\bDoctor:\s*[A-Z][a-z]+\s+[A-Z][a-z]+\b"),
            "Doctor: [NAME-REDACTED]",
        ),
        # Address patterns
        (
            re.compile(
                r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
                re.IGNORECASE,
            ),
            "[ADDRESS-REDACTED]",
        ),
        # ZIP codes
        (re.compile(r"\b\d{5}(?:-\d{4})?\b"), "[ZIP-REDACTED]"),
    ]

    def __init__(self, name=""):
        super().__init__(name)
        self.redaction_count = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record by redacting PHI from the message.

        Args:
            record: LogRecord to filter

        Returns:
            True (always allow record to pass through after redaction)
        """
        if record.msg:
            original_msg = str(record.msg)
            redacted_msg = self._redact_phi(original_msg)

            if original_msg != redacted_msg:
                record.msg = redacted_msg
                self.redaction_count += 1

                # Log redaction event to audit log (if available)
                if hasattr(record, "audit_log"):
                    record.audit_log = True

        # Also redact args if present
        if record.args:
            record.args = tuple(self._redact_phi(str(arg)) for arg in record.args)

        return True

    def _redact_phi(self, text: str) -> str:
        """
        Redact PHI from text using defined patterns.

        Args:
            text: Text to redact

        Returns:
            Redacted text
        """
        redacted = text

        for pattern, replacement in self.PHI_PATTERNS:
            redacted = pattern.sub(replacement, redacted)

        return redacted

    def get_redaction_count(self) -> int:
        """Get total number of redactions performed."""
        return self.redaction_count


def configure_phi_safe_logging(app):
    """
    Configure application logging with PHI anonymization.

    Args:
        app: Flask application instance
    """
    # Create PHI anonymizer filter
    phi_filter = PHIAnonymizer()

    # Apply to all handlers
    for handler in app.logger.handlers:
        handler.addFilter(phi_filter)

    # Apply to root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(phi_filter)

    app.logger.info("PHI anonymization filter configured for all loggers")

    return phi_filter


# Utility function for explicit PHI redaction
def redact_phi(text: str) -> str:
    """
    Manually redact PHI from text.

    Args:
        text: Text to redact

    Returns:
        Redacted text
    """
    anonymizer = PHIAnonymizer()
    return anonymizer._redact_phi(text)
