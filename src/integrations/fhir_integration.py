"""
FHIR R4 Integration Service
Implements HL7 FHIR R4 standard for healthcare data exchange
Supports MedicationRequest, Patient, Practitioner, and Organization resources
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import logging
import json

from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner
from fhir.resources.organization import Organization
from fhir.resources.medication import Medication
from fhir.resources.dosage import Dosage
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.identifier import Identifier
from fhir.resources.humanname import HumanName
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.address import Address
from fhir.resources.reference import Reference

logger = logging.getLogger(__name__)


class FHIRResourceBuilder:
    """
    Builds FHIR R4 compliant resources from prescription data
    """
    
    SYSTEM_RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
    SYSTEM_SNOMED = "http://snomed.info/sct"
    SYSTEM_LOINC = "http://loinc.org"
    SYSTEM_ICD10 = "http://hl7.org/fhir/sid/icd-10"
    SYSTEM_NPI = "http://hl7.org/fhir/sid/us-npi"
    
    def __init__(self, organization_id: str = "healthflow-org"):
        """
        Initialize FHIR resource builder
        
        Args:
            organization_id: Organization identifier
        """
        self.organization_id = organization_id
    
    def build_patient_resource(
        self,
        patient_id: str,
        first_name: str,
        last_name: str,
        dob: str,
        gender: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[Dict] = None,
        mrn: Optional[str] = None
    ) -> Patient:
        """
        Build FHIR Patient resource
        
        Args:
            patient_id: Internal patient ID
            first_name: Patient's first name
            last_name: Patient's last name
            dob: Date of birth (YYYY-MM-DD)
            gender: Gender (male/female/other/unknown)
            phone: Phone number
            email: Email address
            address: Address dictionary
            mrn: Medical Record Number
        
        Returns:
            FHIR Patient resource
        """
        # Build identifiers
        identifiers = [
            Identifier(
                system=f"http://healthflow.ai/patient-id",
                value=patient_id,
                use="official"
            )
        ]
        
        if mrn:
            identifiers.append(
                Identifier(
                    system=f"http://healthflow.ai/mrn",
                    value=mrn,
                    type=CodeableConcept(
                        coding=[
                            Coding(
                                system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                code="MR",
                                display="Medical Record Number"
                            )
                        ]
                    )
                )
            )
        
        # Build name
        name = HumanName(
            family=last_name,
            given=[first_name],
            use="official"
        )
        
        # Build contact points
        telecom = []
        if phone:
            telecom.append(
                ContactPoint(
                    system="phone",
                    value=phone,
                    use="mobile"
                )
            )
        if email:
            telecom.append(
                ContactPoint(
                    system="email",
                    value=email,
                    use="home"
                )
            )
        
        # Build address
        addresses = []
        if address:
            addresses.append(
                Address(
                    line=[address.get("street")],
                    city=address.get("city"),
                    state=address.get("state"),
                    postalCode=address.get("zip"),
                    country=address.get("country", "US"),
                    use="home"
                )
            )
        
        # Create Patient resource
        patient = Patient(
            id=patient_id,
            identifier=identifiers,
            name=[name],
            telecom=telecom if telecom else None,
            address=addresses if addresses else None,
            birthDate=dob,
            gender=gender.lower()
        )
        
        return patient
    
    def build_practitioner_resource(
        self,
        practitioner_id: str,
        first_name: str,
        last_name: str,
        npi: str,
        specialty: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Practitioner:
        """
        Build FHIR Practitioner resource
        
        Args:
            practitioner_id: Internal practitioner ID
            first_name: Practitioner's first name
            last_name: Practitioner's last name
            npi: National Provider Identifier
            specialty: Medical specialty
            phone: Phone number
        
        Returns:
            FHIR Practitioner resource
        """
        # Build identifiers
        identifiers = [
            Identifier(
                system=self.SYSTEM_NPI,
                value=npi,
                use="official"
            ),
            Identifier(
                system=f"http://healthflow.ai/practitioner-id",
                value=practitioner_id
            )
        ]
        
        # Build name
        name = HumanName(
            family=last_name,
            given=[first_name],
            prefix=["Dr."],
            use="official"
        )
        
        # Build contact
        telecom = []
        if phone:
            telecom.append(
                ContactPoint(
                    system="phone",
                    value=phone,
                    use="work"
                )
            )
        
        # Build qualification (specialty)
        qualifications = []
        if specialty:
            qualifications.append({
                "code": CodeableConcept(
                    coding=[
                        Coding(
                            system="http://nucc.org/provider-taxonomy",
                            code=self._map_specialty_code(specialty),
                            display=specialty
                        )
                    ]
                )
            })
        
        # Create Practitioner resource
        practitioner = Practitioner(
            id=practitioner_id,
            identifier=identifiers,
            name=[name],
            telecom=telecom if telecom else None,
            qualification=qualifications if qualifications else None
        )
        
        return practitioner
    
    def build_medication_request(
        self,
        request_id: str,
        patient_reference: str,
        practitioner_reference: str,
        medication_name: str,
        medication_code: str,
        dosage_instruction: str,
        quantity: Optional[int] = None,
        refills: Optional[int] = None,
        status: str = "active",
        intent: str = "order",
        notes: Optional[str] = None
    ) -> MedicationRequest:
        """
        Build FHIR MedicationRequest resource
        
        Args:
            request_id: Prescription ID
            patient_reference: Reference to Patient resource
            practitioner_reference: Reference to Practitioner resource
            medication_name: Medication name
            medication_code: RxNorm code
            dosage_instruction: Dosage instructions
            quantity: Quantity to dispense
            refills: Number of refills
            status: Request status
            intent: Request intent
            notes: Additional notes
        
        Returns:
            FHIR MedicationRequest resource
        """
        # Build medication codeable concept
        medication_codeable = CodeableConcept(
            coding=[
                Coding(
                    system=self.SYSTEM_RXNORM,
                    code=medication_code,
                    display=medication_name
                )
            ],
            text=medication_name
        )
        
        # Build dosage instruction
        dosage = [
            Dosage(
                text=dosage_instruction,
                timing={
                    "repeat": {
                        "frequency": 1,
                        "period": 1,
                        "periodUnit": "d"
                    }
                },
                route=CodeableConcept(
                    coding=[
                        Coding(
                            system=self.SYSTEM_SNOMED,
                            code="26643006",
                            display="Oral route"
                        )
                    ]
                )
            )
        ]
        
        # Build dispense request
        dispense_request = {}
        if quantity:
            dispense_request["quantity"] = {
                "value": quantity,
                "unit": "tablet",
                "system": "http://unitsofmeasure.org",
                "code": "{tablet}"
            }
        if refills is not None:
            dispense_request["numberOfRepeatsAllowed"] = refills
        
        # Build note
        note_list = []
        if notes:
            note_list.append({
                "text": notes,
                "authorReference": Reference(reference=practitioner_reference)
            })
        
        # Create MedicationRequest resource
        med_request = MedicationRequest(
            id=request_id,
            status=status,
            intent=intent,
            medicationCodeableConcept=medication_codeable,
            subject=Reference(reference=patient_reference),
            requester=Reference(reference=practitioner_reference),
            authoredOn=datetime.utcnow().isoformat(),
            dosageInstruction=dosage,
            dispenseRequest=dispense_request if dispense_request else None,
            note=note_list if note_list else None
        )
        
        return med_request
    
    def build_bundle(
        self,
        resources: List[Union[Patient, Practitioner, MedicationRequest]],
        bundle_type: str = "transaction"
    ) -> Bundle:
        """
        Build FHIR Bundle containing multiple resources
        
        Args:
            resources: List of FHIR resources
            bundle_type: Bundle type (transaction, collection, etc.)
        
        Returns:
            FHIR Bundle resource
        """
        entries = []
        
        for resource in resources:
            entry = BundleEntry(
                resource=resource.dict(),
                request={
                    "method": "POST",
                    "url": resource.resource_type
                } if bundle_type == "transaction" else None
            )
            entries.append(entry)
        
        bundle = Bundle(
            type=bundle_type,
            entry=entries,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return bundle
    
    def _map_specialty_code(self, specialty: str) -> str:
        """Map specialty name to NUCC taxonomy code"""
        specialty_map = {
            "Family Medicine": "207Q00000X",
            "Internal Medicine": "207R00000X",
            "Pediatrics": "208000000X",
            "Cardiology": "207RC0000X",
            "Dermatology": "207N00000X",
            "Emergency Medicine": "207P00000X",
            "Psychiatry": "2084P0800X"
        }
        return specialty_map.get(specialty, "208D00000X")  # Default: General Practice


class FHIRConverter:
    """
    Converts prescription data to/from FHIR format
    """
    
    def __init__(self):
        self.builder = FHIRResourceBuilder()
    
    def prescription_to_fhir(self, prescription_data: Dict) -> Bundle:
        """
        Convert internal prescription format to FHIR Bundle
        
        Args:
            prescription_data: Prescription data dictionary
        
        Returns:
            FHIR Bundle with Patient, Practitioner, and MedicationRequest
        """
        resources = []
        
        # Build Patient resource
        patient_data = prescription_data.get("patient", {})
        patient = self.builder.build_patient_resource(
            patient_id=patient_data.get("id"),
            first_name=patient_data.get("first_name"),
            last_name=patient_data.get("last_name"),
            dob=patient_data.get("dob"),
            gender=patient_data.get("gender", "unknown"),
            phone=patient_data.get("phone"),
            email=patient_data.get("email"),
            address=patient_data.get("address"),
            mrn=patient_data.get("mrn")
        )
        resources.append(patient)
        
        # Build Practitioner resource
        practitioner_data = prescription_data.get("practitioner", {})
        practitioner = self.builder.build_practitioner_resource(
            practitioner_id=practitioner_data.get("id"),
            first_name=practitioner_data.get("first_name"),
            last_name=practitioner_data.get("last_name"),
            npi=practitioner_data.get("npi"),
            specialty=practitioner_data.get("specialty"),
            phone=practitioner_data.get("phone")
        )
        resources.append(practitioner)
        
        # Build MedicationRequest resources
        for medication in prescription_data.get("medications", []):
            med_request = self.builder.build_medication_request(
                request_id=medication.get("id"),
                patient_reference=f"Patient/{patient_data.get('id')}",
                practitioner_reference=f"Practitioner/{practitioner_data.get('id')}",
                medication_name=medication.get("name"),
                medication_code=medication.get("rxnorm_code"),
                dosage_instruction=medication.get("dosage_instruction"),
                quantity=medication.get("quantity"),
                refills=medication.get("refills"),
                notes=medication.get("notes")
            )
            resources.append(med_request)
        
        # Create Bundle
        bundle = self.builder.build_bundle(resources, bundle_type="transaction")
        
        logger.info(
            f"Converted prescription to FHIR Bundle with {len(resources)} resources"
        )
        
        return bundle
    
    def fhir_to_prescription(self, bundle: Bundle) -> Dict:
        """
        Convert FHIR Bundle to internal prescription format
        
        Args:
            bundle: FHIR Bundle resource
        
        Returns:
            Prescription data dictionary
        """
        prescription_data = {
            "patient": {},
            "practitioner": {},
            "medications": []
        }
        
        # Extract resources from bundle
        for entry in bundle.entry:
            resource = entry.resource
            resource_type = resource.get("resourceType")
            
            if resource_type == "Patient":
                prescription_data["patient"] = self._extract_patient_data(resource)
            
            elif resource_type == "Practitioner":
                prescription_data["practitioner"] = self._extract_practitioner_data(resource)
            
            elif resource_type == "MedicationRequest":
                medication = self._extract_medication_data(resource)
                prescription_data["medications"].append(medication)
        
        logger.info(
            f"Converted FHIR Bundle to prescription with "
            f"{len(prescription_data['medications'])} medications"
        )
        
        return prescription_data
    
    def _extract_patient_data(self, patient_resource: Dict) -> Dict:
        """Extract patient data from FHIR Patient resource"""
        name = patient_resource.get("name", [{}])[0]
        telecom = patient_resource.get("telecom", [])
        address = patient_resource.get("address", [{}])[0]
        
        phone = next((t.get("value") for t in telecom if t.get("system") == "phone"), None)
        email = next((t.get("value") for t in telecom if t.get("system") == "email"), None)
        
        return {
            "id": patient_resource.get("id"),
            "first_name": name.get("given", [""])[0],
            "last_name": name.get("family", ""),
            "dob": patient_resource.get("birthDate"),
            "gender": patient_resource.get("gender"),
            "phone": phone,
            "email": email,
            "address": {
                "street": address.get("line", [""])[0],
                "city": address.get("city"),
                "state": address.get("state"),
                "zip": address.get("postalCode")
            }
        }
    
    def _extract_practitioner_data(self, practitioner_resource: Dict) -> Dict:
        """Extract practitioner data from FHIR Practitioner resource"""
        name = practitioner_resource.get("name", [{}])[0]
        identifiers = practitioner_resource.get("identifier", [])
        telecom = practitioner_resource.get("telecom", [])
        
        npi = next(
            (i.get("value") for i in identifiers 
             if "npi" in i.get("system", "").lower()),
            None
        )
        
        phone = next((t.get("value") for t in telecom if t.get("system") == "phone"), None)
        
        return {
            "id": practitioner_resource.get("id"),
            "first_name": name.get("given", [""])[0],
            "last_name": name.get("family", ""),
            "npi": npi,
            "phone": phone
        }
    
    def _extract_medication_data(self, med_request_resource: Dict) -> Dict:
        """Extract medication data from FHIR MedicationRequest resource"""
        medication_concept = med_request_resource.get("medicationCodeableConcept", {})
        dosage = med_request_resource.get("dosageInstruction", [{}])[0]
        dispense = med_request_resource.get("dispenseRequest", {})
        
        # Extract RxNorm code
        rxnorm_code = None
        for coding in medication_concept.get("coding", []):
            if "rxnorm" in coding.get("system", "").lower():
                rxnorm_code = coding.get("code")
                break
        
        return {
            "id": med_request_resource.get("id"),
            "name": medication_concept.get("text"),
            "rxnorm_code": rxnorm_code,
            "dosage_instruction": dosage.get("text"),
            "quantity": dispense.get("quantity", {}).get("value"),
            "refills": dispense.get("numberOfRepeatsAllowed")
        }


class FHIRValidator:
    """
    Validates FHIR resources
    """
    
    @staticmethod
    def validate_bundle(bundle: Bundle) -> Dict:
        """
        Validate FHIR Bundle
        
        Args:
            bundle: FHIR Bundle to validate
        
        Returns:
            Validation result with errors
        """
        errors = []
        warnings = []
        
        # Check bundle structure
        if not bundle.entry or len(bundle.entry) == 0:
            errors.append("Bundle must contain at least one entry")
        
        # Validate each resource
        for i, entry in enumerate(bundle.entry or []):
            resource = entry.resource
            resource_type = resource.get("resourceType")
            
            if not resource_type:
                errors.append(f"Entry {i}: Missing resourceType")
                continue
            
            # Resource-specific validation
            if resource_type == "Patient":
                patient_errors = FHIRValidator._validate_patient(resource)
                errors.extend([f"Patient: {e}" for e in patient_errors])
            
            elif resource_type == "Practitioner":
                pract_errors = FHIRValidator._validate_practitioner(resource)
                errors.extend([f"Practitioner: {e}" for e in pract_errors])
            
            elif resource_type == "MedicationRequest":
                med_errors = FHIRValidator._validate_medication_request(resource)
                errors.extend([f"MedicationRequest: {e}" for e in med_errors])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def _validate_patient(resource: Dict) -> List[str]:
        """Validate Patient resource"""
        errors = []
        
        if not resource.get("name"):
            errors.append("Missing required field: name")
        if not resource.get("birthDate"):
            errors.append("Missing required field: birthDate")
        
        return errors
    
    @staticmethod
    def _validate_practitioner(resource: Dict) -> List[str]:
        """Validate Practitioner resource"""
        errors = []
        
        if not resource.get("name"):
            errors.append("Missing required field: name")
        if not resource.get("identifier"):
            errors.append("Missing required field: identifier")
        
        return errors
    
    @staticmethod
    def _validate_medication_request(resource: Dict) -> List[str]:
        """Validate MedicationRequest resource"""
        errors = []
        
        if not resource.get("subject"):
            errors.append("Missing required field: subject")
        if not resource.get("medicationCodeableConcept"):
            errors.append("Missing required field: medicationCodeableConcept")
        if not resource.get("dosageInstruction"):
            errors.append("Missing required field: dosageInstruction")
        
        return errors


# Example usage
if __name__ == "__main__":
    # Sample prescription data
    prescription_data = {
        "patient": {
            "id": "patient-123",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1980-01-15",
            "gender": "male",
            "phone": "555-1234",
            "email": "john.doe@email.com",
            "mrn": "MRN123456"
        },
        "practitioner": {
            "id": "pract-456",
            "first_name": "Jane",
            "last_name": "Smith",
            "npi": "1234567890",
            "specialty": "Family Medicine",
            "phone": "555-5678"
        },
        "medications": [
            {
                "id": "med-req-789",
                "name": "Lisinopril 10mg",
                "rxnorm_code": "314076",
                "dosage_instruction": "Take 1 tablet by mouth daily",
                "quantity": 30,
                "refills": 3
            }
        ]
    }
    
    # Convert to FHIR
    converter = FHIRConverter()
    fhir_bundle = converter.prescription_to_fhir(prescription_data)
    
    # Validate
    validator = FHIRValidator()
    validation_result = validator.validate_bundle(fhir_bundle)
    
    print(f"FHIR Validation: {'✓ Valid' if validation_result['valid'] else '✗ Invalid'}")
    if validation_result['errors']:
        print(f"Errors: {validation_result['errors']}")
    
    # Export as JSON
    fhir_json = fhir_bundle.json(indent=2)
    print("\nFHIR Bundle JSON:")
    print(fhir_json[:500] + "...")