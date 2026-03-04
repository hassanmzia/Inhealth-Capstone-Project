"""Serializers for the research app."""

from rest_framework import serializers

from .models import ClinicalTrial, MedicalEvidence, ResearchQuery


class ResearchQuerySerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ResearchQuery
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "status", "result", "sources",
            "evidence_level", "error_message", "model_used",
            "langfuse_trace_id", "processing_time_ms",
            "created_at", "completed_at", "requested_by_name",
        ]

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name()
        return None

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        validated_data["requested_by"] = self.context["request"].user
        return super().create(validated_data)


class ClinicalTrialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalTrial
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class MedicalEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalEvidence
        fields = "__all__"
        read_only_fields = ["id", "created_at", "indexed_at", "embedding_id"]
