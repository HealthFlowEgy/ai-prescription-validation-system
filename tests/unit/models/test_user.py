"""
Unit tests for User model
"""

import pytest
from datetime import datetime
from models.user import User


class TestUserModel:
    """Test cases for User model"""

    def test_user_creation(self, session):
        """Test creating a user"""
        user = User(
            username="testuser",
            email="test@example.com",
            name="Test User",
            role="pharmacist",
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "pharmacist"
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_password_hashing(self, session):
        """Test password hashing"""
        user = User(username="testuser", email="test@example.com")
        user.set_password("TestPassword123!")
        session.add(user)
        session.commit()

        assert user.password_hash is not None
        assert user.password_hash != "TestPassword123!"
        assert len(user.password_hash) > 50  # Bcrypt hashes are long

    def test_user_password_verification(self, session):
        """Test password verification"""
        user = User(username="testuser", email="test@example.com")
        user.set_password("TestPassword123!")
        session.add(user)
        session.commit()

        assert user.check_password("TestPassword123!") is True
        assert user.check_password("WrongPassword") is False
        assert user.check_password("") is False

    def test_user_password_verification_without_hash(self, session):
        """Test password verification when no password is set"""
        user = User(username="testuser", email="test@example.com")
        session.add(user)
        session.commit()

        assert user.check_password("AnyPassword") is False

    def test_user_unique_username(self, session):
        """Test that usernames must be unique"""
        user1 = User(username="testuser", email="test1@example.com")
        session.add(user1)
        session.commit()

        user2 = User(username="testuser", email="test2@example.com")
        session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_user_unique_email(self, session):
        """Test that emails must be unique"""
        user1 = User(username="testuser1", email="test@example.com")
        session.add(user1)
        session.commit()

        user2 = User(username="testuser2", email="test@example.com")
        session.add(user2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_user_to_dict(self, test_user):
        """Test user to_dict method"""
        user_dict = test_user.to_dict()

        assert "id" in user_dict
        assert "username" in user_dict
        assert "email" in user_dict
        assert "role" in user_dict
        assert "is_active" in user_dict
        assert "password_hash" not in user_dict  # Should not expose password

    def test_user_to_dict_with_sensitive(self, test_user):
        """Test user to_dict with sensitive data"""
        user_dict = test_user.to_dict(include_sensitive=True)

        assert "updated_at" in user_dict
        assert "created_by" in user_dict
        assert "updated_by" in user_dict

    def test_user_has_role(self, test_user):
        """Test has_role method"""
        assert test_user.has_role("pharmacist") is True
        assert test_user.has_role("doctor") is False
        assert test_user.has_role("pharmacist", "doctor") is True
        assert test_user.has_role("admin", "doctor") is False

    def test_user_is_admin(self, test_user, admin_user):
        """Test is_admin method"""
        assert test_user.is_admin() is False
        assert admin_user.is_admin() is True

    def test_user_update_last_login(self, test_user, session):
        """Test updating last login timestamp"""
        assert test_user.last_login is None

        test_user.update_last_login()

        assert test_user.last_login is not None
        assert isinstance(test_user.last_login, datetime)

    def test_user_repr(self, test_user):
        """Test user __repr__ method"""
        repr_str = repr(test_user)
        assert "testuser" in repr_str
        assert "pharmacist" in repr_str

    def test_user_default_values(self, session):
        """Test default values for user fields"""
        user = User(username="testuser", email="test@example.com")
        session.add(user)
        session.commit()

        assert user.is_active is True
        assert user.is_verified is False
        assert user.role == "pharmacist"  # Default role
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_timestamps(self, session):
        """Test that timestamps are set correctly"""
        user = User(username="testuser", email="test@example.com")
        session.add(user)
        session.commit()

        created_at = user.created_at
        updated_at = user.updated_at

        assert created_at is not None
        assert updated_at is not None
        assert isinstance(created_at, datetime)
        assert isinstance(updated_at, datetime)

        # Update user
        user.name = "Updated Name"
        session.commit()

        assert user.updated_at > updated_at  # Should be updated

    def test_user_roles(self, session):
        """Test different user roles"""
        roles = ["pharmacist", "doctor", "admin", "auditor"]

        for role in roles:
            user = User(username=f"{role}_user", email=f"{role}@example.com", role=role)
            session.add(user)
            session.commit()

            assert user.role == role
            session.delete(user)
            session.commit()

    def test_user_inactive(self, session):
        """Test inactive user"""
        user = User(username="inactive", email="inactive@example.com", is_active=False)
        session.add(user)
        session.commit()

        assert user.is_active is False

    def test_user_unverified(self, session):
        """Test unverified user"""
        user = User(
            username="unverified", email="unverified@example.com", is_verified=False
        )
        session.add(user)
        session.commit()

        assert user.is_verified is False
