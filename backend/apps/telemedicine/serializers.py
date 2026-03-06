"""Serializers for the telemedicine app."""

from rest_framework import serializers

from .models import VideoSession


class VideoSessionSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()

    class Meta:
        model = VideoSession
        fields = "__all__"
        read_only_fields = [
            "id",
            "tenant",
            "duration_minutes",
            "created_at",
            "updated_at",
            "provider_name",
        ]

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.get_full_name()
        return None

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user.tenant
        return super().create(validated_data)
