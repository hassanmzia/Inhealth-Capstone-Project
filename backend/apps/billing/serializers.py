"""Serializers for the billing app."""

from rest_framework import serializers

from .models import Claim, RPMEpisode


class ClaimSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "patient_name"]

    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else None

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        return super().create(validated_data)


class RPMEpisodeSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    eligible_billing_codes = serializers.SerializerMethodField()

    class Meta:
        model = RPMEpisode
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "patient_name"]

    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else None

    def get_eligible_billing_codes(self, obj):
        return {code: info for code, info in (obj.billing_codes or {}).items() if info.get("eligible")}

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        return super().create(validated_data)
