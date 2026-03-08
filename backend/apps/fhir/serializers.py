"""
FHIR R4 serializers for all resource types.
Returns proper FHIR JSON format in API responses.
"""

from rest_framework import serializers

from .models import (
    AgentActionLog,
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


class FHIRPatientSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()
    id = serializers.CharField(source="fhir_id", read_only=True)
    name = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    age = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = FHIRPatient
        fields = [
            "resourceType", "id", "fhir_id", "mrn",
            "name", "identifier", "birth_date", "gender",
            "address", "phone", "email", "active",
            "age", "telecom", "communication",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "Patient"

    def get_name(self, obj):
        return [{"use": "official", "family": obj.last_name, "given": [obj.first_name, obj.middle_name] if obj.middle_name else [obj.first_name]}]

    def get_identifier(self, obj):
        return [{"system": "urn:inhealth:mrn", "value": obj.mrn, "type": {"coding": [{"code": "MR", "system": "http://terminology.hl7.org/CodeSystem/v2-0203"}]}}]

    def get_address(self, obj):
        if obj.address_line1:
            return [{"use": "home", "line": [obj.address_line1, obj.address_line2], "city": obj.city, "state": obj.state, "postalCode": obj.postal_code, "country": obj.country}]
        return []


class FHIRObservationSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()
    patient_fhir_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = FHIRObservation
        fields = [
            "resourceType", "fhir_id", "patient", "patient_fhir_id",
            "status", "code", "display",
            "value_quantity", "value_unit", "value_string",
            "reference_range_low", "reference_range_high",
            "effective_datetime", "issued", "components",
            "device_type", "interpretation",
            "meta_version_id", "meta_last_updated",
        ]
        extra_kwargs = {
            "patient": {"required": False, "read_only": True},
            "fhir_id": {"required": False},  # auto-generated in model.save()
        }

    def get_resourceType(self, obj):
        return "Observation"

    def create(self, validated_data):
        patient_fhir_id = validated_data.pop("patient_fhir_id", None)
        if patient_fhir_id and "patient" not in validated_data:
            try:
                validated_data["patient"] = FHIRPatient.objects.get(
                    fhir_id=patient_fhir_id,
                    tenant=validated_data.get("tenant"),
                )
            except FHIRPatient.DoesNotExist:
                raise serializers.ValidationError(
                    {"patient_fhir_id": f"Patient {patient_fhir_id} not found"}
                )
        return super().create(validated_data)


class FHIRConditionSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRCondition
        fields = [
            "resourceType", "fhir_id", "clinical_status", "verification_status",
            "code", "display", "snomed_code", "category", "severity",
            "onset_datetime", "abatement_datetime", "recorded_date",
            "note", "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "Condition"


class FHIRMedicationRequestSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRMedicationRequest
        fields = [
            "resourceType", "fhir_id", "status", "intent",
            "medication_code", "medication_display",
            "dosage_text", "dose_quantity", "dose_unit",
            "frequency", "route", "as_needed",
            "quantity_value", "days_supply", "number_of_repeats_allowed",
            "authored_on", "validity_period_start", "validity_period_end",
            "reason_code", "reason_display", "note",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "MedicationRequest"


class FHIRAllergyIntoleranceSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRAllergyIntolerance
        fields = [
            "resourceType", "fhir_id", "clinical_status", "verification_status",
            "category", "criticality", "code", "display",
            "reactions", "onset_datetime", "recorded_date", "note",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "AllergyIntolerance"


class FHIRAppointmentSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRAppointment
        fields = [
            "resourceType", "fhir_id", "status", "service_type", "specialty",
            "appointment_type", "description", "start", "end", "minutes_duration",
            "location", "is_telehealth", "telehealth_url", "comment",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "Appointment"


class FHIRCarePlanSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()
    id = serializers.CharField(source="fhir_id", read_only=True)
    patient_fhir_id = serializers.CharField(source="patient.fhir_id", read_only=True)

    class Meta:
        model = FHIRCarePlan
        fields = [
            "resourceType", "id", "fhir_id", "patient_fhir_id",
            "status", "intent",
            "title", "description", "category",
            "goals", "activities", "period_start", "period_end",
            "created", "ai_generated", "ai_model_used", "author_id", "note",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "CarePlan"


class FHIREncounterSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIREncounter
        fields = [
            "resourceType", "fhir_id", "status", "encounter_class",
            "type_code", "type_display", "reason_code", "reason_display",
            "period_start", "period_end", "length_minutes",
            "discharge_disposition", "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "Encounter"


class FHIRImmunizationSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRImmunization
        fields = [
            "resourceType", "fhir_id", "status", "vaccine_code", "vaccine_display",
            "occurrence_datetime", "lot_number", "manufacturer",
            "dose_quantity_value", "dose_quantity_unit", "site", "route",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "Immunization"


class FHIRDocumentReferenceSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRDocumentReference
        fields = [
            "resourceType", "fhir_id", "status", "doc_status",
            "type_code", "type_display", "category",
            "content_url", "content_mime_type", "content_title",
            "date", "description", "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "DocumentReference"


class FHIRDiagnosticReportSerializer(serializers.ModelSerializer):
    resourceType = serializers.SerializerMethodField()

    class Meta:
        model = FHIRDiagnosticReport
        fields = [
            "resourceType", "fhir_id", "status", "category_code",
            "code", "display", "effective_datetime", "issued",
            "conclusion", "conclusion_code", "presented_form",
            "meta_version_id", "meta_last_updated",
        ]

    def get_resourceType(self, obj):
        return "DiagnosticReport"


class AgentActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentActionLog
        fields = [
            "id", "patient", "agent_type", "action_type",
            "action_details", "output", "model_used",
            "latency_ms", "tokens_used", "created_at",
            "reviewed_at", "was_accepted",
        ]
        read_only_fields = fields
