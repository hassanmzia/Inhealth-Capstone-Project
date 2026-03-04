"""Notification views."""

import logging

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import CanAccessPHI

from .models import Notification, NotificationTemplate
from .serializers import NotificationSerializer, NotificationTemplateSerializer

logger = logging.getLogger("apps.notifications")


class NotificationViewSet(ModelViewSet):
    """Notification management — list, acknowledge, view history."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["notification_type", "status", "channel", "patient"]
    ordering_fields = ["created_at", "notification_type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.filter(
            tenant=user.tenant
        ).select_related("patient", "acknowledged_by")

        # Patients can only see their own notifications
        if user.role == "patient":
            try:
                patient_fhir = user.fhir_patient
                qs = qs.filter(patient=patient_fhir)
            except Exception:
                return qs.none()

        if self.request.query_params.get("unacknowledged"):
            qs = qs.exclude(status=Notification.Status.ACKNOWLEDGED)

        return qs

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge a notification."""
        notification = self.get_object()
        if notification.status == Notification.Status.ACKNOWLEDGED:
            return Response({"message": "Already acknowledged."})
        notification.acknowledge(user=request.user)
        return Response({"message": "Notification acknowledged.", "acknowledged_at": notification.acknowledged_at})

    @action(detail=False, methods=["post"])
    def acknowledge_all(self, request):
        """Acknowledge all pending notifications for the current user."""
        from django.utils import timezone
        count = self.get_queryset().filter(
            status__in=[Notification.Status.SENT, Notification.Status.DELIVERED, Notification.Status.PENDING]
        ).update(
            status=Notification.Status.ACKNOWLEDGED,
            acknowledged_at=timezone.now(),
            acknowledged_by=request.user,
        )
        return Response({"message": f"Acknowledged {count} notifications."})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unacknowledged notifications."""
        count = self.get_queryset().exclude(
            status=Notification.Status.ACKNOWLEDGED
        ).count()
        return Response({"unread_count": count})


class NotificationTemplateViewSet(ModelViewSet):
    """Notification template management."""

    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = NotificationTemplate.objects.filter(is_active=True)
