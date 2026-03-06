import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_add_email_verification"),
        ("fhir", "0001_initial"),
    ]

    operations = [
        # ── PatientDemographics ──────────────────────────────────────────────
        migrations.CreateModel(
            name="PatientDemographics",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("insurance_provider", models.CharField(blank=True, default="", max_length=100)),
                ("insurance_policy_number", models.CharField(blank=True, default="", max_length=50)),
                ("insurance_group_number", models.CharField(blank=True, default="", max_length=50)),
                ("insurance_effective_date", models.DateField(blank=True, null=True)),
                ("insurance_expiration_date", models.DateField(blank=True, null=True)),
                ("secondary_insurance_provider", models.CharField(blank=True, default="", max_length=100)),
                ("secondary_policy_number", models.CharField(blank=True, default="", max_length=50)),
                ("emergency_contact_name", models.CharField(blank=True, default="", max_length=200)),
                ("emergency_contact_phone", models.CharField(blank=True, default="", max_length=20)),
                ("emergency_contact_relationship", models.CharField(blank=True, default="", max_length=50)),
                ("preferred_pharmacy", models.CharField(blank=True, default="", max_length=255)),
                ("preferred_pharmacy_phone", models.CharField(blank=True, default="", max_length=20)),
                ("race", models.CharField(choices=[("white", "White"), ("black_aa", "Black or African American"), ("aian", "American Indian or Alaska Native"), ("asian", "Asian"), ("nhpi", "Native Hawaiian or Pacific Islander"), ("multiracial", "Two or More Races"), ("other", "Other"), ("unknown", "Unknown / Not Reported")], default="unknown", max_length=20)),
                ("ethnicity", models.CharField(choices=[("hispanic_latino", "Hispanic or Latino"), ("not_hispanic_latino", "Not Hispanic or Latino"), ("unknown", "Unknown / Not Reported")], default="unknown", max_length=30)),
                ("marital_status", models.CharField(choices=[("S", "Single"), ("M", "Married"), ("D", "Divorced"), ("W", "Widowed"), ("L", "Legally Separated"), ("T", "Domestic Partner"), ("UNK", "Unknown")], default="UNK", max_length=10)),
                ("education_level", models.CharField(blank=True, default="", max_length=100)),
                ("occupation", models.CharField(blank=True, default="", max_length=100)),
                ("has_advance_directive", models.BooleanField(blank=True, null=True)),
                ("advance_directive_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="demographics", to="fhir.fhirpatient")),
                ("primary_care_physician", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="demographic_pcp_patients", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Patient Demographics", "verbose_name_plural": "Patient Demographics"},
        ),

        # ── PatientEngagement ────────────────────────────────────────────────
        migrations.CreateModel(
            name="PatientEngagement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("engagement_score", models.FloatField(default=50.0)),
                ("health_goals", models.JSONField(blank=True, default=list)),
                ("achievements", models.JSONField(blank=True, default=list)),
                ("streak_days", models.PositiveIntegerField(default=0)),
                ("last_app_login", models.DateTimeField(blank=True, null=True)),
                ("notification_preferences", models.JSONField(blank=True, default=dict)),
                ("total_messages_sent", models.PositiveIntegerField(default=0)),
                ("total_messages_acknowledged", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="engagement", to="fhir.fhirpatient")),
            ],
            options={"verbose_name": "Patient Engagement"},
        ),

        # ── DeviceRegistration ───────────────────────────────────────────────
        migrations.CreateModel(
            name="DeviceRegistration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_type", models.CharField(choices=[("cgm", "Continuous Glucose Monitor"), ("smartwatch", "Smartwatch / Fitness Tracker"), ("bp_monitor", "Blood Pressure Monitor"), ("pulse_oximeter", "Pulse Oximeter"), ("weight_scale", "Smart Weight Scale"), ("insulin_pump", "Insulin Pump"), ("ecg_monitor", "ECG Monitor"), ("spirometer", "Spirometer"), ("thermometer", "Smart Thermometer"), ("other", "Other")], db_index=True, max_length=20)),
                ("device_id", models.CharField(db_index=True, max_length=100, unique=True)),
                ("manufacturer", models.CharField(max_length=100)),
                ("model", models.CharField(blank=True, default="", max_length=100)),
                ("serial_number", models.CharField(blank=True, default="", max_length=100)),
                ("firmware_version", models.CharField(blank=True, default="", max_length=50)),
                ("fhir_device_id", models.CharField(blank=True, default="", max_length=64)),
                ("last_sync", models.DateTimeField(blank=True, null=True)),
                ("sync_frequency_minutes", models.PositiveIntegerField(default=15)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("alerts_config", models.JSONField(blank=True, default=dict)),
                ("registered_at", models.DateTimeField(auto_now_add=True)),
                ("deregistered_at", models.DateTimeField(blank=True, null=True)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="devices", to="fhir.fhirpatient")),
            ],
            options={"ordering": ["-registered_at"]},
        ),
        migrations.AddIndex(
            model_name="deviceregistration",
            index=models.Index(fields=["patient", "device_type", "is_active"], name="patients_dev_pt_dt_ia_idx"),
        ),
    ]
