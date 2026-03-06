# InHealth Architecture Overview

## System Architecture

```
PRESENTATION LAYER
  React 18 + TypeScript + TailwindCSS + shadcn/ui + Recharts
  Patient Portal | Clinician Dashboard | Admin Console | Analytics

NGINX REVERSE PROXY (port 8788)
  / -> Frontend | /api/ -> Django | /ws/ -> Channels
  /agents/ -> FastAPI | /mcp/ -> MCP Server | /a2a/ -> A2A Gateway

BACKEND API LAYER
  Django 5 + DRF + Channels (ASGI)
  Auth: JWT + OAuth2 | RBAC: 8 healthcare roles
  Multi-tenancy: django-tenants (schema-per-org)
  14 Apps: accounts, tenants, fhir, hl7, patients, clinical,
           analytics, notifications, billing, sdoh, research,
           mcp_bridge, a2a_bridge, telemedicine

AGENT ORCHESTRATION LAYER (FastAPI + LangGraph)
  T1: Monitoring (4)  | T2: Diagnostic (4)
  T3: Risk (5)        | T4: Intervention (4)
  T5: Action (5)      | Research System (5)
  Security: PHI detection, guardrails, audit

DATA LAYER
  PostgreSQL 15 | Neo4j 5.12 | Qdrant | Redis 7
  Ollama + Claude/GPT-4o | MinIO

OBSERVABILITY
  Prometheus | Grafana | Langfuse | OpenTelemetry
```

## Key Design Decisions

- **Multi-tenancy**: django-tenants with PostgreSQL schema-per-tenant
- **Agent Orchestration**: LangGraph StateGraph as master supervisor
- **LLM Strategy**: Ollama local-first + Claude/GPT-4o fallback
- **Frontend**: Vite + React 18 + Zustand + TanStack Query
- **Deployment**: Docker Compose (dev) + Kubernetes/Helm (prod)

See `IMPLEMENTATION_PLAN.md` in the project root for the full specification.
