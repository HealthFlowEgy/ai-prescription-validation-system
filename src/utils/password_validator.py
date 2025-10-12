"""
Enhanced Password Validator following OWASP guidelines
File: src/utils/password_validator.py
"""

import string
import re
from typing import Tuple, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Type-safe validation result"""

    is_valid: bool
    message: str
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class PasswordValidator:
    """
    OWASP-compliant password validator

    Features:
    - Minimum 12 characters (OWASP recommendation)
    - Complexity requirements (uppercase, lowercase, digit, special)
    - Common password detection
    - Sequential character detection
    - Bcrypt 72-byte limit enforcement
    """

    # OWASP recommended settings
    MIN_LENGTH = 12
    MAX_LENGTH = 72  # Bcrypt limitation
    SPECIAL_CHARS = string.punctuation

    # Common passwords (subset - in production, load from file)
    COMMON_PASSWORDS = {
        "password",
        "password123",
        "12345678",
        "qwerty",
        "abc123",
        "monkey",
        "1234567890",
        "letmein",
        "trustno1",
        "dragon",
        "baseball",
        "iloveyou",
        "master",
        "sunshine",
        "ashley",
        "bailey",
        "passw0rd",
        "shadow",
        "123123",
        "654321",
        "superman",
        "qazwsx",
        "michael",
        "football",
        "welcome",
        "jesus",
        "ninja",
        "mustang",
        "password1",
        "123456789",
        "admin",
        "root",
        "toor",
        "pass",
        "test",
        "guest",
        "info",
        "administrator",
        "oracle",
        "postgres",
        "mysql",
    }

    @classmethod
    def load_common_passwords(cls, filepath: str = None) -> None:
        """
        Load common passwords from file

        Args:
            filepath: Path to common passwords file (one per line)
        """
        if filepath and Path(filepath).exists():
            with open(filepath, "r") as f:
                passwords = {line.strip().lower() for line in f if line.strip()}
                cls.COMMON_PASSWORDS.update(passwords)

    @classmethod
    def validate_password_strength(cls, password: str) -> ValidationResult:
        """
        Comprehensive password validation following OWASP guidelines

        Args:
            password: Plain text password to validate

        Returns:
            ValidationResult with is_valid, message, and errors list
        """
        errors = []

        # Check if password is provided
        if not password:
            return ValidationResult(
                is_valid=False,
                message="Password is required",
                errors=["Password cannot be empty"],
            )

        # Check minimum length (OWASP recommends 12)
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")

        # Check bcrypt 72-byte limit
        password_bytes = len(password.encode("utf-8"))
        if password_bytes > cls.MAX_LENGTH:
            errors.append(
                f"Password exceeds {cls.MAX_LENGTH} bytes (bcrypt limitation). Current: {password_bytes} bytes"
            )

        # Check for common passwords
        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append("Password is too common and easily guessable")

        # Complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in cls.SPECIAL_CHARS for c in password)

        complexity_checks = [
            (has_upper, "at least one uppercase letter"),
            (has_lower, "at least one lowercase letter"),
            (has_digit, "at least one digit"),
            (has_special, "at least one special character"),
        ]

        failed_checks = [req for passed, req in complexity_checks if not passed]

        # Allow failing 1 requirement if password is long enough and others pass
        if len(failed_checks) >= 2:
            errors.append(f"Password must contain: {', '.join(failed_checks)}")
        elif len(failed_checks) == 1 and len(password) < 16:
            errors.append(f"Password must contain: {', '.join(failed_checks)}")

        # Check for sequential or repeated characters
        if cls._has_sequential_chars(password):
            errors.append(
                "Password contains too many sequential or repeated characters"
            )

        # Check for dictionary words (basic check)
        if cls._contains_dictionary_word(password):
            errors.append("Password contains common dictionary words")

        # Return result
        if errors:
            return ValidationResult(
                is_valid=False,
                message="Password does not meet security requirements",
                errors=errors,
            )
        else:
            return ValidationResult(
                is_valid=True,
                message="Password meets all security requirements",
                errors=[],
            )

    @staticmethod
    def _has_sequential_chars(password: str, max_sequential: int = 3) -> bool:
        """
        Check for sequential or repeated characters

        Args:
            password: Password to check
            max_sequential: Maximum allowed sequential characters

        Returns:
            True if password has too many sequential characters
        """
        # Check for repeated characters (aaa, 111, etc.)
        for i in range(len(password) - max_sequential + 1):
            if len(set(password[i : i + max_sequential])) == 1:
                return True

        # Check for sequential characters (abc, 123, etc.)
        for i in range(len(password) - max_sequential + 1):
            chars = password[i : i + max_sequential]
            if all(
                ord(chars[j + 1]) == ord(chars[j]) + 1 for j in range(len(chars) - 1)
            ):
                return True
            if all(
                ord(chars[j + 1]) == ord(chars[j]) - 1 for j in range(len(chars) - 1)
            ):
                return True

        return False

    @staticmethod
    def _contains_dictionary_word(password: str, min_word_length: int = 4) -> bool:
        """
        Check if password contains common dictionary words

        Args:
            password: Password to check
            min_word_length: Minimum word length to check

        Returns:
            True if password contains dictionary words
        """
        # Common dictionary words (subset)
        common_words = {
            "love",
            "hate",
            "good",
            "bad",
            "user",
            "admin",
            "test",
            "pass",
            "word",
            "secret",
            "private",
            "public",
            "secure",
            "login",
            "account",
            "system",
            "computer",
            "internet",
            "email",
            "phone",
            "mobile",
            "home",
            "work",
            "office",
        }

        password_lower = password.lower()

        for word in common_words:
            if len(word) >= min_word_length and word in password_lower:
                return True

        return False

    @classmethod
    def get_password_strength_score(cls, password: str) -> int:
        """
        Calculate password strength score (0-100)

        Args:
            password: Password to score

        Returns:
            Score from 0 (very weak) to 100 (very strong)
        """
        score = 0

        # Length score (max 30 points)
        if len(password) >= 16:
            score += 30
        elif len(password) >= 12:
            score += 20
        elif len(password) >= 8:
            score += 10

        # Complexity score (max 40 points)
        if any(c.isupper() for c in password):
            score += 10
        if any(c.islower() for c in password):
            score += 10
        if any(c.isdigit() for c in password):
            score += 10
        if any(c in cls.SPECIAL_CHARS for c in password):
            score += 10

        # Uniqueness score (max 30 points)
        if password.lower() not in cls.COMMON_PASSWORDS:
            score += 10
        if not cls._has_sequential_chars(password):
            score += 10
        if not cls._contains_dictionary_word(password):
            score += 10

        return min(score, 100)

    @classmethod
    def get_password_strength_label(cls, password: str) -> str:
        """
        Get human-readable password strength label

        Args:
            password: Password to evaluate

        Returns:
            Strength label: Very Weak, Weak, Fair, Strong, Very Strong
        """
        score = cls.get_password_strength_score(password)

        if score >= 80:
            return "Very Strong"
        elif score >= 60:
            return "Strong"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Weak"
        else:
            return "Very Weak"


# Convenience function for backward compatibility
def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength (backward compatible interface)

    Args:
        password: Plain text password

    Returns:
        Tuple of (is_valid, message)
    """
    result = PasswordValidator.validate_password_strength(password)
    return result.is_valid, result.message
