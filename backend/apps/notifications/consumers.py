"""
WebSocket consumer for real-time notification delivery via Django Channels.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("apps.notifications")


class AlertConsumer(AsyncWebsocketConsumer):
    """
    Real-time alert delivery WebSocket.
    Connects authenticated users to their personal alert channel.
    """

    async def connect(self):
        user = self.scope.get("user")

        # Accept FIRST — calling close() before accept() drops the TCP
        # connection without a proper WS close frame, producing code 1006.
        await self.accept()

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_id = str(user.id)
        self.tenant_id = str(user.tenant_id) if user.tenant_id else "global"
        self.room_group_name = f"alerts_user_{self.user_id}"

        try:
            # Join user-specific group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            # Also join tenant-wide group (for broadcast alerts)
            self.tenant_group = f"alerts_tenant_{self.tenant_id}"
            await self.channel_layer.group_add(self.tenant_group, self.channel_name)
        except Exception:
            logger.warning("Channel layer unavailable; connected without group membership")

        logger.info(f"Alert WebSocket connected: user={self.user_id}")

        # Send pending unacknowledged notifications
        await self.send_pending_notifications()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, "tenant_group"):
            await self.channel_layer.group_discard(self.tenant_group, self.channel_name)
        logger.info(f"Alert WebSocket disconnected: user={getattr(self, 'user_id', 'unknown')}")

    async def receive(self, text_data):
        """Handle incoming messages from client (acknowledgements)."""
        try:
            data = json.loads(text_data)
            if data.get("type") == "acknowledge":
                notification_id = data.get("notification_id")
                if notification_id:
                    await self.acknowledge_notification(notification_id)
        except json.JSONDecodeError:
            pass

    async def notification_alert(self, event):
        """Receive notification from channel layer and forward to WebSocket."""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event["notification"],
        }))

    @database_sync_to_async
    def acknowledge_notification(self, notification_id: str):
        from .models import Notification
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=self.user_id)
            notif = Notification.objects.get(id=notification_id)
            notif.acknowledge(user=user)
        except Exception as e:
            logger.error(f"Acknowledge failed: {e}")

    @database_sync_to_async
    def get_pending_notifications(self):
        from .models import Notification
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=self.user_id)
            qs = Notification.objects.filter(
                tenant_id=user.tenant_id,
                status__in=["pending", "queued", "sent"],
            ).order_by("-created_at")[:10]
            return list(qs.values("id", "notification_type", "title", "body", "created_at", "status"))
        except Exception:
            return []

    async def send_pending_notifications(self):
        """Push any pending notifications to the newly connected client."""
        notifications = await self.get_pending_notifications()
        if notifications:
            await self.send(text_data=json.dumps({
                "type": "pending_notifications",
                "notifications": [
                    {**n, "id": str(n["id"]), "created_at": n["created_at"].isoformat()}
                    for n in notifications
                ],
            }))
