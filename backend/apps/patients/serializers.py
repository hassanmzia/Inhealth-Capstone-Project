"""
Serializers for the patients app.
"""

from rest_framework import serializers

from apps.fhir.serializers import FHIRPatientSerializer

from .models import DeviceRegistration, PatientDemographics, PatientEngagement


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
