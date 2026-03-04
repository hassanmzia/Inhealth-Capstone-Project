"""
SDOH (Social Determinants of Health) models.
Screens and tracks non-clinical factors affecting patient health outcomes.
"""

import uuid

from django.db import models
from django.utils import timezone


class SDOHAssessment(models.Model):
    """
    SDOH screening assessment based on PRAPARE / AHC-HRSN protocol.
    Scores across five key SDOH domains.
    """

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low SDOH Risk (0-4 total)"
        MEDIUM = "medium", "Moderate SDOH Risk (5-10 total)"
        HIGH = "high", "High SDOH Risk (11-20 total)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, db_index=True)
    patient = models.ForeignKey(
        "fhir.FHIRPatient",
        on_delete=models.CASCADE,
        related_name="sdoh_assessments",
    )
    assessed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sdoh_assessments_conducted",
    )

    # SDOH domain scores (0=none, 1=mild, 2=moderate, 3=severe, 4=extreme)
    food_security_score = models.IntegerField(
        default=0,
        choices=[(i, str(i)) for i in range(5)],
        help_text="0=food secure, 4=severe food insecurity",
    )
    housing_stability_score = models.IntegerField(
        default=0,
        choices=[(i, str(i)) for i in range(5)],
        help_text="0=stable, 4=homeless/at extreme risk",
    )
    transportation_score = models.IntegerField(
        default=0,
        choices=[(i, str(i)) for i in range(5)],
        help_text="0=reliable transport, 4=no access/major barrier",
    )
    social_support_score = models.IntegerField(
        default=0,
        choices=[(i, str(i)) for i in range(5)],
        help_text="0=strong support network, 4=complete isolation",
    )
    financial_stress_score = models.IntegerField(
        default=0,
        choices=[(i, str(i)) for i in range(5)],
        help_text="0=financially stable, 4=unable to cover basic needs",
    )

    # Additional SDOH factors
    education_barrier = models.BooleanField(default=False)
    employment_barrier = models.BooleanField(default=False)
    health_literacy_barrier = models.BooleanField(default=False)
    interpersonal_violence = models.BooleanField(default=False)
    substance_use_concern = models.BooleanField(default=False)
    mental_health_concern = models.BooleanField(default=False)

    # Computed fields
    overall_sdoh_risk = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        db_index=True,
    )
    total_score = models.IntegerField(default=0)

    # Interventions
    interventions_recommended = models.JSONField(
        default=list,
        help_text="""
        [
          {"domain": "food", "intervention": "Refer to food bank", "status": "pending"},
          {"domain": "housing", "intervention": "Contact social worker", "status": "completed"}
        ]
        """,
    )
    community_resources_referred = models.JSONField(default=list, blank=True)

    # Follow-up
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    assessment_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assessment_date"]
        indexes = [
            models.Index(fields=["tenant", "overall_sdoh_risk"]),
            models.Index(fields=["patient", "assessment_date"]),
        ]

    def __str__(self):
        return f"SDOH Assessment: {self.patient} ({self.assessment_date}) — {self.overall_sdoh_risk}"

    def calculate_risk(self):
        """Compute total score and overall risk level."""
        self.total_score = (
            self.food_security_score
            + self.housing_stability_score
            + self.transportation_score
            + self.social_support_score
            + self.financial_stress_score
        )
        if self.total_score <= 4:
            self.overall_sdoh_risk = self.RiskLevel.LOW
        elif self.total_score <= 10:
            self.overall_sdoh_risk = self.RiskLevel.MEDIUM
        else:
            self.overall_sdoh_risk = self.RiskLevel.HIGH

    def save(self, *args, **kwargs):
        self.calculate_risk()
        super().save(*args, **kwargs)

    def get_intervention_recommendations(self) -> list:
        """Generate AI-recommended interventions based on domain scores."""
        recommendations = []

        if self.food_security_score >= 2:
            recommendations.append({
                "domain": "food",
                "priority": "high" if self.food_security_score >= 3 else "medium",
                "intervention": "Refer to local food bank or SNAP enrollment",
                "resources": ["foodpantries.org", "benefits.gov/snap"],
            })

        if self.housing_stability_score >= 2:
            recommendations.append({
                "domain": "housing",
                "priority": "high" if self.housing_stability_score >= 3 else "medium",
                "intervention": "Connect with housing assistance programs and social worker",
                "resources": ["211.org", "hud.gov"],
            })

        if self.transportation_score >= 2:
            recommendations.append({
                "domain": "transportation",
                "priority": "medium",
                "intervention": "Arrange medical transportation or telehealth visits",
                "resources": ["Non-emergency medical transport", "Telehealth portal"],
            })

        if self.social_support_score >= 2:
            recommendations.append({
                "domain": "social_support",
                "priority": "medium",
                "intervention": "Refer to community support groups and senior services",
                "resources": ["eldercare.acl.gov", "NAMI"],
            })

        if self.financial_stress_score >= 2:
            recommendations.append({
                "domain": "financial",
                "priority": "high" if self.financial_stress_score >= 3 else "medium",
                "intervention": "Connect with financial assistance programs and prescription assistance",
                "resources": ["NeedyMeds.org", "RxAssist.org"],
            })

        return recommendations
