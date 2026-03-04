"""Serializers for the analytics app."""

from rest_framework import serializers

from .models import ClinicalKPI, PopulationCohort, RiskScore


class PopulationCohortSerializer(serializers.ModelSerializer):
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = PopulationCohort
        fields = "__all__"
        read_only_fields = ["id", "tenant", "patient_count", "last_refreshed", "created_at", "updated_at"]


class RiskScoreSerializer(serializers.ModelSerializer):
    score_percentage = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = RiskScore
        fields = "__all__"
        read_only_fields = ["id", "risk_level", "calculated_at"]

    def get_score_percentage(self, obj):
        return f"{obj.score:.1%}"

    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else None


class ClinicalKPISerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalKPI
        fields = "__all__"
        read_only_fields = ["id", "calculated_at"]
