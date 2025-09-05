# Contributing to AI-Based Digital Prescription Validation System

Thank you for your interest in contributing to the AI-Based Digital Prescription Validation System! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Deployment](#deployment)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose
- Git
- Digital Ocean account (for deployment)
- Basic knowledge of Flask, OCR, and NLP

### Development Setup

1. **Fork the repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/your-username/ai-prescription-validation-system.git
   cd ai-prescription-validation-system
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install pytest pytest-cov black isort flake8 mypy
   ```

3. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-eng
   
   # macOS
   brew install tesseract
   ```

4. **Initialize database**
   ```bash
   python src/database/init_db.py init
   ```

5. **Run the application**
   ```bash
   python src/main.py
   ```

## Contributing Process

### 1. Create an Issue

Before starting work, create an issue to discuss:
- Bug reports
- Feature requests
- Documentation improvements
- Performance enhancements

### 2. Branch Strategy

We use GitFlow branching strategy:

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/**: Feature development branches
- **hotfix/**: Emergency fixes for production
- **release/**: Release preparation branches

### 3. Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run tests
   python -m pytest tests/ -v
   
   # Run linting
   black src/ tests/
   isort src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new validation rule for drug interactions"
   ```

5. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub targeting develop branch
   ```

### 4. Pull Request Guidelines

- Fill out the PR template completely
- Ensure all tests pass
- Include screenshots for UI changes
- Request review from maintainers
- Address feedback promptly

## Coding Standards

### Python Code Style

- Follow PEP 8 style guide
- Use Black for code formatting
- Use isort for import sorting
- Maximum line length: 88 characters
- Use type hints where appropriate

### Code Organization

```
src/
├── models/          # Database models
├── routes/          # API endpoints
├── services/        # Business logic
├── database/        # Database utilities
└── static/          # Static files
```

### Naming Conventions

- **Files**: snake_case.py
- **Classes**: PascalCase
- **Functions/Variables**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: _leading_underscore

### Documentation

- Use docstrings for all public functions and classes
- Include type hints
- Add inline comments for complex logic
- Update README.md for significant changes

## Testing Guidelines

### Test Structure

```
tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
├── fixtures/        # Test data
└── conftest.py      # Pytest configuration
```

### Writing Tests

1. **Unit Tests**
   - Test individual functions/methods
   - Mock external dependencies
   - Aim for 90%+ code coverage

2. **Integration Tests**
   - Test API endpoints
   - Test database interactions
   - Test file upload/processing

3. **Test Naming**
   ```python
   def test_should_validate_prescription_when_all_fields_present():
       # Test implementation
   ```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_prescription.py

# Run tests with specific marker
python -m pytest -m "not slow"
```

## Documentation

### Code Documentation

- Use Google-style docstrings
- Document all public APIs
- Include examples in docstrings
- Keep documentation up to date

### API Documentation

- Document all endpoints
- Include request/response examples
- Specify error codes and messages
- Update OpenAPI/Swagger specs

### User Documentation

- Update README.md for setup changes
- Update deployment guides for infrastructure changes
- Create tutorials for new features
- Maintain troubleshooting guides

## Deployment

### Local Testing

```bash
# Test with Docker
docker-compose up --build

# Test deployment scripts
./deployment/digitalocean/setup-droplet.sh --dry-run
```

### CI/CD Pipeline

All changes go through automated testing:

1. **Code Quality Checks**
   - Linting (Black, isort, flake8)
   - Type checking (mypy)
   - Security scanning (bandit)

2. **Testing**
   - Unit tests
   - Integration tests
   - Coverage reporting

3. **Deployment**
   - Staging deployment (develop branch)
   - Production deployment (main branch)
   - Release deployment (tags)

### Environment-Specific Changes

- **Development**: Any changes allowed
- **Staging**: Requires PR approval
- **Production**: Requires release process

## Security Guidelines

### Sensitive Data

- Never commit secrets or API keys
- Use environment variables for configuration
- Encrypt sensitive data in database
- Follow OWASP security guidelines

### Dependencies

- Keep dependencies updated
- Run security audits regularly
- Use known secure packages
- Document security considerations

## Performance Guidelines

### Code Performance

- Profile code for bottlenecks
- Optimize database queries
- Use caching where appropriate
- Monitor memory usage

### Infrastructure Performance

- Monitor application metrics
- Optimize Docker images
- Use CDN for static assets
- Implement proper logging

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Request Reviews**: Code-specific discussions

### Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Digital Ocean Documentation](https://docs.digitalocean.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- GitHub contributor graphs

Thank you for contributing to the AI-Based Digital Prescription Validation System!

