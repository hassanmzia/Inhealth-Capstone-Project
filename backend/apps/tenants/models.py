"""
Tenant / Organization models for multi-tenant InHealth deployment.
Uses django-tenants for PostgreSQL schema-based isolation.
"""

import uuid

from django.db import models
from django.utils.text import slugify
from django_tenants.models import DomainMixin, TenantMixin


class Organization(TenantMixin):
    """
    Top-level tenant model. Each organization gets its own PostgreSQL schema.
    The schema_name field (from TenantMixin) is used as the slug.
    """

    class SubscriptionTier(models.TextChoices):
        BASIC = "basic", "Basic"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=253, blank=True, default="")

    subscription_tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.BASIC,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Branding
    branding = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"logo_url": "", "primary_color": "#1976D2", "secondary_color": "#424242", "favicon_url": ""}',
    )

    # Feature settings
    settings = models.JSONField(default=dict, blank=True)
    max_patients = models.PositiveIntegerField(default=500)
    max_providers = models.PositiveIntegerField(default=50)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # django-tenants: auto_create_schema
    auto_create_schema = True

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.schema_name:
            self.schema_name = self.slug.replace("-", "_")
        super().save(*args, **kwargs)

    @property
    def is_ai_enabled(self):
        try:
            return self.config.enable_ai_agents
        except TenantConfig.DoesNotExist:
            return False


class Domain(DomainMixin):
    """Domain mapping for tenant URL routing."""
    pass


class TenantConfig(models.Model):
    """
    Extended configuration for each tenant organization.
    Controls feature flags, integrations, and AI settings.
    """

    class LLMProvider(models.TextChoices):
        OLLAMA = "ollama", "Ollama (Local)"
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic Claude"
        AZURE_OPENAI = "azure_openai", "Azure OpenAI"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="config",
        primary_key=True,
    )

    # Integration endpoints
    fhir_base_url = models.URLField(blank=True, default="")
    hl7_endpoint = models.CharField(max_length=255, blank=True, default="")

    # Feature flags
    enable_ai_agents = models.BooleanField(default=True)
    enable_research_system = models.BooleanField(default=False)
    enable_telemedicine = models.BooleanField(default=False)
    enable_rpm = models.BooleanField(default=False)
    enable_clinical_trials = models.BooleanField(default=False)

    # AI configuration
    llm_provider = models.CharField(
        max_length=20,
        choices=LLMProvider.choices,
        default=LLMProvider.OPENAI,
    )
    llm_model = models.CharField(max_length=100, default="gpt-4o", blank=True)
    custom_prompts = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"triage_system": "", "care_plan": "", "medication_review": ""}',
    )

    # Notification channels
    notification_channels = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"sms": true, "email": true, "push": true, "ehr": false}',
    )

    # Compliance
    require_mfa = models.BooleanField(default=False)
    data_retention_days = models.PositiveIntegerField(default=2555)  # 7 years default
    allow_research_data_sharing = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant Configuration"

    def __str__(self):
        return f"Config for {self.organization.name}"


class APIKey(models.Model):
    """
    API keys for programmatic access to the InHealth API.
    Used by third-party integrations (EHR systems, devices, etc.).
    """

    class Permission(models.TextChoices):
        READ_PATIENTS = "read:patients", "Read Patients"
        WRITE_PATIENTS = "write:patients", "Write Patients"
        READ_FHIR = "read:fhir", "Read FHIR Resources"
        WRITE_FHIR = "write:fhir", "Write FHIR Resources"
        SEND_HL7 = "send:hl7", "Send HL7 Messages"
        READ_ANALYTICS = "read:analytics", "Read Analytics"
        FULL_ACCESS = "full:access", "Full Access"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256 of the key
    key_prefix = models.CharField(max_length=8, db_index=True)  # First 8 chars for identification
    permissions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_api_keys",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or APIKey.Permission.FULL_ACCESS in self.permissions
