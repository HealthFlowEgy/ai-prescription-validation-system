# AI-Based Digital Prescription Validation System

A comprehensive web application that leverages artificial intelligence, optical character recognition (OCR), and natural language processing (NLP) to validate digital prescriptions. This system integrates multiple GitHub projects to provide advanced prescription processing, drug interaction checking, and validation capabilities.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Overview

The AI-Based Digital Prescription Validation System addresses the critical need for automated prescription validation in healthcare settings. By combining advanced OCR technology, natural language processing, and comprehensive validation rules, this system helps healthcare professionals ensure prescription accuracy, detect potential drug interactions, and maintain compliance with medical standards.

### Key Components

The system integrates three primary GitHub projects:

1. **Pharmacy_AI** - Provides OCR and medication NER capabilities
2. **medical-data-extraction** - Offers advanced medical document processing
3. **Snowstorm** - Supplies SNOMED CT terminology services

## Features

### Core Functionality

- **Multi-format Input Support**: Processes handwritten prescriptions, voice audio, and digital data
- **Advanced OCR Processing**: Extracts text from prescription images with high accuracy
- **Natural Language Processing**: Identifies medications, dosages, frequencies, and instructions
- **Drug Interaction Checking**: Detects potential interactions between prescribed medications
- **Dosage Validation**: Verifies medication dosages against standard therapeutic ranges
- **Completeness Validation**: Ensures all required prescription fields are present
- **Audit Trail**: Maintains comprehensive logs of all system activities
- **Real-time Processing**: Provides immediate feedback on prescription validation

### Technical Features

- **RESTful API**: Comprehensive API for integration with external systems
- **Database Management**: SQLite database with SQLAlchemy ORM
- **Backup and Recovery**: Automated database backup and restoration utilities
- **Responsive Web Interface**: Modern, mobile-friendly user interface
- **Security**: Input validation, error handling, and secure file processing
- **Scalability**: Modular architecture supporting horizontal scaling

## Architecture

### System Architecture

The system follows a modular, service-oriented architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer     │    │   Services      │
│   (HTML/CSS/JS) │◄──►│   (Flask)       │◄──►│   (OCR/NLP)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   (SQLite)      │
                       └─────────────────┘
```

### Component Details

#### Frontend Layer
- Modern HTML5 interface with CSS3 styling
- JavaScript for dynamic interactions
- Responsive design for desktop and mobile devices
- File upload with drag-and-drop support

#### API Layer
- Flask-based RESTful API
- CORS support for cross-origin requests
- Comprehensive error handling
- Request validation and sanitization

#### Service Layer
- **OCR Service**: Image preprocessing and text extraction
- **NLP Service**: Entity recognition and data extraction
- **Validation Service**: Drug interaction and completeness checking
- **Database Service**: Data persistence and retrieval

#### Database Layer
- SQLite database for development and testing
- SQLAlchemy ORM for database operations
- Automated migrations and schema management
- Backup and recovery utilities

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Tesseract OCR engine
- Git

### System Dependencies

Install Tesseract OCR:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Application Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd prescription_validation_system
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**
   ```bash
   python src/database/init_db.py init
   ```

5. **Start the Application**
   ```bash
   python src/main.py
   ```

The application will be available at `http://localhost:5000`.

## Usage

### Web Interface

1. **Access the Application**
   - Open your web browser and navigate to `http://localhost:5000`
   - You'll see the main prescription upload interface

2. **Upload a Prescription**
   - Click "Choose File" or drag and drop a prescription image
   - Select the input format (Handwritten Image, Voice Audio, or Digital Data)
   - Click "Upload Prescription"

3. **Process the Prescription**
   - After upload, the system will automatically process the prescription
   - OCR will extract text from the image
   - NLP will identify medications and dosages
   - The system will return processing results

4. **Validate the Prescription**
   - Use the validation endpoint to check for drug interactions
   - Review completeness and dosage validation results
   - Access detailed validation reports

### API Usage

#### Upload Prescription

```bash
curl -X POST \
  -F "file=@prescription.png" \
  -F "input_format=handwritten_image" \
  -F "user_id=1" \
  http://localhost:5000/api/prescriptions/upload
```

#### Process Prescription

```bash
curl -X POST \
  -F "user_id=1" \
  http://localhost:5000/api/prescriptions/{prescription_id}/process
```

#### Validate Prescription

```bash
curl -X POST \
  -F "user_id=1" \
  http://localhost:5000/api/prescriptions/{prescription_id}/validate
```

## API Documentation

### Authentication

Currently, the system uses simple user ID-based authentication. In production, implement proper JWT or OAuth2 authentication.

### Endpoints

#### Health Check
- **GET** `/api/health`
- Returns system health status

#### Prescription Management
- **POST** `/api/prescriptions/upload` - Upload prescription file
- **GET** `/api/prescriptions` - List prescriptions
- **GET** `/api/prescriptions/{id}` - Get prescription details
- **POST** `/api/prescriptions/{id}/process` - Process prescription
- **POST** `/api/prescriptions/{id}/validate` - Validate prescription
- **GET** `/api/prescriptions/{id}/validation-summary` - Get validation summary

#### User Management
- **GET** `/api/users` - List users
- **POST** `/api/users` - Create user
- **GET** `/api/users/{id}` - Get user details

### Response Formats

All API responses follow a consistent JSON format:

```json
{
  "status": "success|error",
  "message": "Human-readable message",
  "data": {},
  "timestamp": "2025-07-15T10:30:00Z"
}
```

## Testing

### Running Tests

Execute the test suite:

```bash
python tests/test_api.py
```

### Test Coverage

The test suite covers:
- API endpoint functionality
- OCR service operations
- NLP service processing
- Validation service logic
- Database operations
- Error handling

### Manual Testing

1. **Upload Test**: Use the provided sample prescription image
2. **Processing Test**: Verify OCR and NLP extraction
3. **Validation Test**: Check drug interaction detection
4. **Error Handling**: Test with invalid inputs

## Deployment

### Local Deployment

For local development and testing, follow the installation instructions above.

### Production Deployment

#### Using Flask Development Server

```bash
export FLASK_ENV=production
python src/main.py
```

#### Using Gunicorn (Recommended)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
```

#### Environment Variables

Set the following environment variables for production:

```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key
export DATABASE_URL=sqlite:///production.db
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y tesseract-ocr

COPY . .

EXPOSE 5000

CMD ["python", "src/main.py"]
```

Build and run:

```bash
docker build -t prescription-validator .
docker run -p 5000:5000 prescription-validator
```

### Cloud Deployment

The application can be deployed to various cloud platforms:

- **Heroku**: Use the provided `Procfile`
- **AWS**: Deploy using Elastic Beanstalk or ECS
- **Google Cloud**: Use App Engine or Cloud Run
- **Azure**: Deploy to App Service

## Database Management

### Initialization

```bash
python src/database/init_db.py init
```

### Backup

```bash
python src/database/backup.py backup --name daily_backup
```

### Restore

```bash
python src/database/backup.py restore --file backups/daily_backup.json
```

### Reset Database

```bash
python src/database/init_db.py reset
```

## Configuration

### Application Configuration

Edit `src/config.py` to modify:
- Database connection settings
- File upload limits
- OCR processing parameters
- Validation rules

### Service Configuration

Each service can be configured independently:
- **OCR Service**: Tesseract parameters, preprocessing options
- **NLP Service**: Entity recognition models, extraction patterns
- **Validation Service**: Drug interaction database, dosage ranges

## Troubleshooting

### Common Issues

1. **Tesseract Not Found**
   - Ensure Tesseract is installed and in PATH
   - Check installation with `tesseract --version`

2. **Database Errors**
   - Initialize database with `python src/database/init_db.py init`
   - Check file permissions for database file

3. **File Upload Issues**
   - Verify file format is supported (PNG, JPG, PDF, etc.)
   - Check file size limits in configuration

4. **OCR Accuracy Issues**
   - Ensure prescription images are clear and well-lit
   - Try different preprocessing options
   - Consider image enhancement before upload

### Logging

The application logs to console by default. For production, configure file logging:

```python
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
```

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Include type hints where appropriate

### Testing Requirements

- All new features must include tests
- Maintain test coverage above 80%
- Test both success and error cases
- Include integration tests for API endpoints

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation wiki

## Acknowledgments

This project integrates and builds upon several open-source projects:
- Pharmacy_AI for OCR and NER capabilities
- medical-data-extraction for document processing
- Snowstorm for SNOMED CT terminology services

Special thanks to the contributors of these projects for their valuable work in the healthcare technology space.

