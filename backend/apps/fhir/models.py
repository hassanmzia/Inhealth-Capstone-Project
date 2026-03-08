"""
FHIR R4 Django models for InHealth Chronic Care.
Each model corresponds to a FHIR resource type with tenant isolation.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class FHIRBase(models.Model):
    """Abstract base for all FHIR resource models."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        db_index=True,
    )
    fhir_id = models.CharField(max_length=64, unique=True, db_index=True)
    meta_version_id = models.CharField(max_length=20, default="1")
    meta_last_updated = models.DateTimeField(default=timezone.now)
    meta_profile = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    raw_resource = models.JSONField(default=dict, blank=True)  # Full FHIR JSON
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.fhir_id:
            self.fhir_id = str(uuid.uuid4())
        self.meta_last_updated = timezone.now()
        # Increment version only on UPDATE (not on initial CREATE).
        # Use _state.adding because UUID PKs are pre-populated, making
        # `if self.pk` always True even for brand-new unsaved instances.
        if not self._state.adding:
            try:
                current = self.__class__.objects.get(pk=self.pk)
                self.meta_version_id = str(int(current.meta_version_id) + 1)
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class FHIRPatient(FHIRBase):
    """FHIR R4 Patient resource."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    # Identity
    mrn = models.CharField(max_length=50, db_index=True)  # Medical Record Number
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True, default="")
    birth_date = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNKNOWN)
    deceased = models.BooleanField(default=False)
    deceased_date = models.DateField(null=True, blank=True)

    # Contact
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    # Address (FHIR Address type)
    address_line1 = models.CharField(max_length=255, blank=True, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=50, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=50, default="US")

    # Identifiers
    ssn_last4 = models.CharField(max_length=4, blank=True, default="")  # Only last 4 for display
    external_id = models.CharField(max_length=100, blank=True, default="")  # EHR system ID

    # Clinical metadata
    primary_care_provider = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_patients",
    )
    active = models.BooleanField(default=True, db_index=True)

    # Telecom (FHIR format)
    telecom = models.JSONField(default=list, blank=True)

    # Communication preferences
    communication = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["tenant", "last_name", "first_name"]),
            models.Index(fields=["tenant", "mrn"]),
            models.Index(fields=["tenant", "birth_date"]),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} (MRN: {self.mrn})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class FHIRObservation(FHIRBase):
    """FHIR R4 Observation resource — vital signs, lab results, device readings."""

    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        PRELIMINARY = "preliminary", "Preliminary"
        FINAL = "final", "Final"
        AMENDED = "amended", "Amended"
        CORRECTED = "corrected", "Corrected"
        CANCELLED = "cancelled", "Cancelled"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="observations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FINAL)

    # LOINC code
    code_system = models.CharField(max_length=100, default="http://loinc.org")
    code = models.CharField(max_length=20, db_index=True)  # LOINC code
    display = models.CharField(max_length=255)

    # Value
    value_quantity = models.FloatField(null=True, blank=True)
    value_unit = models.CharField(max_length=50, blank=True, default="")
    value_string = models.CharField(max_length=500, blank=True, default="")
    value_codeable_concept = models.JSONField(null=True, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)

    # Reference range
    reference_range_low = models.FloatField(null=True, blank=True)
    reference_range_high = models.FloatField(null=True, blank=True)

    # Interpretation (normal/abnormal/critical)
    interpretation = models.CharField(max_length=20, blank=True, default="")

    # Timing
    effective_datetime = models.DateTimeField(db_index=True)
    issued = models.DateTimeField(default=timezone.now)

    # Performer
    performer_id = models.UUIDField(null=True, blank=True)

    # Components (for panel observations like BP)
    components = models.JSONField(default=list, blank=True)

    # Device source
    device_id = models.CharField(max_length=100, blank=True, default="")
    device_type = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["-effective_datetime"]
        indexes = [
            models.Index(fields=["patient", "code", "effective_datetime"]),
            models.Index(fields=["tenant", "code", "effective_datetime"]),
        ]

    def __str__(self):
        return f"{self.display}: {self.value_quantity} {self.value_unit} ({self.patient})"


class FHIRCondition(FHIRBase):
    """FHIR R4 Condition resource — diagnoses and problems."""

    class ClinicalStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        RECURRENCE = "recurrence", "Recurrence"
        RELAPSE = "relapse", "Relapse"
        INACTIVE = "inactive", "Inactive"
        REMISSION = "remission", "Remission"
        RESOLVED = "resolved", "Resolved"

    class VerificationStatus(models.TextChoices):
        UNCONFIRMED = "unconfirmed", "Unconfirmed"
        PROVISIONAL = "provisional", "Provisional"
        DIFFERENTIAL = "differential", "Differential"
        CONFIRMED = "confirmed", "Confirmed"
        REFUTED = "refuted", "Refuted"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="conditions")
    clinical_status = models.CharField(max_length=20, choices=ClinicalStatus.choices, default=ClinicalStatus.ACTIVE)
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.CONFIRMED)

    # ICD-10 / SNOMED
    code_system = models.CharField(max_length=100, default="http://hl7.org/fhir/sid/icd-10-cm")
    code = models.CharField(max_length=20, db_index=True)  # ICD-10 code
    display = models.CharField(max_length=255)
    snomed_code = models.CharField(max_length=20, blank=True, default="")

    # Categorization
    category = models.CharField(max_length=50, default="encounter-diagnosis")
    severity = models.CharField(max_length=20, blank=True, default="")

    # Timing
    onset_datetime = models.DateTimeField(null=True, blank=True)
    onset_string = models.CharField(max_length=100, blank=True, default="")
    abatement_datetime = models.DateTimeField(null=True, blank=True)
    recorded_date = models.DateTimeField(default=timezone.now)

    # Recorder
    recorder_id = models.UUIDField(null=True, blank=True)

    # Notes
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-recorded_date"]
        indexes = [
            models.Index(fields=["patient", "code", "clinical_status"]),
            models.Index(fields=["tenant", "code"]),
        ]

    def __str__(self):
        return f"{self.display} ({self.code}) — {self.patient}"


class FHIRMedicationRequest(FHIRBase):
    """FHIR R4 MedicationRequest resource — prescriptions and medication orders."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on-hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        STOPPED = "stopped", "Stopped"
        DRAFT = "draft", "Draft"
        UNKNOWN = "unknown", "Unknown"

    class Intent(models.TextChoices):
        PROPOSAL = "proposal", "Proposal"
        PLAN = "plan", "Plan"
        ORDER = "order", "Order"
        ORIGINAL_ORDER = "original-order", "Original Order"
        REFLEX_ORDER = "reflex-order", "Reflex Order"
        FILLER_ORDER = "filler-order", "Filler Order"
        INSTANCE_ORDER = "instance-order", "Instance Order"
        OPTION = "option", "Option"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="medication_requests")
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    intent = models.CharField(max_length=20, choices=Intent.choices, default=Intent.ORDER)

    # Medication
    medication_code = models.CharField(max_length=20, db_index=True)  # RxNorm
    medication_display = models.CharField(max_length=255)
    medication_system = models.CharField(max_length=100, default="http://www.nlm.nih.gov/research/umls/rxnorm")

    # Dosage
    dosage_text = models.CharField(max_length=500, blank=True, default="")
    dose_quantity = models.FloatField(null=True, blank=True)
    dose_unit = models.CharField(max_length=50, blank=True, default="")
    frequency = models.CharField(max_length=100, blank=True, default="")
    route = models.CharField(max_length=100, blank=True, default="")
    as_needed = models.BooleanField(default=False)

    # Dispense
    quantity_value = models.FloatField(null=True, blank=True)
    days_supply = models.PositiveIntegerField(null=True, blank=True)
    number_of_repeats_allowed = models.PositiveIntegerField(null=True, blank=True)

    # Prescriber
    requester_id = models.UUIDField(null=True, blank=True)

    # Timing
    authored_on = models.DateTimeField(default=timezone.now)
    validity_period_start = models.DateTimeField(null=True, blank=True)
    validity_period_end = models.DateTimeField(null=True, blank=True)

    # Reason
    reason_code = models.CharField(max_length=20, blank=True, default="")
    reason_display = models.CharField(max_length=255, blank=True, default="")

    # Notes
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-authored_on"]
        indexes = [
            models.Index(fields=["patient", "status", "authored_on"]),
            models.Index(fields=["tenant", "medication_code"]),
        ]

    def __str__(self):
        return f"{self.medication_display} for {self.patient}"


class FHIRDiagnosticReport(FHIRBase):
    """FHIR R4 DiagnosticReport resource — lab reports, radiology, etc."""

    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        PARTIAL = "partial", "Partial"
        PRELIMINARY = "preliminary", "Preliminary"
        FINAL = "final", "Final"
        AMENDED = "amended", "Amended"
        CORRECTED = "corrected", "Corrected"
        APPENDED = "appended", "Appended"
        CANCELLED = "cancelled", "Cancelled"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="diagnostic_reports")
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.FINAL)

    # Report classification
    category_code = models.CharField(max_length=20, blank=True, default="")
    code = models.CharField(max_length=20, db_index=True)  # LOINC
    display = models.CharField(max_length=255)

    # Timing
    effective_datetime = models.DateTimeField(db_index=True)
    issued = models.DateTimeField(default=timezone.now)

    # Results (FK to Observations)
    results = models.ManyToManyField(FHIRObservation, blank=True, related_name="diagnostic_reports")

    # Conclusion
    conclusion = models.TextField(blank=True, default="")
    conclusion_code = models.CharField(max_length=20, blank=True, default="")

    # Performer
    performer_id = models.UUIDField(null=True, blank=True)

    # Presented form (PDF attachment metadata)
    presented_form = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-effective_datetime"]

    def __str__(self):
        return f"{self.display} for {self.patient} ({self.effective_datetime:%Y-%m-%d})"


class FHIRAppointment(FHIRBase):
    """FHIR R4 Appointment resource."""

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        PENDING = "pending", "Pending"
        BOOKED = "booked", "Booked"
        ARRIVED = "arrived", "Arrived"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"
        NOSHOW = "noshow", "No Show"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        CHECKED_IN = "checked-in", "Checked In"
        WAITLIST = "waitlist", "Waitlist"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="appointments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED, db_index=True)

    # Appointment type
    service_type = models.CharField(max_length=100, blank=True, default="")
    specialty = models.CharField(max_length=100, blank=True, default="")
    appointment_type = models.CharField(max_length=50, blank=True, default="")

    reason_code = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(blank=True, default="")

    # Timing
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField()
    minutes_duration = models.PositiveIntegerField(null=True, blank=True)

    # Participants
    provider_id = models.UUIDField(null=True, blank=True, db_index=True)
    location = models.CharField(max_length=255, blank=True, default="")

    # Telehealth
    is_telehealth = models.BooleanField(default=False)
    telehealth_url = models.URLField(blank=True, default="")

    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-start"]
        indexes = [
            models.Index(fields=["tenant", "start", "status"]),
            models.Index(fields=["patient", "start"]),
        ]

    def __str__(self):
        return f"Appt: {self.patient} on {self.start:%Y-%m-%d %H:%M}"


class FHIRCarePlan(FHIRBase):
    """FHIR R4 CarePlan resource."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ON_HOLD = "on-hold", "On Hold"
        REVOKED = "revoked", "Revoked"
        COMPLETED = "completed", "Completed"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        UNKNOWN = "unknown", "Unknown"

    class Intent(models.TextChoices):
        PROPOSAL = "proposal", "Proposal"
        PLAN = "plan", "Plan"
        ORDER = "order", "Order"
        OPTION = "option", "Option"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="care_plans")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    intent = models.CharField(max_length=10, choices=Intent.choices, default=Intent.PLAN)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Categories: assess-plan, longitudinal, etc.
    category = models.CharField(max_length=50, default="assess-plan")

    # Addresses (conditions this plan targets)
    addresses = models.ManyToManyField(FHIRCondition, blank=True, related_name="care_plans")

    # Goals, activities (FHIR structured)
    goals = models.JSONField(default=list, blank=True)
    activities = models.JSONField(default=list, blank=True)

    # Timing
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)

    # Author
    author_id = models.UUIDField(null=True, blank=True)

    # AI-generated flag
    ai_generated = models.BooleanField(default=False)
    ai_model_used = models.CharField(max_length=100, blank=True, default="")

    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Care Plan: {self.title} for {self.patient}"


class FHIRAllergyIntolerance(FHIRBase):
    """FHIR R4 AllergyIntolerance resource."""

    class ClinicalStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        RESOLVED = "resolved", "Resolved"

    class VerificationStatus(models.TextChoices):
        UNCONFIRMED = "unconfirmed", "Unconfirmed"
        CONFIRMED = "confirmed", "Confirmed"
        REFUTED = "refuted", "Refuted"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"

    class Category(models.TextChoices):
        FOOD = "food", "Food"
        MEDICATION = "medication", "Medication"
        ENVIRONMENT = "environment", "Environment"
        BIOLOGIC = "biologic", "Biologic"

    class Criticality(models.TextChoices):
        LOW = "low", "Low"
        HIGH = "high", "High"
        UNABLE_TO_ASSESS = "unable-to-assess", "Unable to Assess"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="allergies")
    clinical_status = models.CharField(max_length=20, choices=ClinicalStatus.choices, default=ClinicalStatus.ACTIVE)
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.CONFIRMED)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.MEDICATION)
    criticality = models.CharField(max_length=20, choices=Criticality.choices, default=Criticality.LOW)

    # Substance
    code = models.CharField(max_length=20, db_index=True)  # RxNorm or SNOMED
    display = models.CharField(max_length=255)
    code_system = models.CharField(max_length=100, blank=True, default="")

    # Reaction
    reactions = models.JSONField(default=list, blank=True)

    # Timing
    onset_datetime = models.DateTimeField(null=True, blank=True)
    recorded_date = models.DateTimeField(default=timezone.now)
    recorder_id = models.UUIDField(null=True, blank=True)

    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-recorded_date"]

    def __str__(self):
        return f"Allergy: {self.display} ({self.criticality}) — {self.patient}"


class FHIREncounter(FHIRBase):
    """FHIR R4 Encounter resource."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ARRIVED = "arrived", "Arrived"
        TRIAGED = "triaged", "Triaged"
        IN_PROGRESS = "in-progress", "In Progress"
        ON_LEAVE = "on-leave", "On Leave"
        FINISHED = "finished", "Finished"
        CANCELLED = "cancelled", "Cancelled"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        UNKNOWN = "unknown", "Unknown"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="fhir_encounters")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FINISHED, db_index=True)

    # Classification
    encounter_class = models.CharField(max_length=50, default="AMB")  # AMB/IMP/EMER/VR
    type_code = models.CharField(max_length=20, blank=True, default="")
    type_display = models.CharField(max_length=255, blank=True, default="")
    service_type = models.CharField(max_length=100, blank=True, default="")

    # Reason
    reason_code = models.CharField(max_length=20, blank=True, default="")
    reason_display = models.CharField(max_length=255, blank=True, default="")

    # Timing
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(null=True, blank=True)
    length_minutes = models.PositiveIntegerField(null=True, blank=True)

    # Participants
    participants = models.JSONField(default=list, blank=True)

    # Location
    location = models.JSONField(default=list, blank=True)

    # Discharge
    discharge_disposition = models.CharField(max_length=50, blank=True, default="")
    hospitalization = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-period_start"]

    def __str__(self):
        return f"Encounter: {self.encounter_class} — {self.patient} ({self.period_start:%Y-%m-%d})"


class FHIRProcedure(FHIRBase):
    """FHIR R4 Procedure resource."""

    class Status(models.TextChoices):
        PREPARATION = "preparation", "Preparation"
        IN_PROGRESS = "in-progress", "In Progress"
        NOT_DONE = "not-done", "Not Done"
        ON_HOLD = "on-hold", "On Hold"
        STOPPED = "stopped", "Stopped"
        COMPLETED = "completed", "Completed"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        UNKNOWN = "unknown", "Unknown"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="procedures")
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.COMPLETED)

    # CPT / SNOMED
    code = models.CharField(max_length=20, db_index=True)
    display = models.CharField(max_length=255)
    code_system = models.CharField(max_length=100, blank=True, default="")

    # Categorization
    category = models.CharField(max_length=50, blank=True, default="")

    # Timing
    performed_datetime = models.DateTimeField(db_index=True)

    # Performer
    performer_id = models.UUIDField(null=True, blank=True)

    # Body site
    body_site = models.JSONField(default=list, blank=True)

    # Outcome
    outcome_code = models.CharField(max_length=20, blank=True, default="")
    outcome_display = models.CharField(max_length=255, blank=True, default="")

    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-performed_datetime"]

    def __str__(self):
        return f"Procedure: {self.display} — {self.patient}"


class FHIRImmunization(FHIRBase):
    """FHIR R4 Immunization resource."""

    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"
        NOT_DONE = "not-done", "Not Done"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="immunizations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)

    # CVX code (vaccine)
    vaccine_code = models.CharField(max_length=20, db_index=True)  # CVX
    vaccine_display = models.CharField(max_length=255)

    # Timing
    occurrence_datetime = models.DateTimeField(db_index=True)

    # Lot / manufacturer
    lot_number = models.CharField(max_length=50, blank=True, default="")
    manufacturer = models.CharField(max_length=100, blank=True, default="")
    expiration_date = models.DateField(null=True, blank=True)

    # Dose
    dose_quantity_value = models.FloatField(null=True, blank=True)
    dose_quantity_unit = models.CharField(max_length=50, blank=True, default="")

    # Site / route
    site = models.CharField(max_length=100, blank=True, default="")
    route = models.CharField(max_length=100, blank=True, default="")

    performer_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-occurrence_datetime"]

    def __str__(self):
        return f"Immunization: {self.vaccine_display} — {self.patient}"


class FHIRDocumentReference(FHIRBase):
    """FHIR R4 DocumentReference resource — clinical notes, scanned documents."""

    class Status(models.TextChoices):
        CURRENT = "current", "Current"
        SUPERSEDED = "superseded", "Superseded"
        ENTERED_IN_ERROR = "entered-in-error", "Entered in Error"

    class DocStatus(models.TextChoices):
        PRELIMINARY = "preliminary", "Preliminary"
        FINAL = "final", "Final"
        AMENDED = "amended", "Amended"

    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, related_name="document_references")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CURRENT)
    doc_status = models.CharField(max_length=20, choices=DocStatus.choices, default=DocStatus.FINAL)

    # Type (LOINC)
    type_code = models.CharField(max_length=20, db_index=True)
    type_display = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True, default="")

    # Content
    content_url = models.URLField(blank=True, default="")  # S3/MinIO URL
    content_mime_type = models.CharField(max_length=100, default="text/plain")
    content_data = models.TextField(blank=True, default="")  # Base64 or plain text for notes
    content_title = models.CharField(max_length=255, blank=True, default="")

    # Timing
    date = models.DateTimeField(default=timezone.now, db_index=True)

    # Author
    author_id = models.UUIDField(null=True, blank=True)

    description = models.TextField(blank=True, default="")

    # Vector embedding ID for RAG
    embedding_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Document: {self.type_display} — {self.patient} ({self.date:%Y-%m-%d})"


class AgentActionLog(models.Model):
    """
    Audit log for all AI agent actions.
    Tracks every decision, recommendation, and intervention made by AI agents.
    """

    class AgentType(models.TextChoices):
        TRIAGE = "triage", "Triage Agent"
        MEDICATION = "medication", "Medication Safety Agent"
        CARE_PLAN = "care_plan", "Care Plan Agent"
        DIAGNOSTIC = "diagnostic", "Diagnostic Agent"
        RESEARCH = "research", "Research Agent"
        PATIENT_ENGAGEMENT = "patient_engagement", "Patient Engagement Agent"
        POPULATION_HEALTH = "population_health", "Population Health Agent"
        ORCHESTRATOR = "orchestrator", "Orchestrator Agent"

    class ActionType(models.TextChoices):
        ALERT_GENERATED = "alert_generated", "Alert Generated"
        RECOMMENDATION = "recommendation", "Recommendation Made"
        ORDER_SUGGESTED = "order_suggested", "Order Suggested"
        CARE_PLAN_UPDATED = "care_plan_updated", "Care Plan Updated"
        RISK_CALCULATED = "risk_calculated", "Risk Score Calculated"
        LITERATURE_SEARCHED = "literature_searched", "Literature Searched"
        MESSAGE_SENT = "message_sent", "Patient Message Sent"
        TOOL_CALLED = "tool_called", "Tool Called"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey(FHIRPatient, on_delete=models.CASCADE, null=True, blank=True, related_name="agent_actions")
    agent_type = models.CharField(max_length=30, choices=AgentType.choices, db_index=True)
    action_type = models.CharField(max_length=30, choices=ActionType.choices, db_index=True)
    action_details = models.JSONField(default=dict)
    input_context = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    model_used = models.CharField(max_length=100, blank=True, default="")
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    langfuse_trace_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_by_id = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    was_accepted = models.BooleanField(null=True, blank=True)

    # Clinician feedback on recommendation quality
    feedback_rating = models.SmallIntegerField(
        null=True,
        blank=True,
        help_text="Clinician quality rating: 1 (not helpful) or 2 (helpful)",
    )
    feedback_comment = models.TextField(blank=True, default="")
    feedback_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["patient", "agent_type", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.agent_type}] {self.action_type} at {self.created_at:%Y-%m-%d %H:%M}"
