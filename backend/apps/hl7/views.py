"""
HL7 v2 API views — REST endpoint for HL7 message ingestion.
"""

import logging

from rest_framework import permissions, status
from rest_framework.parsers import BaseParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HL7Message
from .tasks import process_hl7_message

logger = logging.getLogger("apps.hl7")


class PlainTextParser(BaseParser):
    """Allow plain text / HL7 content type."""
    media_type = "text/plain"
    media_type_2 = "application/hl7-v2"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read().decode("utf-8", errors="replace")


class HL7IngestView(APIView):
    """
    POST /api/v1/fhir/../hl7/
    Accepts raw HL7 v2 messages (plain text or JSON-wrapped).
    Returns ACK message.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [PlainTextParser]

    def post(self, request):
        raw = request.data
        if isinstance(raw, dict):
            raw = raw.get("message", "")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not raw or not isinstance(raw, str):
            return Response(
                {"error": "Request body must be a raw HL7 v2 message"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Detect message type quickly
        msg_type = "UNKNOWN"
        try:
            from .parser import HL7Parser
            parser = HL7Parser()
            parsed = parser.parse(raw)
            msg_type = f"{parsed.message_type}_{parsed.message_event}"
        except Exception as e:
            logger.warning(f"Could not detect HL7 message type: {e}")

        hl7_record = HL7Message.objects.create(
            tenant=(getattr(request, 'tenant', None) or request.user.tenant),
            message_type=msg_type.replace("^", "_") if "^" in msg_type else msg_type,
            raw_message=raw,
            status="received",
            sending_application=getattr(request, "_hl7_sending_app", ""),
        )

        # Process asynchronously
        process_hl7_message.delay(str(hl7_record.id))

        # Return HL7 ACK
        try:
            from .parser import HL7Parser
            parser = HL7Parser()
            parsed_for_ack = parser.parse(raw)
            ack = parser.build_ack(parsed_for_ack, "AA")
        except Exception:
            ack = f"MSA|AA|{hl7_record.id}"

        return Response(ack, content_type="text/plain", status=status.HTTP_202_ACCEPTED)


class HL7MessageListView(APIView):
    """
    GET /api/v1/fhir/../hl7/messages/
    List HL7 messages for the current tenant.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        messages = HL7Message.objects.filter(
            tenant=(getattr(request, 'tenant', None) or request.user.tenant)
        ).values("id", "message_type", "status", "created_at", "processed_at")[:100]
        return Response(list(messages))
