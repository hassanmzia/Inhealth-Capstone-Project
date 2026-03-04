"""Serializers for the clinical app."""

from rest_framework import serializers

from .models import CareGap, Encounter, SmartOrderSet


class EncounterSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = Encounter
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at", "provider_name"]

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.get_full_name()
        return None

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        return super().create(validated_data)


class CareGapSerializer(serializers.ModelSerializer):
    gap_type_display = serializers.CharField(source="get_gap_type_display", read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = CareGap
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]

    def get_is_overdue(self, obj):
        from django.utils import timezone
        return obj.due_date < timezone.now().date()


class SmartOrderSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartOrderSet
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
