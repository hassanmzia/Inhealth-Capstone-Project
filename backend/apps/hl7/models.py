"""
HL7 v2 message models for InHealth.
"""

import uuid

from django.db import models


class HL7Message(models.Model):
    """Stores inbound and outbound HL7 v2 messages."""

    class MessageType(models.TextChoices):
        ADT_A01 = "ADT_A01", "ADT^A01 — Admit/Visit Notification"
        ADT_A02 = "ADT_A02", "ADT^A02 — Transfer a Patient"
        ADT_A03 = "ADT_A03", "ADT^A03 — Discharge Patient"
        ADT_A04 = "ADT_A04", "ADT^A04 — Register a Patient"
        ADT_A08 = "ADT_A08", "ADT^A08 — Update Patient Information"
        ADT_A11 = "ADT_A11", "ADT^A11 — Cancel Admit"
        ORU_R01 = "ORU_R01", "ORU^R01 — Unsolicited Observation Message"
        ORM_O01 = "ORM_O01", "ORM^O01 — Order Message"
        MDM_T02 = "MDM_T02", "MDM^T02 — Original Document Notification"
        SIU_S12 = "SIU_S12", "SIU^S12 — Appointment Notification"
        BAR_P01 = "BAR_P01", "BAR^P01 — Add Patient Account"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        ERROR = "error", "Error"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )
    message_type = models.CharField(max_length=20, choices=MessageType.choices, db_index=True)
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hl7_messages",
    )
    raw_message = models.TextField()
    parsed_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    error_message = models.TextField(blank=True, default="")
    sending_application = models.CharField(max_length=100, blank=True, default="")
    sending_facility = models.CharField(max_length=100, blank=True, default="")
    message_control_id = models.CharField(max_length=50, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["tenant", "message_type", "created_at"]),
        ]

    def __str__(self):
        return f"HL7 {self.message_type} [{self.status}] — {self.created_at:%Y-%m-%d %H:%M}"
