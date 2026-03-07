"""Serializers for the SDOH app."""

from rest_framework import serializers

from .models import SDOHAssessment


class SDOHAssessmentSerializer(serializers.ModelSerializer):
    intervention_recommendations = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    assessed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SDOHAssessment
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "total_score", "overall_sdoh_risk",
            "created_at", "updated_at",
            "intervention_recommendations", "patient_name", "assessed_by_name",
        ]

    def get_intervention_recommendations(self, obj):
        return obj.get_intervention_recommendations()

    def get_patient_name(self, obj):
        try:
            return obj.patient.full_name if obj.patient else None
        except Exception:
            return None

    def get_assessed_by_name(self, obj):
        try:
            return obj.assessed_by.get_full_name() if obj.assessed_by else None
        except Exception:
            return None

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        validated_data["assessed_by"] = self.context["request"].user
        return super().create(validated_data)
