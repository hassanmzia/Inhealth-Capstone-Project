"""Analytics views — population health dashboard and risk stratification."""

import logging
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.accounts.permissions import CanAccessPHI, IsOrgAdmin

from .models import ClinicalKPI, PopulationCohort, RiskScore
from .serializers import ClinicalKPISerializer, PopulationCohortSerializer, RiskScoreSerializer

logger = logging.getLogger("apps.analytics")


class PopulationCohortViewSet(ModelViewSet):
    """Population health cohort management."""

    serializer_class = PopulationCohortSerializer
    permission_classes = [CanAccessPHI]

    def get_queryset(self):
        return PopulationCohort.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def refresh(self, request, pk=None):
        """Trigger an async cohort refresh."""
        cohort = self.get_object()
        from .tasks import refresh_population_cohort
        task = refresh_population_cohort.delay(str(cohort.id))
        return Response({"message": "Cohort refresh queued.", "task_id": task.id})


class RiskScoreViewSet(ReadOnlyModelViewSet):
    """Risk score retrieval and filtering."""

    serializer_class = RiskScoreSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["score_type", "risk_level", "patient"]
    ordering = ["-calculated_at"]

    def get_queryset(self):
        qs = RiskScore.objects.filter(
            tenant=self.request.user.tenant,
            valid_until__gt=timezone.now(),
        ).select_related("patient")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient_id=self.request.query_params["patient"])
        return qs

    @action(detail=False, methods=["get"])
    def high_risk_patients(self, request):
        """Return patients with critical or high risk."""
        from apps.fhir.serializers import FHIRPatientSerializer
        high_risk_scores = RiskScore.objects.filter(
            tenant=request.user.tenant,
            risk_level__in=["high", "critical"],
            valid_until__gt=timezone.now(),
        ).select_related("patient").order_by("-score")[:50]

        return Response({
            "count": high_risk_scores.count(),
            "results": [
                {
                    "patient": FHIRPatientSerializer(s.patient).data,
                    "risk_score": s.score,
                    "risk_level": s.risk_level,
                    "score_type": s.score_type,
                    "key_features": dict(list(s.features.items())[:5]) if s.features else {},
                }
                for s in high_risk_scores
            ],
        })


class ClinicalKPIViewSet(ReadOnlyModelViewSet):
    """Clinical KPI dashboard."""

    serializer_class = ClinicalKPISerializer
    permission_classes = [IsOrgAdmin]
    filterset_fields = ["metric_name"]
    ordering = ["-metric_date"]

    def get_queryset(self):
        qs = ClinicalKPI.objects.filter(tenant=self.request.user.tenant)
        days = self.request.query_params.get("days", 30)
        cutoff = timezone.now().date() - timedelta(days=int(days))
        return qs.filter(metric_date__gte=cutoff)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Return latest values for all KPIs."""
        from django.db.models import Max
        tenant = request.user.tenant
        # Get latest value per metric
        latest = ClinicalKPI.objects.filter(tenant=tenant).order_by(
            "metric_name", "-metric_date"
        ).distinct("metric_name")

        return Response(ClinicalKPISerializer(latest, many=True).data)
