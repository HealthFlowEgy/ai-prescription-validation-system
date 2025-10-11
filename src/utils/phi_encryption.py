"""
PHI (Protected Health Information) Field-Level Encryption Service
Implements HIPAA-compliant encryption for sensitive patient data
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from sqlalchemy import TypeDecorator, String
import base64
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Handles encryption/decryption of PHI fields
    Uses Fernet (symmetric encryption) with key derivation
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master encryption key (from env or key management service)
        """
        # Get master key from environment or generate
        self.master_key = master_key or os.environ.get(
            'PHI_ENCRYPTION_KEY',
            self._generate_key()
        )
        
        # Create cipher
        self.cipher = Fernet(self.master_key.encode() if isinstance(self.master_key, str) else self.master_key)
        
        logger.info("Encryption service initialized")
    
    @staticmethod
    def _generate_key() -> str:
        """Generate a new encryption key"""
        key = Fernet.generate_key()
        logger.warning(
            "Generated new encryption key. Store securely: "
            "export PHI_ENCRYPTION_KEY='%s'", 
            key.decode()
        )
        return key.decode()
    
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Password/passphrase
            salt: Random salt
        
        Returns:
            Derived key
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return plaintext
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Encrypted string
        
        Returns:
            Decrypted plaintext
        """
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def rotate_key(self, new_key: str):
        """
        Rotate encryption key (requires re-encrypting all data)
        
        Args:
            new_key: New master key
        """
        old_cipher = self.cipher
        self.master_key = new_key
        self.cipher = Fernet(new_key.encode())
        
        logger.warning("Encryption key rotated - re-encrypt all PHI data")
        
        return old_cipher


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted string fields
    Automatically encrypts on write, decrypts on read
    """
    
    impl = String
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        """Initialize encrypted string type"""
        self.encryption_service = EncryptionService()
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database"""
        if value is not None:
            return self.encryption_service.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database"""
        if value is not None:
            return self.encryption_service.decrypt(value)
        return value


class PHIAnonymizer:
    """
    Anonymizes PHI in logs and error messages
    Ensures no PHI leaks into logs, metrics, or monitoring
    """
    
    # PHI patterns to redact
    PHI_PATTERNS = {
        'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]'),
        'phone': (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE-REDACTED]'),
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-REDACTED]'),
        'mrn': (r'\bMRN[:\s]*\d{6,}\b', '[MRN-REDACTED]'),
        'dob': (r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '[DOB-REDACTED]'),
        'zip': (r'\b\d{5}(-\d{4})?\b', '[ZIP-REDACTED]')
    }
    
    @classmethod
    def anonymize(cls, text: str) -> str:
        """
        Remove PHI from text
        
        Args:
            text: Text potentially containing PHI
        
        Returns:
            Anonymized text
        """
        import re
        
        if not text:
            return text
        
        anonymized = text
        
        for pattern_name, (pattern, replacement) in cls.PHI_PATTERNS.items():
            anonymized = re.sub(pattern, replacement, anonymized, flags=re.IGNORECASE)
        
        return anonymized
    
    @classmethod
    def anonymize_dict(cls, data: dict) -> dict:
        """
        Recursively anonymize dictionary values
        
        Args:
            data: Dictionary potentially containing PHI
        
        Returns:
            Anonymized dictionary
        """
        anonymized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                anonymized[key] = cls.anonymize(value)
            elif isinstance(value, dict):
                anonymized[key] = cls.anonymize_dict(value)
            elif isinstance(value, list):
                anonymized[key] = [
                    cls.anonymize_dict(item) if isinstance(item, dict)
                    else cls.anonymize(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                anonymized[key] = value
        
        return anonymized


class AuditLogger:
    """
    HIPAA-compliant audit logging for PHI access
    Logs all access to PHI with detailed context
    """
    
    def __init__(self):
        """Initialize audit logger"""
        self.logger = logging.getLogger('phi_audit')
        self.logger.setLevel(logging.INFO)
        
        # Create separate audit log handler
        handler = logging.FileHandler('phi_audit.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_access(
        self,
        user_id: str,
        action: