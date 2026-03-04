"""
Serializers for the tenants app.
"""

import hashlib
import secrets

from rest_framework import serializers

from .models import APIKey, Organization, TenantConfig


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "domain", "subscription_tier",
            "is_active", "branding", "settings", "max_patients",
            "max_providers", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class TenantConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantConfig
        fields = [
            "organization", "fhir_base_url", "hl7_endpoint",
            "enable_ai_agents", "enable_research_system", "enable_telemedicine",
            "enable_rpm", "enable_clinical_trials",
            "llm_provider", "llm_model", "custom_prompts",
            "notification_channels", "require_mfa",
            "data_retention_days", "allow_research_data_sharing",
            "created_at", "updated_at",
        ]
        read_only_fields = ["organization", "created_at", "updated_at"]


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Returns the raw key only on creation."""
    raw_key = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = ["id", "name", "permissions", "expires_at", "raw_key", "key_prefix", "created_at"]
        read_only_fields = ["id", "raw_key", "key_prefix", "created_at"]

    def get_raw_key(self, obj):
        return getattr(obj, "_raw_key", None)

    def create(self, validated_data):
        raw_key = f"ihk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        api_key = APIKey.objects.create(
            key_hash=key_hash,
            key_prefix=key_prefix,
            **validated_data,
        )
        api_key._raw_key = raw_key  # Only available on first creation
        return api_key


class APIKeySerializer(serializers.ModelSerializer):
    """Safe serializer — never exposes the key hash."""
    class Meta:
        model = APIKey
        fields = [
            "id", "name", "key_prefix", "permissions",
            "is_active", "expires_at", "last_used_at", "created_at",
        ]
        read_only_fields = ["id", "key_prefix", "last_used_at", "created_at"]
