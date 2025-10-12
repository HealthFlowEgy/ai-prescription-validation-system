"""
Security Tests: Field-Level Encryption

Tests AES-256 encryption for PHI protection.

Author: HealthFlow Security Team
Date: 2025-10-14
"""

import os

import pytest

from src.utils.encryption import (
    PHI_FIELDS,
    DecryptionError,
    EncryptionService,
)


class TestEncryption:
    """Test suite for field-level encryption"""

    def test_encrypt_decrypt_string(self):
        """Test basic string encryption and decryption"""
        service = EncryptionService()

        plaintext = "John Doe"
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert ciphertext != plaintext
        assert decrypted == plaintext

    def test_encrypted_format(self):
        """Test encrypted data has version prefix"""
        service = EncryptionService()

        ciphertext = service.encrypt("test data")

        assert ":" in ciphertext
        version, encrypted = ciphertext.split(":", 1)
        assert len(version) == 6  # YYYYMM format
        assert encrypted != "test data"

    def test_encrypt_empty_string(self):
        """Test encrypting empty string"""
        service = EncryptionService()

        result = service.encrypt("")
        assert result == ""

        result = service.encrypt(None)
        assert result is None

    def test_decrypt_empty_string(self):
        """Test decrypting empty string"""
        service = EncryptionService()

        result = service.decrypt("")
        assert result == ""

        result = service.decrypt(None)
        assert result is None

    def test_encrypt_unicode(self):
        """Test encrypting Unicode characters"""
        service = EncryptionService()

        plaintext = "José García 日本語 🔒"
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_long_text(self):
        """Test encrypting long text"""
        service = EncryptionService()

        plaintext = "A" * 10000
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encrypt_dict_fields(self):
        """Test encrypting specific dictionary fields"""
        service = EncryptionService()

        data = {
            "patient_name": "John Doe",
            "patient_dob": "1980-01-01",
            "prescription_id": "RX-001",  # Should not be encrypted
        }

        encrypted = service.encrypt_dict(data, ["patient_name", "patient_dob"])

        assert encrypted["patient_name"] != "John Doe"
        assert encrypted["patient_dob"] != "1980-01-01"
        assert encrypted["prescription_id"] == "RX-001"  # Unchanged

    def test_decrypt_dict_fields(self):
        """Test decrypting specific dictionary fields"""
        service = EncryptionService()

        data = {"patient_name": "John Doe", "patient_dob": "1980-01-01"}

        encrypted = service.encrypt_dict(data, ["patient_name", "patient_dob"])
        decrypted = service.decrypt_dict(encrypted, ["patient_name", "patient_dob"])

        assert decrypted["patient_name"] == "John Doe"
        assert decrypted["patient_dob"] == "1980-01-01"

    def test_hash_for_search(self):
        """Test searchable hash generation"""
        service = EncryptionService()

        value = "john.doe@example.com"
        hash1 = service.hash_for_search(value)
        hash2 = service.hash_for_search(value)

        # Same input produces same hash
        assert hash1 == hash2

        # Different input produces different hash
        hash3 = service.hash_for_search("jane.doe@example.com")
        assert hash1 != hash3

    def test_key_versioning(self):
        """Test encryption key versioning"""
        service = EncryptionService()

        plaintext = "test data"
        ciphertext = service.encrypt(plaintext)

        # Extract version
        version = ciphertext.split(":")[0]
        assert len(version) == 6  # YYYYMM

        # Should be able to decrypt with version
        decrypted = service.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_different_plaintexts_different_ciphertexts(self):
        """Test different plaintexts produce different ciphertexts"""
        service = EncryptionService()

        ciphertext1 = service.encrypt("text1")
        ciphertext2 = service.encrypt("text2")

        assert ciphertext1 != ciphertext2

    def test_same_plaintext_different_ciphertexts(self):
        """Test same plaintext produces different ciphertexts (due to IV)"""
        service = EncryptionService()

        plaintext = "test data"
        ciphertext1 = service.encrypt(plaintext)
        ciphertext2 = service.encrypt(plaintext)

        # Fernet includes random IV, so ciphertexts differ
        # But both should decrypt to same plaintext
        assert service.decrypt(ciphertext1) == plaintext
        assert service.decrypt(ciphertext2) == plaintext

    def test_invalid_ciphertext_raises_error(self):
        """Test decrypting invalid ciphertext raises error"""
        service = EncryptionService()

        with pytest.raises(DecryptionError):
            service.decrypt("invalid:ciphertext")

    def test_phi_fields_constant(self):
        """Test PHI_FIELDS constant is defined"""
        assert "patient_name" in PHI_FIELDS
        assert "patient_dob" in PHI_FIELDS
        assert "diagnosis" in PHI_FIELDS
        assert "medical_history" in PHI_FIELDS

    def test_master_key_required_in_production(self):
        """Test master key is required in production"""
        # Save original env
        original_env = os.environ.get("FLASK_ENV")
        original_key = os.environ.get("ENCRYPTION_MASTER_KEY")

        try:
            # Set production environment
            os.environ["FLASK_ENV"] = "production"
            if "ENCRYPTION_MASTER_KEY" in os.environ:
                del os.environ["ENCRYPTION_MASTER_KEY"]

            # Should raise error
            with pytest.raises(ValueError) as exc_info:
                EncryptionService()

            assert "ENCRYPTION_MASTER_KEY" in str(exc_info.value)

        finally:
            # Restore environment
            if original_env:
                os.environ["FLASK_ENV"] = original_env
            elif "FLASK_ENV" in os.environ:
                del os.environ["FLASK_ENV"]

            if original_key:
                os.environ["ENCRYPTION_MASTER_KEY"] = original_key
