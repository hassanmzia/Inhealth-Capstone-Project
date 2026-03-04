"""A2A bridge REST views."""

import json
import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanAccessPHI

from .message_bus import A2AMessage, get_message_bus

logger = logging.getLogger("apps.a2a_bridge")


class A2ASendMessageView(APIView):
    """
    POST /api/v1/a2a/send/
    Send an A2A message to a target agent via REST (alternative to WebSocket).
    """

    permission_classes = [CanAccessPHI]

    def post(self, request):
        to_agent = request.data.get("to_agent")
        message_type = request.data.get("message_type")
        payload = request.data.get("payload", {})

        if not to_agent or not message_type:
            return Response(
                {"error": "to_agent and message_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = A2AMessage(
            sender_agent=f"api_user_{request.user.id}",
            receiver_agent=to_agent,
            message_type=message_type,
            payload=payload,
            tenant_id=str(request.user.tenant_id) if request.user.tenant_id else None,
        )

        bus = get_message_bus()
        success = bus.publish(msg)

        if success:
            return Response({"message_id": msg.id, "correlation_id": msg.correlation_id})
        return Response({"error": "Failed to publish message"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class A2ABroadcastView(APIView):
    """
    POST /api/v1/a2a/broadcast/
    Broadcast a message to all agents in the tenant.
    """

    permission_classes = [CanAccessPHI]

    def post(self, request):
        message_type = request.data.get("message_type")
        payload = request.data.get("payload", {})

        if not message_type:
            return Response({"error": "message_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        msg = A2AMessage(
            sender_agent=f"api_user_{request.user.id}",
            receiver_agent="broadcast",
            message_type=message_type,
            payload=payload,
            tenant_id=str(request.user.tenant_id) if request.user.tenant_id else None,
        )

        bus = get_message_bus()
        success = bus.broadcast(msg)

        if success:
            return Response({"message_id": msg.id, "broadcast": True})
        return Response({"error": "Broadcast failed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
