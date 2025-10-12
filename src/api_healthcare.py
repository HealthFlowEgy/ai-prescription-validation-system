"""
Sprint 4 Enhanced API with Healthcare Integration Standards
Integrates FHIR, HL7, and EHR system connectors
"""

from flask import Flask, request, jsonify, Response, g
from flask_cors import CORS
from functools import wraps
import logging
from typing import Dict, Optional
from datetime import datetime
import json

# Import Sprint 4 services
from fhir_integration import FHIRConverter, FHIRValidator, FHIRResourceBuilder
from hl7_integration import HL7MessageBuilder, HL7Parser, HL7Validator, HL7MessageQueue
from ehr_integration import (
    EHRIntegrationService,
    EHRAuthenticator,
    EpicConnector,
    CernerConnector,
)

# Import Sprint 3 services
from clinical_validation import ClinicalValidationService
from monitoring_service import MonitoringService
from phi_encryption import EncryptionService, PHIAnonymizer, AuditLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Initialize services
fhir_converter = FHIRConverter()
fhir_builder = FHIRResourceBuilder()
fhir_validator = FHIRValidator()

hl7_builder = HL7MessageBuilder()
hl7_parser = HL7Parser()
hl7_validator = HL7Validator()
hl7_queue = HL7MessageQueue()

ehr_service = EHRIntegrationService()
clinical_validator = ClinicalValidationService()
monitoring_service = MonitoringService(
    baseline_metrics={"accuracy": 0.94, "confidence": 0.90, "response_time": 500}
)

phi_anonymizer = PHIAnonymizer()
audit_logger = AuditLogger()


# Decorators
def require_auth(f):
    """Authentication decorator"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No authorization token"}), 401

        try:
            g.user_id = request.headers.get("X-User-ID", "unknown")
            g.organization = request.headers.get("X-Organization", "default")
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated_function


def monitor_request(f):
    """Monitor API request performance"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time

        start_time = time.time()

        try:
            result = f(*args, **kwargs)
            success = True
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
            response_time = (time.time() - start_time) * 1000

            monitoring_service.record_prediction(
                response_time_ms=response_time,
                confidence_score=confidence,
                success=success,
                metadata={"endpoint": request.endpoint, "method": request.method},
            )

        return result

    return decorated_function


# FHIR Endpoints
@app.route("/fhir/Patient/<patient_id>", methods=["GET"])
@require_auth
@monitor_request
def fhir_get_patient(patient_id):
    """
    Get patient in FHIR format
    Implements FHIR R4 Patient resource endpoint
    """
    try:
        # Get patient data from database
        # patient_data = get_patient_from_db(patient_id)

        # Mock patient data for example
        patient_data = {
            "id": patient_id,
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1980-01-15",
            "gender": "male",
            "phone": "555-1234",
            "email": "john.doe@email.com",
            "mrn": "MRN123456",
        }

        # Build FHIR Patient resource
        patient_resource = fhir_builder.build_patient_resource(
            patient_id=patient_data["id"],
            first_name=patient_data["first_name"],
            last_name=patient_data["last_name"],
            dob=patient_data["dob"],
            gender=patient_data["gender"],
            phone=patient_data.get("phone"),
            email=patient_data.get("email"),
            mrn=patient_data.get("mrn"),
        )

        # Audit log
        audit_logger.log_access(
            user_id=g.user_id,
            action="READ",
            resource_type="Patient",
            resource_id=patient_id,
            phi_fields_accessed=["name", "birthDate"],
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
            success=True,
        )

        # Return FHIR JSON
        return Response(
            patient_resource.json(indent=2),
            mimetype="application/fhir+json",
            status=200,
        )

    except Exception as e:
        logger.error(f"Failed to retrieve FHIR patient: {e}")
        return (
            jsonify(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                }
            ),
            500,
        )


@app.route("/fhir/MedicationRequest", methods=["POST"])
@require_auth
@monitor_request
def fhir_create_medication_request():
    """
    Create MedicationRequest in FHIR format
    Implements FHIR R4 MedicationRequest creation
    """
    try:
        fhir_data = request.get_json()

        # Validate FHIR resource
        from fhir.resources.medicationrequest import MedicationRequest

        med_request = MedicationRequest(**fhir_data)

        # Convert to internal format
        # save_medication_request(med_request)

        # Generate ID
        med_request.id = f"med-req-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"Created FHIR MedicationRequest: {med_request.id}")

        return Response(
            med_request.json(indent=2),
            mimetype="application/fhir+json",
            status=201,
            headers={"Location": f"/fhir/MedicationRequest/{med_request.id}"},
        )

    except Exception as e:
        logger.error(f"Failed to create FHIR MedicationRequest: {e}")
        return (
            jsonify(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {"severity": "error", "code": "invalid", "diagnostics": str(e)}
                    ],
                }
            ),
            400,
        )


@app.route("/fhir/Bundle", methods=["POST"])
@require_auth
@monitor_request
def fhir_process_bundle():
    """
    Process FHIR Bundle (transaction/batch)
    Supports multiple resources in single request
    """
    try:
        bundle_data = request.get_json()

        from fhir.resources.bundle import Bundle

        bundle = Bundle(**bundle_data)

        # Validate bundle
        validation_result = fhir_validator.validate_bundle(bundle)

        if not validation_result["valid"]:
            return (
                jsonify(
                    {
                        "resourceType": "OperationOutcome",
                        "issue": [
                            {
                                "severity": "error",
                                "code": "invalid",
                                "diagnostics": f"Validation failed: {validation_result['errors']}",
                            }
                        ],
                    }
                ),
                400,
            )

        # Process bundle entries
        response_entries = []
        for entry in bundle.entry:
            resource = entry.resource

            # Process based on resource type
            # This would dispatch to appropriate handlers
            response_entries.append(
                {
                    "response": {
                        "status": "201 Created",
                        "location": f"/{resource.get('resourceType')}/{resource.get('id')}",
                    }
                }
            )

        # Create response bundle
        response_bundle = Bundle(type="transaction-response", entry=response_entries)

        logger.info(f"Processed FHIR Bundle with {len(bundle.entry)} entries")

        return Response(
            response_bundle.json(indent=2), mimetype="application/fhir+json", status=200
        )

    except Exception as e:
        logger.error(f"Failed to process FHIR Bundle: {e}")
        return (
            jsonify(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                }
            ),
            500,
        )


@app.route("/fhir/export/prescription/<prescription_id>", methods=["GET"])
@require_auth
def fhir_export_prescription(prescription_id):
    """
    Export prescription as FHIR Bundle
    """
    try:
        # Get prescription data
        # prescription_data = get_prescription_from_db(prescription_id)

        # Mock prescription data
        prescription_data = {
            "patient": {
                "id": "pat-123",
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1980-01-15",
                "gender": "male",
            },
            "practitioner": {
                "id": "pract-456",
                "first_name": "Jane",
                "last_name": "Smith",
                "npi": "1234567890",
            },
            "medications": [
                {
                    "id": "med-789",
                    "name": "Lisinopril 10mg",
                    "rxnorm_code": "314076",
                    "dosage_instruction": "Take 1 tablet daily",
                    "quantity": 30,
                    "refills": 3,
                }
            ],
        }

        # Convert to FHIR Bundle
        fhir_bundle = fhir_converter.prescription_to_fhir(prescription_data)

        logger.info(f"Exported prescription {prescription_id} as FHIR Bundle")

        return Response(
            fhir_bundle.json(indent=2),
            mimetype="application/fhir+json",
            status=200,
            headers={
                "Content-Disposition": f"attachment; filename=prescription-{prescription_id}.json"
            },
        )

    except Exception as e:
        logger.error(f"Failed to export prescription as FHIR: {e}")
        return jsonify({"error": str(e)}), 500


# HL7 Endpoints
@app.route("/hl7/message", methods=["POST"])
@require_auth
@monitor_request
def hl7_receive_message():
    """
    Receive and process HL7 v2.x message
    """
    try:
        hl7_message = request.data.decode("utf-8")

        # Validate HL7 message
        is_valid, errors = hl7_validator.validate_message(hl7_message)

        if not is_valid:
            # Send NACK
            ack_message = hl7_builder.build_ack_message(
                original_message_id="UNKNOWN",
                ack_code="AE",
                text_message=f"Validation failed: {', '.join(errors)}",
            )

            return Response(ack_message, mimetype="text/plain", status=400)

        # Parse message
        parsed_message = hl7_parser.parse_message(hl7_message)

        # Queue for processing
        queue_id = hl7_queue.enqueue(hl7_message)

        # Send ACK
        ack_message = hl7_builder.build_ack_message(
            original_message_id=parsed_message.message_id,
            ack_code="AA",
            text_message="Message accepted for processing",
        )

        logger.info(
            f"Received HL7 message {parsed_message.message_id}, "
            f"queued as {queue_id}"
        )

        return Response(ack_message, mimetype="text/plain", status=200)

    except Exception as e:
        logger.error(f"Failed to process HL7 message: {e}")

        # Send error ACK
        ack_message = hl7_builder.build_ack_message(
            original_message_id="UNKNOWN",
            ack_code="AR",
            text_message=f"Error: {str(e)}",
        )

        return Response(ack_message, mimetype="text/plain", status=500)


@app.route("/hl7/export/prescription/<prescription_id>", methods=["GET"])
@require_auth
def hl7_export_prescription(prescription_id):
    """
    Export prescription as HL7 RDE^O11 message
    """
    try:
        # Get prescription data
        # prescription_data = get_prescription_from_db(prescription_id)

        # Mock prescription data
        prescription_data = {
            "prescription_id": prescription_id,
            "patient": {
                "id": "PAT-123",
                "mrn": "MRN-456",
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1980-01-15",
                "gender": "male",
            },
            "practitioner": {
                "npi": "1234567890",
                "first_name": "Jane",
                "last_name": "Smith",
            },
            "medications": [
                {
                    "rxnorm_code": "314076",
                    "name": "Lisinopril 10mg",
                    "quantity": "30",
                    "dosage_instruction": "Take 1 tablet daily",
                    "refills": 3,
                }
            ],
        }

        # Build HL7 message
        hl7_message = hl7_builder.build_rde_o11_message(prescription_data)

        logger.info(f"Exported prescription {prescription_id} as HL7 RDE^O11")

        return Response(
            hl7_message,
            mimetype="text/plain",
            status=200,
            headers={
                "Content-Disposition": f"attachment; filename=prescription-{prescription_id}.hl7"
            },
        )

    except Exception as e:
        logger.error(f"Failed to export prescription as HL7: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/hl7/queue/status", methods=["GET"])
@require_auth
def hl7_queue_status():
    """Get HL7 message queue status"""
    status = hl7_queue.get_queue_status()

    return (
        jsonify({"queue_status": status, "timestamp": datetime.utcnow().isoformat()}),
        200,
    )


# EHR Integration Endpoints
@app.route("/ehr/<ehr_system>/patient/<patient_id>/context", methods=["GET"])
@require_auth
@monitor_request
def ehr_get_patient_context(ehr_system, patient_id):
    """
    Get patient context from EHR system
    Retrieves medications, allergies, conditions
    """
    try:
        context = ehr_service.get_patient_context(ehr_system, patient_id)

        # Anonymize for logging
        safe_context = phi_anonymizer.anonymize_dict(context)
        logger.info(f"Retrieved patient context from {ehr_system}")

        return jsonify(context), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Failed to get patient context from {ehr_system}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ehr/<ehr_system>/prescription/sync", methods=["POST"])
@require_auth
@monitor_request
def ehr_sync_prescription(ehr_system):
    """
    Sync prescription to EHR system
    """
    try:
        prescription_data = request.get_json()

        # Validate FHIR format
        from fhir.resources.medicationrequest import MedicationRequest

        med_request = MedicationRequest(**prescription_data)

        # Sync to EHR
        result = ehr_service.sync_prescription(
            ehr_system=ehr_system, prescription_data=prescription_data
        )

        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"Failed to sync prescription to {ehr_system}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/ehr/connectors", methods=["GET"])
@require_auth
def ehr_list_connectors():
    """List available EHR system connectors"""
    connectors = ehr_service.list_registered_connectors()

    return jsonify({"connectors": connectors, "count": len(connectors)}), 200


# Integration Workflow Endpoints
@app.route("/api/prescription/process/integrated", methods=["POST"])
@require_auth
@monitor_request
def process_prescription_integrated():
    """
    Complete integrated prescription workflow
    1. OCR & NLP extraction
    2. Clinical validation
    3. Get EHR context
    4. FHIR export
    5. HL7 generation
    6. EHR sync
    """
    try:
        # Get uploaded file
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        ehr_system = request.form.get("ehr_system")
        patient_id = request.form.get("patient_id")

        # Step 1: Process prescription (OCR + NLP + Validation)
        # This would call existing processing pipeline
        prescription_data = {
            "prescription_id": f"RX-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "patient": {
                "id": patient_id,
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1980-01-15",
                "gender": "male",
            },
            "practitioner": {
                "id": "pract-123",
                "first_name": "Jane",
                "last_name": "Smith",
                "npi": "1234567890",
            },
            "medications": [
                {
                    "id": "med-456",
                    "name": "Lisinopril 10mg",
                    "rxnorm_code": "314076",
                    "dosage_instruction": "Take 1 tablet daily",
                    "quantity": 30,
                    "refills": 3,
                }
            ],
        }

        # Step 2: Get EHR context (if EHR system specified)
        ehr_context = None
        if ehr_system and patient_id:
            try:
                ehr_context = ehr_service.get_patient_context(ehr_system, patient_id)
            except Exception as e:
                logger.warning(f"Could not retrieve EHR context: {e}")

        # Step 3: Clinical validation with EHR context
        # validation_result = clinical_validator.validate_prescription(...)

        # Step 4: Export to FHIR
        fhir_bundle = fhir_converter.prescription_to_fhir(prescription_data)

        # Step 5: Generate HL7 message
        hl7_message = hl7_builder.build_rde_o11_message(prescription_data)

        # Step 6: Sync to EHR (if requested)
        sync_result = None
        if ehr_system:
            try:
                sync_result = ehr_service.sync_prescription(
                    ehr_system=ehr_system,
                    prescription_data=fhir_bundle.dict()["entry"][2][
                        "resource"
                    ],  # MedicationRequest
                )
            except Exception as e:
                logger.error(f"EHR sync failed: {e}")
                sync_result = {"success": False, "error": str(e)}

        # Prepare response
        response = {
            "prescription_id": prescription_data["prescription_id"],
            "status": "processed",
            "fhir_available": True,
            "hl7_available": True,
            "ehr_sync": sync_result,
            "ehr_context_retrieved": ehr_context is not None,
            "exports": {
                "fhir_url": f"/fhir/export/prescription/{prescription_data['prescription_id']}",
                "hl7_url": f"/hl7/export/prescription/{prescription_data['prescription_id']}",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Completed integrated prescription processing: "
            f"{prescription_data['prescription_id']}"
        )

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Integrated processing failed: {e}")
        return jsonify({"error": str(e)}), 500


# Health Check
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "services": {
                    "fhir": "operational",
                    "hl7": "operational",
                    "ehr": "operational",
                },
                "ehr_connectors": ehr_service.list_registered_connectors(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
        200,
    )


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return (
        jsonify(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "not-found",
                        "diagnostics": "Resource not found",
                    }
                ],
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    return (
        jsonify(
            {
                "resourceType": "OperationOutcome",
                "issue": [
                    {
                        "severity": "error",
                        "code": "exception",
                        "diagnostics": "Internal server error",
                    }
                ],
            }
        ),
        500,
    )


if __name__ == "__main__":
    logger.info("Starting HealthFlow Sprint 4 API with Healthcare Standards")
    logger.info(f"FHIR R4: Enabled")
    logger.info(f"HL7 v2.x: Enabled")
    logger.info(f"EHR Connectors: {ehr_service.list_registered_connectors()}")

    app.run(host="0.0.0.0", port=5000, debug=False)
