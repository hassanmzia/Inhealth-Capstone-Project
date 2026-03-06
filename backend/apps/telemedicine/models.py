"""
Telemedicine models — video consultation sessions with AI-assisted notes.
"""

import uuid

from django.db import models
from django.utils import timezone


class VideoSession(models.Model):
    """
    Video consultation session between a patient and provider.
    Supports scheduling, real-time tracking, and AI-generated clinical notes.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        db_index=True,
    )
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="video_sessions",
    )
    provider = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="video_sessions",
    )

    session_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="External video platform session identifier",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )

    # Timing
    scheduled_at = models.DateTimeField(db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    # Recording & AI
    recording_url = models.URLField(max_length=500, blank=True, default="")
    ai_notes = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"summary": "...", "soap": {...}, "icd10_suggestions": [...]}',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "scheduled_at"]),
            models.Index(fields=["patient", "scheduled_at"]),
            models.Index(fields=["provider", "scheduled_at"]),
        ]

    def __str__(self):
        return f"VideoSession {self.session_id} — {self.patient} ({self.status})"

    def start(self):
        """Mark the session as active."""
        self.status = self.Status.ACTIVE
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def end(self):
        """Mark the session as completed and calculate duration."""
        self.status = self.Status.COMPLETED
        self.ended_at = timezone.now()
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)
        self.save(update_fields=["status", "ended_at", "duration_minutes", "updated_at"])
