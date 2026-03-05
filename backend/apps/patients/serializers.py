"""
Serializers for the patients app.
"""

from rest_framework import serializers

from apps.fhir.models import FHIRPatient
from apps.fhir.serializers import FHIRPatientSerializer

from .models import DeviceRegistration, PatientDemographics, PatientEngagement


class PatientCreateSerializer(serializers.ModelSerializer):
    """Write serializer used for patient creation and updates."""

    class Meta:
        model = FHIRPatient
        fields = [
            "id",
            "mrn", "first_name", "last_name", "middle_name",
            "birth_date", "gender", "phone", "email",
            "address_line1", "address_line2", "city", "state",
            "postal_code", "country", "active",
            "primary_care_provider",
        ]
        extra_kwargs = {
            "id":         {"read_only": True},
            "mrn":        {"required": True},
            "first_name": {"required": True},
            "last_name":  {"required": True},
            "birth_date": {"required": True},
            "middle_name":    {"required": False, "default": ""},
            "address_line1":  {"required": False, "default": ""},
            "address_line2":  {"required": False, "default": ""},
            "city":           {"required": False, "default": ""},
            "state":          {"required": False, "default": ""},
            "postal_code":    {"required": False, "default": ""},
            "country":        {"required": False, "default": "US"},
        }


class PatientDemographicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDemographics
        fields = "__all__"
        read_only_fields = ["id", "patient", "created_at", "updated_at"]


class PatientEngagementSerializer(serializers.ModelSerializer):
    acknowledgement_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = PatientEngagement
        fields = "__all__"
        read_only_fields = ["id", "patient", "engagement_score", "created_at", "updated_at", "acknowledgement_rate"]


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    device_type_display = serializers.CharField(source="get_device_type_display", read_only=True)

    class Meta:
        model = DeviceRegistration
        fields = "__all__"
        read_only_fields = ["id", "registered_at", "last_sync"]


class PatientSummarySerializer(serializers.Serializer):
    """Comprehensive patient summary for the clinical dashboard."""
    patient = FHIRPatientSerializer()
    demographics = PatientDemographicsSerializer(allow_null=True)
    engagement = PatientEngagementSerializer(allow_null=True)
    devices = DeviceRegistrationSerializer(many=True)
    active_conditions_count = serializers.IntegerField()
    active_medications_count = serializers.IntegerField()
    pending_appointments_count = serializers.IntegerField()
    recent_alerts_count = serializers.IntegerField()
    risk_level = serializers.CharField(allow_null=True)
    risk_score = serializers.FloatField(allow_null=True)
