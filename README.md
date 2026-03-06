# InHealth Chronic Care

**Unified Autonomous Agentic AI Platform for Chronic Disease Management**

A production-grade, multi-tenant, HIPAA-compliant SaaS platform combining 25+ specialized AI agents, HL7/FHIR R4 interoperability, Neo4j clinical knowledge graph, LangGraph orchestration, Langfuse observability, and a modern React frontend into a comprehensive healthcare system.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Django Backend](#django-backend)
- [AI Agent System](#ai-agent-system)
- [MCP & A2A Protocols](#mcp--a2a-protocols)
- [Frontend](#frontend)
- [Database Architecture](#database-architecture)
- [Healthcare Interoperability](#healthcare-interoperability)
- [ML Models](#ml-models)
- [Monitoring & Observability](#monitoring--observability)
- [Security & Compliance](#security--compliance)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Tenant Management](#tenant-management)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

InHealth Chronic Care is an enterprise healthcare platform designed for hospital networks, clinic systems, and health organizations managing patients with chronic conditions (Diabetes, COPD, Cardiovascular Disease, Chronic Kidney Disease, Heart Failure).

The platform provides:
- **Autonomous clinical monitoring** via 25+ AI agents organized in 5 tiers
- **Real-time patient risk assessment** using ML models (LSTM, XGBoost, Random Forest, attention-based fusion)
- **Clinical decision support** with evidence-based recommendations from medical literature (PubMed, ClinicalTrials.gov)
- **Full EMR/EHR capability** with FHIR R4 and HL7 v2 interoperability
- **Multi-tenant architecture** with schema-per-organization data isolation
- **Population health analytics** with cohort analysis and predictive modeling
- **Revenue cycle management** with CPT billing and RPM codes

---

## Key Features

### Autonomous AI Agent System (25+ Agents)

| Tier | Agents | Function |
|------|--------|----------|
| **T1: Monitoring** | Glucose, Cardiac, Activity, Temperature | Real-time vital sign analysis from IoT/wearable devices |
| **T2: Diagnostic** | ECG, Kidney, Imaging, Lab | STEMI detection, eGFR trends, AI radiology, lab interpretation |
| **T3: Risk Assessment** | Comorbidity, Prediction, Family History, SDOH, ML Ensemble | Multi-model risk scoring with graph-based genetic risk |
| **T4: Intervention** | Coaching, Prescription, Contraindication, Triage | RAG-powered medication recommendations, drug interaction checks |
| **T5: Action** | Physician Notify, Patient Notify, Scheduling, EHR Integration, Billing | Priority-routed alerts, health-literacy adapted messaging |
| **Research** | Literature, Synthesis, Trial Matching, Guideline, Q&A | PubMed search, evidence grading, clinical trial matching |
| **Security** | PHI Detector, Guardrails, Audit Logger | HIPAA compliance, prompt injection protection |

### Clinical Features
- **14 FHIR R4 Resources**: Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Encounter, Appointment, CarePlan, AllergyIntolerance, Procedure, Immunization, DocumentReference, Bundle, CapabilityStatement
- **HL7 v2 Processing**: ADT (Admit/Discharge/Transfer), ORU (Lab Results), ORM (Orders)
- **Smart Order Sets**: AI-generated evidence-based order templates for Diabetes, Hypertension, COPD, Heart Failure, CKD
- **Care Gap Detection**: 14 types including A1C, eye exam, colonoscopy, mammogram, depression screening
- **Drug Interaction Detection**: Backtracking graph search on Neo4j knowledge graph
- **Telemedicine**: Video consultation with AI-assisted note generation
- **SDOH Assessment**: Food security, housing, transportation risk scoring

### Multi-Tenant SaaS
- Schema-per-organization PostgreSQL isolation via django-tenants
- Per-tenant branding, custom domains, and configuration
- Subscription tiers: Basic, Professional, Enterprise
- API key management and webhook subscriptions
- Usage analytics per organization

### Frontend (17 Pages)
- Patient Portal with vitals dashboard and health goals
- Clinician Dashboard with risk-stratified patient list
- Agent Control Panel with real-time 25-agent status
- Analytics Console with population health and fairness analysis
- Research Interface with natural language clinical Q&A
- Telemedicine, Billing, Admin, Settings pages
- Dark mode, PWA support, responsive design

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│   React 18 + TypeScript + TailwindCSS + shadcn/ui           │
│   17 Pages | Zustand | TanStack Query | Recharts | PWA      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / WSS
┌──────────────────────────▼──────────────────────────────────┐
│              NGINX REVERSE PROXY (Port 8788)                 │
│   / → Frontend | /api/ → Django | /ws/ → Channels           │
│   /agents/ → FastAPI | /mcp/ → MCP | /a2a/ → A2A            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  BACKEND API LAYER                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Django 5 + DRF + Channels (ASGI)                      │  │
│  │  15 Apps | JWT+OAuth2 | RBAC (8 roles) | Multi-tenant  │  │
│  │  ML: LSTM, XGBoost, RF, HMM, Attention, Digital Twin   │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────┐  ┌────────────────────────────┐    │
│  │  MCP Server (3001)  │  │  A2A Gateway (3002)         │    │
│  │  Tool Registry      │  │  Agent Card Registry        │    │
│  │  Context Mgmt       │  │  Task Delegation            │    │
│  └─────────────────────┘  └────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              AGENT ORCHESTRATION LAYER                        │
│  FastAPI + LangGraph StateGraph + LangChain                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LangGraph Supervisor → 25+ Agents (5 Tiers)          │  │
│  │  Parallel Execution | Conditional Routing | HITL       │  │
│  │  Redis A2A Message Bus (7 channels)                    │  │
│  └────────────────────────────────────────────────────────┘  │
│  Tools: FHIR | Neo4j | Qdrant | NL2SQL | Geospatial | Voice │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      DATA LAYER                              │
│  PostgreSQL 15    Neo4j 5.12    Qdrant     Redis 7          │
│  (FHIR+PostGIS)   (Knowledge    (Vector    (Cache/Broker/   │
│  (Multi-tenant)    Graph)        RAG)       A2A PubSub)     │
│                                                              │
│  Ollama/Llama 3.2 (Local LLM)    MinIO (Object Storage)    │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               OBSERVABILITY & MONITORING                     │
│  Prometheus (9390) | Grafana (9391) | Langfuse (3488)       │
│  Alertmanager (9393) | OpenTelemetry Distributed Tracing    │
│  5 Dashboards | 3 Alert Rule Sets                           │
└─────────────────────────────────────────────────────────────┘
```

The draw.io diagram is available at: `docs/architecture/technical_architecture.drawio`
The PowerPoint presentation is at: `docs/architecture/InHealth_Technical_Architecture.pptx`

---

## Technology Stack

### Backend
| Technology | Purpose | Version |
|-----------|---------|---------|
| Python | Backend language | 3.11+ |
| Django | Web framework | 5.x |
| Django REST Framework | REST API | 3.15+ |
| Django Channels | WebSocket/ASGI | 4.x |
| django-tenants | Multi-tenancy | 3.x |
| Celery | Async task queue | 5.x |
| FastAPI | Agent API server | 0.110+ |
| LangGraph | Agent orchestration | 0.2+ |
| LangChain | LLM framework | 0.2+ |

### Frontend
| Technology | Purpose |
|-----------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| TailwindCSS | Utility-first CSS |
| shadcn/ui | Component library |
| Zustand | State management |
| TanStack Query | Server state |
| Recharts | Data visualization |

### Databases
| Database | Purpose | Host Port |
|----------|---------|-----------|
| PostgreSQL 15 | FHIR data, EMR, multi-tenant | 5588 |
| Neo4j 5.12 | Clinical knowledge graph | 7588 (HTTP), 7688 (Bolt) |
| Qdrant | Vector embeddings, RAG | 6388 |
| Redis 7 | Cache, Celery broker, A2A pub/sub | 6489 |

### Infrastructure
| Service | Purpose | Host Port |
|---------|---------|-----------|
| Nginx | Reverse proxy | 8788 |
| Ollama | Local LLM (Llama 3.2) | 11788 |
| MinIO | Object storage | 9588 (API), 9589 (UI) |
| Prometheus | Metrics | 9390 |
| Grafana | Dashboards | 9391 |
| Alertmanager | Alert routing | 9393 |
| Langfuse | LLM tracing | 3488 |

### Node.js Services
| Service | Purpose | Port |
|---------|---------|------|
| MCP Server | Model Context Protocol | 3001 |
| A2A Gateway | Agent-to-Agent Protocol | 3002 |

---

## Project Structure

```
inhealth-chronic-care/
├── docker-compose.yml              # All 20 services
├── docker-compose.override.yml     # Dev overrides (hot reload)
├── .env.example                    # Environment variables template
├── Makefile                        # Developer shortcuts
│
├── nginx/                          # Reverse proxy config
│   ├── nginx.conf
│   └── conf.d/default.conf
│
├── backend/                        # Django 5 application
│   ├── Dockerfile
│   ├── requirements/               # base, development, production
│   ├── manage.py
│   ├── config/                     # Settings, URLs, ASGI, Celery, Telemetry
│   ├── apps/
│   │   ├── accounts/               # JWT, OAuth2, RBAC, 2FA (8 roles)
│   │   ├── tenants/                # Multi-tenant schema isolation
│   │   ├── fhir/                   # 14 FHIR R4 resources
│   │   ├── hl7/                    # HL7 v2 parser (ADT/ORU/ORM)
│   │   ├── patients/               # EMR patient management
│   │   ├── clinical/               # Encounters, care gaps, smart order sets
│   │   ├── analytics/              # Population health, cohorts
│   │   ├── notifications/          # 4-tier priority, multi-channel
│   │   ├── mcp_bridge/             # Django-side MCP bridge
│   │   ├── a2a_bridge/             # Django Channels WebSocket
│   │   ├── research/               # AI research system
│   │   ├── telemedicine/           # Video consultation
│   │   ├── billing/                # RCM, CPT, RPM billing
│   │   └── sdoh/                   # Social Determinants of Health
│   ├── graph/                      # Neo4j connection, queries, algorithms
│   ├── vector/                     # Qdrant client, RAG pipeline
│   ├── ml/                         # ML models (LSTM, XGBoost, RF, etc.)
│   └── tests/                      # Test suite (accounts, FHIR, patients, clinical, billing)
│
├── agents/                         # LangGraph agent system (FastAPI)
│   ├── Dockerfile
│   ├── main.py                     # FastAPI + LangGraph supervisor
│   ├── orchestrator/               # Supervisor, state, router, HITL
│   ├── base/                       # MCPAgent base class, tools, memory
│   ├── tier1_monitoring/           # 4 monitoring agents
│   ├── tier2_diagnostic/           # 4 diagnostic agents
│   ├── tier3_risk/                 # 5 risk assessment agents
│   ├── tier4_intervention/         # 4 intervention agents
│   ├── tier5_action/               # 5 action agents
│   ├── research_system/            # 5 research agents
│   ├── security/                   # PHI detector, guardrails, audit
│   └── tools/                      # 7 LangChain tool wrappers
│
├── mcp-server/                     # Node.js MCP server
│   └── src/                        # TypeScript source
│
├── a2a-gateway/                    # Node.js A2A gateway
│   └── src/                        # TypeScript source
│
├── frontend/                       # React 18 + TypeScript
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/             # ui/, charts/, clinical/, agents/, fhir/, layout/
│   │   ├── pages/                  # 17 pages (auth, dashboard, patients, etc.)
│   │   ├── hooks/                  # useWebSocket, useAuth, useFHIR, etc.
│   │   ├── store/                  # Zustand stores (auth, patient, agent, alert)
│   │   ├── services/               # API client, FHIR service, WebSocket
│   │   └── types/                  # TypeScript type definitions
│   └── public/manifest.json        # PWA manifest
│
├── monitoring/                     # Prometheus, Grafana, Alertmanager
│   ├── prometheus/                 # Config + 3 alert rule sets
│   ├── grafana/                    # 5 dashboards + provisioning
│   └── alertmanager/               # PagerDuty/Slack routing
│
├── database/                       # Schema initialization
│   ├── postgres/                   # 5 SQL schemas (FHIR, clinical, analytics, tenant, audit)
│   └── neo4j/                      # Constraints, indexes, seed data
│
├── scripts/                        # Utility scripts
│   ├── setup.sh                    # Initial setup
│   ├── create_tenant.py            # CLI tenant provisioning
│   ├── seed_graph.py               # Neo4j knowledge graph seeder
│   ├── seed_vectors.py             # Qdrant collection initializer
│   ├── iot_simulator.py            # IoT device simulator
│   └── load_guidelines.py          # Clinical guideline loader
│
├── docs/                           # Documentation
│   ├── architecture/               # Architecture diagrams + PowerPoint
│   ├── api/                        # API reference (Swagger)
│   └── clinical/                   # Clinical workflow docs
│
└── Installation/                   # Kubernetes Helm charts
    └── healthcare-k8s-helm2/
```

---

## Prerequisites

- **Docker** 24.0+ and **Docker Compose** v2.20+
- **Node.js** 18+ (for MCP/A2A gateway development)
- **Python** 3.11+ (for backend development)
- **Git** 2.40+
- Minimum **16 GB RAM** (recommended 32 GB for all services)
- Minimum **50 GB disk space**

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/hassanmzia/Inhealth-Capstone-Project.git
cd Inhealth-Capstone-Project
cp .env.example .env
# Edit .env with your configuration (API keys, secrets, etc.)
```

### 2. Start all services

```bash
# Using Docker Compose (recommended)
docker compose up -d

# Or using Make
make dev
```

### 3. Initialize databases

```bash
# Run Django migrations
docker compose exec django python manage.py migrate

# Seed Neo4j knowledge graph
docker compose exec django python /scripts/seed_graph.py

# Initialize Qdrant vector collections
docker compose exec django python /scripts/seed_vectors.py

# Create initial superuser
docker compose exec django python manage.py createsuperuser
```

### 4. Create a tenant organization

```bash
docker compose exec django python /scripts/create_tenant.py \
  --name "Demo Hospital" \
  --slug demo-hospital \
  --admin admin@demo-hospital.com \
  --tier professional
```

### 5. Access the platform

| Service | URL |
|---------|-----|
| **Application** | http://localhost:8788 |
| **Django Admin** | http://localhost:8788/admin/ |
| **API Docs (Swagger)** | http://localhost:8788/api/v1/docs/ |
| **Grafana** | http://localhost:9391 |
| **Neo4j Browser** | http://localhost:7588 |
| **MinIO Console** | http://localhost:9589 |
| **Langfuse** | http://localhost:3488 |
| **Prometheus** | http://localhost:9390 |

---

## Configuration

### Environment Variables

All configuration is via environment variables. See `.env.example` for the full list.

**Key variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (generate unique) |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://inhealth:password@postgres:5432/inhealth` |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://neo4j:7687` |
| `QDRANT_HOST` | Qdrant host | `qdrant` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `OLLAMA_BASE_URL` | Ollama LLM endpoint | `http://ollama:11434` |
| `ANTHROPIC_API_KEY` | Claude API key (optional fallback) | - |
| `OPENAI_API_KEY` | OpenAI key (optional fallback) | - |
| `LANGFUSE_PUBLIC_KEY` | Langfuse tracing key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret | - |

---

## Django Backend

### 15 Django Applications

| App | Description |
|-----|-------------|
| `accounts` | User authentication (JWT + OAuth2), RBAC with 8 healthcare roles, 2FA (TOTP), email verification |
| `tenants` | Multi-tenant organization management, branding, subscription tiers, API keys |
| `fhir` | 14 FHIR R4 resource models, serializers, REST endpoints, conformance validation |
| `hl7` | HL7 v2 message parsing (ADT/ORU/ORM), MLLP listener, message queue processing |
| `patients` | Patient demographics, insurance, emergency contacts, full EMR management |
| `clinical` | Encounters (SOAP notes), care gap detection (14 types), smart order sets (AI-generated) |
| `analytics` | Population health metrics, cohort analysis, quality measures, prediction audit log |
| `notifications` | 4-tier priority dispatcher (CRITICAL/URGENT/SOON/ROUTINE), SMS/Email/Push/EHR channels |
| `mcp_bridge` | Django-side MCP bridge — context builder, tool executor |
| `a2a_bridge` | Django Channels WebSocket consumers for A2A messaging, Redis pub/sub |
| `research` | AI research queries, evidence storage, clinical trial models |
| `telemedicine` | Video session management with AI-assisted note generation |
| `billing` | Revenue cycle management — claims, CPT codes, pre-authorization, RPM episodes |
| `sdoh` | Social Determinants of Health assessment — food, housing, transportation risk |
| `dashboard` | Dashboard API endpoints for aggregated views |

### Healthcare Roles (RBAC)

| Role | Permissions |
|------|------------|
| `super_admin` | Full system access across all tenants |
| `org_admin` | Full access within their organization |
| `physician` | Patient records, orders, prescriptions, clinical decisions |
| `nurse` | Vitals entry, care coordination, patient communication |
| `patient` | Own records, appointments, secure messaging |
| `pharmacist` | Medication review, drug interaction alerts |
| `billing` | Claims, billing codes, financial reports |
| `researcher` | De-identified data access, research queries |

---

## AI Agent System

### Architecture

The agent system runs as a FastAPI service orchestrated by LangGraph:

```
FastAPI (main.py) → LangGraph Supervisor (StateGraph)
                         │
                    ┌─────┴─────┐
                    │ Conditional │ ← Based on patient data, alert type
                    │  Routing    │
                    └─────┬─────┘
                          │
    ┌───────┬───────┬─────┴─────┬──────────┬──────────┐
    T1      T2      T3          T4         T5       Research
  Monitor Diagnose  Risk     Intervene   Action     System
```

### Agent Base Class

All agents extend `MCPAgent` which provides:
- MCP protocol integration (tool access, context)
- A2A protocol messaging (inter-agent communication)
- LangChain tool binding
- Langfuse tracing
- Tenant-scoped data access

### Tools Available to Agents

| Tool | Description |
|------|-------------|
| `fhir_tools` | Query FHIR resources (Patient, Observation, Condition, etc.) |
| `graph_tools` | Run Cypher queries on Neo4j knowledge graph |
| `vector_tools` | Semantic search across Qdrant collections (RAG) |
| `notification_tools` | Dispatch alerts via SMS/Email/Push/EHR |
| `geospatial_tools` | Find nearest hospitals with PostGIS |
| `nl2sql_tool` | Natural language to SQL queries |
| `voice_tool` | Whisper API voice transcription |

### Human-in-the-Loop (HITL)

Critical clinical decisions require human approval:
- High-risk medication changes
- Emergency protocol activation
- Dosage modifications above thresholds
- New diagnosis suggestions

The HITL system uses LangGraph interrupt nodes that pause execution and notify the clinician via WebSocket.

---

## MCP & A2A Protocols

### MCP Server (Port 3001)

The Model Context Protocol server provides:
- **Tool Registry**: 8 registered tools accessible by all agents
- **Context Management**: Aggregates patient data, conversation history, clinical constraints
- **LLM Proxy**: Routes LLM calls through PHI redaction layer
- **Auth Middleware**: JWT validation for all requests

### A2A Gateway (Port 3002)

The Agent-to-Agent protocol gateway provides:
- **Agent Card Registry**: Each agent publishes capabilities at `.well-known/agent.json`
- **Task Delegation**: Route tasks to the most capable agent
- **Protocol Versioning**: Backward-compatible message formats
- **Message Types**: ALERT, REQUEST, RESPONSE, DATA_UPDATE across 7 channels

---

## Frontend

### Tech Stack
- **React 18** with TypeScript
- **Vite** for fast builds and HMR
- **TailwindCSS** + **shadcn/ui** for styling
- **Zustand** for client state management
- **TanStack Query** for server state (caching, background refetch)
- **Recharts** for clinical data visualizations
- **WebSocket** for real-time updates

### Pages (17)

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | Email/password + 2FA |
| Register | `/register` | New user registration |
| Patient Dashboard | `/dashboard/patient` | Personal vitals, medications, appointments |
| Clinician Dashboard | `/dashboard/clinician` | Risk-stratified patients, AI recommendations |
| Researcher Dashboard | `/dashboard/researcher` | Research tools and analytics |
| Patient List | `/patients` | Searchable patient directory |
| Patient Detail | `/patients/:id` | Full patient record with timeline |
| New Patient | `/patients/new` | Patient registration form |
| Clinical Workspace | `/clinical` | Encounter documentation, orders |
| Vitals Monitor | `/vitals` | Real-time vital signs display |
| Agent Control | `/agents` | 25-agent status and control |
| Analytics | `/analytics` | Population health dashboards |
| Research | `/research` | NL clinical Q&A, literature search |
| Telemedicine | `/telemedicine` | Video consultation |
| Alerts | `/alerts` | Notification center |
| Billing | `/billing` | RCM dashboard |
| Admin | `/admin` | Tenant and user management |
| Settings | `/settings` | User preferences |
| Fairness Analysis | `/fairness` | AI bias assessment |
| What-If Simulator | `/simulator` | Policy threshold editor |

### Component Library

| Category | Components |
|----------|-----------|
| **ui/** | Button, Card, Badge, Input, Modal |
| **charts/** | GlucoseChart, VitalsChart, RiskScoreGauge, PopulationRiskPyramid, AgentActivityTimeline |
| **clinical/** | AIRecommendationPanel, CareGapList, MedicationList, PatientCard, VitalsMonitor |
| **fhir/** | PatientBanner, ObservationTable, ConditionList, MedicationRequestCard |
| **agents/** | AgentControlPanel, AgentExecutionLog, AgentStatusGrid |
| **layout/** | MainLayout, Sidebar, TopNav |

---

## Database Architecture

### PostgreSQL (Multi-Tenant)

5 schema files initialize the database:

| Schema | Contents |
|--------|----------|
| `01_fhir_schema.sql` | FHIR R4 resource tables (Patient, Observation, Condition, etc.) |
| `02_clinical_schema.sql` | EMR extensions (encounters, allergies, procedures, vitals) |
| `03_analytics_schema.sql` | Cohorts, risk snapshots, quality measures, prediction logs, engagement events |
| `03_tenant_schema.sql` | Organization, branding, subscription, API keys |
| `04_audit_schema.sql` | HIPAA audit trail (immutable) |
| `05_indexes.sql` | Performance indexes |

Multi-tenancy uses **schema-per-organization** via django-tenants. Each organization gets its own PostgreSQL schema while sharing the same database instance.

### Neo4j Knowledge Graph

11 node types and 17 relationship types model clinical knowledge:

- **Nodes**: Patient, Disease, Medication, Symptom, LabTest, Gene, FamilyMember, ClinicalGuideline, Hospital, Procedure, DrugClass
- **Key Relationships**: HAS_CONDITION, TAKES_MEDICATION, INTERACTS_WITH, CONTRAINDICATED_IN, TREATS, CAUSES_SYMPTOM, INCREASES_RISK_OF, RECOMMENDS
- **Algorithms**: PageRank risk scoring, shortest path drug interactions, community detection

### Qdrant Vector Store

5 collections with 1536-dimensional embeddings:

| Collection | Content |
|-----------|---------|
| `clinical_guidelines` | ADA, ACC/AHA, GOLD, KDIGO guidelines |
| `medical_literature` | PubMed abstracts and full-text articles |
| `patient_notes` | Clinical notes (de-identified) |
| `drug_information` | Drug monographs, interactions, dosing |
| `disease_knowledge` | Disease pathophysiology, differential diagnosis |

---

## Healthcare Interoperability

### FHIR R4

14 FHIR R4 resources with full REST API:

```
GET    /api/v1/fhir/patients/
POST   /api/v1/fhir/patients/
GET    /api/v1/fhir/patients/{id}/
PUT    /api/v1/fhir/patients/{id}/
DELETE /api/v1/fhir/patients/{id}/
```

Same pattern for Observation, Condition, MedicationRequest, DiagnosticReport, Encounter, Appointment, CarePlan, AllergyIntolerance, Procedure, Immunization, DocumentReference.

### Coding Standards

| Standard | Usage |
|----------|-------|
| LOINC | Laboratory tests and vital signs |
| SNOMED CT | Clinical conditions and findings |
| ICD-10/ICD-11 | Diagnosis coding |
| RxNorm | Medication coding |
| CPT | Billing procedure codes |

### HL7 v2

The HL7 module processes:
- **ADT** messages: Patient admit, discharge, transfer
- **ORU** messages: Lab results and observations
- **ORM** messages: Order entry

Messages are received via MLLP listener, parsed, and auto-mapped to FHIR resources.

---

## ML Models

| Model | Algorithm | Purpose |
|-------|-----------|---------|
| `lstm_glucose.py` | LSTM (PyTorch) | Predict glucose levels from CGM time-series |
| `xgboost_risk.py` | XGBoost | 7-day hospitalization risk score (32 features) |
| `random_forest.py` | Random Forest | Multi-label chronic disease classification |
| `hmm_lifestyle.py` | Hidden Markov Model | Lifestyle pattern detection from wearable data |
| `multimodal_risk.py` | Attention-based Fusion | Combine time-series + tabular + graph + text |
| `digital_twin.py` | Physiological Simulation | Patient digital twin for treatment planning |
| `federated/` | Federated Learning | Privacy-preserving training across organizations |

All models include heuristic fallbacks for when trained weights are unavailable.

---

## Monitoring & Observability

### Grafana Dashboards (5)

| Dashboard | Panels |
|-----------|--------|
| **Agent Operations** | Execution count, latency (p50/p95/p99), failures, queue depth |
| **Clinical Overview** | Active patients by disease, critical alerts, risk distribution |
| **System Health** | API latency, DB connections, Neo4j/Qdrant query time, Redis memory |
| **Population Health** | Risk stratification funnel, disease prevalence, care gap rates, SDOH |
| **LLM Cost Tracking** | Token usage, cost per agent/model, latency distribution, success/failure |

### Prometheus Alert Rules (3 sets)

- **Agent Alerts**: Failure rate > 5%, latency p99 > 30s, queue depth > 1000
- **Clinical Alerts**: Critical patient thresholds, emergency protocol triggers
- **Infrastructure Alerts**: CPU > 80%, memory > 85%, disk > 90%, service down

### Langfuse

All LLM calls are traced through Langfuse for:
- Token usage and cost tracking per agent
- Response latency distribution
- Faithfulness and relevance evaluation scores
- Agent execution traces and debugging

---

## Security & Compliance

### HIPAA Technical Safeguards

| Safeguard | Implementation |
|-----------|---------------|
| Encryption at rest | AES-256 (PostgreSQL TDE, MinIO encryption) |
| Encryption in transit | TLS 1.3 via Nginx |
| Authentication | JWT (15min access + 7-day refresh), OAuth2, TOTP 2FA |
| Authorization | RBAC with 8 roles + attribute-based (django-guardian) |
| PHI Protection | Automatic detection/redaction before LLM calls (presidio) |
| Audit Logging | Every data access/modification logged immutably |
| Rate Limiting | Per-tenant and per-user API rate limits |
| Network Isolation | Docker network isolation, no direct container-to-internet |
| Prompt Injection | Input sanitization + guardrails on all LLM inputs |

---

## API Documentation

Swagger/OpenAPI documentation is auto-generated and available at:

```
http://localhost:8788/api/v1/docs/
```

### Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register/` | POST | User registration |
| `/api/v1/auth/login/` | POST | JWT login |
| `/api/v1/auth/token/refresh/` | POST | Refresh JWT token |
| `/api/v1/fhir/patients/` | GET/POST | FHIR Patient CRUD |
| `/api/v1/fhir/observations/` | GET/POST | FHIR Observation CRUD |
| `/api/v1/clinical/encounters/` | GET/POST | Clinical encounters |
| `/api/v1/clinical/care-gaps/` | GET | Care gap list |
| `/api/v1/patients/` | GET/POST | EMR patient management |
| `/api/v1/billing/claims/` | GET/POST | Billing claims |
| `/api/v1/notifications/` | GET | Notification list |
| `/api/v1/research/queries/` | POST | Research query |
| `/api/v1/telemedicine/sessions/` | GET/POST | Video sessions |
| `/api/v1/analytics/cohorts/` | GET/POST | Population cohorts |
| `/agents/api/v1/trigger/` | POST | Trigger agent execution |
| `/agents/api/v1/status/` | GET | Agent status |

---

## Testing

### Run Backend Tests

```bash
# Run all tests
docker compose exec django pytest

# Run specific test modules
docker compose exec django pytest tests/test_accounts.py
docker compose exec django pytest tests/test_fhir.py
docker compose exec django pytest tests/test_patients.py
docker compose exec django pytest tests/test_clinical.py
docker compose exec django pytest tests/test_billing.py

# Run with coverage
docker compose exec django pytest --cov=apps --cov-report=html
```

### Test Suite Coverage

| Module | Tests |
|--------|-------|
| `test_accounts.py` | Registration, login, token refresh, RBAC role checks |
| `test_fhir.py` | FHIR Patient CRUD, Observation create/list, MedicationRequest |
| `test_patients.py` | Patient list/detail/create/update, tenant isolation |
| `test_clinical.py` | Encounter create, vital observation, care gap list |
| `test_billing.py` | Claim create, RPM episode, billing codes |

### IoT Simulator

Test wearable device data ingestion:

```bash
python scripts/iot_simulator.py \
  --patient-id <uuid> \
  --device-type cgm \
  --interval 30 \
  --duration 3600 \
  --dry-run
```

Device types: `cgm`, `smartwatch`, `pulse_ox`, `bp_monitor`

---

## Deployment

### Docker Compose (Development)

```bash
docker compose up -d          # Start all services
docker compose logs -f django # Follow Django logs
docker compose down           # Stop all services
```

### Docker Compose (Production)

```bash
docker compose -f docker-compose.yml up -d
```

### Kubernetes (Production)

Helm charts are provided in `Installation/healthcare-k8s-helm2/`:

```bash
cd Installation/healthcare-k8s-helm2
helm install inhealth . -f production-values.yaml -n inhealth --create-namespace
```

---

## Tenant Management

### Create a Tenant via CLI

```bash
python scripts/create_tenant.py \
  --name "Metro Health System" \
  --slug metro-health \
  --admin admin@metrohealth.org \
  --tier enterprise
```

### Subscription Tiers

| Feature | Basic | Professional | Enterprise |
|---------|-------|-------------|-----------|
| Max Users | 10 | 100 | Unlimited |
| Max Patients | 500 | 10,000 | Unlimited |
| API Rate Limit | 100/min | 1,000/min | 10,000/min |
| Telemedicine | - | Yes | Yes |
| Research System | - | - | Yes |
| Federated Learning | - | - | Yes |
| Population Analytics | - | Yes | Yes |
| Custom Branding | - | Yes | Yes |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Create a Pull Request

### Code Standards

- **Backend**: Follow PEP 8, use type hints, write docstrings
- **Frontend**: Follow ESLint config, use TypeScript strict mode
- **Tests**: Write tests for all new features
- **Commits**: Use conventional commit messages (`feat:`, `fix:`, `docs:`, etc.)

---

## License

This project is part of a capstone project. All rights reserved.

---

*Built with Django, React, LangGraph, Neo4j, and 25+ AI agents for autonomous chronic disease management.*
