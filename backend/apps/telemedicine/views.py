"""Telemedicine views — video session management."""

import logging

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI

from .models import VideoSession
from .serializers import VideoSessionSerializer

logger = logging.getLogger("apps.telemedicine")


class VideoSessionViewSet(ModelViewSet):
    """Video consultation session CRUD with tenant isolation."""

    serializer_class = VideoSessionSerializer
    permission_classes = [CanAccessPHI]
    filterset_fields = ["status", "patient", "provider"]
    ordering_fields = ["scheduled_at", "created_at"]
    ordering = ["-scheduled_at"]

    def get_queryset(self):
        return VideoSession.objects.filter(
            tenant=(getattr(self.request, "tenant", None) or self.request.user.tenant)
        ).select_related("patient", "provider")

    def perform_create(self, serializer):
        serializer.save(
            tenant=(getattr(self.request, "tenant", None) or self.request.user.tenant),
            provider=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start an active video session."""
        session = self.get_object()
        if session.status != VideoSession.Status.SCHEDULED:
            return Response(
                {"error": f"Cannot start session with status '{session.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.start()
        logger.info("Video session %s started by %s", session.session_id, request.user.email)
        return Response(VideoSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        """End an active video session."""
        session = self.get_object()
        if session.status != VideoSession.Status.ACTIVE:
            return Response(
                {"error": f"Cannot end session with status '{session.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.end()
        logger.info("Video session %s ended (duration: %s min)", session.session_id, session.duration_minutes)
        return Response(VideoSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a scheduled session."""
        session = self.get_object()
        if session.status not in (VideoSession.Status.SCHEDULED,):
            return Response(
                {"error": "Only scheduled sessions can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session.status = VideoSession.Status.CANCELLED
        session.save(update_fields=["status", "updated_at"])
        logger.info("Video session %s cancelled", session.session_id)
        return Response(VideoSessionSerializer(session).data)
