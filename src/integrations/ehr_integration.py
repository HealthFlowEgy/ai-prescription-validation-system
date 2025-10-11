"""
EHR (Electronic Health Record) Integration Service
Supports Epic, Cerner, and Allscripts EHR systems
Implements OAuth2 authentication and SMART on FHIR
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import requests
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EHRAuthenticator:
    """
    Handles OAuth2 authentication for EHR systems
    Implements SMART on FHIR authorization flow
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ):
        """
        Initialize EHR authenticator
        
        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
    
    def get_authorization_url(
        self,
        authorization_endpoint: str,
        scope: str = "patient/*.read"
    ) -> str:
        """
        Generate OAuth2 authorization URL
        
        Args:
            authorization_endpoint: EHR authorization endpoint
            scope: OAuth2 scope (SMART on FHIR scopes)
        
        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": self._generate_state(),
            "aud": authorization_endpoint
        }
        
        url = f"{authorization_endpoint}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        
        return url
    
    def exchange_code_for_token(
        self,
        token_endpoint: str,
        authorization_code: str
    ) -> Dict:
        """
        Exchange authorization code for access token
        
        Args:
            token_endpoint: EHR token endpoint
            authorization_code: Authorization code from callback
        
        Returns:
            Token response dictionary
        """
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        
        # Calculate token expiration
        expires_in = token_data.get("expires_in", 3600)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        logger.info("Successfully exchanged authorization code for access token")
        
        return token_data
    
    def refresh_access_token(self, token_endpoint: str) -> Dict:
        """
        Refresh access token using refresh token
        
        Args:
            token_endpoint: EHR token endpoint
        
        Returns:
            New token data
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        self.access_token = token_data.get("access_token")
        
        # Update expiration
        expires_in = token_data.get("expires_in", 3600)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        logger.info("Successfully refreshed access token")
        
        return token_data
    
    def is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.token_expires_at:
            return True
        
        return datetime.utcnow() >= self.token_expires_at
    
    def get_access_token(self, token_endpoint: str) -> str:
        """
        Get valid access token, refreshing if necessary
        
        Args:
            token_endpoint: EHR token endpoint
        
        Returns:
            Valid access token
        """
        if self.is_token_expired() and self.refresh_token:
            self.refresh_access_token(token_endpoint)
        
        return self.access_token
    
    @staticmethod
    def _generate_state() -> str:
        """Generate random state parameter"""
        import secrets
        return secrets.token_urlsafe(32)


class EHRConnector(ABC):
    """
    Abstract base class for EHR system connectors
    """
    
    def __init__(
        self,
        base_url: str,
        authenticator: EHRAuthenticator
    ):
        """
        Initialize EHR connector
        
        Args:
            base_url: EHR system base URL
            authenticator: EHR authenticator instance
        """
        self.base_url = base_url.rstrip("/")
        self.authenticator = authenticator
    
    @abstractmethod
    def get_patient(self, patient_id: str) -> Dict:
        """Get patient information"""
        pass
    
    @abstractmethod
    def get_medications(self, patient_id: str) -> List[Dict]:
        """Get patient's current medications"""
        pass
    
    @abstractmethod
    def create_prescription(self, prescription_data: Dict) -> Dict:
        """Create new prescription order"""
        pass
    
    @abstractmethod
    def get_prescription_status(self, prescription_id: str) -> Dict:
        """Get prescription status"""
        pass
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Make authenticated API request to EHR system
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Authorization": f"Bearer {self.authenticator.access_token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"EHR API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in EHR request: {e}")
            raise


class EpicConnector(EHRConnector):
    """
    Epic EHR system connector
    Uses Epic's FHIR API
    """
    
    def __init__(
        self,
        base_url: str,
        authenticator: EHRAuthenticator
    ):
        super().__init__(base_url, authenticator)
        self.fhir_version = "R4"
    
    def get_patient(self, patient_id: str) -> Dict:
        """
        Get patient information from Epic
        
        Args:
            patient_id: Epic patient ID (FHIR ID)
        
        Returns:
            FHIR Patient resource
        """
        endpoint = f"Patient/{patient_id}"
        patient_data = self._make_request("GET", endpoint)
        
        logger.info(f"Retrieved patient {patient_id} from Epic")
        
        return patient_data
    
    def get_medications(self, patient_id: str) -> List[Dict]:
        """
        Get patient's current medications from Epic
        
        Args:
            patient_id: Epic patient ID
        
        Returns:
            List of FHIR MedicationRequest resources
        """
        endpoint = "MedicationRequest"
        params = {
            "patient": patient_id,
            "status": "active",
            "_count": 100
        }
        
        response = self._make_request("GET", endpoint, params=params)
        
        medications = []
        if response.get("entry"):
            medications = [entry["resource"] for entry in response["entry"]]
        
        logger.info(f"Retrieved {len(medications)} medications for patient {patient_id}")
        
        return medications
    
    def create_prescription(self, prescription_data: Dict) -> Dict:
        """
        Create new prescription in Epic
        
        Args:
            prescription_data: FHIR MedicationRequest resource
        
        Returns:
            Created resource with ID
        """
        endpoint = "MedicationRequest"
        
        response = self._make_request("POST", endpoint, data=prescription_data)
        
        logger.info(f"Created prescription in Epic: {response.get('id')}")
        
        return response
    
    def get_prescription_status(self, prescription_id: str) -> Dict:
        """
        Get prescription status from Epic
        
        Args:
            prescription_id: Epic prescription ID
        
        Returns:
            FHIR MedicationRequest resource
        """
        endpoint = f"MedicationRequest/{prescription_id}"
        
        prescription = self._make_request("GET", endpoint)
        
        return {
            "prescription_id": prescription.get("id"),
            "status": prescription.get("status"),
            "authored_on": prescription.get("authoredOn"),
            "medication": prescription.get("medicationCodeableConcept", {}).get("text")
        }
    
    def get_allergies(self, patient_id: str) -> List[Dict]:
        """
        Get patient allergies from Epic
        
        Args:
            patient_id: Epic patient ID
        
        Returns:
            List of FHIR AllergyIntolerance resources
        """
        endpoint = "AllergyIntolerance"
        params = {
            "patient": patient_id,
            "_count": 100
        }
        
        response = self._make_request("GET", endpoint, params=params)
        
        allergies = []
        if response.get("entry"):
            allergies = [entry["resource"] for entry in response["entry"]]
        
        logger.info(f"Retrieved {len(allergies)} allergies for patient {patient_id}")
        
        return allergies
    
    def get_conditions(self, patient_id: str) -> List[Dict]:
        """
        Get patient conditions/diagnoses from Epic
        
        Args:
            patient_id: Epic patient ID
        
        Returns:
            List of FHIR Condition resources
        """
        endpoint = "Condition"
        params = {
            "patient": patient_id,
            "clinical-status": "active",
            "_count": 100
        }
        
        response = self._make_request("GET", endpoint, params=params)
        
        conditions = []
        if response.get("entry"):
            conditions = [entry["resource"] for entry in response["entry"]]
        
        logger.info(f"Retrieved {len(conditions)} conditions for patient {patient_id}")
        
        return conditions


class CernerConnector(EHRConnector):
    """
    Cerner EHR system connector
    Uses Cerner's FHIR API
    """
    
    def __init__(
        self,
        base_url: str,
        authenticator: EHRAuthenticator
    ):
        super().__init__(base_url, authenticator)
        self.fhir_version = "R4"
    
    def get_patient(self, patient_id: str) -> Dict:
        """Get patient from Cerner"""
        endpoint = f"Patient/{patient_id}"
        return self._make_request("GET", endpoint)
    
    def get_medications(self, patient_id: str) -> List[Dict]:
        """Get medications from Cerner"""
        endpoint = "MedicationRequest"
        params = {
            "patient": patient_id,
            "status": "active"
        }
        
        response = self._make_request("GET", endpoint, params=params)
        
        medications = []
        if response.get("entry"):
            medications = [entry["resource"] for entry in response["entry"]]
        
        return medications
    
    def create_prescription(self, prescription_data: Dict) -> Dict:
        """Create prescription in Cerner"""
        endpoint = "MedicationRequest"
        return self._make_request("POST", endpoint, data=prescription_data)
    
    def get_prescription_status(self, prescription_id: str) -> Dict:
        """Get prescription status from Cerner"""
        endpoint = f"MedicationRequest/{prescription_id}"
        prescription = self._make_request("GET", endpoint)
        
        return {
            "prescription_id": prescription.get("id"),
            "status": prescription.get("status"),
            "authored_on": prescription.get("authoredOn")
        }


class AllscriptsConnector(EHRConnector):
    """
    Allscripts EHR system connector
    Uses Allscripts' proprietary API (adapts to FHIR)
    """
    
    def __init__(
        self,
        base_url: str,
        authenticator: EHRAuthenticator,
        app_name: str
    ):
        super().__init__(base_url, authenticator)
        self.app_name = app_name
    
    def get_patient(self, patient_id: str) -> Dict:
        """Get patient from Allscripts"""
        # Allscripts uses different endpoint structure
        endpoint = f"fhir/Patient/{patient_id}"
        return self._make_request("GET", endpoint)
    
    def get_medications(self, patient_id: str) -> List[Dict]:
        """Get medications from Allscripts"""
        endpoint = "fhir/MedicationRequest"
        params = {
            "patient": patient_id,
            "status": "active"
        }
        
        response = self._make_request("GET", endpoint, params=params)
        
        medications = []
        if response.get("entry"):
            medications = [entry["resource"] for entry in response["entry"]]
        
        return medications
    
    def create_prescription(self, prescription_data: Dict) -> Dict:
        """Create prescription in Allscripts"""
        endpoint = "fhir/MedicationRequest"
        return self._make_request("POST", endpoint, data=prescription_data)
    
    def get_prescription_status(self, prescription_id: str) -> Dict:
        """Get prescription status from Allscripts"""
        endpoint = f"fhir/MedicationRequest/{prescription_id}"
        prescription = self._make_request("GET", endpoint)
        
        return {
            "prescription_id": prescription.get("id"),
            "status": prescription.get("status")
        }


class EHRIntegrationService:
    """
    Manages connections to multiple EHR systems
    """
    
    def __init__(self):
        self.connectors: Dict[str, EHRConnector] = {}
    
    def register_connector(self, ehr_system: str, connector: EHRConnector):
        """
        Register EHR connector
        
        Args:
            ehr_system: EHR system name (epic, cerner, allscripts)
            connector: EHR connector instance
        """
        self.connectors[ehr_system.lower()] = connector
        logger.info(f"Registered {ehr_system} connector")
    
    def get_connector(self, ehr_system: str) -> EHRConnector:
        """
        Get EHR connector by system name
        
        Args:
            ehr_system: EHR system name
        
        Returns:
            EHR connector instance
        """
        connector = self.connectors.get(ehr_system.lower())
        
        if not connector:
            raise ValueError(f"No connector registered for EHR system: {ehr_system}")
        
        return connector
    
    def get_patient_context(
        self,
        ehr_system: str,
        patient_id: str
    ) -> Dict:
        """
        Get comprehensive patient context from EHR
        
        Args:
            ehr_system: EHR system name
            patient_id: Patient ID in EHR system
        
        Returns:
            Patient context with demographics, medications, allergies, conditions
        """
        connector = self.get_connector(ehr_system)
        
        try:
            # Get patient demographics
            patient = connector.get_patient(patient_id)
            
            # Get current medications
            medications = connector.get_medications(patient_id)
            
            # Get allergies (if supported)
            allergies = []
            if hasattr(connector, 'get_allergies'):
                try:
                    allergies = connector.get_allergies(patient_id)
                except:
                    logger.warning(f"Could not retrieve allergies for patient {patient_id}")
            
            # Get conditions (if supported)
            conditions = []
            if hasattr(connector, 'get_conditions'):
                try:
                    conditions = connector.get_conditions(patient_id)
                except:
                    logger.warning(f"Could not retrieve conditions for patient {patient_id}")
            
            context = {
                "patient": self._extract_patient_summary(patient),
                "current_medications": self._extract_medication_summaries(medications),
                "allergies": self._extract_allergy_summaries(allergies),
                "conditions": self._extract_condition_summaries(conditions),
                "retrieved_at": datetime.utcnow().isoformat(),
                "source_ehr": ehr_system
            }
            
            logger.info(
                f"Retrieved patient context from {ehr_system} for patient {patient_id}: "
                f"{len(medications)} medications, {len(allergies)} allergies, "
                f"{len(conditions)} conditions"
            )
            
            return context
        
        except Exception as e:
            logger.error(f"Failed to get patient context from {ehr_system}: {e}")
            raise
    
    def sync_prescription(
        self,
        ehr_system: str,
        prescription_data: Dict
    ) -> Dict:
        """
        Sync prescription to EHR system
        
        Args:
            ehr_system: Target EHR system
            prescription_data: Prescription data in FHIR format
        
        Returns:
            Sync result with EHR prescription ID
        """
        connector = self.get_connector(ehr_system)
        
        try:
            result = connector.create_prescription(prescription_data)
            
            sync_result = {
                "success": True,
                "ehr_system": ehr_system,
                "ehr_prescription_id": result.get("id"),
                "status": result.get("status"),
                "synced_at": datetime.utcnow().isoformat()
            }
            
            logger.info(
                f"Successfully synced prescription to {ehr_system}: "
                f"{sync_result['ehr_prescription_id']}"
            )
            
            return sync_result
        
        except Exception as e:
            logger.error(f"Failed to sync prescription to {ehr_system}: {e}")
            
            return {
                "success": False,
                "ehr_system": ehr_system,
                "error": str(e),
                "synced_at": datetime.utcnow().isoformat()
            }
    
    def check_prescription_status(
        self,
        ehr_system: str,
        prescription_id: str
    ) -> Dict:
        """
        Check prescription status in EHR
        
        Args:
            ehr_system: EHR system name
            prescription_id: Prescription ID in EHR system
        
        Returns:
            Prescription status
        """
        connector = self.get_connector(ehr_system)
        
        try:
            status = connector.get_prescription_status(prescription_id)
            
            logger.info(
                f"Retrieved prescription status from {ehr_system}: "
                f"{prescription_id} - {status.get('status')}"
            )
            
            return status
        
        except Exception as e:
            logger.error(f"Failed to get prescription status from {ehr_system}: {e}")
            raise
    
    @staticmethod
    def _extract_patient_summary(patient_resource: Dict) -> Dict:
        """Extract key patient information from FHIR Patient resource"""
        name = patient_resource.get("name", [{}])[0]
        
        return {
            "id": patient_resource.get("id"),
            "first_name": name.get("given", [""])[0],
            "last_name": name.get("family", ""),
            "dob": patient_resource.get("birthDate"),
            "gender": patient_resource.get("gender"),
            "mrn": next(
                (i.get("value") for i in patient_resource.get("identifier", [])
                 if i.get("type", {}).get("coding", [{}])[0].get("code") == "MR"),
                None
            )
        }
    
    @staticmethod
    def _extract_medication_summaries(medication_resources: List[Dict]) -> List[Dict]:
        """Extract medication summaries from FHIR MedicationRequest resources"""
        summaries = []
        
        for med_resource in medication_resources:
            medication = med_resource.get("medicationCodeableConcept", {})
            
            summaries.append({
                "name": medication.get("text", "Unknown"),
                "code": medication.get("coding", [{}])[0].get("code"),
                "status": med_resource.get("status"),
                "dosage": med_resource.get("dosageInstruction", [{}])[0].get("text", "")
            })
        
        return summaries
    
    @staticmethod
    def _extract_allergy_summaries(allergy_resources: List[Dict]) -> List[str]:
        """Extract allergy names from FHIR AllergyIntolerance resources"""
        allergies = []
        
        for allergy_resource in allergy_resources:
            code = allergy_resource.get("code", {})
            allergy_name = code.get("text") or code.get("coding", [{}])[0].get("display", "Unknown")
            allergies.append(allergy_name)
        
        return allergies
    
    @staticmethod
    def _extract_condition_summaries(condition_resources: List[Dict]) -> List[Dict]:
        """Extract condition summaries from FHIR Condition resources"""
        conditions = []
        
        for condition_resource in condition_resources:
            code = condition_resource.get("code", {})
            
            conditions.append({
                "name": code.get("text", "Unknown"),
                "code": code.get("coding", [{}])[0].get("code"),
                "status": condition_resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
            })
        
        return conditions
    
    def list_registered_connectors(self) -> List[str]:
        """Get list of registered EHR systems"""
        return list(self.connectors.keys())


class EHRSyncScheduler:
    """
    Schedules periodic syncing with EHR systems
    """
    
    def __init__(self, integration_service: EHRIntegrationService):
        self.integration_service = integration_service
        self.sync_jobs = []
    
    def schedule_sync(
        self,
        prescription_id: str,
        ehr_system: str,
        prescription_data: Dict,
        retry_count: int = 3
    ) -> str:
        """
        Schedule prescription sync to EHR
        
        Args:
            prescription_id: Internal prescription ID
            ehr_system: Target EHR system
            prescription_data: FHIR prescription data
            retry_count: Number of retry attempts
        
        Returns:
            Job ID
        """
        job_id = f"sync-{prescription_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        job = {
            "job_id": job_id,
            "prescription_id": prescription_id,
            "ehr_system": ehr_system,
            "prescription_data": prescription_data,
            "retry_count": retry_count,
            "attempts": 0,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "last_attempt_at": None,
            "result": None
        }
        
        self.sync_jobs.append(job)
        
        logger.info(f"Scheduled sync job {job_id} for {ehr_system}")
        
        return job_id
    
    def process_sync_jobs(self) -> Dict:
        """
        Process pending sync jobs
        
        Returns:
            Processing summary
        """
        pending_jobs = [j for j in self.sync_jobs if j["status"] == "pending"]
        
        results = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "retrying": 0
        }
        
        for job in pending_jobs:
            job["attempts"] += 1
            job["last_attempt_at"] = datetime.utcnow()
            
            try:
                # Attempt sync
                result = self.integration_service.sync_prescription(
                    job["ehr_system"],
                    job["prescription_data"]
                )
                
                if result["success"]:
                    job["status"] = "completed"
                    job["result"] = result
                    results["succeeded"] += 1
                    logger.info(f"Sync job {job['job_id']} completed successfully")
                else:
                    raise Exception(result.get("error", "Unknown error"))
            
            except Exception as e:
                logger.error(f"Sync job {job['job_id']} failed: {e}")
                
                # Check if should retry
                if job["attempts"] < job["retry_count"]:
                    job["status"] = "pending"
                    results["retrying"] += 1
                    logger.info(
                        f"Will retry sync job {job['job_id']} "
                        f"(attempt {job['attempts']}/{job['retry_count']})"
                    )
                else:
                    job["status"] = "failed"
                    job["result"] = {"error": str(e)}
                    results["failed"] += 1
                    logger.error(f"Sync job {job['job_id']} failed after {job['attempts']} attempts")
            
            results["processed"] += 1
        
        return results
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get sync job status"""
        job = next((j for j in self.sync_jobs if j["job_id"] == job_id), None)
        
        if not job:
            return None
        
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "attempts": job["attempts"],
            "created_at": job["created_at"].isoformat(),
            "last_attempt_at": job["last_attempt_at"].isoformat() if job["last_attempt_at"] else None,
            "result": job["result"]
        }


# Example usage
if __name__ == "__main__":
    # Initialize authenticators for different EHR systems
    epic_auth = EHRAuthenticator(
        client_id="epic_client_id",
        client_secret="epic_client_secret",
        redirect_uri="https://healthflow.ai/oauth/callback"
    )
    
    cerner_auth = EHRAuthenticator(
        client_id="cerner_client_id",
        client_secret="cerner_client_secret",
        redirect_uri="https://healthflow.ai/oauth/callback"
    )
    
    # Initialize connectors
    epic_connector = EpicConnector(
        base_url="https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        authenticator=epic_auth
    )
    
    cerner_connector = CernerConnector(
        base_url="https://fhir-myrecord.cerner.com/r4",
        authenticator=cerner_auth
    )
    
    # Initialize integration service
    ehr_service = EHRIntegrationService()
    ehr_service.register_connector("epic", epic_connector)
    ehr_service.register_connector("cerner", cerner_connector)
    
    print(f"Registered EHR connectors: {ehr_service.list_registered_connectors()}")
    
    # Example: Get patient context
    # patient_context = ehr_service.get_patient_context(
    #     ehr_system="epic",
    #     patient_id="eWRhTEW.fhir"
    # )
    
    # Example: Sync prescription
    # prescription_fhir = {...}  # FHIR MedicationRequest
    # sync_result = ehr_service.sync_prescription(
    #     ehr_system="epic",
    #     prescription_data=prescription_fhir
    # )
    
    print("\nEHR Integration Service initialized successfully")