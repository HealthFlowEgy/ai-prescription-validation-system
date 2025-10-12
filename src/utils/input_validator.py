"""
Comprehensive Input Validation
File: src/utils/input_validator.py
"""

import os
import re
import magic
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import Tuple, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validation result"""

    is_valid: bool
    message: str
    sanitized_value: Optional[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class FileValidator:
    """
    Comprehensive file upload validation

    Features:
    - File size limits
    - File type validation (extension + MIME type)
    - Malicious file detection
    - Filename sanitization
    """

    ALLOWED_EXTENSIONS = {
        "image": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
        "document": {".pdf", ".doc", ".docx", ".txt"},
        "prescription": {".png", ".jpg", ".jpeg", ".pdf"},
    }

    ALLOWED_MIME_TYPES = {
        "image": {"image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp"},
        "document": {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        },
        "prescription": {"image/png", "image/jpeg", "application/pdf"},
    }

    # File size limits (in bytes)
    MAX_FILE_SIZE = {
        "image": 10 * 1024 * 1024,  # 10MB
        "document": 20 * 1024 * 1024,  # 20MB
        "prescription": 15 * 1024 * 1024,  # 15MB
    }

    @classmethod
    def validate_upload(
        cls, file: FileStorage, file_category: str = "prescription"
    ) -> ValidationResult:
        """
        Comprehensive file validation

        Args:
            file: Uploaded file
            file_category: Category of file ('image', 'document', 'prescription')

        Returns:
            ValidationResult with validation status
        """
        errors = []

        # Check if file exists
        if not file or not file.filename:
            return ValidationResult(
                is_valid=False, message="No file provided", errors=["File is required"]
            )

        # Sanitize filename
        original_filename = file.filename
        safe_filename = secure_filename(original_filename)

        if not safe_filename:
            return ValidationResult(
                is_valid=False,
                message="Invalid filename",
                errors=["Filename contains invalid characters"],
            )

        # Check file extension
        ext = os.path.splitext(safe_filename)[1].lower()
        allowed_exts = cls.ALLOWED_EXTENSIONS.get(file_category, set())

        if ext not in allowed_exts:
            errors.append(
                f"Invalid file type: {ext}. Allowed: {', '.join(allowed_exts)}"
            )

        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        max_size = cls.MAX_FILE_SIZE.get(file_category, 10 * 1024 * 1024)

        if size > max_size:
            size_mb = size / (1024 * 1024)
            max_mb = max_size / (1024 * 1024)
            errors.append(f"File too large: {size_mb:.2f}MB. Maximum: {max_mb:.2f}MB")

        if size == 0:
            errors.append("File is empty")

        # Verify MIME type (prevent file type spoofing)
        try:
            file_content = file.read(2048)  # Read first 2KB for MIME detection
            file.seek(0)

            mime = magic.from_buffer(file_content, mime=True)
            allowed_mimes = cls.ALLOWED_MIME_TYPES.get(file_category, set())

            if mime not in allowed_mimes:
                errors.append(
                    f"Invalid MIME type: {mime}. Allowed: {', '.join(allowed_mimes)}"
                )

        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            errors.append("Could not verify file type")

        # Check for malicious content patterns
        if cls._contains_malicious_patterns(file):
            errors.append("File contains potentially malicious content")

        # Return result
        if errors:
            return ValidationResult(
                is_valid=False,
                message="File validation failed",
                sanitized_value=safe_filename,
                errors=errors,
            )
        else:
            return ValidationResult(
                is_valid=True,
                message="File is valid",
                sanitized_value=safe_filename,
                errors=[],
            )

    @staticmethod
    def _contains_malicious_patterns(file: FileStorage) -> bool:
        """
        Check for malicious patterns in file

        Args:
            file: File to check

        Returns:
            True if malicious patterns detected
        """
        try:
            # Read first 4KB for pattern matching
            content = file.read(4096)
            file.seek(0)

            # Convert to string (ignore errors)
            try:
                content_str = content.decode("utf-8", errors="ignore")
            except:
                content_str = str(content)

            # Malicious patterns
            malicious_patterns = [
                b"<?php",  # PHP code
                b"<script",  # JavaScript
                b"eval(",  # Code execution
                b"exec(",  # Command execution
                b"system(",  # System commands
                b"<iframe",  # Embedded frames
                b"javascript:",  # JavaScript protocol
                b"vbscript:",  # VBScript protocol
            ]

            for pattern in malicious_patterns:
                if pattern in content:
                    logger.warning(f"Malicious pattern detected: {pattern}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking for malicious patterns: {e}")
            return False


class InputValidator:
    """
    General input validation and sanitization

    Features:
    - Email validation
    - Phone number validation
    - URL validation
    - SQL injection prevention
    - XSS prevention
    - Input sanitization
    """

    # Regex patterns
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{1,14}$")  # E.164 format
    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|\/\*|\*\/)",  # SQL comments
        r"(\bOR\b.*=.*)",  # OR conditions
        r"(\bAND\b.*=.*)",  # AND conditions
        r"(;.*--)",  # Statement termination
        r"(\bUNION\b.*\bSELECT\b)",  # UNION attacks
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    @classmethod
    def validate_email(cls, email: str) -> ValidationResult:
        """
        Validate email address

        Args:
            email: Email address to validate

        Returns:
            ValidationResult
        """
        if not email:
            return ValidationResult(
                is_valid=False,
                message="Email is required",
                errors=["Email cannot be empty"],
            )

        email = email.strip().lower()

        if not cls.EMAIL_PATTERN.match(email):
            return ValidationResult(
                is_valid=False,
                message="Invalid email format",
                errors=["Email format is invalid"],
            )

        if len(email) > 254:  # RFC 5321
            return ValidationResult(
                is_valid=False,
                message="Email too long",
                errors=["Email exceeds maximum length"],
            )

        return ValidationResult(
            is_valid=True, message="Email is valid", sanitized_value=email
        )

    @classmethod
    def validate_phone(cls, phone: str) -> ValidationResult:
        """
        Validate phone number (E.164 format)

        Args:
            phone: Phone number to validate

        Returns:
            ValidationResult
        """
        if not phone:
            return ValidationResult(
                is_valid=False,
                message="Phone number is required",
                errors=["Phone cannot be empty"],
            )

        # Remove spaces and dashes
        phone = re.sub(r"[\s\-\(\)]", "", phone)

        if not cls.PHONE_PATTERN.match(phone):
            return ValidationResult(
                is_valid=False,
                message="Invalid phone number format",
                errors=["Phone must be in E.164 format (e.g., +1234567890)"],
            )

        return ValidationResult(
            is_valid=True, message="Phone number is valid", sanitized_value=phone
        )

    @classmethod
    def validate_url(cls, url: str) -> ValidationResult:
        """
        Validate URL

        Args:
            url: URL to validate

        Returns:
            ValidationResult
        """
        if not url:
            return ValidationResult(
                is_valid=False,
                message="URL is required",
                errors=["URL cannot be empty"],
            )

        url = url.strip()

        if not cls.URL_PATTERN.match(url):
            return ValidationResult(
                is_valid=False,
                message="Invalid URL format",
                errors=["URL format is invalid"],
            )

        return ValidationResult(
            is_valid=True, message="URL is valid", sanitized_value=url
        )

    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 1000) -> ValidationResult:
        """
        Sanitize user input (prevent SQL injection and XSS)

        Args:
            text: Text to sanitize
            max_length: Maximum allowed length

        Returns:
            ValidationResult with sanitized text
        """
        if not text:
            return ValidationResult(
                is_valid=True, message="Input is empty", sanitized_value=""
            )

        errors = []

        # Check length
        if len(text) > max_length:
            errors.append(
                f"Input too long: {len(text)} characters. Maximum: {max_length}"
            )

        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append("Input contains potentially malicious SQL patterns")
                break

        # Check for XSS
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append("Input contains potentially malicious script patterns")
                break

        # Sanitize HTML entities
        sanitized = text
        sanitized = sanitized.replace("<", "&lt;")
        sanitized = sanitized.replace(">", "&gt;")
        sanitized = sanitized.replace('"', "&quot;")
        sanitized = sanitized.replace("'", "&#x27;")
        sanitized = sanitized.replace("/", "&#x2F;")

        if errors:
            return ValidationResult(
                is_valid=False,
                message="Input validation failed",
                sanitized_value=sanitized,
                errors=errors,
            )
        else:
            return ValidationResult(
                is_valid=True, message="Input is valid", sanitized_value=sanitized
            )

    @classmethod
    def validate_username(cls, username: str) -> ValidationResult:
        """
        Validate username

        Args:
            username: Username to validate

        Returns:
            ValidationResult
        """
        if not username:
            return ValidationResult(
                is_valid=False,
                message="Username is required",
                errors=["Username cannot be empty"],
            )

        username = username.strip()
        errors = []

        # Length check
        if len(username) < 3:
            errors.append("Username must be at least 3 characters")
        if len(username) > 50:
            errors.append("Username must be at most 50 characters")

        # Character check (alphanumeric, underscore, hyphen)
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            errors.append(
                "Username can only contain letters, numbers, underscore, and hyphen"
            )

        # Must start with letter
        if not username[0].isalpha():
            errors.append("Username must start with a letter")

        if errors:
            return ValidationResult(
                is_valid=False, message="Invalid username", errors=errors
            )
        else:
            return ValidationResult(
                is_valid=True, message="Username is valid", sanitized_value=username
            )
