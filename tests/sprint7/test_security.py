"""
Tests for Security Middleware
"""
import pytest
from src.middleware.security import InputValidator


class TestInputValidator:
    """Test input validation and sanitization."""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert InputValidator.validate_email('user@example.com') == True
        assert InputValidator.validate_email('test.user+tag@example.co.uk') == True
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        assert InputValidator.validate_email('invalid') == False
        assert InputValidator.validate_email('@example.com') == False
        assert InputValidator.validate_email('user@') == False
        assert InputValidator.validate_email('') == False
        assert InputValidator.validate_email(None) == False
    
    def test_validate_phone_valid(self):
        """Test valid phone number validation."""
        assert InputValidator.validate_phone('5551234567') == True
        assert InputValidator.validate_phone('555-123-4567') == True
        assert InputValidator.validate_phone('(555) 123-4567') == True
        assert InputValidator.validate_phone('+15551234567') == True
    
    def test_validate_phone_invalid(self):
        """Test invalid phone number validation."""
        assert InputValidator.validate_phone('123') == False
        assert InputValidator.validate_phone('abc') == False
        assert InputValidator.validate_phone('') == False
    
    def test_validate_uuid_valid(self):
        """Test valid UUID validation."""
        assert InputValidator.validate_uuid('550e8400-e29b-41d4-a716-446655440000') == True
    
    def test_validate_uuid_invalid(self):
        """Test invalid UUID validation."""
        assert InputValidator.validate_uuid('invalid-uuid') == False
        assert InputValidator.validate_uuid('') == False
        assert InputValidator.validate_uuid(None) == False
    
    def test_sanitize_string_removes_null_bytes(self):
        """Test that null bytes are removed."""
        text = "Hello\x00World"
        result = InputValidator.sanitize_string(text)
        assert '\x00' not in result
        assert result == "HelloWorld"
    
    def test_sanitize_string_removes_control_chars(self):
        """Test that control characters are removed."""
        text = "Hello\x01\x02\x03World"
        result = InputValidator.sanitize_string(text)
        assert result == "HelloWorld"
    
    def test_sanitize_string_preserves_newlines_tabs(self):
        """Test that newlines and tabs are preserved."""
        text = "Hello\nWorld\tTest"
        result = InputValidator.sanitize_string(text)
        assert '\n' in result
        assert '\t' in result
    
    def test_sanitize_string_truncates_length(self):
        """Test that strings are truncated to max length."""
        text = "A" * 2000
        result = InputValidator.sanitize_string(text, max_length=100)
        assert len(result) == 100
    
    def test_check_sql_injection_detects_select(self):
        """Test detection of SQL SELECT injection."""
        assert InputValidator.check_sql_injection("SELECT * FROM users") == True
        assert InputValidator.check_sql_injection("select * from users") == True
    
    def test_check_sql_injection_detects_union(self):
        """Test detection of UNION injection."""
        assert InputValidator.check_sql_injection("' UNION SELECT password FROM users--") == True
    
    def test_check_sql_injection_detects_drop(self):
        """Test detection of DROP injection."""
        assert InputValidator.check_sql_injection("DROP TABLE users") == True
    
    def test_check_sql_injection_detects_comment(self):
        """Test detection of SQL comments."""
        assert InputValidator.check_sql_injection("admin'--") == True
        assert InputValidator.check_sql_injection("admin'/*") == True
    
    def test_check_sql_injection_clean_text(self):
        """Test that clean text is not flagged."""
        assert InputValidator.check_sql_injection("Hello World") == False
        assert InputValidator.check_sql_injection("user@example.com") == False
    
    def test_check_xss_detects_script_tag(self):
        """Test detection of script tags."""
        assert InputValidator.check_xss("<script>alert('xss')</script>") == True
        assert InputValidator.check_xss("<SCRIPT>alert('xss')</SCRIPT>") == True
    
    def test_check_xss_detects_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        assert InputValidator.check_xss("javascript:alert('xss')") == True
    
    def test_check_xss_detects_event_handlers(self):
        """Test detection of event handlers."""
        assert InputValidator.check_xss("<img onerror='alert(1)'>") == True
        assert InputValidator.check_xss("<body onload='alert(1)'>") == True
        assert InputValidator.check_xss("<div onclick='alert(1)'>") == True
    
    def test_check_xss_detects_iframe(self):
        """Test detection of iframe tags."""
        assert InputValidator.check_xss("<iframe src='evil.com'></iframe>") == True
    
    def test_check_xss_clean_text(self):
        """Test that clean text is not flagged."""
        assert InputValidator.check_xss("Hello World") == False
        assert InputValidator.check_xss("<p>Normal HTML</p>") == False
    
    def test_validate_and_sanitize_sql_injection_raises(self):
        """Test that SQL injection raises ValueError."""
        with pytest.raises(ValueError, match="SQL injection"):
            InputValidator.validate_and_sanitize("SELECT * FROM users")
    
    def test_validate_and_sanitize_xss_raises(self):
        """Test that XSS raises ValueError."""
        with pytest.raises(ValueError, match="XSS"):
            InputValidator.validate_and_sanitize("<script>alert('xss')</script>")
    
    def test_validate_and_sanitize_clean_text(self):
        """Test that clean text is sanitized properly."""
        text = "Hello World\x00\x01"
        result = InputValidator.validate_and_sanitize(text)
        assert result == "Hello World"
        assert '\x00' not in result
        assert '\x01' not in result


class TestSecurityHeaders:
    """Test security headers configuration."""
    
    def test_security_headers_present(self):
        """Test that security headers are configured."""
        # This would require a Flask app context
        # Placeholder for actual implementation
        pass


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_enforced(self):
        """Test that rate limits are enforced."""
        # This would require a Flask app context and Redis
        # Placeholder for actual implementation
        pass

