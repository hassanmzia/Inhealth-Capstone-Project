import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "schema_name",
                    models.CharField(max_length=63, unique=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("domain", models.CharField(blank=True, default="", max_length=253)),
                (
                    "subscription_tier",
                    models.CharField(
                        choices=[
                            ("basic", "Basic"),
                            ("professional", "Professional"),
                            ("enterprise", "Enterprise"),
                        ],
                        db_index=True,
                        default="basic",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "branding",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='{"logo_url": "", "primary_color": "#1976D2", "secondary_color": "#424242", "favicon_url": ""}',
                    ),
                ),
                ("settings", models.JSONField(blank=True, default=dict)),
                ("max_patients", models.PositiveIntegerField(default=500)),
                ("max_providers", models.PositiveIntegerField(default=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Domain",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "domain",
                    models.CharField(db_index=True, max_length=253, unique=True),
                ),
                ("is_primary", models.BooleanField(db_index=True, default=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domains",
                        to="tenants.organization",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TenantConfig",
            fields=[
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="config",
                        serialize=False,
                        to="tenants.organization",
                    ),
                ),
                ("fhir_base_url", models.URLField(blank=True, default="")),
                (
                    "hl7_endpoint",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("enable_ai_agents", models.BooleanField(default=True)),
                ("enable_research_system", models.BooleanField(default=False)),
                ("enable_telemedicine", models.BooleanField(default=False)),
                ("enable_rpm", models.BooleanField(default=False)),
                ("enable_clinical_trials", models.BooleanField(default=False)),
                (
                    "llm_provider",
                    models.CharField(
                        choices=[
                            ("ollama", "Ollama (Local)"),
                            ("openai", "OpenAI"),
                            ("anthropic", "Anthropic Claude"),
                            ("azure_openai", "Azure OpenAI"),
                        ],
                        default="openai",
                        max_length=20,
                    ),
                ),
                (
                    "llm_model",
                    models.CharField(blank=True, default="gpt-4o", max_length=100),
                ),
                (
                    "custom_prompts",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='{"triage_system": "", "care_plan": "", "medication_review": ""}',
                    ),
                ),
                (
                    "notification_channels",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='{"sms": true, "email": true, "push": true, "ehr": false}',
                    ),
                ),
                ("require_mfa", models.BooleanField(default=False)),
                ("data_retention_days", models.PositiveIntegerField(default=2555)),
                ("allow_research_data_sharing", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tenant Configuration",
            },
        ),
    ]
