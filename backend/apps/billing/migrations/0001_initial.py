"""Initial migration for the billing app."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
        ("fhir", "0001_initial"),
        ("clinical", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Claim",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("cpt_codes", models.JSONField(
                    default=list,
                    help_text='[{"code": "99213", "description": "E/M Office Visit Level 3", "units": 1, "fee": 150.00}]',
                )),
                ("icd10_codes", models.JSONField(
                    default=list,
                    help_text='["E11.9", "I10"]',
                )),
                ("hcpcs_codes", models.JSONField(blank=True, default=list)),
                ("modifier_codes", models.JSONField(blank=True, default=list)),
                ("billed_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("allowed_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("insurance_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("patient_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("adjustment_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("payer_name", models.CharField(blank=True, default="", max_length=255)),
                ("payer_id", models.CharField(blank=True, default="", max_length=50)),
                ("group_number", models.CharField(blank=True, default="", max_length=50)),
                ("member_id", models.CharField(blank=True, default="", max_length=50)),
                ("prior_auth_number", models.CharField(blank=True, default="", max_length=50)),
                ("claim_number", models.CharField(blank=True, db_index=True, default="", max_length=50)),
                ("npi", models.CharField(blank=True, default="", max_length=10)),
                ("service_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Draft"),
                        ("ready", "Ready to Submit"),
                        ("submitted", "Submitted"),
                        ("pending", "Pending Review"),
                        ("approved", "Approved"),
                        ("denied", "Denied"),
                        ("paid", "Paid"),
                        ("partial", "Partial Payment"),
                        ("voided", "Voided"),
                        ("refunded", "Refunded"),
                    ],
                    db_index=True,
                    default="draft",
                    max_length=15,
                )),
                ("payer_response", models.JSONField(blank=True, default=dict)),
                ("denial_reason", models.CharField(blank=True, default="", max_length=500)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("encounter", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="claims",
                    to="clinical.encounter",
                )),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="claims",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "status", "service_date"], name="billing_claim_tenant_status_idx"),
                    models.Index(fields=["patient", "status"], name="billing_claim_patient_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RPMEpisode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ordering_provider_id", models.UUIDField(blank=True, null=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("monitoring_minutes", models.PositiveIntegerField(default=0)),
                ("total_readings", models.PositiveIntegerField(default=0)),
                ("devices_used", models.JSONField(
                    default=list,
                    help_text='[{"device_type": "cgm", "device_id": "...", "manufacturer": "Dexcom"}]',
                )),
                ("billing_codes", models.JSONField(
                    default=dict,
                    help_text='{" 99453": {"eligible": true, "billed": false, "date": null}, "99454": {...}}',
                )),
                ("monthly_summaries", models.JSONField(
                    blank=True,
                    default=list,
                    help_text='[{"month": "2024-01", "minutes": 35, "readings": 180, "99454_eligible": true}]',
                )),
                ("status", models.CharField(
                    choices=[
                        ("active", "Active"),
                        ("completed", "Completed"),
                        ("cancelled", "Cancelled"),
                        ("suspended", "Suspended"),
                    ],
                    db_index=True,
                    default="active",
                    max_length=15,
                )),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="rpm_episodes",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-start_date"],
                "indexes": [
                    models.Index(fields=["tenant", "status"], name="billing_rpm_tenant_status_idx"),
                    models.Index(fields=["patient", "start_date"], name="billing_rpm_patient_start_idx"),
                ],
            },
        ),
    ]
