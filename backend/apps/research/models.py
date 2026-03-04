"""
Research models — literature queries, clinical trial matching, medical evidence.
"""

import uuid

from django.db import models
from django.utils import timezone


class ResearchQuery(models.Model):
    """
    Research and clinical evidence queries submitted by clinicians.
    Processed by the Research Agent using RAG + PubMed.
    """

    class QueryType(models.TextChoices):
        LITERATURE = "literature", "Literature Search"
        TRIAL_MATCHING = "trial_matching", "Clinical Trial Matching"
        GUIDELINE = "guideline", "Clinical Guideline Lookup"
        QA = "qa", "Clinical Q&A"
        DRUG_INTERACTION = "drug_interaction", "Drug Interaction Check"
        DIFFERENTIAL_DIAGNOSIS = "differential_dx", "Differential Diagnosis"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETE = "complete", "Complete"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="research_queries",
    )
    query_text = models.TextField()
    query_type = models.CharField(max_length=25, choices=QueryType.choices, default=QueryType.QA, db_index=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True)

    result = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"summary": "", "recommendations": [], "evidence_strength": ""}',
    )
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"title": "", "pmid": "", "doi": "", "url": "", "relevance_score": 0.9}]',
    )
    evidence_level = models.CharField(max_length=2, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="research_queries",
    )

    # AI metadata
    model_used = models.CharField(max_length=100, blank=True, default="")
    langfuse_trace_id = models.CharField(max_length=100, blank=True, default="")
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "created_at"]),
            models.Index(fields=["requested_by", "created_at"]),
        ]

    def __str__(self):
        return f"Research ({self.query_type}): {self.query_text[:50]}..."


class ClinicalTrial(models.Model):
    """
    Clinical trial records synced from ClinicalTrials.gov.
    Used for patient matching by the Research Agent.
    """

    class Phase(models.TextChoices):
        PHASE_1 = "Phase 1", "Phase 1"
        PHASE_2 = "Phase 2", "Phase 2"
        PHASE_3 = "Phase 3", "Phase 3"
        PHASE_4 = "Phase 4", "Phase 4"
        NOT_APPLICABLE = "N/A", "Not Applicable"

    class Status(models.TextChoices):
        RECRUITING = "Recruiting", "Recruiting"
        NOT_YET_RECRUITING = "Not yet recruiting", "Not Yet Recruiting"
        ACTIVE_NOT_RECRUITING = "Active, not recruiting", "Active, Not Recruiting"
        COMPLETED = "Completed", "Completed"
        TERMINATED = "Terminated", "Terminated"
        SUSPENDED = "Suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nct_id = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    brief_summary = models.TextField(blank=True, default="")
    condition = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.RECRUITING, db_index=True)
    phase = models.CharField(max_length=20, choices=Phase.choices, default=Phase.PHASE_2)

    eligibility_criteria = models.JSONField(
        default=dict,
        help_text='{"inclusion": [], "exclusion": [], "age_min": 18, "age_max": 75, "accepts_healthy_volunteers": false}',
    )
    locations = models.JSONField(
        default=list,
        help_text='[{"facility": "", "city": "", "state": "", "country": "", "zip": ""}]',
    )
    contact = models.JSONField(
        default=dict,
        help_text='{"name": "", "email": "", "phone": ""}',
    )
    sponsor = models.CharField(max_length=255, blank=True, default="")
    primary_outcome = models.TextField(blank=True, default="")
    enrollment_target = models.PositiveIntegerField(null=True, blank=True)

    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Vector embedding ID for semantic search
    embedding_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["-last_updated"]
        indexes = [
            models.Index(fields=["condition", "status"]),
        ]

    def __str__(self):
        return f"Trial {self.nct_id}: {self.title[:60]}"


class MedicalEvidence(models.Model):
    """
    Medical literature evidence from PubMed and other sources.
    Stored with vector embeddings for semantic search (RAG).
    """

    class EvidenceLevel(models.TextChoices):
        A = "A", "Level A — Systematic reviews / RCTs"
        B = "B", "Level B — Cohort studies / Case-control"
        C = "C", "Level C — Expert opinion / Case series"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pubmed_id = models.CharField(max_length=20, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    authors = models.JSONField(default=list)
    journal = models.CharField(max_length=255, blank=True, default="")
    year = models.PositiveIntegerField(db_index=True)
    doi = models.CharField(max_length=100, blank=True, default="")

    evidence_level = models.CharField(max_length=2, choices=EvidenceLevel.choices, default=EvidenceLevel.B)
    conditions = models.JSONField(default=list, blank=True)  # List of ICD-10 codes
    mesh_terms = models.JSONField(default=list, blank=True)

    relevance_score = models.FloatField(default=0.0)
    citation_count = models.PositiveIntegerField(default=0)

    # Qdrant vector DB
    embedding_id = models.CharField(max_length=100, blank=True, default="", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    indexed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "-citation_count"]
        indexes = [
            models.Index(fields=["year", "evidence_level"]),
        ]

    def __str__(self):
        return f"PubMed {self.pubmed_id}: {self.title[:60]} ({self.year})"
