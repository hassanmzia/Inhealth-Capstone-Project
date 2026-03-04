"""
Clinical workflow models — encounters, care gaps, smart order sets.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class Encounter(models.Model):
    """
    Clinical encounter record, extending FHIR encounter with structured clinical documentation.
    """

    class EncounterType(models.TextChoices):
        OUTPATIENT = "outpatient", "Outpatient"
        INPATIENT = "inpatient", "Inpatient"
        EMERGENCY = "emergency", "Emergency"
        TELEHEALTH = "telehealth", "Telehealth / Virtual"
        HOME_HEALTH = "home_health", "Home Health"
        SKILLED_NURSING = "skilled_nursing", "Skilled Nursing Facility"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey("fhir.FHIRPatient", on_delete=models.CASCADE, related_name="clinical_encounters")
    provider = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_encounters",
    )
    fhir_encounter_id = models.CharField(max_length=64, blank=True, default="")

    encounter_type = models.CharField(max_length=20, choices=EncounterType.choices, default=EncounterType.OUTPATIENT)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANNED, db_index=True)

    # Timing
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    # Clinical documentation (SOAP note components)
    chief_complaint = models.TextField(blank=True, default="")
    hpi = models.TextField(
        blank=True,
        default="",
        verbose_name="History of Present Illness",
    )
    review_of_systems = models.JSONField(default=dict, blank=True)
    physical_exam = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"general": "NAD", "vitals": {...}, "cardiovascular": "", "respiratory": ""}',
    )
    assessment = models.TextField(blank=True, default="")
    treatment_plan = models.TextField(blank=True, default="")

    # Diagnoses
    icd10_primary = models.CharField(max_length=20, blank=True, default="", db_index=True)
    icd10_primary_display = models.CharField(max_length=255, blank=True, default="")
    icd10_secondary = ArrayField(models.CharField(max_length=20), default=list, blank=True)

    # Orders placed during this encounter
    orders_placed = models.JSONField(default=list, blank=True)

    # AI assistance
    ai_scribe_notes = models.TextField(blank=True, default="")
    ai_suggested_codes = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_datetime"]
        indexes = [
            models.Index(fields=["tenant", "patient", "start_datetime"]),
            models.Index(fields=["provider", "start_datetime"]),
        ]

    def __str__(self):
        return f"Encounter: {self.patient} ({self.encounter_type}) — {self.start_datetime:%Y-%m-%d}"


class CareGap(models.Model):
    """
    Clinical care gaps — preventive and chronic care quality measures.
    Identifies when a patient is overdue for a specific clinical action.
    """

    class GapType(models.TextChoices):
        A1C_OVERDUE = "A1C_overdue", "A1C Test Overdue (>3 months)"
        BP_CHECK_OVERDUE = "BP_check_overdue", "Blood Pressure Check Overdue"
        EYE_EXAM_OVERDUE = "eye_exam_overdue", "Diabetic Eye Exam Overdue"
        FOOT_EXAM_OVERDUE = "foot_exam_overdue", "Diabetic Foot Exam Overdue"
        NEPHROPATHY_SCREEN = "nephropathy_screen", "Nephropathy Screening Overdue"
        STATIN_NOT_PRESCRIBED = "statin_not_prescribed", "Statin Not Prescribed (ASCVD risk)"
        ACE_ARB_NOT_PRESCRIBED = "ace_arb_not_prescribed", "ACE-I/ARB Not Prescribed (DM + HTN)"
        IMMUNIZATION_OVERDUE = "immunization_overdue", "Immunization Overdue"
        COLONOSCOPY_OVERDUE = "colonoscopy_overdue", "Colonoscopy Overdue"
        MAMMOGRAM_OVERDUE = "mammogram_overdue", "Mammogram Overdue"
        DEPRESSION_SCREEN = "depression_screen", "Depression Screening Overdue (PHQ-9)"
        SMOKING_CESSATION = "smoking_cessation", "Smoking Cessation Counseling Needed"
        MEDICATION_ADHERENCE = "medication_adherence", "Medication Adherence Gap"
        FOLLOW_UP_MISSED = "follow_up_missed", "Missed Follow-Up Visit"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        DEFERRED = "deferred", "Deferred"
        PATIENT_DECLINED = "patient_declined", "Patient Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey("fhir.FHIRPatient", on_delete=models.CASCADE, related_name="care_gaps")
    gap_type = models.CharField(max_length=40, choices=GapType.choices, db_index=True)
    last_completed = models.DateField(null=True, blank=True)
    due_date = models.DateField(db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    ai_recommendation = models.TextField(blank=True, default="")
    evidence_reference = models.CharField(max_length=255, blank=True, default="")
    deferred_until = models.DateField(null=True, blank=True)
    deferred_by_id = models.UUIDField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "due_date"]
        unique_together = [("patient", "gap_type", "status")]
        indexes = [
            models.Index(fields=["tenant", "status", "priority"]),
            models.Index(fields=["patient", "status"]),
        ]

    def __str__(self):
        return f"Care Gap: {self.get_gap_type_display()} for {self.patient} (due: {self.due_date})"


class SmartOrderSet(models.Model):
    """
    AI-powered smart order sets for evidence-based clinical decision support.
    Maps conditions to recommended labs, medications, imaging, and referrals.
    """

    class EvidenceLevel(models.TextChoices):
        A = "A", "Level A — Strong evidence (RCTs)"
        B = "B", "Level B — Moderate evidence"
        C = "C", "Level C — Expert consensus"
        D = "D", "Level D — Limited evidence"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=255)
    condition = models.CharField(max_length=20, db_index=True)  # ICD-10
    condition_display = models.CharField(max_length=255)
    orders = models.JSONField(
        default=dict,
        help_text="""
        {
          "medications": [{"name": "Metformin 500mg", "sig": "BID with meals", "rxnorm": "860975"}],
          "labs": [{"name": "HbA1c", "loinc": "4548-4", "frequency": "every 3 months"}],
          "imaging": [],
          "referrals": [{"specialty": "Endocrinology", "reason": "Uncontrolled DM"}],
          "patient_education": ["Diabetes management", "Carb counting"]
        }
        """,
    )
    evidence_level = models.CharField(max_length=2, choices=EvidenceLevel.choices, default=EvidenceLevel.B)
    source_guideline = models.CharField(max_length=255, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    created_by_ai = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["condition", "name"]
        indexes = [
            models.Index(fields=["condition", "is_active"]),
            models.Index(fields=["tenant", "condition"]),
        ]

    def __str__(self):
        return f"Order Set: {self.name} ({self.condition})"
