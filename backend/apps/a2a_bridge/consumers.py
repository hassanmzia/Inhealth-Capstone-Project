"""
Django Channels WebSocket consumers for A2A agent communication
and real-time vitals streaming.
"""

import json
import logging
from typing import Any, Dict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .message_bus import A2AMessage, get_message_bus

logger = logging.getLogger("apps.a2a_bridge")


class A2AConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for A2A agent messaging.
    Allows external AI agents (or agent orchestrators) to communicate
    with Django backend agents via WebSocket.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.agent_name = self.scope["url_route"]["kwargs"].get("agent_name", "external")
        self.tenant_id = str(user.tenant_id) if user.tenant_id else "global"
        self.room_group = f"a2a_{self.tenant_id}_{self.agent_name}"

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        logger.info(f"A2A WebSocket connected: agent={self.agent_name}, tenant={self.tenant_id}")

        # Announce connection
        await self.send(text_data=json.dumps({
            "type": "connected",
            "agent": self.agent_name,
            "tenant_id": self.tenant_id,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)
        logger.info(f"A2A WebSocket disconnected: agent={getattr(self, 'agent_name', 'unknown')}")

    async def receive(self, text_data):
        """Handle incoming A2A messages from connected agents."""
        try:
            data = json.loads(text_data)
            msg_type = data.get("type", "unknown")

            if msg_type == "task.request":
                await self.handle_task_request(data)
            elif msg_type == "task.result":
                await self.handle_task_result(data)
            elif msg_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
            elif msg_type == "subscribe":
                await self.handle_subscribe(data)
            else:
                logger.warning(f"Unknown A2A message type: {msg_type}")

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))

    async def handle_task_request(self, data: Dict):
        """Process a task request and dispatch it."""
        target_agent = data.get("to_agent")
        task_type = data.get("task_type")
        payload = data.get("payload", {})

        if not target_agent or not task_type:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "to_agent and task_type are required",
            }))
            return

        bus = get_message_bus()
        correlation_id = bus.send_task(
            from_agent=self.agent_name,
            to_agent=target_agent,
            task_type=task_type,
            task_data=payload,
            tenant_id=self.tenant_id,
        )

        await self.send(text_data=json.dumps({
            "type": "task.queued",
            "correlation_id": correlation_id,
            "to_agent": target_agent,
        }))

    async def handle_task_result(self, data: Dict):
        """Forward a task result to the original requester."""
        correlation_id = data.get("correlation_id")
        # Broadcast result to the requesting agent's group
        if correlation_id:
            await self.channel_layer.group_send(
                self.room_group,
                {"type": "a2a_message", "message": data},
            )

    async def handle_subscribe(self, data: Dict):
        """Subscribe to additional agent channels."""
        channels = data.get("channels", [])
        for channel in channels:
            group_name = f"a2a_{self.tenant_id}_{channel}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            logger.info(f"Agent {self.agent_name} subscribed to {channel}")

    async def a2a_message(self, event):
        """Receive A2A message from channel layer and forward to WebSocket."""
        await self.send(text_data=json.dumps(event["message"]))


class VitalsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time patient vitals streaming.
    Streams new vital sign observations as they arrive.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        patient_id = str(self.scope["url_route"]["kwargs"]["patient_id"])
        self.patient_id = patient_id
        self.room_group = f"vitals_{patient_id}"

        # Verify access to this patient
        has_access = await self.check_patient_access(patient_id, user)
        if not has_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()
        logger.info(f"Vitals WebSocket: patient={patient_id}, user={user.id}")

        # Send latest vitals on connect
        recent_vitals = await self.get_recent_vitals(patient_id)
        await self.send(text_data=json.dumps({
            "type": "initial_vitals",
            "vitals": recent_vitals,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        pass  # Vitals stream is read-only from client

    async def vitals_update(self, event):
        """Receive new vital from channel layer and push to WebSocket."""
        await self.send(text_data=json.dumps({
            "type": "vitals_update",
            "vital": event["vital"],
        }))

    @database_sync_to_async
    def check_patient_access(self, patient_id: str, user) -> bool:
        from apps.fhir.models import FHIRPatient
        try:
            patient = FHIRPatient.objects.get(id=patient_id)
            if user.role == "super_admin":
                return True
            return str(patient.tenant_id) == str(user.tenant_id)
        except FHIRPatient.DoesNotExist:
            return False

    @database_sync_to_async
    def get_recent_vitals(self, patient_id: str) -> list:
        from apps.fhir.models import FHIRObservation
        from django.utils import timezone
        from datetime import timedelta

        vitals = FHIRObservation.objects.filter(
            patient_id=patient_id,
            effective_datetime__gte=timezone.now() - timedelta(hours=24),
            status="final",
        ).order_by("-effective_datetime").values(
            "code", "display", "value_quantity", "value_unit", "effective_datetime"
        )[:20]

        return [
            {**v, "effective_datetime": v["effective_datetime"].isoformat()}
            for v in vitals
        ]
