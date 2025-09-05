"""
Enhanced HealthFlow AI Digital Prescription System
Vercel Serverless API Entry Point - Simplified
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Basic configuration
app.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key'),
    'FLASK_ENV': os.environ.get('FLASK_ENV', 'production'),
})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced HealthFlow API',
        'version': '2.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': app.config.get('FLASK_ENV', 'unknown')
    })

@app.route('/api/v1/version', methods=['GET'])
def api_version():
    """API version information."""
    return jsonify({
        'api_version': 'v1',
        'service_version': '2.0.0',
        'status': 'active'
    })

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """User authentication endpoint."""
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Mock authentication for demo
        return jsonify({
            'access_token': 'demo-jwt-token',
            'user': {
                'id': '1',
                'username': username,
                'role': 'doctor'
            }
        })
    except Exception as e:
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/v1/prescriptions', methods=['GET'])
def get_prescriptions():
    """Get prescriptions list."""
    return jsonify({
        'prescriptions': [],
        'total': 0,
        'page': 1,
        'per_page': 10
    })

@app.route('/api/v1/prescriptions/upload', methods=['POST'])
def upload_prescription():
    """Upload prescription for processing."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        return jsonify({
            'prescription_id': 'demo-prescription-id',
            'status': 'processing',
            'message': 'Prescription uploaded successfully'
        })
    except Exception as e:
        return jsonify({'error': 'Failed to upload prescription'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Vercel handler
def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)

