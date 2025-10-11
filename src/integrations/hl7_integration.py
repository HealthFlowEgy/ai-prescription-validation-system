"""
HL7 v2.x Message Integration Service
Supports HL7 v2.5+ message parsing and generation
Handles RDE (Pharmacy/Treatment Encoded Order) messages
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging
import re

from hl7apy.core import Message, Segment
from hl7apy.parser import parse_message
from hl7apy import consts

logger = logging.getLogger(__name__)


@dataclass
class HL7Message:
    """HL7 message representation"""
    message_type: str
    message_id: str
    timestamp: datetime
    sending_application: str
    sending_facility: str
    receiving_application: str
    receiving_facility: str
    segments: List[Dict]
    raw_message: str


class HL7MessageBuilder:
    """
    Builds HL7 v2.x messages for pharmacy orders
    """
    
    def __init__(
        self,
        sending_application: str = "HEALTHFLOW",
        sending_facility: str = "HEALTHFLOW_AI",
        receiving_application: str = "PHARMACY_SYS",
        receiving_facility: str = "PHARMACY"
    ):
        """
        Initialize HL7 message builder
        
        Args:
            sending_application: Sending application name
            sending_facility: Sending facility name
            receiving_application: Receiving application name
            receiving_facility: Receiving facility name
        """
        self.sending_application = sending_application
        self.sending_facility = sending_facility
        self.receiving_application = receiving_application
        self.receiving_facility = receiving_facility
    
    def build_rde_o11_message(
        self,
        prescription_data: Dict
    ) -> str:
        """
        Build RDE^O11 (Pharmacy/Treatment Encoded Order) message
        
        Args:
            prescription_data: Prescription data dictionary
        
        Returns:
            HL7 message string
        """
        # Create message
        msg = Message("RDE_O11", version="2.5")
        
        # MSH - Message Header
        msh = msg.msh
        msh.msh_3 = self.sending_application
        msh.msh_4 = self.sending_facility
        msh.msh_5 = self.receiving_application
        msh.msh_6 = self.receiving_facility
        msh.msh_7 = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        msh.msh_9 = "RDE^O11^RDE_O11"
        msh.msh_10 = prescription_data.get("prescription_id", "")
        msh.msh_11 = "P"  # Production
        msh.msh_12 = "2.5"
        
        # PID - Patient Identification
        patient = prescription_data.get("patient", {})
        pid = msg.add_segment("PID")
        pid.pid_1 = "1"
        pid.pid_2 = patient.get("mrn", "")
        pid.pid_3 = patient.get("id", "")
        pid.pid_5 = f"{patient.get('last_name', '')}^{patient.get('first_name', '')}"
        pid.pid_7 = patient.get("dob", "").replace("-", "")
        pid.pid_8 = patient.get("gender", "U").upper()[0]
        
        # Add patient address
        if patient.get("address"):
            addr = patient["address"]
            pid.pid_11 = f"{addr.get('street', '')}^^{addr.get('city', '')}^{addr.get('state', '')}^{addr.get('zip', '')}"
        
        # Add patient phone
        if patient.get("phone"):
            pid.pid_13 = f"^PRN^PH^^^{patient['phone']}"
        
        # ORC - Common Order
        orc = msg.add_segment("ORC")
        orc.orc_1 = "NW"  # New order
        orc.orc_2 = prescription_data.get("prescription_id", "")
        orc.orc_9 = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # Add ordering provider
        practitioner = prescription_data.get("practitioner", {})
        if practitioner:
            orc.orc_12 = f"{practitioner.get('npi', '')}^{practitioner.get('last_name', '')}^{practitioner.get('first_name', '')}"
        
        # RXE - Pharmacy/Treatment Encoded Order
        for medication in prescription_data.get("medications", []):
            rxe = msg.add_segment("RXE")
            rxe.rxe_1 = "1"  # Quantity/Timing
            rxe.rxe_2 = f"{medication.get('rxnorm_code', '')}^{medication.get('name', '')}^RXN"
            rxe.rxe_3 = medication.get("quantity", "")
            rxe.rxe_5 = medication.get("dosage_instruction", "")
            rxe.rxe_6 = "TAB"  # Dosage form (tablet)
            
            # Add refills
            if medication.get("refills"):
                rxe.rxe_12 = medication["refills"]
        
        # Generate HL7 string
        hl7_message = msg.to_er7()
        
        logger.info(f"Built RDE^O11 message for prescription {prescription_data.get('prescription_id')}")
        
        return hl7_message
    
    def build_ack_message(
        self,
        original_message_id: str,
        ack_code: str = "AA",
        text_message: Optional[str] = None
    ) -> str:
        """
        Build ACK (General Acknowledgment) message
        
        Args:
            original_message_id: ID of message being acknowledged
            ack_code: AA (Application Accept), AE (Application Error), AR (Application Reject)
            text_message: Optional error/status message
        
        Returns:
            HL7 ACK message string
        """
        msg = Message("ACK", version="2.5")
        
        # MSH - Message Header
        msh = msg.msh
        msh.msh_3 = self.sending_application
        msh.msh_4 = self.sending_facility
        msh.msh_5 = self.receiving_application
        msh.msh_6 = self.receiving_facility
        msh.msh_7 = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        msh.msh_9 = "ACK"
        msh.msh_10 = f"ACK-{original_message_id}"
        msh.msh_11 = "P"
        msh.msh_12 = "2.5"
        
        # MSA - Message Acknowledgment
        msa = msg.add_segment("MSA")
        msa.msa_1 = ack_code
        msa.msa_2 = original_message_id
        
        if text_message:
            msa.msa_3 = text_message
        
        return msg.to_er7()


class HL7Parser:
    """
    Parses incoming HL7 v2.x messages
    """
    
    def parse_message(self, hl7_string: str) -> HL7Message:
        """
        Parse HL7 message string
        
        Args:
            hl7_string: HL7 message in ER7 format
        
        Returns:
            HL7Message object
        """
        try:
            # Parse using hl7apy
            msg = parse_message(hl7_string, validation_level=consts.VALIDATION_LEVEL.STRICT)
            
            # Extract MSH fields
            msh = msg.msh
            message_type = str(msh.msh_9.msh_9_1.value)
            message_id = str(msh.msh_10.value)
            timestamp_str = str(msh.msh_7.value)
            
            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            
            # Extract segments
            segments = []
            for segment in msg.children:
                segment_dict = self._segment_to_dict(segment)
                segments.append(segment_dict)
            
            hl7_message = HL7Message(
                message_type=message_type,
                message_id=message_id,
                timestamp=timestamp,
                sending_application=str(msh.msh_3.value),
                sending_facility=str(msh.msh_4.value),
                receiving_application=str(msh.msh_5.value),
                receiving_facility=str(msh.msh_6.value),
                segments=segments,
                raw_message=hl7_string
            )
            
            logger.info(f"Parsed HL7 message: {message_type} - {message_id}")
            
            return hl7_message
        
        except Exception as e:
            logger.error(f"Failed to parse HL7 message: {e}")
            raise
    
    def extract_prescription_data(self, hl7_message: HL7Message) -> Dict:
        """
        Extract prescription data from RDE^O11 message
        
        Args:
            hl7_message: Parsed HL7 message
        
        Returns:
            Prescription data dictionary
        """
        if hl7_message.message_type != "RDE":
            raise ValueError(f"Expected RDE message, got {hl7_message.message_type}")
        
        prescription_data = {
            "prescription_id": hl7_message.message_id,
            "patient": {},
            "practitioner": {},
            "medications": []
        }
        
        # Extract patient data from PID segment
        pid_segment = self._find_segment(hl7_message.segments, "PID")
        if pid_segment:
            prescription_data["patient"] = self._extract_patient_from_pid(pid_segment)
        
        # Extract practitioner from ORC segment
        orc_segment = self._find_segment(hl7_message.segments, "ORC")
        if orc_segment:
            prescription_data["practitioner"] = self._extract_practitioner_from_orc(orc_segment)
        
        # Extract medications from RXE segments
        rxe_segments = self._find_all_segments(hl7_message.segments, "RXE")
        for rxe in rxe_segments:
            medication = self._extract_medication_from_rxe(rxe)
            prescription_data["medications"].append(medication)
        
        return prescription_data
    
    def _segment_to_dict(self, segment: Segment) -> Dict:
        """Convert HL7 segment to dictionary"""
        segment_dict = {
            "segment_id": segment.name,
            "fields": {}
        }
        
        for i, field in enumerate(segment.children, start=1):
            if field.value:
                segment_dict["fields"][f"{segment.name}_{i}"] = str(field.value)
        
        return segment_dict
    
    def _find_segment(self, segments: List[Dict], segment_id: str) -> Optional[Dict]:
        """Find first segment by ID"""
        for segment in segments:
            if segment["segment_id"] == segment_id:
                return segment
        return None
    
    def _find_all_segments(self, segments: List[Dict], segment_id: str) -> List[Dict]:
        """Find all segments by ID"""
        return [s for s in segments if s["segment_id"] == segment_id]
    
    def _extract_patient_from_pid(self, pid_segment: Dict) -> Dict:
        """Extract patient data from PID segment"""
        fields = pid_segment["fields"]
        
        # Parse name (PID-5)
        name_field = fields.get("PID_5", "")
        name_parts = name_field.split("^")
        
        # Parse address (PID-11)
        address_field = fields.get("PID_11", "")
        address_parts = address_field.split("^")
        
        # Parse phone (PID-13)
        phone_field = fields.get("PID_13", "")
        phone = phone_field.split("^")[-1] if phone_field else None
        
        return {
            "id": fields.get("PID_3", ""),
            "mrn": fields.get("PID_2", ""),
            "last_name": name_parts[0] if len(name_parts) > 0 else "",
            "first_name": name_parts[1] if len(name_parts) > 1 else "",
            "dob": fields.get("PID_7", ""),
            "gender": fields.get("PID_8", "U"),
            "phone": phone,
            "address": {
                "street": address_parts[0] if len(address_parts) > 0 else "",
                "city": address_parts[2] if len(address_parts) > 2 else "",
                "state": address_parts[3] if len(address_parts) > 3 else "",
                "zip": address_parts[4] if len(address_parts) > 4 else ""
            }
        }
    
    def _extract_practitioner_from_orc(self, orc_segment: Dict) -> Dict:
        """Extract practitioner data from ORC segment"""
        fields = orc_segment["fields"]
        
        # Parse ordering provider (ORC-12)
        provider_field = fields.get("ORC_12", "")
        provider_parts = provider_field.split("^")
        
        return {
            "npi": provider_parts[0] if len(provider_parts) > 0 else "",
            "last_name": provider_parts[1] if len(provider_parts) > 1 else "",
            "first_name": provider_parts[2] if len(provider_parts) > 2 else ""
        }
    
    def _extract_medication_from_rxe(self, rxe_segment: Dict) -> Dict:
        """Extract medication data from RXE segment"""
        fields = rxe_segment["fields"]
        
        # Parse medication code (RXE-2)
        med_field = fields.get("RXE_2", "")
        med_parts = med_field.split("^")
        
        return {
            "rxnorm_code": med_parts[0] if len(med_parts) > 0 else "",
            "name": med_parts[1] if len(med_parts) > 1 else "",
            "quantity": fields.get("RXE_3", ""),
            "dosage_instruction": fields.get("RXE_5", ""),
            "dosage_form": fields.get("RXE_6", ""),
            "refills": fields.get("RXE_12", 0)
        }


class HL7Validator:
    """
    Validates HL7 messages
    """
    
    @staticmethod
    def validate_message(hl7_string: str) -> Tuple[bool, List[str]]:
        """
        Validate HL7 message structure
        
        Args:
            hl7_string: HL7 message string
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check basic structure
        if not hl7_string:
            errors.append("Empty message")
            return False, errors
        
        # Check for MSH segment
        if not hl7_string.startswith("MSH"):
            errors.append("Message must start with MSH segment")
        
        # Check for proper segment delimiter
        lines = hl7_string.split("\r")
        if len(lines) < 2:
            errors.append("Message must contain at least 2 segments")
        
        # Validate each segment
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # Check segment format
            if len(line) < 3:
                errors.append(f"Line {i+1}: Segment too short")
                continue
            
            segment_id = line[:3]
            if not segment_id.isupper():
                errors.append(f"Line {i+1}: Invalid segment ID '{segment_id}'")
        
        # Try parsing with hl7apy
        try:
            parse_message(hl7_string, validation_level=consts.VALIDATION_LEVEL.STRICT)
        except Exception as e:
            errors.append(f"Parsing error: {str(e)}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("HL7 message validation passed")
        else:
            logger.warning(f"HL7 message validation failed: {errors}")
        
        return is_valid, errors


class HL7MessageQueue:
    """
    Manages HL7 message queue for async processing
    """
    
    def __init__(self):
        self.queue = []
        self.processed = []
    
    def enqueue(self, hl7_message: str, priority: int = 0) -> str:
        """
        Add message to queue
        
        Args:
            hl7_message: HL7 message string
            priority: Message priority (higher = more urgent)
        
        Returns:
            Message queue ID
        """
        queue_id = f"Q-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        self.queue.append({
            "queue_id": queue_id,
            "message": hl7_message,
            "priority": priority,
            "queued_at": datetime.utcnow(),
            "status": "pending"
        })
        
        # Sort by priority
        self.queue.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(f"Enqueued HL7 message: {queue_id}")
        
        return queue_id
    
    def dequeue(self) -> Optional[Dict]:
        """
        Get next message from queue
        
        Returns:
            Message dictionary or None if queue is empty
        """
        if not self.queue:
            return None
        
        message = self.queue.pop(0)
        message["status"] = "processing"
        message["dequeued_at"] = datetime.utcnow()
        
        logger.info(f"Dequeued HL7 message: {message['queue_id']}")
        
        return message
    
    def mark_processed(self, queue_id: str, success: bool, error_message: Optional[str] = None):
        """
        Mark message as processed
        
        Args:
            queue_id: Queue ID
            success: Whether processing succeeded
            error_message: Error message if failed
        """
        # Find in queue
        message = next((m for m in self.queue if m["queue_id"] == queue_id), None)
        
        if message:
            self.queue.remove(message)
        
        # Add to processed
        if message:
            message["status"] = "success" if success else "error"
            message["processed_at"] = datetime.utcnow()
            message["error_message"] = error_message
            self.processed.append(message)
            
            logger.info(f"Marked message {queue_id} as {message['status']}")
    
    def get_queue_status(self) -> Dict:
        """Get queue statistics"""
        return {
            "pending": len([m for m in self.queue if m["status"] == "pending"]),
            "processing": len([m for m in self.queue if m["status"] == "processing"]),
            "total_processed": len(self.processed),
            "success_count": len([m for m in self.processed if m["status"] == "success"]),
            "error_count": len([m for m in self.processed if m["status"] == "error"])
        }


# Example usage
if __name__ == "__main__":
    # Sample prescription data
    prescription_data = {
        "prescription_id": "RX-20251011-001",
        "patient": {
            "id": "PAT-123",
            "mrn": "MRN-456",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1980-01-15",
            "gender": "male",
            "phone": "5551234567",
            "address": {
                "street": "123 Main St",
                "city": "Boston",
                "state": "MA",
                "zip": "02101"
            }
        },
        "practitioner": {
            "npi": "1234567890",
            "first_name": "Jane",
            "last_name": "Smith"
        },
        "medications": [
            {
                "rxnorm_code": "314076",
                "name": "Lisinopril 10mg",
                "quantity": "30",
                "dosage_instruction": "Take 1 tablet by mouth daily",
                "refills": 3
            }
        ]
    }
    
    # Build HL7 message
    builder = HL7MessageBuilder()
    hl7_message = builder.build_rde_o11_message(prescription_data)
    
    print("Generated HL7 RDE^O11 Message:")
    print(hl7_message)
    print("\n" + "="*50 + "\n")
    
    # Validate message
    validator = HL7Validator()
    is_valid, errors = validator.validate_message(hl7_message)
    print(f"Validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
    if errors:
        print(f"Errors: {errors}")
    
    # Parse message
    parser = HL7Parser()
    parsed_message = parser.parse_message(hl7_message)
    print(f"\nParsed Message Type: {parsed_message.message_type}")
    print(f"Message ID: {parsed_message.message_id}")
    print(f"Segments: {len(parsed_message.segments)}")
    
    # Extract prescription data
    extracted_data = parser.extract_prescription_data(parsed_message)
    print(f"\nExtracted Patient: {extracted_data['patient']['first_name']} {extracted_data['patient']['last_name']}")
    print(f"Medications: {len(extracted_data['medications'])}")