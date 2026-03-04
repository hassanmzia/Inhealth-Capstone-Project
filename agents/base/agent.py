"""
MCPAgent — base class for all 25 InHealth AI agents.

Supports:
  - MCP (Model Context Protocol) context injection
  - A2A (Agent-to-Agent) message bus via Redis pub/sub
  - PHI detection and redaction before LLM calls
  - LangChain agent executor with tool calling
  - Langfuse tracing for every LLM call
  - Structured, typed result output
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from base.memory import AgentMemory
from base.tools import detect_phi, redact_phi, query_fhir_database, vector_search

logger = logging.getLogger("inhealth.agent")


# ---------------------------------------------------------------------------
# A2A message types
# ---------------------------------------------------------------------------

A2A_MESSAGE_TYPES = {
    "ALERT": "ALERT",
    "REQUEST": "REQUEST",
    "RESPONSE": "RESPONSE",
    "DATA_UPDATE": "DATA_UPDATE",
    "EMERGENCY": "EMERGENCY",
}

A2A_PRIORITY_LEVELS = {
    "CRITICAL": 1,
    "HIGH": 2,
    "NORMAL": 3,
    "LOW": 4,
}


# ---------------------------------------------------------------------------
# MCPAgent base class
# ---------------------------------------------------------------------------

class MCPAgent(ABC):
    """
    Base class for all 25 InHealth AI agents.
    Implements MCP context injection, A2A messaging, PHI redaction, and Langfuse tracing.
    """

    # Subclasses override these
    agent_id: int = 0
    agent_name: str = "base_agent"
    agent_tier: str = "base"
    system_prompt: str = (
        "You are an AI clinical decision support agent for InHealth Chronic Care. "
        "You analyze patient data, generate clinical insights, and recommend evidence-based "
        "interventions. Always be precise, cite evidence levels, and flag emergencies immediately. "
        "Never fabricate clinical data."
    )

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        memory: Optional[AgentMemory] = None,
        langfuse_handler: Optional[LangfuseCallbackHandler] = None,
    ):
        self.llm = llm
        self.tools = tools or self._default_tools()
        self.memory = memory
        self.langfuse_handler = langfuse_handler
        self._redis_client: Optional[aioredis.Redis] = None
        self._fhir_base_url = os.getenv("FHIR_SERVER_URL", "http://fhir-server:8080/fhir")

        # Build LangChain agent
        self._agent_executor = self._build_agent_executor()

        logger.info(
            "Initialised %s (id=%d, tier=%s)",
            self.agent_name,
            self.agent_id,
            self.agent_tier,
        )

    # ── Subclass interface ─────────────────────────────────────────────────

    @abstractmethod
    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Agent-specific analysis logic. Must return a structured result dict.
        Called internally by execute() after MCP context is loaded and PHI is redacted.
        """
        ...

    def _default_tools(self) -> List[BaseTool]:
        """Default tools available to all agents; subclasses can extend."""
        return [query_fhir_database, vector_search, detect_phi, redact_phi]

    # ── Core execute flow ──────────────────────────────────────────────────

    async def execute(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Full agent execution pipeline:
          1. Get MCP context (patient data + guidelines)
          2. Detect / redact PHI in any text inputs
          3. Run agent-specific analyze()
          4. Log result to Langfuse
          5. Publish A2A results if alerts present
          6. Return structured result
        """
        run_id = str(uuid.uuid4())
        start_ts = time.monotonic()
        trace = None

        # Start Langfuse trace
        if self.langfuse_handler:
            try:
                from langfuse import Langfuse

                langfuse_client = Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
                    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                )
                trace = langfuse_client.trace(
                    name=f"{self.agent_name}.execute",
                    user_id=patient_id,
                    metadata={
                        "agent_id": self.agent_id,
                        "agent_tier": self.agent_tier,
                        "run_id": run_id,
                        "tenant_id": state.get("tenant_id", ""),
                    },
                )
            except Exception as exc:
                logger.debug("Langfuse trace init failed (non-fatal): %s", exc)

        try:
            # 1. MCP context
            mcp_context = await self.get_mcp_context(patient_id)
            context = {**mcp_context, **context}

            # 2. PHI redaction on any string inputs in context
            context = self._redact_context_phi(context)

            # 3. Agent-specific analysis
            result = await self.analyze(
                patient_id=patient_id,
                state=state,
                context=context,
            )

            # Inject metadata
            duration_ms = (time.monotonic() - start_ts) * 1000
            result["agent_name"] = self.agent_name
            result["agent_id"] = self.agent_id
            result["run_id"] = run_id
            result["duration_ms"] = round(duration_ms, 2)
            result["trace_id"] = trace.id if trace else ""
            result["timestamp"] = datetime.now(timezone.utc).isoformat()

            # 4. Langfuse span update
            if trace:
                try:
                    trace.update(
                        output=json.dumps(result, default=str),
                        level="DEFAULT",
                    )
                except Exception:
                    pass

            # 5. A2A broadcast if alerts present
            alerts = result.get("alerts", [])
            if alerts:
                for alert in alerts:
                    await self.send_a2a_message(
                        recipient_id="supervisor",
                        message_type=A2A_MESSAGE_TYPES["ALERT"],
                        payload=alert,
                        priority=alert.get("severity", "NORMAL"),
                    )

            return result

        except Exception as exc:
            duration_ms = (time.monotonic() - start_ts) * 1000
            logger.error(
                "%s.execute failed for patient=%s: %s",
                self.agent_name,
                patient_id,
                exc,
                exc_info=True,
            )
            if trace:
                try:
                    trace.update(level="ERROR", status_message=str(exc))
                except Exception:
                    pass
            return {
                "agent_name": self.agent_name,
                "agent_id": self.agent_id,
                "run_id": run_id,
                "status": "error",
                "error": str(exc),
                "duration_ms": round(duration_ms, 2),
                "alerts": [],
                "emergency_detected": False,
            }

    # ── MCP context ────────────────────────────────────────────────────────

    async def get_mcp_context(self, patient_id: str) -> Dict[str, Any]:
        """
        Build the MCP-formatted context for this agent:
          - Patient demographics and active conditions from FHIR
          - Relevant clinical guidelines via RAG (Qdrant)
          - Agent-specific tool constraints and permissions
        """
        import httpx

        context: Dict[str, Any] = {
            "mcp_version": "1.0",
            "agent": self.agent_name,
            "patient_id": patient_id,
            "tools": [t.name for t in self.tools],
            "constraints": {
                "max_tokens": 4096,
                "phi_redaction": True,
                "require_evidence": True,
            },
        }

        # Fetch patient demographics from FHIR
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._fhir_base_url}/Patient/{patient_id}",
                    headers={"Accept": "application/fhir+json"},
                )
                if resp.status_code == 200:
                    patient_data = resp.json()
                    context["patient"] = {
                        "id": patient_id,
                        "birthDate": patient_data.get("birthDate", ""),
                        "gender": patient_data.get("gender", ""),
                        "name": patient_data.get("name", [{}])[0].get("text", ""),
                    }
                else:
                    context["patient"] = {"id": patient_id}
        except Exception as exc:
            logger.debug("FHIR patient fetch failed: %s", exc)
            context["patient"] = {"id": patient_id}

        # Retrieve relevant guidelines via RAG
        try:
            guidelines = vector_search.invoke({
                "query": f"clinical guidelines {self.agent_tier} {self.agent_name}",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
            context["guidelines"] = guidelines
        except Exception as exc:
            logger.debug("RAG guideline fetch failed: %s", exc)
            context["guidelines"] = []

        return context

    # ── PHI redaction ──────────────────────────────────────────────────────

    def _redact_context_phi(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PHI from string values in the context dict."""
        result = {}
        for key, value in context.items():
            if isinstance(value, str) and len(value) > 10:
                try:
                    phi_check = detect_phi.invoke({"text": value})
                    if phi_check.get("has_phi"):
                        value = redact_phi.invoke({"text": value})
                except Exception:
                    pass
            elif isinstance(value, dict):
                value = self._redact_context_phi(value)
            elif isinstance(value, list):
                value = [
                    self._redact_context_phi(item) if isinstance(item, dict) else item
                    for item in value
                ]
            result[key] = value
        return result

    # ── LangChain agent builder ────────────────────────────────────────────

    def _build_agent_executor(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        callbacks = [self.langfuse_handler] if self.langfuse_handler else []

        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=bool(os.getenv("AGENT_VERBOSE", "false").lower() == "true"),
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
            handle_parsing_errors=True,
            callbacks=callbacks,
            return_intermediate_steps=True,
        )

    async def run_agent_chain(
        self,
        input_text: str,
        chat_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Run the LangChain agent executor with the given input.
        Wraps synchronous invoke in an executor for async compatibility.
        """
        loop = asyncio.get_event_loop()
        kwargs = {"input": input_text}
        if chat_history:
            kwargs["chat_history"] = chat_history

        result = await loop.run_in_executor(
            None, lambda: self._agent_executor.invoke(kwargs)
        )
        return result

    # ── A2A messaging ──────────────────────────────────────────────────────

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        if self._redis_client is None:
            try:
                url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self._redis_client = await aioredis.from_url(url, decode_responses=True)
                await self._redis_client.ping()
            except Exception as exc:
                logger.debug("A2A Redis unavailable: %s", exc)
                return None
        return self._redis_client

    async def send_a2a_message(
        self,
        recipient_id: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: str = "NORMAL",
    ) -> bool:
        """
        Publish an A2A/1.0 protocol message to the Redis message bus.

        Message format:
          {
            "a2a_version": "1.0",
            "message_id": "<uuid>",
            "sender_id": "<agent_name>",
            "recipient_id": "<agent_name | supervisor | broadcast>",
            "message_type": "ALERT | REQUEST | RESPONSE | DATA_UPDATE | EMERGENCY",
            "priority": "CRITICAL | HIGH | NORMAL | LOW",
            "payload": {...},
            "timestamp": "<ISO-8601>"
          }
        """
        message = {
            "a2a_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "sender_id": self.agent_name,
            "recipient_id": recipient_id,
            "message_type": message_type,
            "priority": priority,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        channel = f"a2a:{recipient_id}"
        if priority == "CRITICAL":
            channel = f"a2a:critical:{recipient_id}"

        redis = await self._get_redis()
        if redis:
            try:
                await redis.publish(channel, json.dumps(message))
                logger.debug(
                    "A2A: %s → %s [%s] on %s",
                    self.agent_name,
                    recipient_id,
                    message_type,
                    channel,
                )
                return True
            except Exception as exc:
                logger.warning("A2A publish failed: %s", exc)
        return False

    async def receive_a2a_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle an incoming A2A message from another agent or the supervisor.
        Route based on message_type.
        """
        msg_type = message.get("message_type", "")
        sender = message.get("sender_id", "unknown")
        payload = message.get("payload", {})

        logger.info(
            "A2A received: %s from %s (type=%s)",
            self.agent_name,
            sender,
            msg_type,
        )

        if msg_type == A2A_MESSAGE_TYPES["ALERT"]:
            return await self._handle_alert_message(sender, payload)
        elif msg_type == A2A_MESSAGE_TYPES["REQUEST"]:
            return await self._handle_request_message(sender, payload)
        elif msg_type == A2A_MESSAGE_TYPES["RESPONSE"]:
            return await self._handle_response_message(sender, payload)
        elif msg_type == A2A_MESSAGE_TYPES["DATA_UPDATE"]:
            return await self._handle_data_update_message(sender, payload)
        elif msg_type == A2A_MESSAGE_TYPES["EMERGENCY"]:
            return await self._handle_emergency_message(sender, payload)
        else:
            logger.warning("Unknown A2A message type: %s", msg_type)
            return None

    async def _handle_alert_message(self, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Default alert handler — log and return acknowledgment."""
        logger.warning("ALERT from %s: %s", sender, payload.get("message", ""))
        return {"status": "acknowledged", "agent": self.agent_name}

    async def _handle_request_message(self, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Default request handler — to be overridden by specific agents."""
        return {"status": "not_implemented", "agent": self.agent_name}

    async def _handle_response_message(self, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "agent": self.agent_name}

    async def _handle_data_update_message(self, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "agent": self.agent_name}

    async def _handle_emergency_message(self, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.critical("EMERGENCY from %s: %s", sender, payload)
        return {"status": "acknowledged", "agent": self.agent_name, "action": "escalating"}

    # ── Utilities ──────────────────────────────────────────────────────────

    def _build_alert(
        self,
        severity: str,
        message: str,
        patient_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Helper to build a standardized alert dict."""
        return {
            "alert_id": str(uuid.uuid4()),
            "severity": severity,
            "source": self.agent_name,
            "patient_id": patient_id,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "acknowledged": False,
        }

    def _build_result(
        self,
        status: str = "completed",
        findings: Optional[Dict[str, Any]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        recommendations: Optional[List[str]] = None,
        emergency_detected: bool = False,
        requires_hitl: bool = False,
    ) -> Dict[str, Any]:
        """Build a standardized agent result dict."""
        return {
            "status": status,
            "findings": findings or {},
            "alerts": alerts or [],
            "recommendations": recommendations or [],
            "emergency_detected": emergency_detected,
            "requires_hitl": requires_hitl,
        }
