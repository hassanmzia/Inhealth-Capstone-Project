"""
Conversation memory management for InHealth AI agents.

- Per-patient, per-agent rolling window memory (last 20 messages)
- Redis-backed for persistence across requests
- Memory summarization for long conversations using LLM
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from langchain.memory import ConversationSummaryBufferMemory
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger("inhealth.memory")

_MAX_WINDOW = int(os.getenv("AGENT_MEMORY_WINDOW", "20"))
_SUMMARY_THRESHOLD = int(os.getenv("AGENT_MEMORY_SUMMARY_THRESHOLD", "40"))


# ---------------------------------------------------------------------------
# Redis-backed message store
# ---------------------------------------------------------------------------

def _get_sync_redis():
    """Return a synchronous Redis client or None."""
    try:
        import redis as sync_redis

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = sync_redis.from_url(url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.debug("Sync Redis unavailable: %s", exc)
        return None


class RedisMessageStore:
    """
    Lightweight Redis-backed store for serialized LangChain messages.
    Falls back to an in-memory dict if Redis is unavailable.
    """

    _fallback: Dict[str, List[Dict[str, Any]]] = {}
    _TTL = 60 * 60 * 24 * 7  # 7 days

    def _key(self, agent_name: str, patient_id: str) -> str:
        return f"agent_memory:{agent_name}:{patient_id}"

    def _serialize_message(self, message: BaseMessage) -> Dict[str, Any]:
        return {
            "type": message.__class__.__name__,
            "content": message.content,
            "additional_kwargs": message.additional_kwargs,
        }

    def _deserialize_message(self, data: Dict[str, Any]) -> BaseMessage:
        msg_type = data.get("type", "HumanMessage")
        content = data.get("content", "")
        kwargs = data.get("additional_kwargs", {})
        mapping = {
            "HumanMessage": HumanMessage,
            "AIMessage": AIMessage,
            "SystemMessage": SystemMessage,
        }
        cls = mapping.get(msg_type, HumanMessage)
        return cls(content=content, additional_kwargs=kwargs)

    def load_messages(self, agent_name: str, patient_id: str) -> List[BaseMessage]:
        key = self._key(agent_name, patient_id)
        redis = _get_sync_redis()
        if redis:
            try:
                raw = redis.get(key)
                if raw:
                    data = json.loads(raw)
                    return [self._deserialize_message(m) for m in data]
                return []
            except Exception as exc:
                logger.warning("RedisMessageStore.load_messages failed: %s", exc)
                return []
        return [
            self._deserialize_message(m)
            for m in self._fallback.get(key, [])
        ]

    def save_messages(
        self, agent_name: str, patient_id: str, messages: List[BaseMessage]
    ) -> None:
        key = self._key(agent_name, patient_id)
        serialized = [self._serialize_message(m) for m in messages[-_MAX_WINDOW:]]
        redis = _get_sync_redis()
        if redis:
            try:
                redis.setex(key, self._TTL, json.dumps(serialized))
                return
            except Exception as exc:
                logger.warning("RedisMessageStore.save_messages failed: %s", exc)
        self._fallback[key] = serialized

    def clear_messages(self, agent_name: str, patient_id: str) -> None:
        key = self._key(agent_name, patient_id)
        redis = _get_sync_redis()
        if redis:
            try:
                redis.delete(key)
                return
            except Exception as exc:
                logger.warning("RedisMessageStore.clear_messages failed: %s", exc)
        self._fallback.pop(key, None)


# ---------------------------------------------------------------------------
# Per-agent memory wrapper
# ---------------------------------------------------------------------------

class AgentMemory:
    """
    Rolling-window conversation memory for a specific (agent, patient) pair.
    Supports optional LLM-based summarization when history grows too long.
    """

    def __init__(
        self,
        agent_name: str,
        patient_id: str,
        llm: Optional[BaseChatModel] = None,
        max_window: int = _MAX_WINDOW,
        summary_threshold: int = _SUMMARY_THRESHOLD,
    ):
        self.agent_name = agent_name
        self.patient_id = patient_id
        self.max_window = max_window
        self.summary_threshold = summary_threshold
        self._store = RedisMessageStore()
        self._llm = llm
        self._summary: Optional[str] = None

        # Load persisted messages
        self._messages: List[BaseMessage] = self._store.load_messages(
            agent_name, patient_id
        )

    @property
    def messages(self) -> List[BaseMessage]:
        return list(self._messages)

    def add_user_message(self, content: str) -> None:
        self._messages.append(HumanMessage(content=content))
        self._maybe_summarize_and_persist()

    def add_ai_message(self, content: str) -> None:
        self._messages.append(AIMessage(content=content))
        self._maybe_summarize_and_persist()

    def add_system_message(self, content: str) -> None:
        self._messages.append(SystemMessage(content=content))
        self._maybe_summarize_and_persist()

    def get_recent_messages(self, n: Optional[int] = None) -> List[BaseMessage]:
        """Return the last n messages (default: max_window)."""
        limit = n or self.max_window
        return self._messages[-limit:]

    def get_context_string(self, n: Optional[int] = None) -> str:
        """Return a plain-text representation of recent conversation history."""
        lines = []
        if self._summary:
            lines.append(f"[SUMMARY OF EARLIER CONVERSATION]\n{self._summary}\n")
        for msg in self.get_recent_messages(n):
            role = msg.__class__.__name__.replace("Message", "").upper()
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._messages = []
        self._summary = None
        self._store.clear_messages(self.agent_name, self.patient_id)

    def _maybe_summarize_and_persist(self) -> None:
        """Summarize when history exceeds threshold; always persist."""
        if len(self._messages) > self.summary_threshold and self._llm:
            try:
                self._summarize()
            except Exception as exc:
                logger.warning("Memory summarization failed: %s", exc)

        # Trim to rolling window
        if len(self._messages) > self.max_window:
            self._messages = self._messages[-self.max_window:]

        self._store.save_messages(self.agent_name, self.patient_id, self._messages)

    def _summarize(self) -> None:
        """Use LLM to produce a running summary of older messages."""
        if not self._llm:
            return
        older = self._messages[: -self.max_window]
        if not older:
            return
        prompt = (
            "You are a clinical AI summarizer. Summarize the following conversation "
            "between the AI agent and the patient management system. Be concise. "
            "Focus on clinical findings, decisions, and outstanding actions.\n\n"
        )
        for msg in older:
            role = msg.__class__.__name__.replace("Message", "").upper()
            prompt += f"{role}: {msg.content}\n"

        response = self._llm.invoke(prompt)
        self._summary = response.content if hasattr(response, "content") else str(response)
        logger.debug(
            "Memory summarized for agent=%s patient=%s (%d messages)",
            self.agent_name,
            self.patient_id,
            len(older),
        )


# ---------------------------------------------------------------------------
# Memory manager — singleton per process
# ---------------------------------------------------------------------------

class AgentMemoryManager:
    """
    Factory / cache for AgentMemory instances.
    Ensures a single AgentMemory per (agent_name, patient_id) pair per process.
    """

    _instances: Dict[str, AgentMemory] = {}

    def get_memory(
        self,
        agent_name: str,
        patient_id: str,
        llm: Optional[BaseChatModel] = None,
    ) -> AgentMemory:
        cache_key = f"{agent_name}:{patient_id}"
        if cache_key not in self._instances:
            self._instances[cache_key] = AgentMemory(
                agent_name=agent_name,
                patient_id=patient_id,
                llm=llm,
            )
        return self._instances[cache_key]

    def clear_patient_memory(self, patient_id: str) -> None:
        """Clear all agent memories for a specific patient."""
        to_delete = [k for k in self._instances if k.endswith(f":{patient_id}")]
        for key in to_delete:
            self._instances[key].clear()
            del self._instances[key]

    def clear_all(self) -> None:
        for mem in self._instances.values():
            mem.clear()
        self._instances.clear()
