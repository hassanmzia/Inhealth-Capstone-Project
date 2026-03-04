"""
InHealth Chronic Care — AI Agent System
FastAPI entrypoint with LangGraph supervisor, Langfuse tracing, WebSocket support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("inhealth.agents")

# ---------------------------------------------------------------------------
# Langfuse initialisation
# ---------------------------------------------------------------------------
from langfuse import Langfuse  # noqa: E402
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler  # noqa: E402

langfuse_client: Optional[Langfuse] = None
langfuse_handler: Optional[LangfuseCallbackHandler] = None

# ---------------------------------------------------------------------------
# LangGraph supervisor (lazy import to avoid circular deps)
# ---------------------------------------------------------------------------
supervisor_graph = None
redis_client: Optional[aioredis.Redis] = None

# In-memory store for agent execution history (per-run; production would use DB)
execution_history: Dict[str, List[Dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Prometheus metrics (pure-Python counter implementation — no prometheus_client
# required at import time; falls back gracefully if not installed)
# ---------------------------------------------------------------------------
try:
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    REQUEST_COUNT = Counter(
        "inhealth_agent_requests_total",
        "Total agent API requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "inhealth_agent_request_latency_seconds",
        "Agent API request latency",
        ["endpoint"],
    )
    AGENT_RUNS = Counter(
        "inhealth_agent_runs_total",
        "Total agent run invocations",
        ["agent_name", "status"],
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed; /metrics will return empty body")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global langfuse_client, langfuse_handler, supervisor_graph, redis_client

    # Langfuse
    try:
        langfuse_client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        langfuse_handler = LangfuseCallbackHandler(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        logger.info("Langfuse initialised successfully")
    except Exception as exc:
        logger.warning("Langfuse init failed (non-fatal): %s", exc)

    # Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await aioredis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as exc:
        logger.warning("Redis connection failed (non-fatal): %s", exc)

    # LangGraph supervisor
    try:
        from orchestrator.supervisor import build_supervisor_graph

        supervisor_graph = build_supervisor_graph(
            langfuse_handler=langfuse_handler,
        )
        logger.info("LangGraph supervisor graph compiled successfully")
    except Exception as exc:
        logger.error("Supervisor graph init failed: %s", exc, exc_info=True)

    yield

    # Shutdown
    if redis_client:
        await redis_client.aclose()
    if langfuse_client:
        langfuse_client.flush()
    logger.info("Agent service shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="InHealth AI Agent System",
    description="Production multi-agent chronic disease management platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AgentRunRequest(BaseModel):
    agent_name: str = Field(..., description="Name of the agent to run")
    patient_id: str = Field(..., description="FHIR patient ID")
    tenant_id: str = Field(..., description="Tenant identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: str = Field(default="NORMAL", description="CRITICAL|HIGH|NORMAL|LOW")


class PipelineRunRequest(BaseModel):
    patient_id: str
    tenant_id: str
    trigger: str = Field(default="scheduled", description="scheduled|alert|manual")
    context: Dict[str, Any] = Field(default_factory=dict)


class ResearchRequest(BaseModel):
    query: str
    condition: Optional[str] = None
    patient_id: Optional[str] = None
    tenant_id: str
    include_trials: bool = False


class AgentRunResponse(BaseModel):
    run_id: str
    agent_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float
    trace_url: Optional[str] = None


class PipelineRunResponse(BaseModel):
    pipeline_id: str
    patient_id: str
    status: str
    results: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    duration_ms: float
    trace_url: Optional[str] = None


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket client connected: %s", client_id)

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        logger.info("WebSocket client disconnected: %s", client_id)

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning("Failed to send WS message to %s: %s", client_id, exc)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)


ws_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _record_history(agent_id: str, record: Dict[str, Any]):
    if agent_id not in execution_history:
        execution_history[agent_id] = []
    execution_history[agent_id].append(record)
    # Keep last 100 records per agent
    if len(execution_history[agent_id]) > 100:
        execution_history[agent_id] = execution_history[agent_id][-100:]


def _get_trace_url(trace_id: str) -> Optional[str]:
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    return f"{host}/trace/{trace_id}" if trace_id else None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness / readiness probe."""
    checks = {
        "status": "healthy",
        "service": "inhealth-ai-agents",
        "version": "1.0.0",
        "langfuse": langfuse_client is not None,
        "supervisor": supervisor_graph is not None,
        "redis": False,
    }
    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
    return checks


@app.get("/metrics", response_class=PlainTextResponse, tags=["System"])
async def metrics():
    """Prometheus metrics endpoint."""
    if PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
    return PlainTextResponse(content="# prometheus_client not installed\n")


@app.post("/agents/run", response_model=AgentRunResponse, tags=["Agents"])
async def run_agent(request: AgentRunRequest):
    """Trigger a specific named agent for a patient."""
    run_id = str(uuid.uuid4())
    start_ts = time.monotonic()

    if PROMETHEUS_AVAILABLE:
        REQUEST_COUNT.labels(method="POST", endpoint="/agents/run", status="started").inc()

    try:
        # Lazy-import the agent registry
        from orchestrator.supervisor import get_agent_by_name

        agent = get_agent_by_name(request.agent_name, langfuse_handler=langfuse_handler)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{request.agent_name}' not found",
            )

        # Build minimal state
        initial_state: Dict[str, Any] = {
            "patient_id": request.patient_id,
            "tenant_id": request.tenant_id,
            "messages": [],
            "monitoring_results": {},
            "diagnostic_results": {},
            "risk_scores": {},
            "interventions": [],
            "actions_taken": [],
            "alerts": [],
            "emergency_detected": False,
            "current_tier": "tier1",
            "iteration": 0,
            "error": None,
            "hitl_required": False,
            "hitl_decision": None,
            "final_report": None,
        }

        result = await agent.execute(
            patient_id=request.patient_id,
            state=initial_state,
            context=request.context,
        )

        duration_ms = (time.monotonic() - start_ts) * 1000
        trace_id = result.get("trace_id", "")
        response = AgentRunResponse(
            run_id=run_id,
            agent_name=request.agent_name,
            status="completed",
            result=result,
            duration_ms=duration_ms,
            trace_url=_get_trace_url(trace_id),
        )

        _record_history(
            request.agent_name,
            {"run_id": run_id, "patient_id": request.patient_id, **response.model_dump()},
        )

        # Broadcast to WebSocket subscribers
        await ws_manager.broadcast(
            {
                "event": "agent_completed",
                "run_id": run_id,
                "agent_name": request.agent_name,
                "patient_id": request.patient_id,
                "status": "completed",
            }
        )

        if PROMETHEUS_AVAILABLE:
            AGENT_RUNS.labels(agent_name=request.agent_name, status="success").inc()
            REQUEST_LATENCY.labels(endpoint="/agents/run").observe(duration_ms / 1000)

        return response

    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.monotonic() - start_ts) * 1000
        logger.error("Agent run failed: %s", exc, exc_info=True)
        if PROMETHEUS_AVAILABLE:
            AGENT_RUNS.labels(agent_name=request.agent_name, status="error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.post("/agents/run-pipeline", response_model=PipelineRunResponse, tags=["Agents"])
async def run_pipeline(request: PipelineRunRequest):
    """Trigger the full 5-tier patient monitoring pipeline via LangGraph."""
    pipeline_id = str(uuid.uuid4())
    start_ts = time.monotonic()

    if supervisor_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supervisor graph not initialised. Check logs.",
        )

    initial_state = {
        "patient_id": request.patient_id,
        "tenant_id": request.tenant_id,
        "messages": [],
        "monitoring_results": {},
        "diagnostic_results": {},
        "risk_scores": {},
        "interventions": [],
        "actions_taken": [],
        "alerts": [],
        "emergency_detected": False,
        "current_tier": "tier1",
        "iteration": 0,
        "error": None,
        "hitl_required": False,
        "hitl_decision": None,
        "final_report": None,
    }

    config = {
        "configurable": {"thread_id": pipeline_id},
        "callbacks": [langfuse_handler] if langfuse_handler else [],
    }

    try:
        final_state = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supervisor_graph.invoke(initial_state, config=config),
        )
        duration_ms = (time.monotonic() - start_ts) * 1000

        response = PipelineRunResponse(
            pipeline_id=pipeline_id,
            patient_id=request.patient_id,
            status="completed",
            results=final_state.get("final_report", {}),
            alerts=final_state.get("alerts", []),
            duration_ms=duration_ms,
        )

        await ws_manager.broadcast(
            {
                "event": "pipeline_completed",
                "pipeline_id": pipeline_id,
                "patient_id": request.patient_id,
                "status": "completed",
                "alert_count": len(response.alerts),
            }
        )

        return response

    except Exception as exc:
        duration_ms = (time.monotonic() - start_ts) * 1000
        logger.error("Pipeline run failed for patient %s: %s", request.patient_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.get("/agents/status", tags=["Agents"])
async def get_agent_statuses():
    """Return health / status of all registered agents."""
    try:
        from orchestrator.supervisor import AGENT_REGISTRY

        statuses = {}
        for name, cls in AGENT_REGISTRY.items():
            statuses[name] = {
                "agent_name": name,
                "status": "available",
                "last_run": None,
                "run_count": len(execution_history.get(name, [])),
            }
        return {"agents": statuses, "total": len(statuses)}
    except Exception as exc:
        logger.error("Failed to retrieve agent statuses: %s", exc)
        return {"agents": {}, "total": 0, "error": str(exc)}


@app.get("/agents/{agent_id}/history", tags=["Agents"])
async def get_agent_history(agent_id: str, limit: int = 20):
    """Return recent execution history for a specific agent."""
    history = execution_history.get(agent_id, [])
    return {
        "agent_id": agent_id,
        "history": history[-limit:],
        "total_runs": len(history),
    }


@app.post("/agents/research", tags=["Research"])
async def run_research_pipeline(request: ResearchRequest):
    """Trigger the research pipeline (literature + synthesis + trials + guidelines + Q&A)."""
    run_id = str(uuid.uuid4())
    start_ts = time.monotonic()

    try:
        from research_system.literature_agent import LiteratureAgent
        from research_system.synthesis_agent import SynthesisAgent
        from research_system.qa_agent import QAAgent

        lit_agent = LiteratureAgent(langfuse_handler=langfuse_handler)
        synth_agent = SynthesisAgent(langfuse_handler=langfuse_handler)
        qa_agent = QAAgent(langfuse_handler=langfuse_handler)

        # Run sequentially: literature → synthesis → QA
        lit_results = await lit_agent.search(query=request.query, condition=request.condition)
        synthesis = await synth_agent.synthesize(literature_results=lit_results)
        qa_answer = await qa_agent.answer(
            question=request.query,
            patient_id=request.patient_id,
            context={"synthesis": synthesis},
        )

        trials = []
        if request.include_trials and request.condition:
            from research_system.trial_matching_agent import TrialMatchingAgent

            trial_agent = TrialMatchingAgent(langfuse_handler=langfuse_handler)
            trials = await trial_agent.find_trials(
                condition=request.condition,
                patient_id=request.patient_id,
            )

        duration_ms = (time.monotonic() - start_ts) * 1000
        return {
            "run_id": run_id,
            "status": "completed",
            "literature": lit_results,
            "synthesis": synthesis,
            "qa_answer": qa_answer,
            "trials": trials,
            "duration_ms": duration_ms,
        }

    except Exception as exc:
        duration_ms = (time.monotonic() - start_ts) * 1000
        logger.error("Research pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@app.websocket("/agents/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time agent updates via WebSocket."""
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id)
    try:
        # Send initial handshake
        await websocket.send_json(
            {"event": "connected", "client_id": client_id, "message": "InHealth Agent WS ready"}
        )
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                event_type = data.get("event", "unknown")

                if event_type == "ping":
                    await websocket.send_json({"event": "pong", "client_id": client_id})

                elif event_type == "subscribe_patient":
                    patient_id = data.get("patient_id")
                    if redis_client and patient_id:
                        # Subscribe to Redis channel for this patient
                        pubsub = redis_client.pubsub()
                        await pubsub.subscribe(f"patient:{patient_id}:alerts")
                        await websocket.send_json(
                            {"event": "subscribed", "patient_id": patient_id}
                        )
                    else:
                        await websocket.send_json(
                            {"event": "error", "message": "Cannot subscribe: Redis unavailable or missing patient_id"}
                        )

                elif event_type == "hitl_decision":
                    # Forward HITL decision to supervisor
                    from orchestrator.hitl import process_hitl_response

                    decision = data.get("decision", {})
                    result = await process_hitl_response(decision)
                    await websocket.send_json({"event": "hitl_processed", "result": result})

                else:
                    await websocket.send_json(
                        {"event": "echo", "original": data, "client_id": client_id}
                    )

            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as exc:
        logger.error("WebSocket error for client %s: %s", client_id, exc)
        ws_manager.disconnect(client_id)
