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
    FHIRObservation,
    FHIRPatient,
)
from apps.fhir.serializers import FHIRPatientSerializer

from .models import DeviceRegistration, PatientDemographics, PatientEngagement
from .serializers import (
    DeviceRegistrationSerializer,
    PatientCreateSerializer,
    PatientDemographicsSerializer,
    PatientEngagementSerializer,
    PatientSummarySerializer,
)

logger = logging.getLogger("apps.patients")

# Maps LOINC codes to the VitalType enum values the frontend expects
_LOINC_TO_VITAL_TYPE = {
    "8867-4": "heart_rate",
    "8480-6": "blood_pressure_systolic",
    "8462-4": "blood_pressure_diastolic",
    "59408-5": "spo2",
    "2708-6": "spo2",
    "8310-5": "temperature",
    "29463-7": "weight",
    "8302-2": "height",
    "39156-5": "bmi",
    "9279-1": "respiratory_rate",
    "72514-3": "pain_score",
    "2339-0": "glucose",
}

_INTERP_TO_STATUS = {
    "N": "normal", "normal": "normal",
    "H": "warning", "L": "warning", "A": "warning",
    "HH": "critical", "LL": "critical", "AA": "critical",
}


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

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PatientCreateSerializer
        return FHIRPatientSerializer

    def _tenant(self):
        """Return the effective tenant: middleware-activated or user's FK."""
        return getattr(self.request, 'tenant', None) or self.request.user.tenant

    def perform_create(self, serializer):
        serializer.save(tenant=self._tenant())

    def retrieve(self, request, *args, **kwargs):
        """Return PatientSummary camelCase format for the detail page."""
        try:
            patient = (
                FHIRPatient.objects
                .prefetch_related("conditions")
                .get(pk=self.kwargs.get("pk"), tenant=self._tenant())
            )
        except FHIRPatient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(self._to_summary(patient))

    @action(detail=True, methods=["get"])
    def vitals(self, request, pk=None):
        """Return recent vital signs for a patient as VitalSign[]."""
        try:
            observations = (
                FHIRObservation.objects
                .filter(patient_id=pk, tenant=self._tenant(), code__in=_LOINC_TO_VITAL_TYPE)
                .order_by("-effective_datetime")[:200]
            )
            data = [self._obs_to_vital(obs) for obs in observations]
        except Exception:
            data = []
        return Response(data)

    @action(detail=True, methods=["get"])
    def medications(self, request, pk=None):
        """Return active and recent medications as Medication[]."""
        try:
            meds = (
                FHIRMedicationRequest.objects
                .filter(patient_id=pk, tenant=self._tenant())
                .order_by("-authored_on")
            )
            data = [self._med_to_dict(med) for med in meds]
        except Exception:
            data = []
        return Response(data)

    @action(detail=True, methods=["get"], url_path="care-gaps")
    def care_gaps(self, request, pk=None):
        """Return open care gaps for a patient as CareGap[]."""
        try:
            from apps.clinical.models import CareGap
            gaps = CareGap.objects.filter(patient_id=pk, tenant=self._tenant())
            data = [self._gap_to_dict(g) for g in gaps]
        except Exception:
            data = []
        return Response(data)

    # ── helper serialisers ────────────────────────────────────────────────────

    @staticmethod
    def _obs_to_vital(obs: FHIRObservation) -> dict:
        interp = (obs.interpretation or "").strip()
        return {
            "id": str(obs.id),
            "patientId": str(obs.patient_id),
            "type": _LOINC_TO_VITAL_TYPE.get(obs.code, "heart_rate"),
            "value": obs.value_quantity if obs.value_quantity is not None else 0,
            "unit": obs.value_unit,
            "timestamp": obs.effective_datetime.isoformat(),
            "status": _INTERP_TO_STATUS.get(interp, "normal"),
            "source": "device" if obs.device_id else "ehr",
            "deviceId": obs.device_id or None,
            "loincCode": obs.code,
            "normalMin": obs.reference_range_low,
            "normalMax": obs.reference_range_high,
        }

    @staticmethod
    def _med_to_dict(med: FHIRMedicationRequest) -> dict:
        status_map = {
            "active": "active", "on-hold": "on_hold",
            "cancelled": "discontinued", "stopped": "discontinued",
            "completed": "completed",
        }
        return {
            "id": str(med.id),
            "patientId": str(med.patient_id),
            "name": med.medication_display,
            "rxNormCode": med.medication_code,
            "dose": str(med.dose_quantity or ""),
            "doseUnit": med.dose_unit,
            "frequency": med.frequency,
            "route": med.route,
            "prescribedDate": med.authored_on.isoformat(),
            "startDate": med.authored_on.isoformat(),
            "endDate": med.validity_period_end.isoformat() if med.validity_period_end else None,
            "status": status_map.get(med.status, "active"),
            "daysSupply": med.days_supply,
            "fhirMedicationRequestId": med.fhir_id,
        }

    @staticmethod
    def _gap_to_dict(gap) -> dict:
        status_map = {
            "open": "open", "closed": "closed",
            "deferred": "deferred", "patient_declined": "excluded",
        }
        return {
            "id": str(gap.id),
            "patientId": str(gap.patient_id),
            "title": gap.get_gap_type_display(),
            "description": gap.gap_type,
            "category": "chronic_management",
            "priority": gap.priority,
            "status": status_map.get(gap.status, "open"),
            "dueDate": gap.due_date.isoformat() if gap.due_date else None,
            "openedAt": gap.created_at.isoformat(),
            "closedAt": gap.closed_at.isoformat() if gap.closed_at else None,
            "deferredUntil": gap.deferred_until.isoformat() if gap.deferred_until else None,
            "aiRecommendation": gap.ai_recommendation or None,
        }

    def list(self, request, *args, **kwargs):
        """Return PatientSummary shape expected by the frontend."""
        try:
            qs = self.filter_queryset(self.get_queryset()).prefetch_related(
                "conditions"
            )
            page = self.paginate_queryset(qs)
            items = page if page is not None else qs
            data = [self._to_summary(p) for p in items]
            if page is not None:
                return self.get_paginated_response(data)
            return Response(data)
        except Exception:
            logger.warning("patients list query failed (schema not ready?)", exc_info=True)
            return Response({"count": 0, "next": None, "previous": None, "results": []})

    @staticmethod
    def _to_summary(patient):
        """Build the PatientSummary dict the frontend consumes."""
        from django.utils import timezone as tz
        now = tz.now()

        # Active conditions (use prefetched set, filter in Python)
        active_conditions = []
        try:
            active_conditions = [
                {"code": c.code, "display": c.display}
                for c in patient.conditions.all()
                if c.clinical_status == "active"
            ][:5]
        except Exception:
            pass

        # Latest valid risk score
        risk_score_data = None
        alert_status = "normal"
        try:
            latest_risk = next(
                (r for r in patient.analytics_risk_scores.all()
                 if r.valid_until and r.valid_until > now),
                None
            )
            if latest_risk:
                risk_score_data = {
                    "score": latest_risk.score,
                    "level": latest_risk.risk_level,
                }
                alert_status = (
                    "critical" if latest_risk.risk_level in ("critical", "high")
                    else "warning" if latest_risk.risk_level == "medium"
                    else "normal"
                )
        except Exception:
            pass

        # Primary provider
        provider_data = None
        try:
            pcp = patient.primary_care_provider
            if pcp:
                provider_data = {
                    "id": str(pcp.id),
                    "name": f"{pcp.first_name} {pcp.last_name}".strip(),
                    "specialty": pcp.specialty or "",
                }
        except Exception:
            pass

        return {
            "id": str(patient.id),
            "mrn": patient.mrn,
            "firstName": patient.first_name,
            "lastName": patient.last_name,
            "dateOfBirth": patient.birth_date.isoformat() if patient.birth_date else None,
            "age": patient.age,
            "gender": patient.gender,
            "phone": patient.phone,
            "email": patient.email,
            "active": patient.active,
            "primaryProvider": provider_data,
            "activeConditions": active_conditions,
            "riskScore": risk_score_data,
            "openCareGaps": 0,
            "lastContactDate": None,
            "alertStatus": alert_status,
        }

    def get_queryset(self):
        try:
            tenant = self._tenant()
            qs = FHIRPatient.objects.filter(
                tenant=tenant
            ).select_related("primary_care_provider")
        except Exception:
            # DB schema not ready (e.g. no tenant schema migrated yet)
            return FHIRPatient.objects.none()

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
                    tenant=tenant,
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
            patient = FHIRPatient.objects.get(pk=pk, tenant=self._tenant())
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
            tenant=self._tenant(),
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
            patient__tenant=getattr(self.request, 'tenant', None) or self.request.user.tenant,
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
