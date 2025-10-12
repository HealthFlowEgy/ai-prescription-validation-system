"""
Unit tests for AuthService
"""

import pytest
import os
from services.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed != password  # Should be different from original

    def test_hash_password_different_each_time(self):
        """Test that hashing same password produces different hashes"""
        password = "TestPassword123!"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash"""
        assert AuthService.verify_password("password", "invalid_hash") is False

    def test_validate_password_strength_weak(self):
        """Test password strength validation with weak password"""
        is_valid, message = AuthService.validate_password_strength("weak")

        assert is_valid is False
        assert len(message) > 0

    def test_validate_password_strength_no_uppercase(self):
        """Test password validation without uppercase"""
        is_valid, message = AuthService.validate_password_strength("password123!")

        assert is_valid is False

    def test_validate_password_strength_no_lowercase(self):
        """Test password validation without lowercase"""
        is_valid, message = AuthService.validate_password_strength("PASSWORD123!")

        assert is_valid is False

    def test_validate_password_strength_no_digit(self):
        """Test password validation without digit"""
        is_valid, message = AuthService.validate_password_strength("Password!")

        assert is_valid is False

    def test_validate_password_strength_no_special(self):
        """Test password validation without special character"""
        is_valid, message = AuthService.validate_password_strength("Password123")

        assert is_valid is False

    def test_validate_password_strength_too_short(self):
        """Test password validation with too short password"""
        is_valid, message = AuthService.validate_password_strength("Pass1!")

        assert is_valid is False

    def test_get_secret_key_from_env(self, monkeypatch):
        """Test getting secret key from environment"""
        test_secret = "test-secret-key-12345"
        monkeypatch.setenv("JWT_SECRET_KEY", test_secret)

        secret = AuthService.get_secret_key()
        assert secret == test_secret

    def test_get_secret_key_missing(self, monkeypatch):
        """Test error when secret key is missing"""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            AuthService.get_secret_key()
