"""Clinical workflow views."""

import logging
import uuid as _uuid

from django.utils import timezone as tz
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI, IsClinician

from .models import CareGap, Encounter, SmartOrderSet, VitalTargetPolicy
from .serializers import (
    CareGapSerializer, EncounterSerializer, SmartOrderSetSerializer,
    VitalTargetPolicySerializer,
)

logger = logging.getLogger("apps.clinical")


class EncounterViewSet(ModelViewSet):
    """Encounter CRUD with clinical documentation."""

    serializer_class = EncounterSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["status", "encounter_type", "patient"]
    ordering_fields = ["start_datetime"]
    ordering = ["-start_datetime"]

    def get_queryset(self):
        qs = Encounter.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).select_related("patient", "provider")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient_id=self.request.query_params["patient"])
        if self.request.query_params.get("provider"):
            qs = qs.filter(provider_id=self.request.query_params["provider"])
        return qs

    def perform_create(self, serializer):
        serializer.save(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant),
            provider=self.request.user,
        )


class CareGapViewSet(ModelViewSet):
    """Care gap management."""

    serializer_class = CareGapSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["status", "priority", "gap_type", "patient"]
    ordering = ["priority", "due_date"]

    def get_queryset(self):
        return CareGap.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).select_related("patient")

    def perform_create(self, serializer):
        serializer.save(tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant))

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Mark a care gap as closed."""
        from django.utils import timezone
        care_gap = self.get_object()
        care_gap.status = CareGap.Status.CLOSED
        care_gap.closed_at = timezone.now()
        care_gap.save(update_fields=["status", "closed_at"])
        return Response({"message": "Care gap closed."})

    @action(detail=True, methods=["post"])
    def defer(self, request, pk=None):
        """Defer a care gap to a future date."""
        defer_until = request.data.get("defer_until")
        if not defer_until:
            return Response({"error": "defer_until date is required."}, status=status.HTTP_400_BAD_REQUEST)
        care_gap = self.get_object()
        care_gap.status = CareGap.Status.DEFERRED
        care_gap.deferred_until = defer_until
        care_gap.deferred_by_id = request.user.id
        care_gap.save(update_fields=["status", "deferred_until", "deferred_by_id"])
        return Response({"message": "Care gap deferred."})


class SmartOrderSetViewSet(ModelViewSet):
    """Smart order set management."""

    serializer_class = SmartOrderSetSerializer
    permission_classes = [IsClinician]
    filterset_fields = ["condition", "evidence_level", "created_by_ai"]

    def get_queryset(self):
        tenant = (getattr(self.request, 'tenant', None) or self.request.user.tenant)
        # Return global order sets + tenant-specific ones
        from django.db.models import Q
        return SmartOrderSet.objects.filter(
            Q(tenant=tenant) | Q(tenant__isnull=True),
            is_active=True,
        ).order_by("condition", "name")

    @action(detail=False, methods=["get"])
    def by_condition(self, request):
        """Get order sets for a specific ICD-10 condition code."""
        condition = request.query_params.get("condition")
        if not condition:
            return Response({"error": "condition parameter required"}, status=status.HTTP_400_BAD_REQUEST)
        order_sets = self.get_queryset().filter(condition=condition)
        return Response(SmartOrderSetSerializer(order_sets, many=True).data)


class VitalTargetPolicyViewSet(ModelViewSet):
    """
    Per-patient vital target policies.

    Clinicians set personalized vital sign target ranges.
    The feedback loop uses these to evaluate care plan outcomes.
    """

    serializer_class = VitalTargetPolicySerializer
    permission_classes = [IsClinician]
    filterset_fields = ["patient", "loinc_code", "is_active", "source"]
    ordering = ["vital_name"]

    def get_queryset(self):
        return VitalTargetPolicy.objects.filter(
            tenant=(getattr(self.request, "tenant", None) or self.request.user.tenant),
        ).select_related("patient", "set_by", "care_plan")

    def perform_create(self, serializer):
        tenant = getattr(self.request, "tenant", None) or self.request.user.tenant
        # Deactivate existing active target for same vital + patient
        patient = serializer.validated_data.get("patient")
        loinc_code = serializer.validated_data.get("loinc_code")
        if patient and loinc_code:
            VitalTargetPolicy.objects.filter(
                patient=patient, loinc_code=loinc_code, is_active=True,
            ).update(is_active=False)
        serializer.save(tenant=tenant, set_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="initialize-defaults")
    def initialize_defaults(self, request):
        """Create default evidence-based vital targets for a patient."""
        patient_id = request.data.get("patient_id")
        if not patient_id:
            return Response({"error": "patient_id required"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.fhir.models import FHIRPatient
        try:
            patient = FHIRPatient.objects.get(id=patient_id)
        except FHIRPatient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

        tenant = getattr(request, "tenant", None) or request.user.tenant
        created = _create_default_vital_targets(patient, tenant, request.user)
        return Response({
            "message": f"Created {len(created)} default vital target policies",
            "targets": VitalTargetPolicySerializer(created, many=True).data,
        })


# Evidence-based default vital targets
DEFAULT_VITAL_TARGETS = [
    {
        "loinc_code": "8867-4",
        "vital_name": "Heart Rate",
        "unit": "bpm",
        "target_low": 60,
        "target_high": 100,
        "source_guideline": "ACC/AHA 2023",
    },
    {
        "loinc_code": "8480-6",
        "vital_name": "Systolic BP",
        "unit": "mmHg",
        "target_low": 90,
        "target_high": 130,
        "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
    },
    {
        "loinc_code": "8462-4",
        "vital_name": "Diastolic BP",
        "unit": "mmHg",
        "target_low": 60,
        "target_high": 80,
        "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
    },
    {
        "loinc_code": "59408-5",
        "vital_name": "SpO2",
        "unit": "%",
        "target_low": 95,
        "target_high": 100,
        "source_guideline": "ATS/ERS 2024 Guidelines",
    },
    {
        "loinc_code": "8310-5",
        "vital_name": "Temperature",
        "unit": "°C",
        "target_low": 36.1,
        "target_high": 37.2,
        "source_guideline": "Standard clinical reference range",
    },
    {
        "loinc_code": "2339-0",
        "vital_name": "Glucose",
        "unit": "mg/dL",
        "target_low": 70,
        "target_high": 180,
        "source_guideline": "ADA Standards of Care 2024",
    },
]


def _create_default_vital_targets(patient, tenant, set_by=None):
    """Create default vital targets for a patient (skip vitals that already have active targets)."""
    existing = set(
        VitalTargetPolicy.objects.filter(
            patient=patient, is_active=True,
        ).values_list("loinc_code", flat=True)
    )

    created = []
    for defaults in DEFAULT_VITAL_TARGETS:
        if defaults["loinc_code"] in existing:
            continue
        target = VitalTargetPolicy.objects.create(
            tenant=tenant,
            patient=patient,
            set_by=set_by,
            source=VitalTargetPolicy.Source.GUIDELINE,
            rationale="Default evidence-based target range",
            **defaults,
        )
        created.append(target)
    return created


class VitalsIngestView(APIView):
    """
    POST /api/v1/clinical/vitals/

    Accepts IoT simulator payloads and creates FHIR Observations.
    Payload:
        {
            "patient_id": "<uuid>",
            "device_type": "ecg_monitor",
            "device_id": "sim-ecg_monitor-abcd1234",
            "readings": [
                {"vital_type": "ecg", "value": 74, "unit": "bpm",
                 "loinc_code": "8867-4", "timestamp": "...",
                 "ecg_rhythm": "normal_sinus"}
            ]
        }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.fhir.models import FHIRObservation, FHIRPatient

        patient_id = request.data.get("patient_id")
        readings = request.data.get("readings", [])
        device_id = request.data.get("device_id", "")

        if not patient_id or not readings:
            return Response(
                {"error": "patient_id and readings are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = getattr(request, "tenant", None) or request.user.tenant

        try:
            patient = FHIRPatient.objects.get(id=patient_id, tenant=tenant)
        except FHIRPatient.DoesNotExist:
            # Try by fhir_id
            try:
                patient = FHIRPatient.objects.get(fhir_id=patient_id, tenant=tenant)
            except FHIRPatient.DoesNotExist:
                return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

        created = []
        for r in readings:
            loinc = r.get("loinc_code", "")
            value = r.get("value")
            unit = r.get("unit", "")
            vital_type = r.get("vital_type", "")

            raw = {}
            if r.get("ecg_rhythm"):
                raw["ecg_rhythm"] = r["ecg_rhythm"]

            obs = FHIRObservation.objects.create(
                tenant=tenant,
                fhir_id=str(_uuid.uuid4()),
                patient=patient,
                code=loinc,
                display=vital_type.replace("_", " ").title(),
                value_quantity=float(value) if value is not None else 0,
                value_unit=unit,
                effective_datetime=r.get("timestamp") or tz.now(),
                status="final",
                device_id=device_id,
                raw_resource=raw,
            )
            created.append(str(obs.fhir_id))

        return Response(
            {"created": len(created), "observation_ids": created},
            status=status.HTTP_201_CREATED,
        )
