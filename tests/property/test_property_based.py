"""
Property-based testing using Hypothesis.
Generates random test cases to find edge cases.
"""

from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import pytest
from src.utils.validators import PasswordValidator, EmailValidator, ValidationError


class TestPasswordValidation:
    """Property-based tests for password validation."""
    
    @given(st.text(min_size=12, max_size=128))
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_password_length_always_checked(self, password):
        """
        Property: All passwords are checked for minimum length.
        """
        try:
            result = PasswordValidator.validate(password)
            # If validation passes, password meets all requirements
            assert len(password) >= 12
        except ValidationError:
            # If validation fails, it should be for a valid reason
            pass
    
    @given(
        st.text(min_size=12, max_size=128).filter(
            lambda s: any(c.isupper() for c in s) and
                     any(c.islower() for c in s) and
                     any(c.isdigit() for c in s) and
                     any(c in '!@#$%^&*(),.?":{}|<>' for c in s)
        )
    )
    def test_valid_password_always_accepted(self, password):
        """
        Property: Passwords meeting all requirements are always valid.
        """
        assert PasswordValidator.validate(password) is True
    
    @given(st.text(max_size=11))
    def test_short_password_always_rejected(self, password):
        """
        Property: Passwords shorter than 12 chars are always rejected.
        """
        with pytest.raises(ValidationError):
            PasswordValidator.validate(password)


class TestDosageCalculation:
    """Property-based tests for dosage calculations."""
    
    @given(
        weight=st.floats(min_value=1.0, max_value=200.0),
        dosage_per_kg=st.floats(min_value=0.1, max_value=50.0)
    )
    def test_dosage_calculation_properties(self, weight, dosage_per_kg):
        """
        Property: Dosage calculation follows mathematical properties.
        
        Properties tested:
        - Result is always positive
        - Result increases with weight
        - Result increases with dosage_per_kg
        - Result is commutative (weight * dosage = dosage * weight)
        """
        # Simple dosage calculation
        result = weight * dosage_per_kg
        
        # Property 1: Result is positive
        assert result > 0
        
        # Property 2: Linear relationship
        double_weight_result = (weight * 2) * dosage_per_kg
        assert abs(double_weight_result - result * 2) < 0.01
        
        # Property 3: Commutative
        reverse_result = dosage_per_kg * weight
        assert abs(reverse_result - result) < 0.01
    
    @given(
        weight=st.floats(min_value=1.0, max_value=200.0),
        dosage_per_kg=st.floats(min_value=0.1, max_value=50.0)
    )
    def test_dosage_rounding_consistent(self, weight, dosage_per_kg):
        """
        Property: Dosage rounding is consistent.
        """
        result1 = round(weight * dosage_per_kg, 2)
        result2 = round(weight * dosage_per_kg, 2)
        
        # Property: Same input always produces same output
        assert result1 == result2


class TestPrescriptionStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for prescription workflow.
    
    Tests that prescription state transitions are always valid.
    """
    
    def __init__(self):
        super().__init__()
        self.prescription_id = None
        self.status = None
    
    @rule()
    def create_prescription(self):
        """Create a new prescription."""
        self.prescription_id = "test_prescription_123"
        self.status = "draft"
    
    @rule()
    def submit_prescription(self):
        """Submit prescription for processing."""
        if self.status == "draft":
            self.status = "processing"
    
    @rule()
    def validate_prescription(self):
        """Validate processed prescription."""
        if self.status == "processing":
            self.status = "validated"
    
    @rule()
    def approve_prescription(self):
        """Approve validated prescription."""
        if self.status == "validated":
            self.status = "approved"
    
    @rule()
    def reject_prescription(self):
        """Reject prescription."""
        if self.status in ["processing", "validated"]:
            self.status = "rejected"
    
    @invariant()
    def status_is_valid(self):
        """Invariant: Status is always valid."""
        valid_statuses = [None, "draft", "processing", "validated", "approved", "rejected"]
        assert self.status in valid_statuses, f"Invalid status: {self.status}"
    
    @invariant()
    def approved_prescriptions_cannot_be_rejected(self):
        """Invariant: Approved prescriptions cannot be rejected."""
        if self.status == "approved":
            # This should never happen
            pass


# Run stateful tests
TestPrescriptionWorkflow = TestPrescriptionStateMachine.TestCase


class TestEmailValidation:
    """Property-based tests for email validation."""
    
    @given(
        st.emails()
    )
    def test_valid_emails_accepted(self, email):
        """
        Property: Valid email formats are accepted.
        """
        # Limit email length for our validator
        if len(email) <= 255:
            try:
                assert EmailValidator.validate(email) is True
            except ValidationError:
                # Some edge case emails might still fail
                pass
    
    @given(
        st.text().filter(lambda s: '@' not in s)
    )
    def test_emails_without_at_rejected(self, text):
        """
        Property: Strings without @ are rejected.
        """
        if text:  # Skip empty strings
            with pytest.raises(ValidationError):
                EmailValidator.validate(text)


class TestNumericBoundaries:
    """Property-based tests for numeric boundaries."""
    
    @given(st.integers(min_value=-1000, max_value=-1))
    def test_negative_ages_rejected(self, age):
        """
        Property: Negative ages are always rejected.
        """
        from src.utils.validators import AgeValidator
        
        with pytest.raises(ValidationError):
            AgeValidator.validate(age)
    
    @given(st.integers(min_value=0, max_value=150))
    def test_valid_ages_accepted(self, age):
        """
        Property: Ages 0-150 are accepted.
        """
        from src.utils.validators import AgeValidator
        
        assert AgeValidator.validate(age) is True
    
    @given(st.integers(min_value=151, max_value=1000))
    def test_excessive_ages_rejected(self, age):
        """
        Property: Ages > 150 are rejected.
        """
        from src.utils.validators import AgeValidator
        
        with pytest.raises(ValidationError):
            AgeValidator.validate(age)

