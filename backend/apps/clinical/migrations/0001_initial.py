"""Initial migration for the clinical app."""

import uuid

import django.contrib.postgres.fields
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
            name="Encounter",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("fhir_encounter_id", models.CharField(blank=True, default="", max_length=64)),
                ("encounter_type", models.CharField(
                    choices=[
                        ("outpatient", "Outpatient"),
                        ("inpatient", "Inpatient"),
                        ("emergency", "Emergency"),
                        ("telehealth", "Telehealth / Virtual"),
                        ("home_health", "Home Health"),
                        ("skilled_nursing", "Skilled Nursing Facility"),
                    ],
                    default="outpatient",
                    max_length=20,
                )),
                ("status", models.CharField(
                    choices=[
                        ("planned", "Planned"),
                        ("in_progress", "In Progress"),
                        ("completed", "Completed"),
                        ("cancelled", "Cancelled"),
                        ("no_show", "No Show"),
                    ],
                    db_index=True,
                    default="planned",
                    max_length=15,
                )),
                ("start_datetime", models.DateTimeField(db_index=True)),
                ("end_datetime", models.DateTimeField(blank=True, null=True)),
                ("follow_up_date", models.DateField(blank=True, null=True)),
                ("chief_complaint", models.TextField(blank=True, default="")),
                ("hpi", models.TextField(blank=True, default="", verbose_name="History of Present Illness")),
                ("review_of_systems", models.JSONField(blank=True, default=dict)),
                ("physical_exam", models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='{"general": "NAD", "vitals": {...}, "cardiovascular": "", "respiratory": ""}',
                )),
                ("assessment", models.TextField(blank=True, default="")),
                ("treatment_plan", models.TextField(blank=True, default="")),
                ("icd10_primary", models.CharField(blank=True, db_index=True, default="", max_length=20)),
                ("icd10_primary_display", models.CharField(blank=True, default="", max_length=255)),
                ("icd10_secondary", django.contrib.postgres.fields.ArrayField(
                    base_field=models.CharField(max_length=20),
                    blank=True,
                    default=list,
                    size=None,
                )),
                ("orders_placed", models.JSONField(blank=True, default=list)),
                ("ai_scribe_notes", models.TextField(blank=True, default="")),
                ("ai_suggested_codes", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="clinical_encounters",
                    to="fhir.fhirpatient",
                )),
                ("provider", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="clinical_encounters",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-start_datetime"],
                "indexes": [
                    models.Index(fields=["tenant", "patient", "start_datetime"], name="clinical_enc_tenant_pat_idx"),
                    models.Index(fields=["provider", "start_datetime"], name="clinical_enc_provider_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CareGap",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("gap_type", models.CharField(
                    choices=[
                        ("A1C_overdue", "A1C Test Overdue (>3 months)"),
                        ("BP_check_overdue", "Blood Pressure Check Overdue"),
                        ("eye_exam_overdue", "Diabetic Eye Exam Overdue"),
                        ("foot_exam_overdue", "Diabetic Foot Exam Overdue"),
                        ("nephropathy_screen", "Nephropathy Screening Overdue"),
                        ("statin_not_prescribed", "Statin Not Prescribed (ASCVD risk)"),
                        ("ace_arb_not_prescribed", "ACE-I/ARB Not Prescribed (DM + HTN)"),
                        ("immunization_overdue", "Immunization Overdue"),
                        ("colonoscopy_overdue", "Colonoscopy Overdue"),
                        ("mammogram_overdue", "Mammogram Overdue"),
                        ("depression_screen", "Depression Screening Overdue (PHQ-9)"),
                        ("smoking_cessation", "Smoking Cessation Counseling Needed"),
                        ("medication_adherence", "Medication Adherence Gap"),
                        ("follow_up_missed", "Missed Follow-Up Visit"),
                    ],
                    db_index=True,
                    max_length=40,
                )),
                ("last_completed", models.DateField(blank=True, null=True)),
                ("due_date", models.DateField(db_index=True)),
                ("priority", models.CharField(
                    choices=[
                        ("critical", "Critical"),
                        ("high", "High"),
                        ("medium", "Medium"),
                        ("low", "Low"),
                    ],
                    default="medium",
                    max_length=10,
                )),
                ("status", models.CharField(
                    choices=[
                        ("open", "Open"),
                        ("closed", "Closed"),
                        ("deferred", "Deferred"),
                        ("patient_declined", "Patient Declined"),
                    ],
                    db_index=True,
                    default="open",
                    max_length=20,
                )),
                ("ai_recommendation", models.TextField(blank=True, default="")),
                ("evidence_reference", models.CharField(blank=True, default="", max_length=255)),
                ("deferred_until", models.DateField(blank=True, null=True)),
                ("deferred_by_id", models.UUIDField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("patient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="care_gaps",
                    to="fhir.fhirpatient",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["priority", "due_date"],
                "unique_together": {("patient", "gap_type", "status")},
                "indexes": [
                    models.Index(fields=["tenant", "status", "priority"], name="clinical_cg_tenant_status_idx"),
                    models.Index(fields=["patient", "status"], name="clinical_cg_patient_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SmartOrderSet",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("condition", models.CharField(db_index=True, max_length=20)),
                ("condition_display", models.CharField(max_length=255)),
                ("orders", models.JSONField(
                    default=dict,
                    help_text='\n        {\n          "medications": [{"name": "Metformin 500mg", "sig": "BID with meals", "rxnorm": "860975"}],\n          "labs": [{"name": "HbA1c", "loinc": "4548-4", "frequency": "every 3 months"}],\n          "imaging": [],\n          "referrals": [{"specialty": "Endocrinology", "reason": "Uncontrolled DM"}],\n          "patient_education": ["Diabetes management", "Carb counting"]\n        }\n        ',
                )),
                ("evidence_level", models.CharField(
                    choices=[
                        ("A", "Level A \u2014 Strong evidence (RCTs)"),
                        ("B", "Level B \u2014 Moderate evidence"),
                        ("C", "Level C \u2014 Expert consensus"),
                        ("D", "Level D \u2014 Limited evidence"),
                    ],
                    default="B",
                    max_length=2,
                )),
                ("source_guideline", models.CharField(blank=True, default="", max_length=255)),
                ("source_url", models.URLField(blank=True, default="")),
                ("created_by_ai", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["condition", "name"],
                "indexes": [
                    models.Index(fields=["condition", "is_active"], name="clinical_sos_condition_idx"),
                    models.Index(fields=["tenant", "condition"], name="clinical_sos_tenant_cond_idx"),
                ],
            },
        ),
    ]
