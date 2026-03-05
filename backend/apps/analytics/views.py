"""Analytics views — population health dashboard and risk stratification."""

import logging
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
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
        try:
            return PopulationCohort.objects.filter(tenant=getattr(self.request, 'tenant', None) or self.request.user.tenant)
        except Exception:
            return PopulationCohort.objects.none()

    def perform_create(self, serializer):
        serializer.save(tenant=getattr(self.request, 'tenant', None) or self.request.user.tenant, created_by=self.request.user)

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
        try:
            qs = RiskScore.objects.filter(
                tenant=getattr(self.request, 'tenant', None) or self.request.user.tenant,
                valid_until__gt=timezone.now(),
            ).select_related("patient")
            if self.request.query_params.get("patient"):
                qs = qs.filter(patient_id=self.request.query_params["patient"])
            return qs
        except Exception:
            return RiskScore.objects.none()

    @action(detail=False, methods=["get"])
    def high_risk_patients(self, request):
        """Return patients with critical or high risk."""
        try:
            from apps.fhir.serializers import FHIRPatientSerializer
            high_risk_scores = list(
                RiskScore.objects.filter(
                    tenant=getattr(request, 'tenant', None) or request.user.tenant,
                    risk_level__in=["high", "critical"],
                    valid_until__gt=timezone.now(),
                ).select_related("patient").order_by("-score")[:50]
            )
            return Response({
                "count": len(high_risk_scores),
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
        except Exception:
            return Response({"count": 0, "results": []})


class ClinicalKPIViewSet(ReadOnlyModelViewSet):
    """Clinical KPI dashboard."""

    serializer_class = ClinicalKPISerializer
    permission_classes = [IsOrgAdmin]
    filterset_fields = ["metric_name"]
    ordering = ["-metric_date"]

    def get_queryset(self):
        try:
            qs = ClinicalKPI.objects.filter(tenant=getattr(self.request, 'tenant', None) or self.request.user.tenant)
            days = self.request.query_params.get("days", 30)
            cutoff = timezone.now().date() - timedelta(days=int(days))
            return qs.filter(metric_date__gte=cutoff)
        except Exception:
            return ClinicalKPI.objects.none()

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Return latest values for all KPIs."""
        try:
            tenant = getattr(request, 'tenant', None) or request.user.tenant
            latest = ClinicalKPI.objects.filter(tenant=tenant).order_by(
                "metric_name", "-metric_date"
            ).distinct("metric_name")
            return Response(ClinicalKPISerializer(latest, many=True).data)
        except Exception:
            return Response([])


class PopulationHealthView(APIView):
    """Aggregated population health metrics for the analytics dashboard."""

    permission_classes = [CanAccessPHI]

    _EMPTY_RESPONSE = {
        "riskDistribution": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
        "diseasePrevalence": [],
        "careGapRates": [],
        "adherenceTrend": [],
        "qualityMeasures": [],
    }

    def get(self, request):
        tenant = getattr(request, 'tenant', None) or request.user.tenant
        now = timezone.now()

        # --- Risk distribution from RiskScore ---
        try:
            risk_counts = (
                RiskScore.objects.filter(tenant=tenant, valid_until__gt=now)
                .values("risk_level")
                .annotate(count=Count("id"))
            )
            risk_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for row in risk_counts:
                if row["risk_level"] in risk_dist:
                    risk_dist[row["risk_level"]] = row["count"]
            risk_dist["total"] = sum(risk_dist.values())
        except Exception:
            return Response(self._EMPTY_RESPONSE)

        # --- Disease prevalence from FHIRCondition ---
        try:
            from apps.fhir.models import FHIRCondition
            from django.db.models import F
            total_patients = (
                RiskScore.objects.filter(tenant=tenant, valid_until__gt=now)
                .values("patient").distinct().count() or 1
            )
            condition_counts = (
                FHIRCondition.objects.filter(tenant=tenant)
                .values("display")
                .annotate(count=Count("id"))
                .order_by("-count")[:8]
            )
            disease_prevalence = [
                {
                    "condition": row["display"] or "Unknown",
                    "count": row["count"],
                    "percentage": round(row["count"] / total_patients * 100, 1),
                }
                for row in condition_counts
                if row["display"]
            ]
        except Exception:
            disease_prevalence = []

        # --- Adherence trend: last 6 months of medication_adherence_rate KPI ---
        try:
            six_months_ago = (now - timedelta(days=180)).date()
            adherence_rows = (
                ClinicalKPI.objects.filter(
                    tenant=tenant,
                    metric_name=ClinicalKPI.MetricName.MEDICATION_ADHERENCE_RATE,
                    metric_date__gte=six_months_ago,
                )
                .order_by("metric_date")
                .values("metric_date", "metric_value")
            )
            adherence_trend = [
                {
                    "month": row["metric_date"].strftime("%b"),
                    "adherence": round(row["metric_value"], 1),
                }
                for row in adherence_rows
            ]
        except Exception:
            adherence_trend = []

        # --- Care gap closure rates from ClinicalKPI ---
        try:
            care_gap_row = (
                ClinicalKPI.objects.filter(
                    tenant=tenant,
                    metric_name=ClinicalKPI.MetricName.CARE_GAP_CLOSURE_RATE,
                )
                .order_by("-metric_date")
                .first()
            )
            care_gap_rates = []
            if care_gap_row and isinstance(care_gap_row.metadata, dict):
                for category, values in care_gap_row.metadata.get("breakdown", {}).items():
                    care_gap_rates.append({
                        "category": category,
                        "openGaps": values.get("open_gaps", 0),
                        "closureRate": values.get("closure_rate", 0),
                    })
        except Exception:
            care_gap_rates = []

        # --- Quality measures from ClinicalKPI ---
        try:
            quality_metric_map = {
                ClinicalKPI.MetricName.PCT_A1C_CONTROLLED: ("HbA1c Control (<8%)", 72),
                ClinicalKPI.MetricName.PCT_BP_CONTROLLED: ("BP Control (<140/90)", 68),
                ClinicalKPI.MetricName.MEDICATION_ADHERENCE_RATE: ("Medication Adherence", 80),
                ClinicalKPI.MetricName.CARE_GAP_CLOSURE_RATE: ("Care Gap Closure", 70),
            }
            latest_kpis = (
                ClinicalKPI.objects.filter(
                    tenant=tenant,
                    metric_name__in=list(quality_metric_map.keys()),
                )
                .order_by("metric_name", "-metric_date")
                .distinct("metric_name")
            )
            quality_measures = [
                {
                    "measure": quality_metric_map[kpi.metric_name][0],
                    "rate": round(kpi.metric_value, 1),
                    "benchmark": quality_metric_map[kpi.metric_name][1],
                }
                for kpi in latest_kpis
                if kpi.metric_name in quality_metric_map
            ]
        except Exception:
            quality_measures = []

        return Response({
            "riskDistribution": risk_dist,
            "diseasePrevalence": disease_prevalence,
            "careGapRates": care_gap_rates,
            "adherenceTrend": adherence_trend,
            "qualityMeasures": quality_measures,
        })
