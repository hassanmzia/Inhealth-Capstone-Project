"""
Notification models for InHealth — multi-channel alert system.
"""

import uuid

from django.db import models
from django.utils import timezone


class NotificationTemplate(models.Model):
    """
    Templated notifications with health literacy level variants.
    Supports multilingual, multi-channel messages.
    """

    class HealthLiteracyLevel(models.IntegerChoices):
        MINIMAL = 1, "Minimal (< 6th grade)"
        LIMITED = 2, "Limited (6th-8th grade)"
        ADEQUATE = 3, "Adequate (high school)"
        PROFICIENT = 4, "Proficient (college)"
        EXPERT = 5, "Expert (healthcare professional)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=20)
    health_literacy_level = models.IntegerField(choices=HealthLiteracyLevel.choices, default=3)
    language = models.CharField(max_length=10, default="en")
    subject_template = models.CharField(max_length=255)
    body_template = models.TextField()
    channel = models.CharField(max_length=20, default="all")  # sms/email/push/all
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("name", "health_literacy_level", "language")]

    def __str__(self):
        return f"{self.name} (HL{self.health_literacy_level}/{self.language})"

    def render(self, context: dict) -> tuple:
        """Render subject and body with context variables."""
        subject = self.subject_template.format(**context)
        body = self.body_template.format(**context)
        return subject, body


class Notification(models.Model):
    """
    Individual notification instance — one per patient per alert event.
    """

    class NotificationType(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical — Immediate Action Required"
        URGENT = "URGENT", "Urgent — Action Required Today"
        SOON = "SOON", "Soon — Action Required This Week"
        ROUTINE = "ROUTINE", "Routine — General Information"
        EDUCATIONAL = "EDUCATIONAL", "Educational Content"
        APPOINTMENT = "APPOINTMENT", "Appointment Reminder"

    class Channel(models.TextChoices):
        SMS = "sms", "SMS Text Message"
        EMAIL = "email", "Email"
        PUSH = "push", "Push Notification"
        EHR = "ehr", "In-App EHR Alert"
        PHONE = "phone", "Phone Call"
        ALL = "all", "All Channels"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        ACKNOWLEDGED = "acknowledged", "Acknowledged by Patient"
        ESCALATED = "escalated", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.ROUTINE,
        db_index=True,
    )
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)

    title = models.CharField(max_length=255)
    body = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"loinc_code": "4548-4", "value": 9.2, "threshold": 7.0}',
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # AI source
    agent_source = models.CharField(max_length=50, blank=True, default="")

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True, default="")
    retry_count = models.PositiveSmallIntegerField(default=0)
    external_message_id = models.CharField(max_length=100, blank=True, default="")

    # Acknowledgement
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_notifications",
    )

    # Escalation
    escalation_level = models.PositiveSmallIntegerField(default=0)
    escalated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "notification_type", "status"]),
            models.Index(fields=["patient", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.patient} ({self.status})"

    def mark_sent(self, external_id: str = ""):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.external_message_id = external_id
        self.save(update_fields=["status", "sent_at", "external_message_id", "updated_at"])

    def mark_failed(self, reason: str):
        self.status = self.Status.FAILED
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.retry_count += 1
        self.save(update_fields=["status", "failed_at", "failure_reason", "retry_count", "updated_at"])

    def acknowledge(self, user=None):
        self.status = self.Status.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=["status", "acknowledged_at", "acknowledged_by", "updated_at"])
