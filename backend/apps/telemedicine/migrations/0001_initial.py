"""Initial migration for the telemedicine app."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
        ("fhir", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="VideoSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_id", models.CharField(
                    db_index=True,
                    help_text="External video platform session identifier",
                    max_length=255,
                    unique=True,
                )),
                ("status", models.CharField(
                    choices=[
                        ("scheduled", "Scheduled"),
                        ("active", "Active"),
                        ("completed", "Completed"),
                        ("cancelled", "Cancelled"),
                    ],
                    db_index=True,
                    default="scheduled",
                    max_length=15,
                )),
                ("scheduled_at", models.DateTimeField(db_index=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("duration_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("recording_url", models.URLField(blank=True, default="", max_length=500)),
                ("ai_notes", models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='{"summary": "...", "soap": {...}, "icd10_suggestions": [...]}',
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="video_sessions",
                    to="fhir.fhirpatient",
                )),
                ("provider", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="video_sessions",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-scheduled_at"],
                "indexes": [
                    models.Index(fields=["tenant", "status", "scheduled_at"], name="telemedicine_vs_tenant_idx"),
                    models.Index(fields=["patient", "scheduled_at"], name="telemedicine_vs_patient_idx"),
                    models.Index(fields=["provider", "scheduled_at"], name="telemedicine_vs_provider_idx"),
                ],
            },
        ),
    ]
