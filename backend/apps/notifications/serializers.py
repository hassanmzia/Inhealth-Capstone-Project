"""Serializers for the notifications app."""

from rest_framework import serializers

from .models import Notification, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = [
            "id", "tenant", "status", "sent_at", "delivered_at",
            "failed_at", "failure_reason", "retry_count", "external_message_id",
            "acknowledged_at", "acknowledged_by", "escalation_level", "escalated_at",
            "created_at", "updated_at", "patient_name",
        ]

    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else None


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
