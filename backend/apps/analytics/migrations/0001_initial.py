"""Initial migration for the analytics app."""

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
            name="PopulationCohort",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("condition_filter", models.JSONField(
                    default=dict,
                    help_text='\n        {\n          "icd10_codes": ["E11", "I50"],\n          "age_min": 18,\n          "age_max": 80,\n          "risk_level": ["high", "critical"],\n          "has_active_condition": true\n        }\n        ',
                )),
                ("patient_count", models.PositiveIntegerField(default=0)),
                ("last_refreshed", models.DateTimeField(blank=True, null=True)),
                ("refresh_frequency_hours", models.PositiveIntegerField(default=24)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_cohorts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["tenant", "is_active"], name="analytics_pc_tenant_active_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RiskScore",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("score_type", models.CharField(
                    choices=[
                        ("7_day_hospitalization", "7-Day Hospitalization Risk"),
                        ("30_day_mortality", "30-Day Mortality Risk"),
                        ("30_day_readmission", "30-Day Readmission Risk"),
                        ("30_day_ed_visit", "30-Day ED Visit Risk"),
                        ("medication_nonadherence", "Medication Non-Adherence Risk"),
                        ("glucose_control", "Poor Glucose Control Risk"),
                        ("falls_risk", "Falls Risk"),
                        ("sepsis_risk", "Sepsis Risk"),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ("score", models.FloatField()),
                ("risk_level", models.CharField(
                    choices=[
                        ("low", "Low (<30%)"),
                        ("medium", "Medium (30-60%)"),
                        ("high", "High (60-80%)"),
                        ("critical", "Critical (>80%)"),
                    ],
                    db_index=True,
                    max_length=10,
                )),
                ("features", models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='{"a1c_value": 0.32, "bp_systolic": 0.18, "age": 0.15, "comorbidities": 0.12}',
                )),
                ("model_version", models.CharField(default="xgboost_v1", max_length=50)),
                ("calculated_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("valid_until", models.DateTimeField(db_index=True)),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="analytics_risk_scores",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-calculated_at"],
                "indexes": [
                    models.Index(fields=["patient", "score_type", "calculated_at"], name="analytics_rs_patient_type_idx"),
                    models.Index(fields=["tenant", "risk_level", "valid_until"], name="analytics_rs_tenant_risk_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ClinicalKPI",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("metric_name", models.CharField(
                    choices=[
                        ("avg_a1c", "Average A1C"),
                        ("pct_a1c_controlled", "% Patients A1C < 8.0"),
                        ("pct_bp_controlled", "% Patients BP Controlled"),
                        ("readmission_rate_30d", "30-Day Readmission Rate"),
                        ("ed_visit_rate", "ED Visit Rate per 1000"),
                        ("care_gap_closure_rate", "Care Gap Closure Rate"),
                        ("medication_adherence_rate", "Medication Adherence Rate"),
                        ("patient_satisfaction", "Patient Satisfaction Score"),
                        ("avg_engagement_score", "Average Patient Engagement Score"),
                        ("alert_response_time_min", "Average Alert Response Time (minutes)"),
                    ],
                    db_index=True,
                    max_length=50,
                )),
                ("metric_value", models.FloatField()),
                ("metric_date", models.DateField(db_index=True)),
                ("unit", models.CharField(blank=True, default="", max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-metric_date"],
                "unique_together": {("tenant", "metric_name", "metric_date")},
                "indexes": [
                    models.Index(fields=["tenant", "metric_name", "metric_date"], name="analytics_kpi_tenant_metric_idx"),
                ],
            },
        ),
    ]
