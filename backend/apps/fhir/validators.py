"""
FHIR R4 conformance validation utilities.
Validates resources against FHIR R4 profile requirements.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("apps.fhir")

# LOINC pattern: digits optionally followed by hyphen and digit
LOINC_PATTERN = re.compile(r"^\d{1,5}-\d$")
# ICD-10-CM pattern
ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$")
# RxNorm pattern (numeric)
RXNORM_PATTERN = re.compile(r"^\d+$")
# CVX pattern (numeric)
CVX_PATTERN = re.compile(r"^\d{1,3}$")


class FHIRValidationError(Exception):
    """Raised when a FHIR resource fails validation."""

    def __init__(self, errors: List[Dict]):
        self.errors = errors
        super().__init__(f"FHIR validation failed: {errors}")


def validate_fhir_patient(data: Dict) -> Tuple[bool, List[Dict]]:
    """Validate a FHIR Patient resource dictionary."""
    errors = []

    if data.get("resourceType") != "Patient":
        errors.append({"path": "resourceType", "message": "Must be 'Patient'"})

    if not data.get("id"):
        errors.append({"path": "id", "message": "Patient.id is required"})

    # Validate name
    names = data.get("name", [])
    if not names:
        errors.append({"path": "name", "message": "At least one name is required"})
    else:
        for i, name in enumerate(names):
            if not name.get("family") and not name.get("given"):
                errors.append({"path": f"name[{i}]", "message": "Name must have family or given"})

    # Validate birthDate format
    birth_date = data.get("birthDate")
    if birth_date:
        if not re.match(r"^\d{4}(-\d{2}(-\d{2})?)?$", birth_date):
            errors.append({"path": "birthDate", "message": "birthDate must be in YYYY, YYYY-MM, or YYYY-MM-DD format"})

    # Validate gender
    if data.get("gender") and data["gender"] not in ("male", "female", "other", "unknown"):
        errors.append({"path": "gender", "message": "gender must be male|female|other|unknown"})

    return len(errors) == 0, errors


def validate_fhir_observation(data: Dict) -> Tuple[bool, List[Dict]]:
    """Validate a FHIR Observation resource."""
    errors = []

    if data.get("resourceType") != "Observation":
        errors.append({"path": "resourceType", "message": "Must be 'Observation'"})

    required_fields = ["status", "code", "subject"]
    for field in required_fields:
        if not data.get(field):
            errors.append({"path": field, "message": f"Observation.{field} is required"})

    valid_statuses = ("registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error")
    if data.get("status") and data["status"] not in valid_statuses:
        errors.append({"path": "status", "message": f"status must be one of {valid_statuses}"})

    # Validate that value or dataAbsentReason is present
    has_value = any(k.startswith("value") for k in data.keys())
    has_absent_reason = "dataAbsentReason" in data
    has_components = data.get("component")
    if not has_value and not has_absent_reason and not has_components:
        errors.append({
            "path": "value[x]",
            "message": "Either a value, dataAbsentReason, or component must be present",
        })

    return len(errors) == 0, errors


def validate_fhir_condition(data: Dict) -> Tuple[bool, List[Dict]]:
    """Validate a FHIR Condition resource."""
    errors = []

    if data.get("resourceType") != "Condition":
        errors.append({"path": "resourceType", "message": "Must be 'Condition'"})

    if not data.get("subject"):
        errors.append({"path": "subject", "message": "Condition.subject is required"})

    if not data.get("code"):
        errors.append({"path": "code", "message": "Condition.code is required"})

    # Validate ICD-10 if provided
    codings = data.get("code", {}).get("coding", [])
    for coding in codings:
        if "icd" in coding.get("system", "").lower():
            code_val = coding.get("code", "")
            if code_val and not ICD10_PATTERN.match(code_val):
                errors.append({"path": "code.coding.code", "message": f"ICD-10 code format invalid: {code_val}"})

    return len(errors) == 0, errors


def validate_fhir_medication_request(data: Dict) -> Tuple[bool, List[Dict]]:
    """Validate a FHIR MedicationRequest resource."""
    errors = []

    if data.get("resourceType") != "MedicationRequest":
        errors.append({"path": "resourceType", "message": "Must be 'MedicationRequest'"})

    for field in ("status", "intent", "subject"):
        if not data.get(field):
            errors.append({"path": field, "message": f"MedicationRequest.{field} is required"})

    if not data.get("medication") and not data.get("medicationCodeableConcept") and not data.get("medicationReference"):
        errors.append({"path": "medication[x]", "message": "medication[x] is required"})

    return len(errors) == 0, errors


def validate_fhir_resource(resource_type: str, data: Dict) -> Tuple[bool, List[Dict]]:
    """
    Entry point: dispatch to the appropriate FHIR resource validator.
    Returns (is_valid, errors_list).
    """
    validators = {
        "Patient": validate_fhir_patient,
        "Observation": validate_fhir_observation,
        "Condition": validate_fhir_condition,
        "MedicationRequest": validate_fhir_medication_request,
    }

    validator = validators.get(resource_type)
    if validator is None:
        # For resource types without specific validators, do basic check
        if data.get("resourceType") != resource_type:
            return False, [{"path": "resourceType", "message": f"Expected {resource_type}"}]
        return True, []

    return validator(data)
