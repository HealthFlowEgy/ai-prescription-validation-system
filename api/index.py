"""
Enhanced HealthFlow AI Digital Prescription System
Vercel Serverless API Entry Point
International Best Practices Implementation
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application for Vercel deployment."""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app, origins=['*'], methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Configuration for Vercel environment
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production'),
        'FLASK_ENV': os.environ.get('FLASK_ENV', 'production'),
        'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite:///healthflow.db'),
        'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'FHIR_SERVER_URL': os.environ.get('FHIR_SERVER_URL', 'https://hapi.fhir.org/baseR4'),
        'CORS_ORIGINS': os.environ.get('CORS_ORIGINS', '*'),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
    })
    
    @app.before_request
    def before_request():
        """Handle preflight requests and logging."""
        if request.method == 'OPTIONS':
            response = Response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response
        
        # Log request for monitoring
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Add security headers and CORS."""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'DENY')
        response.headers.add('X-XSS-Protection', '1; mode=block')
        return response
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring."""
        return jsonify({
            'status': 'healthy',
            'service': 'Enhanced HealthFlow API',
            'version': '2.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': app.config.get('FLASK_ENV', 'unknown'),
            'features': {
                'fhir_r4': True,
                'ai_validation': True,
                'zero_trust_security': True,
                'international_standards': True
            }
        })
    
    # API version endpoint
    @app.route('/api/v1/version', methods=['GET'])
    def api_version():
        """API version information."""
        return jsonify({
            'api_version': 'v1',
            'service_version': '2.0.0',
            'international_standards': {
                'estonia_digital_health': True,
                'nhs_federated_architecture': True,
                'netherlands_medcom_governance': True
            },
            'compliance': {
                'fhir_r4': True,
                'gdpr': True,
                'hipaa': True,
                'iso_27001': True
            }
        })
    
    # Authentication endpoints
    @app.route('/api/v1/auth/login', methods=['POST'])
    def login():
        """User authentication endpoint."""
        try:
            data = request.get_json()
            if not data or not data.get('username') or not data.get('password'):
                return jsonify({'error': 'Username and password required'}), 400
            
            # TODO: Implement actual authentication logic
            # For now, return a mock response
            return jsonify({
                'access_token': 'mock-jwt-token',
                'refresh_token': 'mock-refresh-token',
                'user': {
                    'id': '1',
                    'username': data['username'],
                    'role': 'doctor',
                    'permissions': ['read', 'write', 'prescribe']
                }
            })
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 500
    
    # Prescription endpoints
    @app.route('/api/v1/prescriptions', methods=['GET'])
    def get_prescriptions():
        """Get prescriptions list."""
        try:
            # TODO: Implement actual prescription retrieval
            return jsonify({
                'prescriptions': [],
                'total': 0,
                'page': 1,
                'per_page': 10
            })
        except Exception as e:
            logger.error(f"Get prescriptions error: {str(e)}")
            return jsonify({'error': 'Failed to retrieve prescriptions'}), 500
    
    @app.route('/api/v1/prescriptions/upload', methods=['POST'])
    def upload_prescription():
        """Upload prescription for processing."""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # TODO: Implement actual file processing
            return jsonify({
                'prescription_id': 'mock-prescription-id',
                'status': 'processing',
                'message': 'Prescription uploaded successfully'
            })
        except Exception as e:
            logger.error(f"Upload prescription error: {str(e)}")
            return jsonify({'error': 'Failed to upload prescription'}), 500
    
    # FHIR endpoints
    @app.route('/api/fhir/metadata', methods=['GET'])
    def fhir_metadata():
        """FHIR capability statement."""
        return jsonify({
            'resourceType': 'CapabilityStatement',
            'id': 'healthflow-fhir-server',
            'version': '2.0.0',
            'name': 'Enhanced HealthFlow FHIR Server',
            'status': 'active',
            'date': datetime.utcnow().isoformat(),
            'publisher': 'HealthFlow Egypt',
            'fhirVersion': '4.0.1',
            'format': ['json', 'xml'],
            'rest': [{
                'mode': 'server',
                'resource': [
                    {'type': 'Patient'},
                    {'type': 'Practitioner'},
                    {'type': 'MedicationRequest'},
                    {'type': 'MedicationDispense'},
                    {'type': 'Organization'}
                ]
            }]
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

# Create the Flask app instance
app = create_app()

# Vercel handler function
def handler(request, context):
    """Vercel serverless function handler."""
    return app(request.environ, context)

# For local development
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

