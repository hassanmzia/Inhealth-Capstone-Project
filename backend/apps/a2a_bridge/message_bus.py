"""
A2A (Agent-to-Agent) message bus using Redis pub/sub.
Enables async communication between AI agents.
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import redis
from django.conf import settings

logger = logging.getLogger("apps.a2a_bridge")


class A2AMessage:
    """Represents an A2A message envelope."""

    def __init__(
        self,
        sender_agent: str,
        receiver_agent: str,
        message_type: str,
        payload: Dict,
        correlation_id: str = None,
        tenant_id: str = None,
    ):
        self.id = str(uuid.uuid4())
        self.sender_agent = sender_agent
        self.receiver_agent = receiver_agent
        self.message_type = message_type
        self.payload = payload
        self.correlation_id = correlation_id or self.id
        self.tenant_id = tenant_id
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender_agent": self.sender_agent,
            "receiver_agent": self.receiver_agent,
            "message_type": self.message_type,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "A2AMessage":
        msg = cls(
            sender_agent=data["sender_agent"],
            receiver_agent=data["receiver_agent"],
            message_type=data["message_type"],
            payload=data["payload"],
            correlation_id=data.get("correlation_id"),
            tenant_id=data.get("tenant_id"),
        )
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class A2AMessageBus:
    """
    Redis-based pub/sub message bus for agent-to-agent communication.

    Agents publish and subscribe to channels:
    - a2a:{tenant_id}:{agent_name} — agent-specific channel
    - a2a:{tenant_id}:broadcast — broadcast to all agents in tenant
    """

    def __init__(self):
        self._redis = None
        self._subscriptions: Dict[str, Callable] = {}
        self._subscriber_threads: Dict[str, threading.Thread] = {}

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def publish(self, message: A2AMessage) -> bool:
        """Publish a message to the receiver agent's channel."""
        channel = self._get_channel(message.tenant_id, message.receiver_agent)
        try:
            self.redis.publish(channel, message.to_json())
            logger.debug(
                f"A2A published: {message.sender_agent} → {message.receiver_agent} "
                f"[{message.message_type}] on {channel}"
            )
            return True
        except Exception as e:
            logger.error(f"A2A publish failed: {e}")
            return False

    def broadcast(self, message: A2AMessage) -> bool:
        """Broadcast a message to all agents in the tenant."""
        channel = self._get_broadcast_channel(message.tenant_id)
        try:
            self.redis.publish(channel, message.to_json())
            return True
        except Exception as e:
            logger.error(f"A2A broadcast failed: {e}")
            return False

    def subscribe(self, agent_name: str, tenant_id: str, handler: Callable) -> None:
        """Subscribe an agent to its dedicated channel."""
        channel = self._get_channel(tenant_id, agent_name)
        broadcast_channel = self._get_broadcast_channel(tenant_id)

        def listen_thread():
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(channel, broadcast_channel)
            logger.info(f"A2A subscriber started for {agent_name} on {channel}")

            for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                try:
                    data = json.loads(raw_message["data"])
                    msg = A2AMessage.from_dict(data)
                    handler(msg)
                except Exception as e:
                    logger.error(f"A2A message handler error for {agent_name}: {e}")

        thread = threading.Thread(target=listen_thread, daemon=True, name=f"a2a_{agent_name}")
        thread.start()
        self._subscriber_threads[agent_name] = thread

    def send_task(
        self,
        from_agent: str,
        to_agent: str,
        task_type: str,
        task_data: Dict,
        tenant_id: str,
    ) -> str:
        """Send a task request from one agent to another. Returns correlation ID."""
        msg = A2AMessage(
            sender_agent=from_agent,
            receiver_agent=to_agent,
            message_type=f"task.{task_type}",
            payload=task_data,
            tenant_id=tenant_id,
        )
        self.publish(msg)
        return msg.correlation_id

    def send_result(
        self,
        from_agent: str,
        to_agent: str,
        correlation_id: str,
        result: Dict,
        tenant_id: str,
    ) -> None:
        """Send a task result back to the requesting agent."""
        msg = A2AMessage(
            sender_agent=from_agent,
            receiver_agent=to_agent,
            message_type="task.result",
            payload=result,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )
        self.publish(msg)

    @staticmethod
    def _get_channel(tenant_id: str, agent_name: str) -> str:
        return f"a2a:{tenant_id}:{agent_name}"

    @staticmethod
    def _get_broadcast_channel(tenant_id: str) -> str:
        return f"a2a:{tenant_id}:broadcast"


# Global message bus singleton
_bus_instance: Optional[A2AMessageBus] = None


def get_message_bus() -> A2AMessageBus:
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = A2AMessageBus()
    return _bus_instance
