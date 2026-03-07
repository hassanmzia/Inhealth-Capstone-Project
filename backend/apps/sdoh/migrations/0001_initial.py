"""Initial migration for the SDOH app."""

import uuid

import django.db.models.deletion
import django.utils.timezone
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
            name="SDOHAssessment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                # SDOH domain scores
                ("food_security_score", models.IntegerField(
                    choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                    default=0,
                    help_text="0=food secure, 4=severe food insecurity",
                )),
                ("housing_stability_score", models.IntegerField(
                    choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                    default=0,
                    help_text="0=stable, 4=homeless/at extreme risk",
                )),
                ("transportation_score", models.IntegerField(
                    choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                    default=0,
                    help_text="0=reliable transport, 4=no access/major barrier",
                )),
                ("social_support_score", models.IntegerField(
                    choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                    default=0,
                    help_text="0=strong support network, 4=complete isolation",
                )),
                ("financial_stress_score", models.IntegerField(
                    choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                    default=0,
                    help_text="0=financially stable, 4=unable to cover basic needs",
                )),
                # Additional SDOH factors
                ("education_barrier", models.BooleanField(default=False)),
                ("employment_barrier", models.BooleanField(default=False)),
                ("health_literacy_barrier", models.BooleanField(default=False)),
                ("interpersonal_violence", models.BooleanField(default=False)),
                ("substance_use_concern", models.BooleanField(default=False)),
                ("mental_health_concern", models.BooleanField(default=False)),
                # Computed fields
                ("overall_sdoh_risk", models.CharField(
                    choices=[
                        ("low", "Low SDOH Risk (0-4 total)"),
                        ("medium", "Moderate SDOH Risk (5-10 total)"),
                        ("high", "High SDOH Risk (11-20 total)"),
                    ],
                    db_index=True,
                    default="low",
                    max_length=10,
                )),
                ("total_score", models.IntegerField(default=0)),
                # Interventions
                ("interventions_recommended", models.JSONField(
                    default=list,
                    help_text='\n        [\n          {"domain": "food", "intervention": "Refer to food bank", "status": "pending"},\n          {"domain": "housing", "intervention": "Contact social worker", "status": "completed"}\n        ]\n        ',
                )),
                ("community_resources_referred", models.JSONField(blank=True, default=list)),
                # Follow-up
                ("follow_up_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                # Dates
                ("assessment_date", models.DateField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # Foreign keys
                ("assessed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sdoh_assessments_conducted",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="sdoh_assessments",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-assessment_date"],
            },
        ),
        migrations.AddIndex(
            model_name="sdohassessment",
            index=models.Index(fields=["tenant", "overall_sdoh_risk"], name="sdoh_sdohas_tenant__idx"),
        ),
        migrations.AddIndex(
            model_name="sdohassessment",
            index=models.Index(fields=["patient", "assessment_date"], name="sdoh_sdohas_patient_idx"),
        ),
    ]
