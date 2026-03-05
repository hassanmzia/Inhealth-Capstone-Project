"""Billing views — claim management and RPM episode tracking."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsBilling, IsClinician

from .models import Claim, RPMEpisode
from .serializers import ClaimSerializer, RPMEpisodeSerializer

logger = logging.getLogger("apps.billing")


class ClaimViewSet(ModelViewSet):
    """Medical insurance claim management."""

    serializer_class = ClaimSerializer
    permission_classes = [IsBilling]
    filterset_fields = ["status", "patient"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Claim.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).select_related("patient", "encounter")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a claim to the payer."""
        from django.utils import timezone
        claim = self.get_object()
        if claim.status not in (Claim.Status.DRAFT, Claim.Status.READY):
            return Response(
                {"error": f"Cannot submit claim with status {claim.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        claim.status = Claim.Status.SUBMITTED
        claim.submitted_at = timezone.now()
        claim.save(update_fields=["status", "submitted_at"])
        return Response({"message": "Claim submitted.", "claim_id": str(claim.id)})

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """Void a submitted claim."""
        claim = self.get_object()
        claim.status = Claim.Status.VOIDED
        claim.save(update_fields=["status"])
        return Response({"message": "Claim voided."})


class RPMEpisodeViewSet(ModelViewSet):
    """Remote Patient Monitoring episode tracking."""

    serializer_class = RPMEpisodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "patient"]
    ordering = ["-start_date"]

    def get_queryset(self):
        return RPMEpisode.objects.filter(
            tenant=(getattr(self.request, 'tenant', None) or self.request.user.tenant)
        ).select_related("patient")

    @action(detail=True, methods=["post"])
    def add_minutes(self, request, pk=None):
        """Add monitoring minutes to an RPM episode."""
        minutes = request.data.get("minutes")
        if not minutes or not isinstance(minutes, int) or minutes <= 0:
            return Response({"error": "minutes must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_object()
        episode.add_monitoring_minutes(minutes)
        return Response({
            "message": f"Added {minutes} minutes.",
            "total_minutes": episode.monitoring_minutes,
            "eligible_codes": {
                code: info for code, info in (episode.billing_codes or {}).items()
                if info.get("eligible")
            },
        })
