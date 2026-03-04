"""
Billing models — insurance claims and Remote Patient Monitoring episodes.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class Claim(models.Model):
    """
    Insurance claim for clinical encounters.
    Supports standard CMS-1500 / UB-04 billing.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready to Submit"
        SUBMITTED = "submitted", "Submitted"
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        PAID = "paid", "Paid"
        PARTIAL_PAYMENT = "partial", "Partial Payment"
        VOIDED = "voided", "Voided"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey("fhir.FHIRPatient", on_delete=models.CASCADE, related_name="claims")
    encounter = models.ForeignKey(
        "clinical.Encounter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
    )

    # Billing codes
    cpt_codes = models.JSONField(
        default=list,
        help_text='[{"code": "99213", "description": "E/M Office Visit Level 3", "units": 1, "fee": 150.00}]',
    )
    icd10_codes = models.JSONField(
        default=list,
        help_text='["E11.9", "I10"]',
    )
    hcpcs_codes = models.JSONField(default=list, blank=True)
    modifier_codes = models.JSONField(default=list, blank=True)

    # Amounts
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allowed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    insurance_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    patient_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    adjustment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Insurance
    payer_name = models.CharField(max_length=255, blank=True, default="")
    payer_id = models.CharField(max_length=50, blank=True, default="")
    group_number = models.CharField(max_length=50, blank=True, default="")
    member_id = models.CharField(max_length=50, blank=True, default="")
    prior_auth_number = models.CharField(max_length=50, blank=True, default="")

    # Claim metadata
    claim_number = models.CharField(max_length=50, blank=True, default="", db_index=True)
    npi = models.CharField(max_length=10, blank=True, default="")
    service_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT, db_index=True)
    payer_response = models.JSONField(default=dict, blank=True)
    denial_reason = models.CharField(max_length=500, blank=True, default="")

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "service_date"]),
            models.Index(fields=["patient", "status"]),
        ]

    def __str__(self):
        return f"Claim {self.claim_number or self.id} — {self.patient} ({self.status})"


class RPMEpisode(models.Model):
    """
    Remote Patient Monitoring episode for RPM billing codes.
    Tracks monitoring minutes and devices used for CPT 99453/99454/99457/99458.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        SUSPENDED = "suspended", "Suspended"

    # CMS RPM billing codes
    RPM_BILLING_CODES = {
        "99453": "Remote monitoring setup and patient education (one-time)",
        "99454": "Device supply with daily recording/transmission, per 30-day period",
        "99457": "Remote physiologic monitoring, first 20 minutes/month",
        "99458": "Remote physiologic monitoring, additional 20 minutes/month",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey("fhir.FHIRPatient", on_delete=models.CASCADE, related_name="rpm_episodes")
    ordering_provider_id = models.UUIDField(null=True, blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Monitoring data
    monitoring_minutes = models.PositiveIntegerField(default=0)
    total_readings = models.PositiveIntegerField(default=0)
    devices_used = models.JSONField(
        default=list,
        help_text='[{"device_type": "cgm", "device_id": "...", "manufacturer": "Dexcom"}]',
    )

    # Billing
    billing_codes = models.JSONField(
        default=dict,
        help_text='{" 99453": {"eligible": true, "billed": false, "date": null}, "99454": {...}}',
    )
    monthly_summaries = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"month": "2024-01", "minutes": 35, "readings": 180, "99454_eligible": true}]',
    )

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["patient", "start_date"]),
        ]

    def __str__(self):
        return f"RPM Episode: {self.patient} ({self.start_date} — {self.end_date or 'ongoing'})"

    def add_monitoring_minutes(self, minutes: int):
        """Add monitoring minutes and check billing eligibility."""
        self.monitoring_minutes += minutes
        self.save(update_fields=["monitoring_minutes", "updated_at"])
        self._update_billing_eligibility()

    def _update_billing_eligibility(self):
        """Update which RPM codes are now billable based on accumulated minutes."""
        billing = self.billing_codes or {}

        # 99457: eligible after first 20 minutes in a calendar month
        if self.monitoring_minutes >= 20:
            if "99457" not in billing:
                billing["99457"] = {"eligible": True, "billed": False}

        # 99458: eligible after 40 total minutes (20 additional)
        if self.monitoring_minutes >= 40:
            if "99458" not in billing:
                billing["99458"] = {"eligible": True, "billed": False}

        self.billing_codes = billing
        self.save(update_fields=["billing_codes", "updated_at"])
