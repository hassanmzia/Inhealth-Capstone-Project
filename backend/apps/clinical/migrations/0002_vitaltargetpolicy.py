"""
Migration for VitalTargetPolicy model — per-patient vital sign target policies.
"""

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clinical", "0001_initial"),
        ("tenants", "0001_initial"),
        ("fhir", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VitalTargetPolicy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "loinc_code",
                    models.CharField(
                        db_index=True,
                        help_text="LOINC code for the vital sign (e.g., 8480-6 for Systolic BP)",
                        max_length=20,
                    ),
                ),
                (
                    "vital_name",
                    models.CharField(
                        help_text="Human-readable vital sign name",
                        max_length=100,
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        help_text="Measurement unit (e.g., mmHg, bpm)",
                        max_length=20,
                    ),
                ),
                (
                    "target_low",
                    models.FloatField(
                        help_text="Lower bound of target range (inclusive)",
                    ),
                ),
                (
                    "target_high",
                    models.FloatField(
                        help_text="Upper bound of target range (inclusive)",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("clinician", "Clinician-Set"),
                            ("guideline", "Evidence-Based Guideline"),
                            ("ai_suggested", "AI-Suggested"),
                            ("care_plan", "Auto-Created from Care Plan"),
                        ],
                        default="guideline",
                        max_length=20,
                    ),
                ),
                (
                    "source_guideline",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Clinical guideline reference (e.g., ACC/AHA 2023)",
                        max_length=255,
                    ),
                ),
                (
                    "rationale",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Why this target was chosen for this patient",
                    ),
                ),
                (
                    "times_evaluated",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "times_in_range",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="tenants.organization",
                        db_index=True,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vital_targets",
                        to="fhir.fhirpatient",
                    ),
                ),
                (
                    "set_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Clinician who set or approved this target",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vital_target_policies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "care_plan",
                    models.ForeignKey(
                        blank=True,
                        help_text="Care plan that triggered this target policy",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vital_targets",
                        to="fhir.fhircareplan",
                    ),
                ),
            ],
            options={
                "ordering": ["vital_name"],
                "indexes": [
                    models.Index(
                        fields=["patient", "is_active"],
                        name="clinical_vi_patient_active_idx",
                    ),
                    models.Index(
                        fields=["tenant", "loinc_code"],
                        name="clinical_vi_tenant_loinc_idx",
                    ),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="vitaltargetpolicy",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("patient", "loinc_code"),
                name="unique_active_vital_target_per_patient",
            ),
        ),
    ]
