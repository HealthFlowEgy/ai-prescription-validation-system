"""
Shared utility modules to eliminate duplicated code.
Extract common patterns into reusable functions.
"""

from typing import Optional, List
import re
from email_validator import validate_email as _validate_email, EmailNotValidError
from src.config.constants import SecurityConstants, ValidationConstants


class ValidationError(Exception):
    """Base validation error."""
    pass


class EmailValidator:
    """Email validation utilities."""
    
    @staticmethod
    def validate(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If email invalid
        """
        if not email:
            raise ValidationError("Email is required")
        
        if len(email) > ValidationConstants.MAX_EMAIL_LENGTH:
            raise ValidationError(
                f"Email must be at most {ValidationConstants.MAX_EMAIL_LENGTH} characters"
            )
        
        try:
            _validate_email(email)
            return True
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email: {str(e)}")


class PasswordValidator:
    """Password validation utilities."""
    
    @staticmethod
    def validate(password: str) -> bool:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not password:
            raise ValidationError("Password is required")
        
        if len(password) < SecurityConstants.PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"Password must be at least {SecurityConstants.PASSWORD_MIN_LENGTH} characters"
            )
        
        if len(password) > SecurityConstants.PASSWORD_MAX_LENGTH:
            raise ValidationError(
                f"Password must be at most {SecurityConstants.PASSWORD_MAX_LENGTH} characters"
            )
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")
        
        return True


class PhoneValidator:
    """Phone number validation utilities."""
    
    @staticmethod
    def validate(phone: str, country: str = 'US') -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            country: Country code (default: US)
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If phone invalid
        """
        if not phone:
            raise ValidationError("Phone number is required")
        
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', phone)
        
        if country == 'US':
            if len(digits) != 10:
                raise ValidationError("US phone number must be 10 digits")
        else:
            if len(digits) < 7 or len(digits) > 15:
                raise ValidationError("Phone number must be 7-15 digits")
        
        return True


class AgeValidator:
    """Age validation utilities."""
    
    @staticmethod
    def validate(age: int) -> bool:
        """
        Validate age is within reasonable bounds.
        
        Args:
            age: Age in years
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If age invalid
        """
        if age < ValidationConstants.MIN_AGE:
            raise ValidationError(f"Age cannot be less than {ValidationConstants.MIN_AGE}")
        
        if age > ValidationConstants.MAX_AGE:
            raise ValidationError(f"Age cannot be greater than {ValidationConstants.MAX_AGE}")
        
        return True

