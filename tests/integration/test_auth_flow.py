"""
Integration tests for authentication flow
Tests complete registration, login, and token refresh workflows
"""

import pytest
import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from main import create_app
from models.user import db, User


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


class TestUserRegistration:
    """Test user registration flow"""
    
    def test_register_new_user(self, client):
        """Test successful user registration"""
        response = client.post('/api/auth/register', 
            json={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'test@example.com'
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        # Register first user
        client.post('/api/auth/register',
            json={
                'name': 'First User',
                'email': 'duplicate@example.com',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            }
        )
        
        # Try to register with same email
        response = client.post('/api/auth/register',
            json={
                'name': 'Second User',
                'email': 'duplicate@example.com',
                'password': 'DifferentPass123!',
                'role': 'doctor'
            }
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/auth/register',
            json={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'weak',  # Too short, no uppercase, no special char
                'role': 'pharmacist'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/api/auth/register',
            json={
                'email': 'test@example.com'
                # Missing name, password, role
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email format"""
        response = client.post('/api/auth/register',
            json={
                'name': 'Test User',
                'email': 'invalid-email',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'


class TestUserLogin:
    """Test user login flow"""
    
    @pytest.fixture(autouse=True)
    def setup_user(self, client):
        """Create a test user before each test"""
        client.post('/api/auth/register',
            json={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            }
        )
    
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'TestPass123!'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'user' in data['data']
        assert data['data']['user']['email'] == 'test@example.com'
    
    def test_login_wrong_password(self, client):
        """Test login with incorrect password"""
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'WrongPassword123!'
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email"""
        response = client.post('/api/auth/login',
            json={
                'email': 'nonexistent@example.com',
                'password': 'TestPass123!'
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com'
                # Missing password
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'


class TestTokenRefresh:
    """Test token refresh flow"""
    
    @pytest.fixture
    def tokens(self, client):
        """Register and login to get tokens"""
        # Register
        client.post('/api/auth/register',
            json={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            }
        )
        
        # Login
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'TestPass123!'
            }
        )
        
        data = json.loads(response.data)
        return data['data']
    
    def test_refresh_token_success(self, client, tokens):
        """Test successful token refresh"""
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': tokens['refresh_token']
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert data['data']['access_token'] != tokens['access_token']  # New token
    
    def test_refresh_with_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': 'invalid.token.here'
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_refresh_with_access_token(self, client, tokens):
        """Test refresh with access token (should fail)"""
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': tokens['access_token']  # Using access token instead
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'


class TestProtectedEndpoints:
    """Test protected endpoints with authentication"""
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        # Register and login
        client.post('/api/auth/register',
            json={
                'name': 'Test User',
                'email': 'test@example.com',
                'password': 'TestPass123!',
                'role': 'pharmacist'
            }
        )
        
        response = client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'TestPass123!'
            }
        )
        
        data = json.loads(response.data)
        token = data['data']['access_token']
        
        return {'Authorization': f'Bearer {token}'}
    
    def test_access_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token"""
        response = client.get('/api/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'user' in data['data']
    
    def test_access_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    def test_access_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {'Authorization': 'Bearer invalid.token.here'}
        response = client.get('/api/auth/me', headers=headers)
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['status'] == 'error'


class TestCompleteAuthWorkflow:
    """Test complete authentication workflow"""
    
    def test_full_auth_cycle(self, client):
        """Test complete registration -> login -> access -> refresh -> logout cycle"""
        
        # 1. Register
        register_response = client.post('/api/auth/register',
            json={
                'name': 'Complete Test User',
                'email': 'complete@example.com',
                'password': 'CompleteTest123!',
                'role': 'doctor'
            }
        )
        assert register_response.status_code == 201
        
        # 2. Login
        login_response = client.post('/api/auth/login',
            json={
                'email': 'complete@example.com',
                'password': 'CompleteTest123!'
            }
        )
        assert login_response.status_code == 200
        login_data = json.loads(login_response.data)
        access_token = login_data['data']['access_token']
        refresh_token = login_data['data']['refresh_token']
        
        # 3. Access protected endpoint
        headers = {'Authorization': f'Bearer {access_token}'}
        me_response = client.get('/api/auth/me', headers=headers)
        assert me_response.status_code == 200
        me_data = json.loads(me_response.data)
        assert me_data['data']['user']['email'] == 'complete@example.com'
        
        # 4. Refresh token
        refresh_response = client.post('/api/auth/refresh',
            json={'refresh_token': refresh_token}
        )
        assert refresh_response.status_code == 200
        refresh_data = json.loads(refresh_response.data)
        new_access_token = refresh_data['data']['access_token']
        
        # 5. Access with new token
        new_headers = {'Authorization': f'Bearer {new_access_token}'}
        new_me_response = client.get('/api/auth/me', headers=new_headers)
        assert new_me_response.status_code == 200
        
        # 6. Logout
        logout_response = client.post('/api/auth/logout', headers=new_headers)
        assert logout_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
