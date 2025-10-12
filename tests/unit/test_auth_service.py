"""
Unit tests for AuthService
Tests password hashing, JWT tokens, and authentication logic
"""

import pytest
import os
import time
from datetime import datetime, timedelta
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from services.auth_service import AuthService


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test that password hashing works"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plaintext
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        result = AuthService.verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        result = AuthService.verify_password("WrongPassword", hashed)
        assert result is False

    def test_hash_different_passwords_different_hashes(self):
        """Test that same password produces different hashes (due to salt)"""
        password = "TestPassword123!"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        assert hash1 != hash2  # Different salts
        assert AuthService.verify_password(password, hash1)
        assert AuthService.verify_password(password, hash2)

    def test_empty_password(self):
        """Test handling of empty password"""
        with pytest.raises(Exception):
            AuthService.hash_password("")

    def test_long_password(self):
        """Test handling of very long password"""
        password = "A" * 1000
        hashed = AuthService.hash_password(password)
        assert AuthService.verify_password(password, hashed)


class TestJWTTokens:
    """Test JWT token generation and validation"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"

    def test_generate_access_token(self):
        """Test access token generation"""
        user_id = 1
        role = "admin"

        token, expiration = AuthService.generate_token(user_id, role)

        assert token is not None
        assert len(token) > 0
        assert isinstance(expiration, datetime)

    def test_generate_refresh_token(self):
        """Test refresh token generation"""
        user_id = 1
        role = "pharmacist"

        token, expiration = AuthService.generate_refresh_token(user_id, role)

        assert token is not None
        assert len(token) > 0
        assert isinstance(expiration, datetime)

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        user_id = 42
        role = "doctor"

        token, _ = AuthService.generate_token(user_id, role)
        payload = AuthService.decode_token(token)

        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["role"] == role
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_expired_token(self):
        """Test decoding an expired token"""
        user_id = 1
        role = "admin"

        # Generate token with 1 second expiration
        token, _ = AuthService.generate_token(user_id, role, expires_in=1)

        # Wait for token to expire
        time.sleep(2)

        payload = AuthService.decode_token(token)
        assert payload is None  # Expired tokens should return None

    def test_decode_invalid_token(self):
        """Test decoding an invalid token"""
        invalid_token = "invalid.token.here"

        payload = AuthService.decode_token(invalid_token)
        assert payload is None

    def test_decode_tampered_token(self):
        """Test decoding a tampered token"""
        user_id = 1
        role = "admin"

        token, _ = AuthService.generate_token(user_id, role)

        # Tamper with the token
        tampered_token = token[:-5] + "XXXXX"

        payload = AuthService.decode_token(tampered_token)
        assert payload is None

    def test_token_expiration_times(self):
        """Test that token expiration times are correct"""
        user_id = 1
        role = "admin"

        # Access token (default 1 hour)
        access_token, access_exp = AuthService.generate_token(user_id, role)
        assert access_exp > datetime.utcnow()
        assert access_exp < datetime.utcnow() + timedelta(hours=2)

        # Refresh token (default 30 days)
        refresh_token, refresh_exp = AuthService.generate_refresh_token(user_id, role)
        assert refresh_exp > datetime.utcnow()
        assert refresh_exp < datetime.utcnow() + timedelta(days=31)

    def test_custom_expiration(self):
        """Test token generation with custom expiration"""
        user_id = 1
        role = "admin"
        custom_expiration = 300  # 5 minutes

        token, expiration = AuthService.generate_token(
            user_id, role, expires_in=custom_expiration
        )

        expected_exp = datetime.utcnow() + timedelta(seconds=custom_expiration)
        assert abs((expiration - expected_exp).total_seconds()) < 2  # Within 2 seconds


class TestPasswordValidation:
    """Test password strength validation"""

    def test_validate_strong_password(self):
        """Test validation of strong password"""
        strong_passwords = ["StrongPass123!", "MyP@ssw0rd", "Secure#2024", "Test!ng123"]

        for password in strong_passwords:
            is_valid, message = AuthService.validate_password_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid"

    def test_validate_weak_password_too_short(self):
        """Test validation of too short password"""
        weak_password = "Short1!"

        is_valid, message = AuthService.validate_password_strength(weak_password)
        assert is_valid is False
        assert "at least 8 characters" in message.lower()

    def test_validate_weak_password_no_uppercase(self):
        """Test validation of password without uppercase"""
        weak_password = "lowercase123!"

        is_valid, message = AuthService.validate_password_strength(weak_password)
        assert is_valid is False
        assert "uppercase" in message.lower()

    def test_validate_weak_password_no_lowercase(self):
        """Test validation of password without lowercase"""
        weak_password = "UPPERCASE123!"

        is_valid, message = AuthService.validate_password_strength(weak_password)
        assert is_valid is False
        assert "lowercase" in message.lower()

    def test_validate_weak_password_no_digit(self):
        """Test validation of password without digit"""
        weak_password = "NoDigits!"

        is_valid, message = AuthService.validate_password_strength(weak_password)
        assert is_valid is False
        assert "digit" in message.lower()

    def test_validate_weak_password_no_special(self):
        """Test validation of password without special character"""
        weak_password = "NoSpecial123"

        is_valid, message = AuthService.validate_password_strength(weak_password)
        assert is_valid is False
        assert "special character" in message.lower()


class TestAuthServiceIntegration:
    """Integration tests for AuthService"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"

    def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        # 1. Hash password
        password = "UserPassword123!"
        hashed = AuthService.hash_password(password)

        # 2. Verify password
        assert AuthService.verify_password(password, hashed)

        # 3. Generate token
        user_id = 1
        role = "pharmacist"
        token, expiration = AuthService.generate_token(user_id, role)

        # 4. Decode token
        payload = AuthService.decode_token(token)
        assert payload["user_id"] == user_id
        assert payload["role"] == role

        # 5. Verify password again
        assert AuthService.verify_password(password, hashed)
        assert not AuthService.verify_password("WrongPassword", hashed)

    def test_token_refresh_flow(self):
        """Test token refresh flow"""
        user_id = 1
        role = "admin"

        # Generate refresh token
        refresh_token, _ = AuthService.generate_refresh_token(user_id, role)

        # Decode refresh token
        payload = AuthService.decode_token(refresh_token)
        assert payload is not None
        assert payload["type"] == "refresh"

        # Generate new access token from refresh token
        new_access_token, _ = AuthService.generate_token(
            payload["user_id"], payload["role"]
        )

        # Verify new access token
        new_payload = AuthService.decode_token(new_access_token)
        assert new_payload["user_id"] == user_id
        assert new_payload["role"] == role
        assert new_payload["type"] == "access"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
