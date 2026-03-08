"""
Dashboard aggregate views — one endpoint per role type.

All DB operations are wrapped in try/except so that missing tables
(e.g. during initial migration) return graceful 200 responses with zeros
rather than 500 errors.
"""

import logging
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanAccessPHI

logger = logging.getLogger("apps.dashboard")


def _pct_change(current: int, previous: int) -> float:
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


# ─── Clinician Dashboard ──────────────────────────────────────────────────────

class ClinicalDashboardStatsView(APIView):
    """GET /api/v1/dashboard/stats/"""

    permission_classes = [CanAccessPHI]

    def get(self, request):
        tenant = (getattr(request, 'tenant', None) or request.user.tenant)
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        total_patients = 0
        prev_patients = 0
        open_gaps = 0
        prev_gaps = 0
        critical_alerts = 0
        risk_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        todays_appointments = 0

        try:
            from apps.fhir.models import FHIRPatient
            total_patients = FHIRPatient.objects.filter(tenant=tenant, active=True).count()
            prev_patients = FHIRPatient.objects.filter(
                tenant=tenant, active=True, created_at__lt=thirty_days_ago
            ).count()
        except Exception as e:
            logger.debug("dashboard stats: patients query failed: %s", e)

        try:
            from apps.clinical.models import CareGap
            open_gaps = CareGap.objects.filter(
                tenant=tenant, status=CareGap.Status.OPEN
            ).count()
            prev_gaps = CareGap.objects.filter(
                tenant=tenant,
                status=CareGap.Status.OPEN,
                created_at__lt=thirty_days_ago,
            ).count()
        except Exception as e:
            logger.debug("dashboard stats: care_gaps query failed: %s", e)

        try:
            from apps.notifications.models import Notification
            critical_alerts = Notification.objects.filter(
                tenant=tenant,
                notification_type=Notification.NotificationType.CRITICAL,
            ).exclude(status=Notification.Status.ACKNOWLEDGED).count()
        except Exception as e:
            logger.debug("dashboard stats: notifications query failed: %s", e)

        try:
            from apps.analytics.models import RiskScore
            # Try valid scores first; fall back to latest per patient if all expired
            qs = RiskScore.objects.filter(
                tenant=tenant,
                score_type="7_day_hospitalization",
            )
            valid_qs = qs.filter(valid_until__gt=now)
            use_qs = valid_qs if valid_qs.exists() else qs
            for row in (
                use_qs
                .values("risk_level")
                .annotate(n=Count("id"))
            ):
                lvl = row["risk_level"]
                if lvl in risk_dist:
                    risk_dist[lvl] = row["n"]
        except Exception as e:
            logger.debug("dashboard stats: risk_scores query failed: %s", e)

        try:
            from apps.fhir.models import FHIRAppointment
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            todays_appointments = FHIRAppointment.objects.filter(
                tenant=tenant,
                status__in=["booked", "arrived", "checked-in"],
                start__gte=today_start,
                start__lt=today_end,
            ).count()
        except Exception as e:
            logger.debug("dashboard stats: appointments query failed: %s", e)

        risk_dist["total"] = sum(risk_dist.values())

        return Response({
            "totalPatients": total_patients,
            "criticalAlerts": critical_alerts,
            "activeAgents": 0,
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
    """GET /api/v1/appointments/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = (getattr(request, 'tenant', None) or request.user.tenant)
        now = timezone.now()

        status_param = request.query_params.get("status", "booked,pending")
        statuses = [s.strip() for s in status_param.split(",")]
        try:
            limit = min(int(request.query_params.get("limit", 10)), 50)
            days_ahead = int(request.query_params.get("days_ahead", 7))
        except (ValueError, TypeError):
            limit, days_ahead = 10, 7

        try:
            from apps.fhir.models import FHIRAppointment
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
                try:
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
                except Exception:
                    continue
            return Response({"count": len(results), "results": results})
        except Exception as e:
            logger.debug("appointments list failed: %s", e)
            return Response({"count": 0, "results": []})


# ─── Researcher Dashboard ─────────────────────────────────────────────────────

class ResearcherDashboardView(APIView):
    """GET /api/v1/dashboard/researcher/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = (getattr(request, 'tenant', None) or request.user.tenant)
        user = request.user
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        total_my_queries = 0
        recent_queries: list = []
        active_trials = 0
        evidence_count = 0
        recent_evidence: list = []
        tenant_queries_month = 0

        try:
            from apps.research.models import ResearchQuery
            my_qs = ResearchQuery.objects.filter(tenant=tenant, requested_by=user)
            total_my_queries = my_qs.count()
            recent_queries = list(
                my_qs.order_by("-created_at")[:5].values(
                    "id", "query_text", "query_type", "status", "created_at"
                )
            )
            for q in recent_queries:
                q["id"] = str(q["id"])
                q["created_at"] = q["created_at"].isoformat() if q["created_at"] else None
            tenant_queries_month = ResearchQuery.objects.filter(
                tenant=tenant, created_at__gte=thirty_days_ago
            ).count()
        except Exception as e:
            logger.debug("researcher dashboard: research queries failed: %s", e)

        try:
            from apps.research.models import ClinicalTrial
            active_trials = ClinicalTrial.objects.filter(
                status=ClinicalTrial.Status.RECRUITING
            ).count()
        except Exception as e:
            logger.debug("researcher dashboard: trials query failed: %s", e)

        try:
            from apps.research.models import MedicalEvidence
            evidence_count = MedicalEvidence.objects.count()
            recent_evidence = list(
                MedicalEvidence.objects.order_by("-year", "-citation_count")[:5].values(
                    "id", "title", "journal", "year", "evidence_level", "citation_count"
                )
            )
            for ev in recent_evidence:
                ev["id"] = str(ev["id"])
        except Exception as e:
            logger.debug("researcher dashboard: evidence query failed: %s", e)

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
    """GET /api/v1/dashboard/nurse-stats/"""

    permission_classes = [CanAccessPHI]

    def get(self, request):
        tenant = (getattr(request, 'tenant', None) or request.user.tenant)
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        total_patients = 0
        open_gaps = 0
        high_priority_gaps = 0
        todays_appointments = 0
        critical_alerts = 0

        try:
            from apps.fhir.models import FHIRPatient
            total_patients = FHIRPatient.objects.filter(tenant=tenant, active=True).count()
        except Exception as e:
            logger.debug("nurse stats: patients query failed: %s", e)

        try:
            from apps.clinical.models import CareGap
            open_gaps = CareGap.objects.filter(
                tenant=tenant, status=CareGap.Status.OPEN
            ).count()
            high_priority_gaps = CareGap.objects.filter(
                tenant=tenant,
                status=CareGap.Status.OPEN,
                priority__in=["high", "critical"],
            ).count()
        except Exception as e:
            logger.debug("nurse stats: care_gaps query failed: %s", e)

        try:
            from apps.fhir.models import FHIRAppointment
            todays_appointments = FHIRAppointment.objects.filter(
                tenant=tenant,
                status__in=["booked", "arrived", "checked-in"],
                start__gte=today_start,
                start__lt=today_end,
            ).count()
        except Exception as e:
            logger.debug("nurse stats: appointments query failed: %s", e)

        try:
            from apps.notifications.models import Notification
            critical_alerts = Notification.objects.filter(
                tenant=tenant,
                notification_type=Notification.NotificationType.CRITICAL,
            ).exclude(status=Notification.Status.ACKNOWLEDGED).count()
        except Exception as e:
            logger.debug("nurse stats: notifications query failed: %s", e)

        return Response({
            "totalPatients": total_patients,
            "openCareGaps": open_gaps,
            "highPriorityCareGaps": high_priority_gaps,
            "todaysAppointments": todays_appointments,
            "criticalAlerts": critical_alerts,
        })
