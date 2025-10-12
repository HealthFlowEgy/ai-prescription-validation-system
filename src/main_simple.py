import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder="static")
CORS(app)

# Configuration
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///prescription_validation.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database
db = SQLAlchemy(app)


# Simple User model
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# Simple Prescription model
class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="uploaded")
    extracted_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship("User", backref=db.backref("prescriptions", lazy=True))


# Routes
@app.route("/")
def index():
    """Serve the main application page"""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "message": "AI-Based Digital Prescription Validation System is running",
            "version": "1.0.0",
        }
    )


@app.route("/api/users", methods=["GET"])
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        return jsonify(
            [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                }
                for user in users
            ]
        )
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/users", methods=["POST"])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()

        if not data or "username" not in data or "email" not in data:
            return jsonify({"error": "Username and email are required"}), 400

        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == data["username"]) | (User.email == data["email"])
        ).first()

        if existing_user:
            return (
                jsonify({"error": "User with this username or email already exists"}),
                409,
            )

        user = User(username=data["username"], email=data["email"])

        db.session.add(user)
        db.session.commit()

        return (
            jsonify(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/prescriptions/upload", methods=["POST"])
def upload_prescription():
    """Upload a prescription file"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        user_id = request.form.get("user_id", 1)  # Default to user 1

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Generate unique prescription ID
        import uuid

        prescription_id = str(uuid.uuid4())

        # Create prescription record
        prescription = Prescription(
            id=prescription_id,
            user_id=user_id,
            filename=file.filename,
            status="uploaded",
        )

        db.session.add(prescription)
        db.session.commit()

        return (
            jsonify(
                {
                    "prescription_id": prescription_id,
                    "filename": file.filename,
                    "status": "uploaded",
                    "message": "Prescription uploaded successfully",
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error uploading prescription: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/prescriptions/<prescription_id>/process", methods=["POST"])
def process_prescription(prescription_id):
    """Process a prescription (simplified version)"""
    try:
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404

        # Simulate processing
        prescription.status = "processed"
        prescription.extracted_text = (
            "Sample extracted text: Lisinopril 10mg, take once daily"
        )
        db.session.commit()

        return jsonify(
            {
                "prescription_id": prescription_id,
                "status": "processed",
                "extracted_text": prescription.extracted_text,
                "message": "Prescription processed successfully",
            }
        )

    except Exception as e:
        logger.error(f"Error processing prescription: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/prescriptions/<prescription_id>/validate", methods=["POST"])
def validate_prescription(prescription_id):
    """Validate a prescription (simplified version)"""
    try:
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404

        # Simulate validation
        validation_result = {
            "prescription_id": prescription_id,
            "status": "validated",
            "validation_score": 0.95,
            "issues": [],
            "recommendations": [
                "Prescription appears valid",
                "No drug interactions detected",
            ],
            "message": "Prescription validation completed successfully",
        }

        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"Error validating prescription: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/prescriptions", methods=["GET"])
def get_prescriptions():
    """Get all prescriptions"""
    try:
        prescriptions = Prescription.query.all()
        return jsonify(
            [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "filename": p.filename,
                    "status": p.status,
                    "created_at": p.created_at.isoformat(),
                }
                for p in prescriptions
            ]
        )
    except Exception as e:
        logger.error(f"Error getting prescriptions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# Initialize database
def create_tables():
    """Create database tables"""
    try:
        db.create_all()

        # Create default user if none exists
        if User.query.count() == 0:
            default_user = User(
                username="admin", email="admin@prescription-validator.com"
            )
            db.session.add(default_user)
            db.session.commit()
            logger.info("Created default admin user")

    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")


if __name__ == "__main__":
    # Create tables
    with app.app_context():
        db.create_all()

        # Create default user if none exists
        if User.query.count() == 0:
            default_user = User(
                username="admin", email="admin@prescription-validator.com"
            )
            db.session.add(default_user)
            db.session.commit()
            logger.info("Created default admin user")

    # Run the application
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
