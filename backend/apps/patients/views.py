"""
Patient management views.
"""

import logging
from datetime import timedelta

from django.utils import timezone
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

        # Filter by risk level via latest valid RiskScore
        risk_level_param = self.request.query_params.get("risk_level")
        if risk_level_param:
            try:
                from django.utils import timezone
                from apps.analytics.models import RiskScore
                levels = [r.strip() for r in risk_level_param.split(",")]
                patient_ids = RiskScore.objects.filter(
                    tenant=self.request.user.tenant,
                    risk_level__in=levels,
                    valid_until__gt=timezone.now(),
                ).values_list("patient_id", flat=True).distinct()
                qs = qs.filter(id__in=patient_ids)
            except Exception:
                pass  # DB not ready — return unfiltered list

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


class PatientHealthSummaryView(generics.GenericAPIView):
    """
    GET /api/v1/patient/health-summary/

    Patient-facing self-service summary.  Resolves the logged-in user to
    their FHIRPatient record by email and returns the data shape expected
    by PatientDashboard.tsx.
    """

    permission_classes = [permissions.IsAuthenticated]

    # LOINC codes used to fetch today's vitals
    LOINC_HEART_RATE = "8867-4"
    LOINC_BP_SYSTOLIC = "8480-6"
    LOINC_BP_DIASTOLIC = "8462-4"
    LOINC_GLUCOSE = "2339-0"
    LOINC_WEIGHT = "29463-7"

    def get(self, request):
        from apps.fhir.models import FHIRObservation

        user = request.user
        since_24h = timezone.now() - timedelta(hours=24)

        # ── Resolve FHIRPatient ──────────────────────────────────────────────
        try:
            patient = FHIRPatient.objects.select_related("engagement").get(
                email=user.email,
                tenant=user.tenant,
            )
        except FHIRPatient.DoesNotExist:
            # User account exists but no patient record yet – return safe defaults
            return Response(self._empty_summary())
        except Exception:
            # DB not ready, table missing, multiple objects, etc.
            return Response(self._empty_summary())

        engagement, _ = PatientEngagement.objects.get_or_create(patient=patient)

        # ── Next upcoming appointment ────────────────────────────────────────
        next_appt = (
            FHIRAppointment.objects.filter(
                patient=patient,
                status__in=["booked", "pending"],
                start__gt=timezone.now(),
            )
            .order_by("start")
            .first()
        )

        # ── Today's vitals (last 24 h) ───────────────────────────────────────
        def latest_obs(code):
            return (
                FHIRObservation.objects.filter(
                    patient=patient,
                    code=code,
                    effective_datetime__gte=since_24h,
                )
                .order_by("-effective_datetime")
                .first()
            )

        hr_obs = latest_obs(self.LOINC_HEART_RATE)
        sys_obs = latest_obs(self.LOINC_BP_SYSTOLIC)
        dia_obs = latest_obs(self.LOINC_BP_DIASTOLIC)
        glucose_obs = latest_obs(self.LOINC_GLUCOSE)
        weight_obs = latest_obs(self.LOINC_WEIGHT)

        today_vitals = {}
        if sys_obs and dia_obs:
            today_vitals["bloodPressure"] = (
                f"{int(sys_obs.value_quantity or 0)}/{int(dia_obs.value_quantity or 0)}"
            )
        if hr_obs and hr_obs.value_quantity is not None:
            today_vitals["heartRate"] = round(hr_obs.value_quantity)
        if glucose_obs and glucose_obs.value_quantity is not None:
            today_vitals["glucose"] = round(glucose_obs.value_quantity)
        if weight_obs and weight_obs.value_quantity is not None:
            today_vitals["weight"] = round(weight_obs.value_quantity, 1)

        # ── Goals ────────────────────────────────────────────────────────────
        goals = [
            {
                "title": g.get("goal") or g.get("title", ""),
                "progress": int(g.get("progress", 0)),
                "unit": g.get("unit", ""),
                "current": g.get("current", 0),
                "target": g.get("target", 0),
                "category": g.get("category", "other"),
            }
            for g in (engagement.health_goals or [])
        ]

        # ── Badges ───────────────────────────────────────────────────────────
        badges = [
            a.get("badge") or a.get("title", "")
            for a in (engagement.achievements or [])
            if a.get("badge") or a.get("title")
        ]

        # ── Adherence calendar (last 30 days, placeholder True until real
        #    dispense records are tracked) ────────────────────────────────────
        adherence_calendar = [
            {
                "date": (timezone.now() - timedelta(days=29 - i)).date().isoformat(),
                "taken": True,
            }
            for i in range(30)
        ]

        # ── Tips based on available vitals ───────────────────────────────────
        tips = []
        if sys_obs and sys_obs.value_quantity and sys_obs.value_quantity > 130:
            tips.append({
                "icon": "heart",
                "text": "Your blood pressure is elevated. Reducing sodium and a short walk can help.",
            })
        if hr_obs and hr_obs.value_quantity and hr_obs.value_quantity > 100:
            tips.append({
                "icon": "activity",
                "text": "Your heart rate is elevated. Consider rest or a breathing exercise.",
            })
        active_meds = FHIRMedicationRequest.objects.filter(patient=patient, status="active").count()
        if active_meds:
            tips.append({
                "icon": "pill",
                "text": f"You have {active_meds} active medication(s). Remember to take them as prescribed.",
            })
        if not tips:
            tips.append({
                "icon": "heart",
                "text": "Stay hydrated and aim for a 10-minute walk today!",
            })

        return Response({
            "healthScore": round(engagement.engagement_score),
            "streakDays": engagement.streak_days,
            "medicationAdherence": round(engagement.engagement_score),
            "nextAppointment": next_appt.start.isoformat() if next_appt else None,
            "goals": goals,
            "badges": badges,
            "todayVitals": today_vitals,
            "tips": tips,
            "adherenceCalendar": adherence_calendar,
            "messages": [],
        })

    @staticmethod
    def _empty_summary():
        return {
            "healthScore": 50,
            "streakDays": 0,
            "medicationAdherence": 0,
            "nextAppointment": None,
            "goals": [],
            "badges": [],
            "todayVitals": {},
            "tips": [{"icon": "heart", "text": "Welcome! Your care team will set up your health profile shortly."}],
            "adherenceCalendar": [],
            "messages": [],
        }
