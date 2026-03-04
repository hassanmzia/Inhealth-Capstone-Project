"""
FHIRService — helper methods for creating, reading, and updating FHIR resources.
Provides a clean service layer between views and models.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Type

from django.db import transaction
from django.utils import timezone

from .models import (
    FHIRAllergyIntolerance,
    FHIRAppointment,
    FHIRCarePlan,
    FHIRCondition,
    FHIRDiagnosticReport,
    FHIRDocumentReference,
    FHIREncounter,
    FHIRImmunization,
    FHIRMedicationRequest,
    FHIRObservation,
    FHIRPatient,
    FHIRProcedure,
)
from .validators import FHIRValidationError, validate_fhir_resource

logger = logging.getLogger("apps.fhir")


class FHIRService:
    """
    Service layer for FHIR R4 resource operations.
    Handles validation, persistence, and FHIR JSON serialization.
    """

    RESOURCE_MODEL_MAP = {
        "Patient": FHIRPatient,
        "Observation": FHIRObservation,
        "Condition": FHIRCondition,
        "MedicationRequest": FHIRMedicationRequest,
        "DiagnosticReport": FHIRDiagnosticReport,
        "Appointment": FHIRAppointment,
        "CarePlan": FHIRCarePlan,
        "AllergyIntolerance": FHIRAllergyIntolerance,
        "Encounter": FHIREncounter,
        "Procedure": FHIRProcedure,
        "Immunization": FHIRImmunization,
        "DocumentReference": FHIRDocumentReference,
    }

    def __init__(self, tenant):
        self.tenant = tenant

    def validate(self, resource_type: str, data: Dict) -> None:
        """Validate a FHIR resource; raises FHIRValidationError on failure."""
        from django.conf import settings
        if not getattr(settings, "FHIR_VALIDATION_ENABLED", True):
            return
        is_valid, errors = validate_fhir_resource(resource_type, data)
        if not is_valid:
            raise FHIRValidationError(errors)

    def get_model(self, resource_type: str) -> Type:
        model = self.RESOURCE_MODEL_MAP.get(resource_type)
        if model is None:
            raise ValueError(f"Unsupported FHIR resource type: {resource_type}")
        return model

    def get_resource(self, resource_type: str, resource_id: str):
        """Retrieve a single FHIR resource by ID within the current tenant."""
        model = self.get_model(resource_type)
        try:
            return model.objects.get(fhir_id=resource_id, tenant=self.tenant)
        except model.DoesNotExist:
            return None

    def search_resources(self, resource_type: str, params: Dict) -> Any:
        """Search FHIR resources with parameter filtering."""
        model = self.get_model(resource_type)
        qs = model.objects.filter(tenant=self.tenant)

        # Apply common search params
        if "patient" in params:
            qs = qs.filter(patient__fhir_id=params["patient"])
        if "_count" in params:
            qs = qs[:int(params["_count"])]

        return qs

    def create_patient_from_fhir(self, fhir_json: Dict) -> FHIRPatient:
        """Create a FHIRPatient from a FHIR JSON Patient resource."""
        self.validate("Patient", fhir_json)

        # Extract name
        name = fhir_json.get("name", [{}])[0]
        given = name.get("given", [""])
        family = name.get("family", "")

        # Extract identifiers
        mrn = ""
        for identifier in fhir_json.get("identifier", []):
            if "MR" in identifier.get("type", {}).get("coding", [{}])[0].get("code", ""):
                mrn = identifier.get("value", "")
                break
        if not mrn:
            mrn = fhir_json.get("id", str(uuid.uuid4()))[:20]

        # Extract address
        address = fhir_json.get("address", [{}])[0]
        lines = address.get("line", ["", ""])

        patient = FHIRPatient.objects.create(
            tenant=self.tenant,
            fhir_id=fhir_json.get("id", str(uuid.uuid4())),
            mrn=mrn,
            first_name=given[0] if given else "",
            last_name=family,
            middle_name=given[1] if len(given) > 1 else "",
            birth_date=fhir_json.get("birthDate"),
            gender=fhir_json.get("gender", "unknown"),
            active=fhir_json.get("active", True),
            address_line1=lines[0] if lines else "",
            address_line2=lines[1] if len(lines) > 1 else "",
            city=address.get("city", ""),
            state=address.get("state", ""),
            postal_code=address.get("postalCode", ""),
            country=address.get("country", "US"),
            telecom=fhir_json.get("telecom", []),
            communication=fhir_json.get("communication", []),
            raw_resource=fhir_json,
        )
        logger.info(f"Created FHIRPatient {patient.fhir_id} in tenant {self.tenant.slug}")
        return patient

    def create_observation_from_fhir(self, fhir_json: Dict, patient: FHIRPatient) -> FHIRObservation:
        """Create a FHIRObservation from a FHIR JSON Observation resource."""
        self.validate("Observation", fhir_json)

        code_cc = fhir_json.get("code", {})
        coding = code_cc.get("coding", [{}])[0]
        value_quantity = fhir_json.get("valueQuantity", {})
        ref_range = fhir_json.get("referenceRange", [{}])[0]

        effective = fhir_json.get("effectiveDateTime") or fhir_json.get("effectivePeriod", {}).get("start")

        obs = FHIRObservation.objects.create(
            tenant=self.tenant,
            fhir_id=fhir_json.get("id", str(uuid.uuid4())),
            patient=patient,
            status=fhir_json.get("status", "final"),
            code_system=coding.get("system", "http://loinc.org"),
            code=coding.get("code", ""),
            display=coding.get("display", code_cc.get("text", "")),
            value_quantity=value_quantity.get("value"),
            value_unit=value_quantity.get("unit", ""),
            value_string=fhir_json.get("valueString", ""),
            reference_range_low=ref_range.get("low", {}).get("value"),
            reference_range_high=ref_range.get("high", {}).get("value"),
            effective_datetime=effective or timezone.now(),
            components=fhir_json.get("component", []),
            raw_resource=fhir_json,
        )
        return obs

    def build_fhir_bundle(self, resource_type: str, resources: list, total: int, base_url: str) -> Dict:
        """Build a FHIR Bundle (searchset) response."""
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": {"lastUpdated": timezone.now().isoformat()},
            "type": "searchset",
            "total": total,
            "link": [{"relation": "self", "url": f"{base_url}/{resource_type}"}],
            "entry": [
                {
                    "fullUrl": f"{base_url}/{resource_type}/{r.fhir_id}",
                    "resource": r.raw_resource or {"resourceType": resource_type, "id": r.fhir_id},
                }
                for r in resources
            ],
        }

    def build_operation_outcome(self, severity: str, code: str, details: str) -> Dict:
        """Build a FHIR OperationOutcome for error responses."""
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": severity,
                    "code": code,
                    "details": {"text": details},
                }
            ],
        }
