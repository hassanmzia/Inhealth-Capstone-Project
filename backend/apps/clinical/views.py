"""Clinical workflow views."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI, IsClinician

from .models import CareGap, Encounter, SmartOrderSet
from .serializers import CareGapSerializer, EncounterSerializer, SmartOrderSetSerializer

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
            tenant=self.request.user.tenant
        ).select_related("patient", "provider")
        if self.request.query_params.get("patient"):
            qs = qs.filter(patient_id=self.request.query_params["patient"])
        if self.request.query_params.get("provider"):
            qs = qs.filter(provider_id=self.request.query_params["provider"])
        return qs

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
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
            tenant=self.request.user.tenant
        ).select_related("patient")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

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
        tenant = self.request.user.tenant
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
