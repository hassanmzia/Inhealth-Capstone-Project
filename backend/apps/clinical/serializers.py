"""Serializers for the clinical app."""

from rest_framework import serializers

from .models import CareGap, Encounter, SmartOrderSet, VitalTargetPolicy


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


class VitalTargetPolicySerializer(serializers.ModelSerializer):
    adherence_rate = serializers.FloatField(read_only=True)
    set_by_name = serializers.SerializerMethodField()

    class Meta:
        model = VitalTargetPolicy
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "set_by", "times_evaluated", "times_in_range",
            "created_at", "updated_at", "adherence_rate", "set_by_name",
        ]

    def get_set_by_name(self, obj):
        if obj.set_by:
            return obj.set_by.get_full_name()
        return None

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["tenant"] = getattr(request, "tenant", None) or request.user.tenant
        validated_data["set_by"] = request.user
        return super().create(validated_data)
