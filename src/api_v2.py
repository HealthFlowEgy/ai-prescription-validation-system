"""
Enhanced Flask API with Model Governance, Monitoring, and Clinical Validation
Integrates all Sprint 3 services
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
import time
import logging
from typing import Dict, Optional
from datetime import datetime
import uuid

# Import Sprint 3 services
from mlflow_registry import ModelRegistry, ModelPerformanceTracker
from clinical_validation import ClinicalValidationService
from monitoring_service import MonitoringService
from phi_encryption import (
    EncryptionService,
    PHIAnonymizer,
    AuditLogger,
    DataRetentionService,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize services
model_registry = ModelRegistry(tracking_uri="http://mlflow:5000")
performance_tracker = ModelPerformanceTracker(model_registry)
clinical_validator = ClinicalValidationService()
encryption_service = EncryptionService()
phi_anonymizer = PHIAnonymizer()
audit_logger = AuditLogger()
retention_service = DataRetentionService()

# Initialize monitoring with baseline metrics
baseline_metrics = {"accuracy": 0.94, "confidence": 0.90, "response_time": 500}
monitoring_service = MonitoringService(baseline_metrics)

# Load production models
try:
    ocr_model, ocr_version = model_registry.load_production_model("prescription-ocr-v1")
    nlp_model, nlp_version = model_registry.load_production_model("prescription-nlp-v1")
    logger.info(
        f"Loaded models - OCR: v{ocr_version.version}, " f"NLP: v{nlp_version.version}"
    )
except Exception as e:
    logger.error(f"Failed to load production models: {e}")
    ocr_model = None
    nlp_model = None


# Decorators
def require_auth(f):
    """Authentication decorator"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No authorization token"}), 401

        # Verify JWT token (simplified)
        # In production, use proper JWT verification
        try:
            # user = verify_jwt_token(token)
            g.user_id = request.headers.get("X-User-ID", "unknown")
            g.session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function


def log_phi_access(action: str):
    """Decorator to log PHI access"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract resource info
            resource_id = kwargs.get("prescription_id", "N/A")

            # Execute function
            start_time = time.time()
            result = f(*args, **kwargs)
            duration = (time.time() - start_time) * 1000

            # Log access
            audit_logger.log_access(
                user_id=g.get("user_id", "unknown"),
                action=action,
                resource_type="Prescription",
                resource_id=resource_id,
                phi_fields_accessed=["patient_name", "medications"],
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
                access_justification=request.args.get("reason"),
                success=isinstance(result, tuple) and result[1] == 200,
            )

            return result

        return decorated_function

    return decorator


def monitor_request(f):
    """Decorator to monitor API requests"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        try:
            result = f(*args, **kwargs)
            success = True

            # Extract confidence if available
            confidence = 0.0
            if isinstance(result, tuple) and len(result) > 0:
                response_data = (
                    result[0].get_json() if hasattr(result[0], "get_json") else {}
                )
                confidence = response_data.get("confidence", 0.0)

        except Exception as e:
            logger.error(f"Request failed: {e}")
            success = False
            confidence = 0.0
            raise

        finally:
            # Record metrics
            response_time = (time.time() - start_time) * 1000

            monitoring_service.record_prediction(
                response_time_ms=response_time,
                confidence_score=confidence,
                success=success,
                metadata={"endpoint": request.endpoint, "method": request.method},
            )

        return result

    return decorated_function


# Health Check Endpoints
@app.route("/health", methods=["GET"])
def health_check():
    """Basic health check"""
    return (
        jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "3.0.0",
            }
        ),
        200,
    )


@app.route("/health/detailed", methods=["GET"])
@require_auth
def detailed_health():
    """Detailed health check with system metrics"""
    health_status = monitoring_service.check_system_health()

    return (
        jsonify(
            {
                "status": health_status["status"],
                "metrics": health_status["metrics"],
                "drift_detection": health_status["drift"],
                "active_alerts": health_status["alerts"]["active"],
                "models": {
                    "ocr": {
                        "loaded": ocr_model is not None,
                        "version": ocr_version.version if ocr_model else None,
                    },
                    "nlp": {
                        "loaded": nlp_model is not None,
                        "version": nlp_version.version if nlp_model else None,
                    },
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
        200,
    )


# Model Management Endpoints
@app.route("/api/models/<model_name>/versions", methods=["GET"])
@require_auth
def get_model_versions(model_name):
    """Get all versions of a model"""
    try:
        versions = model_registry.client.search_model_versions(f"name='{model_name}'")

        version_info = [
            {
                "version": v.version,
                "stage": v.current_stage,
                "created_at": datetime.fromtimestamp(
                    v.creation_timestamp / 1000
                ).isoformat(),
                "run_id": v.run_id,
            }
            for v in versions
        ]

        return (
            jsonify(
                {
                    "model_name": model_name,
                    "versions": version_info,
                    "total": len(version_info),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Failed to get model versions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/<model_name>/promote", methods=["POST"])
@require_auth
def promote_model(model_name):
    """Promote model version to production"""
    data = request.json
    version = data.get("version")

    if not version:
        return jsonify({"error": "Version required"}), 400

    try:
        # Transition to production
        model_registry.transition_model_stage(
            model_name=model_name,
            version=version,
            stage="Production",
            archive_existing=True,
        )

        logger.info(f"Promoted {model_name} v{version} to Production")

        return (
            jsonify(
                {
                    "message": f"Model {model_name} v{version} promoted to Production",
                    "model_name": model_name,
                    "version": version,
                    "stage": "Production",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        return jsonify({"error": str(e)}), 500


# Prescription Processing Endpoints
@app.route("/api/prescriptions/process", methods=["POST"])
@require_auth
@log_phi_access("WRITE")
@monitor_request
def process_prescription():
    """
    Process prescription with clinical validation
    Main endpoint integrating all services
    """
    start_time = time.time()

    # Get uploaded file
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if not file or file.filename == "":
        return jsonify({"error": "Empty file"}), 400

    try:
        # Generate prescription ID
        prescription_id = str(uuid.uuid4())

        # Step 1: OCR Extraction
        logger.info(f"Processing prescription {prescription_id} - OCR extraction")
        ocr_start = time.time()

        # Simulate OCR (replace with actual model inference)
        ocr_result = {
            "text": "Sample extracted text",
            "confidence": 0.88,
            "field_confidences": {
                "patient_name": 0.92,
                "medication": 0.85,
                "dosage": 0.79,
            },
            "processing_time_ms": (time.time() - ocr_start) * 1000,
        }

        # Log OCR performance
        performance_tracker.log_prediction(
            model_name="prescription-ocr-v1",
            model_version=ocr_version.version if ocr_model else "unknown",
            input_data={"image_size": "1024x768"},
            prediction=ocr_result,
            ground_truth=None,
        )

        # Step 2: NLP Entity Extraction
        logger.info(f"Processing prescription {prescription_id} - NLP extraction")
        nlp_start = time.time()

        # Simulate NLP (replace with actual model inference)
        nlp_result = {
            "medications": [
                {"name": "Lisinopril", "dosage": "10mg daily", "confidence": 0.91}
            ],
            "patient_name": "John Doe",
            "prescriber_name": "Dr. Smith",
            "date": "2025-10-11",
            "entities": [
                {"type": "medication", "value": "Lisinopril", "confidence": 0.91}
            ],
            "processing_time_ms": (time.time() - nlp_start) * 1000,
        }

        # Step 3: Clinical Validation
        logger.info(f"Processing prescription {prescription_id} - Clinical validation")
        validation_start = time.time()

        # Get patient context (from database or request)
        patient_context = request.json.get("patient_context") if request.json else None

        validation_result = clinical_validator.validate_prescription(
            ocr_result=ocr_result,
            nlp_result=nlp_result,
            patient_context=patient_context,
        )

        # Step 4: Encrypt PHI before storage
        encrypted_patient_name = encryption_service.encrypt(
            nlp_result.get("patient_name", "")
        )

        # Calculate total processing time
        total_time = (time.time() - start_time) * 1000

        # Prepare response (anonymize for logging)
        response_data = {
            "prescription_id": prescription_id,
            "status": validation_result["status"],
            "validation": {
                "requires_review": validation_result["requires_pharmacist_review"],
                "risk_score": validation_result["risk_score"],
                "flags": validation_result["flags"],
                "summary": validation_result["summary"],
            },
            "confidence": {
                "ocr": ocr_result["confidence"],
                "nlp": (
                    nlp_result["entities"][0]["confidence"]
                    if nlp_result["entities"]
                    else 0
                ),
                "overall": (
                    ocr_result["confidence"] + nlp_result["entities"][0]["confidence"]
                )
                / 2,
            },
            "processing_time_ms": total_time,
            "model_versions": {
                "ocr": ocr_version.version if ocr_model else "unknown",
                "nlp": nlp_version.version if nlp_model else "unknown",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Log anonymized response
        safe_response = phi_anonymizer.anonymize_dict(response_data)
        logger.info(
            f"Processed prescription {prescription_id}: {safe_response['status']}"
        )

        return jsonify(response_data), 200

    except Exception as e:
        # Anonymize error message
        safe_error = phi_anonymizer.anonymize(str(e))
        logger.error(f"Processing failed: {safe_error}")

        return (
            jsonify(
                {
                    "error": "Processing failed",
                    "details": safe_error,
                    "prescription_id": (
                        prescription_id if "prescription_id" in locals() else None
                    ),
                }
            ),
            500,
        )


@app.route("/api/prescriptions/<prescription_id>", methods=["GET"])
@require_auth
@log_phi_access("READ")
def get_prescription(prescription_id):
    """Get prescription details"""
    try:
        # Query prescription from database
        # prescription = query_prescription(prescription_id)

        # Return anonymized data (PHI automatically decrypted by SQLAlchemy)
        return (
            jsonify(
                {
                    "prescription_id": prescription_id,
                    "status": "processed",
                    "patient_name": "[REDACTED]",  # Don't expose raw PHI in API
                    "medications": "[REDACTED]",
                    "message": "Full PHI data available through secure channel only",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Failed to retrieve prescription: {e}")
        return jsonify({"error": "Prescription not found"}), 404


@app.route("/api/prescriptions/<prescription_id>/review", methods=["POST"])
@require_auth
@log_phi_access("WRITE")
def submit_pharmacist_review(prescription_id):
    """Submit pharmacist review for flagged prescription"""
    data = request.json

    review_decision = data.get("decision")  # 'approve' or 'reject'
    pharmacist_notes = data.get("notes")

    if not review_decision:
        return jsonify({"error": "Decision required"}), 400

    try:
        # Update prescription status
        # update_prescription_status(
        #     prescription_id,
        #     review_decision,
        #     pharmacist_notes
        # )

        logger.info(
            f"Pharmacist review submitted for {prescription_id}: {review_decision}"
        )

        return (
            jsonify(
                {
                    "prescription_id": prescription_id,
                    "decision": review_decision,
                    "reviewed_by": g.user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Review submission failed: {e}")
        return jsonify({"error": str(e)}), 500


# Monitoring and Metrics Endpoints
@app.route("/api/metrics/current", methods=["GET"])
@require_auth
def get_current_metrics():
    """Get current system metrics"""
    metrics = monitoring_service.metrics_collector.get_current_metrics()

    return jsonify(metrics), 200


@app.route("/api/metrics/drift", methods=["GET"])
@require_auth
def check_drift():
    """Check for model drift"""
    current_metrics = monitoring_service.metrics_collector.get_current_metrics()
    drift_result = monitoring_service.drift_detector.check_drift(current_metrics)

    return jsonify(drift_result), 200


@app.route("/api/alerts", methods=["GET"])
@require_auth
def get_alerts():
    """Get active alerts"""
    active_alerts = monitoring_service.alert_manager.get_active_alerts()

    return (
        jsonify(
            {
                "active_alerts": [
                    {
                        "alert_id": a.alert_id,
                        "severity": a.severity,
                        "title": a.title,
                        "description": a.description,
                        "timestamp": a.timestamp.isoformat(),
                    }
                    for a in active_alerts
                ],
                "count": len(active_alerts),
            }
        ),
        200,
    )


@app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
@require_auth
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    monitoring_service.alert_manager.acknowledge_alert(alert_id)

    return (
        jsonify(
            {
                "alert_id": alert_id,
                "acknowledged": True,
                "acknowledged_by": g.user_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
        200,
    )


# Data Retention Endpoints
@app.route("/api/prescriptions/<prescription_id>/delete", methods=["DELETE"])
@require_auth
def delete_prescription(prescription_id):
    """Securely delete prescription (HIPAA-compliant)"""
    reason = request.json.get("reason", "User requested deletion")

    try:
        retention_service.secure_delete(
            resource_type="Prescription",
            resource_id=prescription_id,
            user_id=g.user_id,
            reason=reason,
        )

        return (
            jsonify(
                {
                    "prescription_id": prescription_id,
                    "deleted": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Deletion failed: {e}")
        return jsonify({"error": str(e)}), 500


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    # Anonymize error
    safe_error = phi_anonymizer.anonymize(str(error))

    return jsonify({"error": "Internal server error", "details": safe_error}), 500


@app.errorhandler(Exception)
def handle_exception(error):
    # Anonymize error
    safe_error = phi_anonymizer.anonymize(str(error))
    logger.error(f"Unhandled exception: {safe_error}")

    return jsonify({"error": "An error occurred", "details": safe_error}), 500


if __name__ == "__main__":
    logger.info("Starting HealthFlow AI API Server")
    logger.info(
        f"Models loaded: OCR={ocr_model is not None}, NLP={nlp_model is not None}"
    )

    # Run in production with gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 enhanced_api:app
    app.run(host="0.0.0.0", port=5000, debug=False)
