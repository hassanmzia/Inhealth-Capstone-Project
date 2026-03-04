"""
Patient management views.
"""

import logging

from django.db.models import Count, Q
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI, IsClinician
from apps.fhir.models import (
    FHIRAppointment,
    FHIRCondition,
    FHIRMedicationRequest,
    FHIRPatient,
)
from apps.fhir.serializers import FHIRPatientSerializer

from .models import DeviceRegistration, PatientDemographics, PatientEngagement
from .serializers import (
    DeviceRegistrationSerializer,
    PatientDemographicsSerializer,
    PatientEngagementSerializer,
    PatientSummarySerializer,
)

logger = logging.getLogger("apps.patients")


class PatientViewSet(ModelViewSet):
    """
    Patient list, detail, search, and risk stratification.
    """

    serializer_class = FHIRPatientSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["gender", "active"]
    search_fields = ["first_name", "last_name", "mrn", "email"]
    ordering_fields = ["last_name", "birth_date", "created_at"]
    ordering = ["last_name"]

    def get_queryset(self):
        qs = FHIRPatient.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("primary_care_provider")

        # Search by DOB
        if self.request.query_params.get("birthdate"):
            qs = qs.filter(birth_date=self.request.query_params["birthdate"])

        # Filter by PCP
        if self.request.query_params.get("pcp"):
            qs = qs.filter(primary_care_provider_id=self.request.query_params["pcp"])

        return qs

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Full patient summary for the clinical dashboard."""
        try:
            patient = FHIRPatient.objects.get(pk=pk, tenant=request.user.tenant)
        except FHIRPatient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Try to get risk score
        risk_level = None
        risk_score = None
        try:
            from apps.analytics.models import RiskScore
            latest_risk = RiskScore.objects.filter(
                patient=patient,
                score_type="7_day_hospitalization"
            ).order_by("-calculated_at").first()
            if latest_risk:
                risk_level = latest_risk.risk_level
                risk_score = latest_risk.score
        except Exception:
            pass

        data = {
            "patient": FHIRPatientSerializer(patient).data,
            "demographics": PatientDemographicsSerializer(
                getattr(patient, "demographics", None)
            ).data if hasattr(patient, "demographics") else None,
            "engagement": PatientEngagementSerializer(
                getattr(patient, "engagement", None)
            ).data if hasattr(patient, "engagement") else None,
            "devices": DeviceRegistrationSerializer(
                DeviceRegistration.objects.filter(patient=patient, is_active=True),
                many=True
            ).data,
            "active_conditions_count": FHIRCondition.objects.filter(patient=patient, clinical_status="active").count(),
            "active_medications_count": FHIRMedicationRequest.objects.filter(patient=patient, status="active").count(),
            "pending_appointments_count": FHIRAppointment.objects.filter(patient=patient, status__in=["booked", "pending"]).count(),
            "recent_alerts_count": 0,  # Updated by notifications app
            "risk_level": risk_level,
            "risk_score": risk_score,
        }
        return Response(data)

    @action(detail=False, methods=["get"])
    def risk_stratification(self, request):
        """Return patients grouped by risk level."""
        from apps.analytics.models import RiskScore
        from django.utils import timezone

        high_risk = FHIRPatient.objects.filter(
            tenant=request.user.tenant,
            active=True,
        ).filter(
            analytics_risk_scores__risk_level__in=["high", "critical"],
            analytics_risk_scores__valid_until__gt=timezone.now(),
        ).distinct()

        return Response({
            "high_risk_count": high_risk.count(),
            "high_risk_patients": FHIRPatientSerializer(high_risk[:20], many=True).data,
        })


class PatientDemographicsView(generics.RetrieveUpdateAPIView):
    """GET/PATCH patient demographics."""

    serializer_class = PatientDemographicsSerializer
    permission_classes = [CanAccessPHI]

    def get_object(self):
        patient_id = self.kwargs["patient_pk"]
        demo, _ = PatientDemographics.objects.get_or_create(
            patient_id=patient_id,
            defaults={"patient_id": patient_id},
        )
        return demo


class PatientEngagementView(generics.RetrieveUpdateAPIView):
    """GET/PATCH patient engagement metrics."""

    serializer_class = PatientEngagementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        patient_id = self.kwargs["patient_pk"]
        eng, _ = PatientEngagement.objects.get_or_create(patient_id=patient_id)
        return eng


class DeviceRegistrationViewSet(ModelViewSet):
    """Device registration CRUD."""

    serializer_class = DeviceRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DeviceRegistration.objects.filter(
            patient__tenant=self.request.user.tenant,
            patient_id=self.kwargs.get("patient_pk"),
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs["patient_pk"])
