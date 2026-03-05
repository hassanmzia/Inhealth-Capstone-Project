"""
Dashboard aggregate views — one endpoint per role type.

These views are intentionally kept lightweight: they aggregate counts and
summaries from multiple apps so the frontend can populate dashboards in a
single request rather than N parallel calls.
"""

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanAccessPHI
from apps.clinical.models import CareGap
from apps.fhir.models import FHIRAppointment, FHIRPatient
from apps.research.models import ClinicalTrial, MedicalEvidence, ResearchQuery

logger = logging.getLogger("apps.dashboard")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pct_change(current: int, previous: int) -> float:
    """Return percentage change, positive = increase."""
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


# ─── Clinician Dashboard ──────────────────────────────────────────────────────

class ClinicalDashboardStatsView(APIView):
    """
    GET /api/v1/dashboard/stats/

    Aggregate stats used by ClinicianDashboard.  Accessible to all
    clinical roles (physician, nurse, admin, org_admin).
    """

    permission_classes = [CanAccessPHI]

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # ── Patient counts ────────────────────────────────────────────────────
        total_patients = FHIRPatient.objects.filter(tenant=tenant, active=True).count()
        prev_patients = FHIRPatient.objects.filter(
            tenant=tenant, active=True, created_at__lt=thirty_days_ago
        ).count()

        # ── Care gaps ─────────────────────────────────────────────────────────
        open_gaps = CareGap.objects.filter(
            tenant=tenant, status=CareGap.Status.OPEN
        ).count()
        prev_gaps = CareGap.objects.filter(
            tenant=tenant,
            status=CareGap.Status.OPEN,
            created_at__lt=thirty_days_ago,
        ).count()

        # ── Critical alerts (Notifications) ───────────────────────────────────
        critical_alerts = 0
        try:
            from apps.notifications.models import Notification
            critical_alerts = Notification.objects.filter(
                tenant=tenant,
                notification_type=Notification.NotificationType.CRITICAL,
            ).exclude(status=Notification.Status.ACKNOWLEDGED).count()
        except Exception:
            pass

        # ── Risk distribution (latest valid scores) ───────────────────────────
        risk_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        try:
            from apps.analytics.models import RiskScore
            scores = (
                RiskScore.objects.filter(
                    tenant=tenant,
                    valid_until__gt=now,
                    score_type="7_day_hospitalization",
                )
                .values("risk_level")
                .annotate(n=__import__("django.db.models", fromlist=["Count"]).Count("id"))
            )
            for row in scores:
                lvl = row["risk_level"]
                if lvl in risk_dist:
                    risk_dist[lvl] = row["n"]
        except Exception:
            pass

        risk_dist["total"] = sum(risk_dist.values())

        # ── Upcoming appointments today ────────────────────────────────────────
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        todays_appointments = FHIRAppointment.objects.filter(
            tenant=tenant,
            status__in=["booked", "arrived", "checked-in"],
            start__gte=today_start,
            start__lt=today_end,
        ).count()

        return Response({
            "totalPatients": total_patients,
            "criticalAlerts": critical_alerts,
            "activeAgents": 0,          # Real value pushed via WebSocket / agentStore
            "openCareGaps": open_gaps,
            "todaysAppointments": todays_appointments,
            "trends": {
                "patients": _pct_change(total_patients, prev_patients),
                "alerts": 0,
                "careGaps": _pct_change(open_gaps, prev_gaps),
            },
            "riskDistribution": risk_dist,
        })


# ─── Appointments List ────────────────────────────────────────────────────────

class AppointmentsListView(APIView):
    """
    GET /api/v1/appointments/

    Returns upcoming appointments for patients in the authenticated
    user's tenant.  Supports ?status=booked,pending&limit=10&days_ahead=7
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()

        # Query params
        status_param = request.query_params.get("status", "booked,pending")
        statuses = [s.strip() for s in status_param.split(",")]
        limit = min(int(request.query_params.get("limit", 10)), 50)
        days_ahead = int(request.query_params.get("days_ahead", 7))

        qs = (
            FHIRAppointment.objects.filter(
                tenant=tenant,
                status__in=statuses,
                start__gte=now,
                start__lte=now + timedelta(days=days_ahead),
            )
            .select_related("patient")
            .order_by("start")[:limit]
        )

        results = []
        for appt in qs:
            results.append({
                "id": str(appt.id),
                "patientName": f"{appt.patient.first_name} {appt.patient.last_name}",
                "patientId": str(appt.patient.id),
                "start": appt.start.isoformat(),
                "end": appt.end.isoformat(),
                "serviceType": appt.service_type,
                "appointmentType": appt.appointment_type,
                "status": appt.status,
                "isTelehealth": appt.is_telehealth,
                "location": appt.location,
            })

        return Response({"count": len(results), "results": results})


# ─── Researcher Dashboard ─────────────────────────────────────────────────────

class ResearcherDashboardView(APIView):
    """
    GET /api/v1/researcher/dashboard/

    Researcher-specific dashboard summary.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = request.user.tenant
        user = request.user
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # ── My queries ────────────────────────────────────────────────────────
        my_queries_qs = ResearchQuery.objects.filter(
            tenant=tenant, requested_by=user
        )
        total_my_queries = my_queries_qs.count()
        recent_queries = list(
            my_queries_qs.order_by("-created_at")[:5].values(
                "id", "query_text", "query_type", "status", "created_at"
            )
        )
        for q in recent_queries:
            q["id"] = str(q["id"])
            q["created_at"] = q["created_at"].isoformat() if q["created_at"] else None

        # ── Active trials ─────────────────────────────────────────────────────
        active_trials = ClinicalTrial.objects.filter(
            status=ClinicalTrial.Status.RECRUITING
        ).count()

        # ── Evidence database ─────────────────────────────────────────────────
        evidence_count = MedicalEvidence.objects.count()

        # ── Recent evidence ───────────────────────────────────────────────────
        recent_evidence = list(
            MedicalEvidence.objects.order_by("-year", "-citation_count")[:5].values(
                "id", "title", "journal", "year", "evidence_level", "citation_count"
            )
        )
        for e in recent_evidence:
            e["id"] = str(e["id"])

        # ── Tenant-wide queries this month ────────────────────────────────────
        tenant_queries_month = ResearchQuery.objects.filter(
            tenant=tenant, created_at__gte=thirty_days_ago
        ).count()

        return Response({
            "totalMyQueries": total_my_queries,
            "activeTrials": active_trials,
            "evidenceCount": evidence_count,
            "tenantQueriesThisMonth": tenant_queries_month,
            "recentQueries": recent_queries,
            "recentEvidence": recent_evidence,
        })


# ─── Nurse Dashboard ──────────────────────────────────────────────────────────

class NurseDashboardStatsView(APIView):
    """
    GET /api/v1/dashboard/nurse-stats/

    Nurse-specific stats: today's tasks, high-priority patients,
    pending care gap actions.
    """

    permission_classes = [CanAccessPHI]

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        total_patients = FHIRPatient.objects.filter(tenant=tenant, active=True).count()

        open_gaps = CareGap.objects.filter(
            tenant=tenant, status=CareGap.Status.OPEN
        ).count()

        high_priority_gaps = CareGap.objects.filter(
            tenant=tenant,
            status=CareGap.Status.OPEN,
            priority__in=["high", "critical"],
        ).count()

        todays_appointments = FHIRAppointment.objects.filter(
            tenant=tenant,
            status__in=["booked", "arrived", "checked-in"],
            start__gte=today_start,
            start__lt=today_end,
        ).count()

        critical_alerts = 0
        try:
            from apps.notifications.models import Notification
            critical_alerts = Notification.objects.filter(
                tenant=tenant,
                notification_type=Notification.NotificationType.CRITICAL,
            ).exclude(status=Notification.Status.ACKNOWLEDGED).count()
        except Exception:
            pass

        return Response({
            "totalPatients": total_patients,
            "openCareGaps": open_gaps,
            "highPriorityCareGaps": high_priority_gaps,
            "todaysAppointments": todays_appointments,
            "criticalAlerts": critical_alerts,
        })
