"""Initial migration for the research app."""

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
            name="ClinicalTrial",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nct_id", models.CharField(db_index=True, max_length=20, unique=True)),
                ("title", models.CharField(max_length=500)),
                ("brief_summary", models.TextField(blank=True, default="")),
                ("condition", models.CharField(db_index=True, max_length=255)),
                ("status", models.CharField(
                    choices=[
                        ("Recruiting", "Recruiting"),
                        ("Not yet recruiting", "Not Yet Recruiting"),
                        ("Active, not recruiting", "Active, Not Recruiting"),
                        ("Completed", "Completed"),
                        ("Terminated", "Terminated"),
                        ("Suspended", "Suspended"),
                    ],
                    db_index=True,
                    default="Recruiting",
                    max_length=50,
                )),
                ("phase", models.CharField(
                    choices=[
                        ("Phase 1", "Phase 1"),
                        ("Phase 2", "Phase 2"),
                        ("Phase 3", "Phase 3"),
                        ("Phase 4", "Phase 4"),
                        ("N/A", "Not Applicable"),
                    ],
                    default="Phase 2",
                    max_length=20,
                )),
                ("eligibility_criteria", models.JSONField(
                    default=dict,
                    help_text='{"inclusion": [], "exclusion": [], "age_min": 18, "age_max": 75, "accepts_healthy_volunteers": false}',
                )),
                ("locations", models.JSONField(
                    default=list,
                    help_text='[{"facility": "", "city": "", "state": "", "country": "", "zip": ""}]',
                )),
                ("contact", models.JSONField(
                    default=dict,
                    help_text='{"name": "", "email": "", "phone": ""}',
                )),
                ("sponsor", models.CharField(blank=True, default="", max_length=255)),
                ("primary_outcome", models.TextField(blank=True, default="")),
                ("enrollment_target", models.PositiveIntegerField(blank=True, null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("completion_date", models.DateField(blank=True, null=True)),
                ("last_updated", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("embedding_id", models.CharField(blank=True, db_index=True, default="", max_length=100)),
            ],
            options={
                "ordering": ["-last_updated"],
                "indexes": [
                    models.Index(fields=["condition", "status"], name="research_cl_conditi_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="MedicalEvidence",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("pubmed_id", models.CharField(db_index=True, max_length=20, unique=True)),
                ("title", models.CharField(max_length=500)),
                ("abstract", models.TextField()),
                ("authors", models.JSONField(default=list)),
                ("journal", models.CharField(blank=True, default="", max_length=255)),
                ("year", models.PositiveIntegerField(db_index=True)),
                ("doi", models.CharField(blank=True, default="", max_length=100)),
                ("evidence_level", models.CharField(
                    choices=[
                        ("A", "Level A \u2014 Systematic reviews / RCTs"),
                        ("B", "Level B \u2014 Cohort studies / Case-control"),
                        ("C", "Level C \u2014 Expert opinion / Case series"),
                    ],
                    default="B",
                    max_length=2,
                )),
                ("conditions", models.JSONField(blank=True, default=list)),
                ("mesh_terms", models.JSONField(blank=True, default=list)),
                ("relevance_score", models.FloatField(default=0.0)),
                ("citation_count", models.PositiveIntegerField(default=0)),
                ("embedding_id", models.CharField(blank=True, db_index=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("indexed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-year", "-citation_count"],
                "indexes": [
                    models.Index(fields=["year", "evidence_level"], name="research_me_year_ev_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ResearchQuery",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("query_text", models.TextField()),
                ("query_type", models.CharField(
                    choices=[
                        ("literature", "Literature Search"),
                        ("trial_matching", "Clinical Trial Matching"),
                        ("guideline", "Clinical Guideline Lookup"),
                        ("qa", "Clinical Q&A"),
                        ("drug_interaction", "Drug Interaction Check"),
                        ("differential_dx", "Differential Diagnosis"),
                    ],
                    db_index=True,
                    default="qa",
                    max_length=25,
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("processing", "Processing"),
                        ("complete", "Complete"),
                        ("error", "Error"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=15,
                )),
                ("result", models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='{"summary": "", "recommendations": [], "evidence_strength": ""}',
                )),
                ("sources", models.JSONField(
                    blank=True,
                    default=list,
                    help_text='[{"title": "", "pmid": "", "doi": "", "url": "", "relevance_score": 0.9}]',
                )),
                ("evidence_level", models.CharField(blank=True, default="", max_length=2)),
                ("error_message", models.TextField(blank=True, default="")),
                ("model_used", models.CharField(blank=True, default="", max_length=100)),
                ("langfuse_trace_id", models.CharField(blank=True, default="", max_length=100)),
                ("processing_time_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("patient", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="research_queries",
                    to="fhir.fhirpatient",
                )),
                ("requested_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="research_queries",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to="tenants.organization",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "status", "created_at"], name="research_rq_tenant_idx"),
                    models.Index(fields=["requested_by", "created_at"], name="research_rq_reqby_idx"),
                ],
            },
        ),
    ]
