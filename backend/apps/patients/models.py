"""
Extended patient models beyond FHIR — demographics, engagement, devices.
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class PatientDemographics(models.Model):
    """
    Extended patient demographics not in FHIR baseline.
    Links to FHIRPatient as OneToOne.
    """

    class Race(models.TextChoices):
        WHITE = "white", "White"
        BLACK_AFRICAN_AMERICAN = "black_aa", "Black or African American"
        AMERICAN_INDIAN_ALASKA_NATIVE = "aian", "American Indian or Alaska Native"
        ASIAN = "asian", "Asian"
        NATIVE_HAWAIIAN_PACIFIC_ISLANDER = "nhpi", "Native Hawaiian or Pacific Islander"
        MULTIRACIAL = "multiracial", "Two or More Races"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown / Not Reported"

    class Ethnicity(models.TextChoices):
        HISPANIC_LATINO = "hispanic_latino", "Hispanic or Latino"
        NOT_HISPANIC_LATINO = "not_hispanic_latino", "Not Hispanic or Latino"
        UNKNOWN = "unknown", "Unknown / Not Reported"

    class MaritalStatus(models.TextChoices):
        SINGLE = "S", "Single"
        MARRIED = "M", "Married"
        DIVORCED = "D", "Divorced"
        WIDOWED = "W", "Widowed"
        SEPARATED = "L", "Legally Separated"
        DOMESTIC_PARTNER = "T", "Domestic Partner"
        UNKNOWN = "UNK", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="demographics",
    )

    # Insurance
    insurance_provider = models.CharField(max_length=100, blank=True, default="")
    insurance_policy_number = models.CharField(max_length=50, blank=True, default="")
    insurance_group_number = models.CharField(max_length=50, blank=True, default="")
    insurance_effective_date = models.DateField(null=True, blank=True)
    insurance_expiration_date = models.DateField(null=True, blank=True)
    secondary_insurance_provider = models.CharField(max_length=100, blank=True, default="")
    secondary_policy_number = models.CharField(max_length=50, blank=True, default="")

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, default="")
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, default="")

    # Care team
    preferred_pharmacy = models.CharField(max_length=255, blank=True, default="")
    preferred_pharmacy_phone = models.CharField(max_length=20, blank=True, default="")
    primary_care_physician = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="demographic_pcp_patients",
    )

    # Social determinants (basic)
    race = models.CharField(max_length=20, choices=Race.choices, default=Race.UNKNOWN)
    ethnicity = models.CharField(max_length=30, choices=Ethnicity.choices, default=Ethnicity.UNKNOWN)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices, default=MaritalStatus.UNKNOWN)

    # Education and occupation
    education_level = models.CharField(max_length=100, blank=True, default="")
    occupation = models.CharField(max_length=100, blank=True, default="")

    # Advance directives
    has_advance_directive = models.BooleanField(null=True, blank=True)
    advance_directive_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient Demographics"
        verbose_name_plural = "Patient Demographics"

    def __str__(self):
        return f"Demographics for {self.patient}"


class PatientEngagement(models.Model):
    """
    Tracks patient engagement metrics, goals, and achievements.
    Used by the Patient Engagement Agent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="engagement",
    )

    engagement_score = models.FloatField(default=50.0)  # 0-100
    health_goals = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"goal": "Reduce A1C to <7.0", "target": 7.0, "current": 8.2, "deadline": "2025-06-01"}]',
    )
    achievements = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"badge": "A1C_Warrior", "earned_at": "2024-01-15", "description": ""}]',
    )
    streak_days = models.PositiveIntegerField(default=0)
    last_app_login = models.DateTimeField(null=True, blank=True)
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"sms": true, "email": true, "push": true, "preferred_time": "09:00", "frequency": "daily"}',
    )
    total_messages_sent = models.PositiveIntegerField(default=0)
    total_messages_acknowledged = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient Engagement"

    def __str__(self):
        return f"Engagement for {self.patient} (score: {self.engagement_score:.0f})"

    @property
    def acknowledgement_rate(self) -> float:
        if self.total_messages_sent == 0:
            return 0.0
        return self.total_messages_acknowledged / self.total_messages_sent

    def update_engagement_score(self):
        """Recalculate engagement score based on recent activity."""
        score = 0.0
        # Streak component (max 25 points)
        score += min(self.streak_days * 2, 25)
        # Acknowledgement rate (max 25 points)
        score += self.acknowledgement_rate * 25
        # Goals met (max 25 points)
        if self.health_goals:
            met = sum(1 for g in self.health_goals if g.get("status") == "met")
            score += (met / len(self.health_goals)) * 25
        # Recent login (max 25 points)
        if self.last_app_login:
            days_since = (timezone.now() - self.last_app_login).days
            score += max(0, 25 - days_since * 5)

        self.engagement_score = min(100.0, max(0.0, score))
        self.save(update_fields=["engagement_score", "updated_at"])


class DeviceRegistration(models.Model):
    """
    Registered patient-connected medical devices.
    CGM, smartwatch, BP monitor, pulse oximeter, etc.
    """

    class DeviceType(models.TextChoices):
        CGM = "cgm", "Continuous Glucose Monitor"
        SMARTWATCH = "smartwatch", "Smartwatch / Fitness Tracker"
        BP_MONITOR = "bp_monitor", "Blood Pressure Monitor"
        PULSE_OXIMETER = "pulse_oximeter", "Pulse Oximeter"
        WEIGHT_SCALE = "weight_scale", "Smart Weight Scale"
        INSULIN_PUMP = "insulin_pump", "Insulin Pump"
        ECG_MONITOR = "ecg_monitor", "ECG Monitor"
        SPIROMETER = "spirometer", "Spirometer"
        THERMOMETER = "thermometer", "Smart Thermometer"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="devices",
    )
    device_type = models.CharField(max_length=20, choices=DeviceType.choices, db_index=True)
    device_id = models.CharField(max_length=100, unique=True, db_index=True)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(max_length=100, blank=True, default="")
    firmware_version = models.CharField(max_length=50, blank=True, default="")

    # FHIR Device identifier
    fhir_device_id = models.CharField(max_length=64, blank=True, default="")

    # Sync metadata
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_frequency_minutes = models.PositiveIntegerField(default=15)
    is_active = models.BooleanField(default=True, db_index=True)

    # Configuration
    config = models.JSONField(default=dict, blank=True)
    alerts_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"glucose_low": 70, "glucose_high": 250, "systolic_high": 160}',
    )

    registered_at = models.DateTimeField(auto_now_add=True)
    deregistered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-registered_at"]
        indexes = [
            models.Index(fields=["patient", "device_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_device_type_display()} ({self.manufacturer} {self.model}) — {self.patient}"
