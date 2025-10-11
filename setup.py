"""
HealthFlow AI Digital Prescription Validation System
Setup configuration for package installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
requirements_path = this_directory / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="healthflow-prescription-validator",
    version="1.0.0",
    author="HealthFlow Development Team",
    author_email="dev@healthflow.egypt.gov",
    description="AI-powered digital prescription validation system for Egyptian healthcare",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HealthFlowEgy/ai-prescription-validation-system",
    project_urls={
        "Bug Tracker": "https://github.com/HealthFlowEgy/ai-prescription-validation-system/issues",
        "Documentation": "https://github.com/HealthFlowEgy/ai-prescription-validation-system/docs",
        "Source Code": "https://github.com/HealthFlowEgy/ai-prescription-validation-system",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: Flask",
        "Environment :: Web Environment",
        "Natural Language :: English",
        "Natural Language :: Arabic",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.1",
            "pytest-mock>=3.12.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
            "bandit>=1.7.5",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=1.3.0",
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.4.8",
        ],
        "ml": [
            "tensorflow>=2.15.0",
            "torch>=2.1.2",
            "transformers>=4.36.2",
            "spacy>=3.7.2",
            "nltk>=3.8.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "healthflow=main:main",
            "healthflow-migrate=database.init_db:main",
            "healthflow-backup=database.backup:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml", "*.txt"],
    },
    zip_safe=False,
    keywords=[
        "healthcare",
        "prescription",
        "validation",
        "ai",
        "machine-learning",
        "ocr",
        "nlp",
        "fhir",
        "egypt",
        "digital-health",
    ],
    platforms=["any"],
    license="MIT",
)

