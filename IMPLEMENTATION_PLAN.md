# InHealth Chronic Care — Full Implementation Plan
## Unified Autonomous Agentic AI Platform for Chronic Disease Management

---

## 1. EXECUTIVE SUMMARY

A production-grade, multi-tenant, HIPAA-compliant platform built on the existing capstone design documents, enhanced with features from all four InHealth repositories, and enriched with industry-best practices to create the most capable autonomous AI healthcare system available. The system combines 25+ specialized AI agents, HL7/FHIR R4 interoperability, Neo4j clinical knowledge graph, LangGraph orchestration, Langfuse observability, Prometheus/Grafana monitoring, MCP, and A2A protocols into a stunning multi-tenant SaaS platform.

---

## 2. FEATURES INVENTORY (from all sources)

### From Current Capstone Repository
- 25-agent autonomous AI system (5 tiers: Monitoring → Diagnostic → Risk → Intervention → Action)
- FHIR R4 fully compliant PostgreSQL schema (Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Appointment)
- HL7 v2 message processing (ADT, ORU, ORM)
- Neo4j clinical knowledge graph (Patient, Disease, Medication, Gene, Family, Guidelines, Hospital)
- Qdrant vector database for RAG (5 collections: clinical_guidelines, medical_literature, patient_notes, drug_information, disease_knowledge)
- ML models: LSTM glucose prediction, XGBoost 7-day risk scoring, Random Forest classification, HMM lifestyle patterns
- A2A protocol (Redis Pub/Sub, 7 channels, typed messages: ALERT, REQUEST, RESPONSE, DATA_UPDATE)
- MCP server (context distribution, tool registry, LLM integration)
- Emergency protocols: STEMI, Stroke, COPD exacerbation with geospatial hospital routing
- Multi-modal risk fusion: time-series + tabular + graph + text with attention
- Tiered notification system (CRITICAL → URGENT → SOON → ROUTINE), multi-channel (SMS/Email/Push/EHR)
- Health literacy adaptation (5 levels) and multi-language (English, Spanish)
- Wearable device integration (CGM, smartwatch, pulse oximeter, BP monitor)
- Drug interaction detection via backtracking graph search
- Physician preference learning (multi-armed bandit)
- PostGIS geospatial hospital selection
- Kubernetes/Helm production deployment charts
- Celery distributed task orchestration

### From InhealthUSA (EMR/EHR — Laravel/PHP)
- Complete patient demographics with insurance, emergency contacts
- Encounter/visit documentation (chief complaint, HPI, physical exam, assessment, treatment plan)
- E-prescribing with pharmacy integration
- ICD-10/ICD-11 dual coding, primary/secondary/differential diagnoses
- Laboratory test management, imaging study records
- Billing with CPT codes, refill management
- 40+ table normalized clinical schema (adapt to FHIR-compliant Django models)
- Allergy management with severity alerts
- Surgical, family, social history tracking

### From HealthCare-Agentic-Platform (Python/TypeScript)
- IoT device simulator for wearables testing
- Clinician dashboard with specialized clinical workflow views
- MCP integration patterns (adapt/merge with our MCP server)
- Agent orchestration patterns

### From Health_Assistant (Django/LangGraph)
- Natural Language to SQL query interface ("ask your data")
- SQL Agent + Classifier Agent + HITL (Human-in-the-Loop) Agent + Executor Agent pattern
- Human approval workflows for write operations
- Multi-layer SQL/prompt security guardrails
- Complete audit logging for PHI protection
- WebSocket-based real-time notification system
- LangGraph + LangChain + GPT-4o / Claude integration patterns

### From AI-Healthcare-Embodiment (Django/React)
- 5-agent screening pipeline (Retrieval, Phenotyping, Notes & Imaging, Safety, Coordinator)
- Explainable AI risk scoring with per-feature contribution weights
- Tiered autonomy system (4 levels: No Action → Auto-Order)
- Safety governance with PHI detection, low evidence flagging, contradiction alerts
- Fairness analysis (demographic subgroup assessment: sex, age, diagnosis)
- What-If simulation engine (policy threshold editor)
- Zustand state management patterns
- Material-UI + Recharts component library

### New/Enhanced Features (Business Value Additions)
- **Multi-tenancy** — Organization/hospital-network isolation with tenant-scoped data, branding, and configs
- **AI Research System** — Autonomous multi-agent medical literature research and evidence synthesis
- **Clinical Trial Matching** — ML-based patient-to-trial matching using ClinicalTrials.gov API
- **Predictive Population Health** — Cohort-level risk stratification and intervention prioritization
- **Voice Interface** — Voice-to-text clinical documentation (Whisper API integration)
- **Digital Twin** — Patient physiological simulation for treatment planning
- **Federated Learning** — Privacy-preserving model training across tenant organizations
- **Blockchain Audit Trail** — Immutable HIPAA audit log with smart contract verification
- **Revenue Cycle Management** — Automated billing, pre-authorization, claims tracking
- **Provider Credentialing** — License verification, specialty tracking, privilege management
- **Care Gap Analysis** — Automated preventive care gap identification
- **Social Determinants of Health (SDOH)** — Food security, housing, transportation risk assessment
- **Remote Patient Monitoring (RPM)** — CMS billing codes for remote monitoring episodes
- **Patient Engagement Score** — Gamified health goals with rewards system
- **API Marketplace** — Partner integration hub with webhook subscriptions
- **White-label Customization** — Per-tenant theme, logo, custom domains
- **Mobile PWA** — Progressive Web App for patients and clinicians
- **Telemedicine Integration** — Embedded video consultation with AI-assisted note generation
- **Smart Order Sets** — AI-curated clinical order templates based on diagnosis
- **Population Analytics Dashboard** — Grafana-powered population health insights

---

## 3. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                                │
│  React 18 + TypeScript + TailwindCSS + Material-UI + Recharts        │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────┐   │
│  │Patient Portal│ │Clinician Dash │ │Admin Console │ │Analytics │   │
│  │(Multi-tenant)│ │(AI-assisted)  │ │(Multi-tenant)│ │Board     │   │
│  └──────────────┘ └───────────────┘ └──────────────┘ └──────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS / WSS
┌──────────────────────────────▼──────────────────────────────────────┐
│                 NGINX REVERSE PROXY (port 8788)                      │
│  Routes: / → Frontend | /api/ → Django | /ws/ → Django Channels     │
│  /agents/ → LangGraph | /mcp/ → MCP Server | /a2a/ → A2A Gateway    │
└──────────┬──────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────┐
│               BACKEND API LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │        Django 5 + DRF + Django Channels (ASGI)              │    │
│  │  Auth: JWT + OAuth2 | RBAC: django-guardian + custom roles  │    │
│  │  Multi-tenancy: django-tenants (schema isolation per org)   │    │
│  │  Apps: accounts, tenants, fhir, hl7, patients, clinical,   │    │
│  │        analytics, notifications, mcp_bridge, a2a_bridge,    │    │
│  │        research, telemedicine, billing, rpg, sdoh            │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │     Node.js Gateway Services                                 │    │
│  │  ┌────────────────┐    ┌─────────────────────────────────┐  │    │
│  │  │  MCP Server    │    │      A2A Protocol Gateway        │  │    │
│  │  │  (port 3001)   │    │      (port 3002)                 │  │    │
│  │  │  Tool registry │    │  Agent card registry             │  │    │
│  │  │  Context mgmt  │    │  Task delegation & routing       │  │    │
│  │  │  LLM proxy     │    │  Protocol versioning             │  │    │
│  │  └────────────────┘    └─────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────┐
│               AGENT ORCHESTRATION LAYER                              │
│  FastAPI + LangGraph + LangChain + Celery                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │         LangGraph Supervisor (Master Orchestrator)           │   │
│  │         State machine: parallel agent execution              │   │
│  │         Conditional routing based on agent outputs           │   │
│  │         Human-in-the-loop checkpoints for critical actions   │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
│                           │ Redis A2A Message Bus                    │
│  ┌────────────────────────┼─────────────────────────────────────┐   │
│  │  T1: MONITORING        │  T2: DIAGNOSTIC                      │   │
│  │  • Glucose Monitor     │  • ECG Analysis                      │   │
│  │  • Cardiac Monitor     │  • Kidney Function                   │   │
│  │  • Activity Monitor    │  • Imaging Analysis (AI)             │   │
│  │  • Temperature Monitor │  • Lab Interpretation                │   │
│  ├────────────────────────┼─────────────────────────────────────┤   │
│  │  T3: RISK ASSESSMENT   │  T4: INTERVENTION                    │   │
│  │  • Comorbidity Risk    │  • Lifestyle Coaching                │   │
│  │  • Disease Prediction  │  • Medication Recommendation (RAG)  │   │
│  │  • Family History Risk │  • Contraindication Check            │   │
│  │  • SDOH Risk           │  • Triage & Emergency Response       │   │
│  │  • ML Ensemble Risk    │  • Hospital Coordination             │   │
│  ├────────────────────────┼─────────────────────────────────────┤   │
│  │  T5: ACTION            │  RESEARCH SYSTEM                     │   │
│  │  • Physician Notify    │  • Literature Search Agent           │   │
│  │  • Patient Notify      │  • Evidence Synthesis Agent          │   │
│  │  • Appointment Sched.  │  • Clinical Trial Matching           │   │
│  │  • EHR Integration     │  • Guideline Update Agent            │   │
│  │  • Billing/RPM         │  • Research Q&A Agent                │   │
│  └────────────────────────┴─────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────┐
│               DATA LAYER                                             │
│  ┌───────────────┐ ┌──────────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ PostgreSQL 15 │ │  Neo4j 5.12  │ │  Qdrant   │ │  Redis 7    │  │
│  │ FHIR R4 Schema│ │ Clinical KG  │ │ Vector RAG│ │ Cache/Broker│  │
│  │ pg_vector ext │ │ APOC + GDS   │ │ 5 coll.   │ │ A2A PubSub  │  │
│  │ PostGIS ext   │ │ 3M+ nodes    │ │ 1536-dim  │ │ Celery tasks│  │
│  │ Multi-tenant  │ │ Graph algos  │ │           │ │             │  │
│  └───────────────┘ └──────────────┘ └───────────┘ └─────────────┘  │
│  ┌───────────────┐ ┌──────────────────────────────────────────────┐ │
│  │  Ollama LLM   │ │              MinIO Object Store              │ │
│  │  Llama 3.2    │ │  Medical images, reports, documents, models  │ │
│  │  + Claude API │ │                                              │ │
│  │  + GPT-4o     │ │                                              │ │
│  └───────────────┘ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────────┐
│               OBSERVABILITY & MONITORING                             │
│  ┌─────────────────┐ ┌──────────────┐ ┌────────────────────────┐   │
│  │  Prometheus     │ │   Grafana    │ │      Langfuse           │   │
│  │  (port 9390)    │ │  (port 9391) │ │  (port 3488)            │   │
│  │  Metrics scrape │ │  Dashboards  │ │  LLM traces/evals       │   │
│  │  Alert rules    │ │  Alerts UI   │ │  Agent cost tracking    │   │
│  └─────────────────┘ └──────────────┘ └────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. PORT ASSIGNMENT STRATEGY (No Conflicts)

All services expose on the **88xx/94xx/34xx/55xx/76xx/67xx/117xx** ranges to avoid conflicts with other apps on the server (Health_Assistant uses 3000/8000/8001, AI-Healthcare-Embodiment uses 3055/8055/9055).

| Service | Container Port | Host Port | Notes |
|---|---|---|---|
| **nginx** | 80 | **8788** | Main entry point — routes all traffic |
| **django** | 8000 | (internal only) | Via nginx upstream |
| **agents-api** | 8001 | (internal only) | LangGraph FastAPI |
| **mcp-server** | 3001 | (internal only) | Node.js MCP |
| **a2a-gateway** | 3002 | (internal only) | Node.js A2A |
| **frontend** | 3000 | (internal only) | Served via nginx in prod |
| **celery-worker** | — | — | No port |
| **celery-beat** | — | — | No port |
| **postgres** | 5432 | **5588** | DBA admin access |
| **neo4j http** | 7474 | **7588** | Graph browser |
| **neo4j bolt** | 7687 | **7688** | Driver connections |
| **qdrant** | 6333 | **6388** | Vector DB |
| **redis** | 6379 | **6489** | Cache/broker |
| **ollama** | 11434 | **11788** | LLM server |
| **prometheus** | 9090 | **9390** | Metrics |
| **grafana** | 4000 | **9391** | Dashboards (GF_SERVER_HTTP_PORT=4000) |
| **alertmanager** | 9093 | **9393** | Alert routing |
| **langfuse-web** | 3000 | **3488** | LLM tracing UI |
| **langfuse-worker** | — | — | No port |
| **minio-api** | 9000 | **9588** | Object storage |
| **minio-console** | 9001 | **9589** | MinIO UI |

---

## 5. PROJECT DIRECTORY STRUCTURE

```
inhealth-chronic-care/
├── docker-compose.yml               ← All services, port assignments
├── docker-compose.override.yml      ← Dev overrides (hot reload, debug)
├── .env.example                     ← All env vars documented
├── Makefile                         ← make dev/build/test/deploy shortcuts
│
├── nginx/
│   ├── nginx.conf
│   └── conf.d/                      ← Site configs
│
├── backend/                         ← Django 5 application
│   ├── Dockerfile
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   └── production.txt
│   ├── manage.py
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── asgi.py                  ← Django Channels ASGI
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── apps/
│   │   ├── accounts/                ← Auth: JWT, OAuth2, RBAC, 2FA
│   │   │   ├── models.py            ← User, Role, Permission, AuditLog
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── tenants/                 ← Multi-tenancy (django-tenants)
│   │   │   ├── models.py            ← Organization, TenantConfig, Branding
│   │   │   ├── middleware.py
│   │   │   └── views.py
│   │   ├── fhir/                    ← FHIR R4 resources
│   │   │   ├── models.py            ← Patient, Observation, Condition, etc.
│   │   │   ├── serializers.py       ← FHIR JSON serialization
│   │   │   ├── views.py             ← FHIR REST endpoints
│   │   │   ├── urls.py
│   │   │   └── validators.py        ← FHIR conformance validation
│   │   ├── hl7/                     ← HL7 v2 message processing
│   │   │   ├── models.py            ← HL7Message, HL7Queue
│   │   │   ├── parser.py            ← ADT/ORU/ORM parser
│   │   │   ├── processor.py         ← Message handler
│   │   │   └── views.py             ← HL7 MLLP endpoint
│   │   ├── patients/                ← Patient management (EMR features)
│   │   │   ├── models.py            ← Demographics, Insurance, Contacts
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   ├── clinical/                ← Clinical workflows
│   │   │   ├── models.py            ← Encounter, VitalSigns, Allergy,
│   │   │   │                           Procedure, Referral, CareGap
│   │   │   ├── views.py
│   │   │   └── order_sets.py        ← Smart AI-generated order sets
│   │   ├── analytics/               ← Population health analytics
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   └── cohort.py            ← Cohort analysis engine
│   │   ├── notifications/           ← Tiered alert/notification system
│   │   │   ├── models.py            ← Notification, Channel, Preference
│   │   │   ├── dispatcher.py        ← Priority routing engine
│   │   │   ├── channels.py          ← SMS/Email/Push/EHR adapters
│   │   │   └── tasks.py             ← Celery async send tasks
│   │   ├── mcp_bridge/              ← Django-side MCP bridge
│   │   │   ├── context_builder.py
│   │   │   ├── tool_executor.py
│   │   │   └── views.py
│   │   ├── a2a_bridge/              ← Django-side A2A bridge
│   │   │   ├── consumers.py         ← Django Channels WebSocket
│   │   │   ├── message_bus.py       ← Redis pub/sub handlers
│   │   │   └── views.py
│   │   ├── research/                ← AI research system
│   │   │   ├── models.py            ← ResearchQuery, Evidence, ClinicalTrial
│   │   │   ├── views.py
│   │   │   └── tasks.py
│   │   ├── telemedicine/            ← Video consult integration
│   │   │   ├── models.py
│   │   │   └── views.py
│   │   ├── billing/                 ← RCM and RPM billing
│   │   │   ├── models.py            ← Claim, CPTCode, PreAuth
│   │   │   └── views.py
│   │   └── sdoh/                    ← Social Determinants of Health
│   │       ├── models.py
│   │       └── views.py
│   ├── graph/                       ← Neo4j graph layer
│   │   ├── connection.py
│   │   ├── queries/                 ← All Cypher queries by domain
│   │   ├── seed_data/               ← Drug/disease/guideline seed scripts
│   │   └── algorithms.py            ← Graph algorithms (PageRank risk, etc.)
│   ├── vector/                      ← Qdrant vector layer
│   │   ├── client.py
│   │   ├── collections.py           ← Collection management
│   │   ├── rag.py                   ← RAG pipeline
│   │   └── embeddings.py            ← Embedding generation
│   ├── ml/                          ← ML models
│   │   ├── lstm_glucose.py
│   │   ├── xgboost_risk.py
│   │   ├── random_forest.py
│   │   ├── hmm_lifestyle.py
│   │   ├── multimodal_risk.py       ← Attention-based fusion model
│   │   ├── digital_twin.py          ← Patient physiological simulation
│   │   └── federated/               ← Federated learning modules
│   └── tests/
│
├── agents/                          ← LangGraph agent system (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      ← FastAPI app + LangGraph supervisor
│   ├── orchestrator/
│   │   ├── supervisor.py            ← LangGraph StateGraph supervisor
│   │   ├── state.py                 ← AgentState TypedDict definitions
│   │   ├── router.py                ← Conditional edge routing logic
│   │   └── hitl.py                  ← Human-in-the-loop interrupt handlers
│   ├── base/
│   │   ├── agent.py                 ← MCPAgent base class (MCP + A2A)
│   │   ├── tools.py                 ← LangChain tool wrappers
│   │   └── memory.py                ← Conversation memory management
│   ├── tier1_monitoring/
│   │   ├── glucose_agent.py         ← LSTM CGM analysis
│   │   ├── cardiac_agent.py         ← ECG/vitals monitoring
│   │   ├── activity_agent.py        ← Wearable activity data
│   │   └── temperature_agent.py     ← Fever/infection detection
│   ├── tier2_diagnostic/
│   │   ├── ecg_agent.py             ← STEMI/arrhythmia detection
│   │   ├── kidney_agent.py          ← eGFR/creatinine trend analysis
│   │   ├── imaging_agent.py         ← AI radiology report interpretation
│   │   └── lab_agent.py             ← Lab result interpretation
│   ├── tier3_risk/
│   │   ├── comorbidity_agent.py     ← Multi-condition risk
│   │   ├── prediction_agent.py      ← XGBoost 7-day prediction + RAG
│   │   ├── family_history_agent.py  ← Genetic risk from Neo4j
│   │   ├── sdoh_agent.py            ← Social determinants risk
│   │   └── ml_ensemble_agent.py     ← Multi-modal attention fusion
│   ├── tier4_intervention/
│   │   ├── coaching_agent.py        ← Personalized lifestyle coaching
│   │   ├── prescription_agent.py    ← Medication recommendation + RAG
│   │   ├── contraindication_agent.py← Backtracking drug interaction check
│   │   └── triage_agent.py          ← Emergency triage + hospital coord.
│   ├── tier5_action/
│   │   ├── physician_notify_agent.py← Priority-routed physician alerts
│   │   ├── patient_notify_agent.py  ← Health-literacy adapted messages
│   │   ├── scheduling_agent.py      ← Appointment booking
│   │   ├── ehr_integration_agent.py ← EHR write-back + FHIR export
│   │   └── billing_agent.py         ← RPM billing code generation
│   ├── research_system/
│   │   ├── literature_agent.py      ← PubMed/Semantic Scholar search
│   │   ├── synthesis_agent.py       ← Evidence synthesis + summarization
│   │   ├── trial_matching_agent.py  ← ClinicalTrials.gov matching
│   │   ├── guideline_agent.py       ← Guideline update monitoring
│   │   └── qa_agent.py              ← Clinical Q&A with RAG
│   ├── security/
│   │   ├── phi_detector.py          ← PHI detection/redaction
│   │   ├── guardrails.py            ← Prompt injection protection
│   │   └── audit_logger.py          ← Blockchain-compatible audit log
│   └── tools/
│       ├── fhir_tools.py            ← LangChain FHIR query tools
│       ├── graph_tools.py           ← Neo4j Cypher tools
│       ├── vector_tools.py          ← Qdrant search tools
│       ├── notification_tools.py    ← Alert dispatch tools
│       ├── geospatial_tools.py      ← Hospital routing tools
│       ├── nl2sql_tool.py           ← Natural language to SQL (from Health_Assistant)
│       └── voice_tool.py            ← Whisper voice transcription
│
├── mcp-server/                      ← Node.js MCP server
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── index.ts                 ← Express server entry
│   │   ├── mcp/
│   │   │   ├── server.ts            ← MCP protocol handler
│   │   │   ├── context.ts           ← Context builder
│   │   │   ├── tools.ts             ← Tool registry + executor
│   │   │   └── types.ts             ← MCP type definitions
│   │   └── routes/
│   │       ├── context.ts           ← POST /mcp/context
│   │       ├── tools.ts             ← POST /mcp/tools/execute
│   │       └── health.ts
│   └── tsconfig.json
│
├── a2a-gateway/                     ← Node.js A2A gateway
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.ts
│       ├── a2a/
│       │   ├── gateway.ts           ← A2A protocol gateway
│       │   ├── registry.ts          ← Agent card registry
│       │   ├── router.ts            ← Task delegation/routing
│       │   └── types.ts             ← A2A type definitions
│       └── routes/
│           ├── agents.ts            ← GET /.well-known/agent.json
│           ├── tasks.ts             ← POST /a2a/tasks
│           └── health.ts
│
├── frontend/                        ← React 18 + TypeScript
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── ui/                  ← shadcn/ui base components
│       │   ├── charts/              ← Recharts clinical visualizations
│       │   ├── agents/              ← Agent status, activity monitor
│       │   ├── fhir/                ← FHIR resource display components
│       │   └── layout/              ← Navbar, Sidebar, Header
│       ├── pages/
│       │   ├── auth/                ← Login, Register, 2FA
│       │   ├── dashboard/           ← Main patient/clinician dashboards
│       │   ├── patients/            ← Patient list, detail, timeline
│       │   ├── clinical/            ← Encounters, orders, prescriptions
│       │   ├── vitals/              ← Real-time vitals monitoring
│       │   ├── agents/              ← Agent control panel, logs, traces
│       │   ├── analytics/           ← Population health analytics
│       │   ├── research/            ← AI research Q&A interface
│       │   ├── telemedicine/        ← Video consultation
│       │   ├── alerts/              ← Notification center
│       │   ├── admin/               ← Multi-tenant admin
│       │   ├── billing/             ← RCM dashboard
│       │   └── settings/            ← User/org settings
│       ├── hooks/
│       │   ├── useWebSocket.ts      ← Real-time vitals WS hook
│       │   ├── useAgentStatus.ts    ← Agent monitoring hook
│       │   ├── useFHIR.ts           ← FHIR API hooks
│       │   └── useAuth.ts           ← Auth state hook
│       ├── store/
│       │   ├── authStore.ts         ← Zustand auth store
│       │   ├── patientStore.ts      ← Patient data store
│       │   ├── agentStore.ts        ← Agent state store
│       │   └── alertStore.ts        ← Notification store
│       ├── services/
│       │   ├── api.ts               ← Axios API client
│       │   ├── fhir.ts              ← FHIR API service
│       │   ├── agents.ts            ← Agent API service
│       │   └── websocket.ts         ← WebSocket service
│       └── types/
│           ├── fhir.ts              ← FHIR resource types
│           ├── agent.ts             ← Agent types
│           └── clinical.ts          ← Clinical data types
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/
│   │       ├── agent_alerts.yml     ← Agent failure/latency alerts
│   │       ├── clinical_alerts.yml  ← Critical patient thresholds
│   │       └── infra_alerts.yml     ← Infrastructure alerts
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── dashboards/          ← Auto-provisioned dashboards
│   │   │   └── datasources/         ← Prometheus + Loki data sources
│   │   └── dashboards/
│   │       ├── agent_operations.json
│   │       ├── clinical_overview.json
│   │       ├── patient_population.json
│   │       ├── system_health.json
│   │       └── llm_costs.json       ← Langfuse-integrated LLM cost tracking
│   └── alertmanager/
│       └── alertmanager.yml         ← PagerDuty/Slack routing
│
├── database/
│   ├── postgres/
│   │   ├── 01_fhir_schema.sql       ← FHIR R4 schema (from capstone)
│   │   ├── 02_clinical_schema.sql   ← EMR extensions (from InhealthUSA)
│   │   ├── 03_analytics_schema.sql  ← Population health tables
│   │   ├── 04_tenant_schema.sql     ← Multi-tenancy schema
│   │   └── 05_audit_schema.sql      ← HIPAA audit tables
│   └── neo4j/
│       ├── 01_constraints.cypher    ← Node/relationship constraints
│       ├── 02_indexes.cypher        ← Performance indexes
│       └── 03_seed_data.cypher      ← Drug/disease/guideline knowledge
│
├── scripts/
│   ├── setup.sh                     ← Initial setup script
│   ├── seed_graph.py                ← Neo4j knowledge graph seeder
│   ├── seed_vectors.py              ← Qdrant collection initializer
│   ├── create_tenant.py             ← CLI tenant provisioning
│   └── load_guidelines.py           ← Load ADA/ACC/AHA guidelines
│
└── docs/
    ├── api/                         ← OpenAPI/Swagger docs
    ├── architecture/                ← Architecture diagrams
    └── clinical/                    ← Clinical workflow documentation
```

---

## 6. IMPLEMENTATION PHASES

### Phase 1: Foundation & Infrastructure (Week 1-2)
1. Create `docker-compose.yml` with all 20 services, correct port assignments
2. Create `.env.example` with all required environment variables
3. Initialize Django project with all apps scaffolded
4. Set up PostgreSQL with all 5 SQL schema files (FHIR, clinical, analytics, tenant, audit)
5. Initialize Neo4j with constraints, indexes, and seed data (drugs, diseases, guidelines)
6. Initialize Qdrant with 5 collections and load medical embeddings
7. Create Nginx config routing all services
8. Create Makefile for developer shortcuts

### Phase 2: Django Backend Core (Week 2-3)
1. `accounts` app — JWT auth, OAuth2, RBAC with 8 healthcare roles (Super Admin, Org Admin, Physician, Nurse, Patient, Pharmacist, Billing, Researcher)
2. `tenants` app — Multi-tenant schema isolation, organization branding, white-label config
3. `fhir` app — All FHIR R4 models, serializers, and REST endpoints
4. `hl7` app — HL7 v2 parser and MLLP listener (ADT, ORU, ORM)
5. `patients` app — Complete EMR patient management (merged from InhealthUSA features)
6. `clinical` app — Encounters, vitals, allergies, orders, care gaps
7. `notifications` app — Priority dispatcher, SMS/email/push/EHR adapters
8. `a2a_bridge` app — Django Channels WebSocket consumers for A2A messaging
9. Django Celery setup with Redis broker

### Phase 3: Agent System (Week 3-5)
1. LangGraph Supervisor with StateGraph and conditional routing
2. Base MCPAgent class with A2A + MCP protocol implementations
3. All 25 Tier 1-5 agents (ported from capstone design documents)
4. Research system (5 research agents)
5. Security agents (PHI detection, guardrails, audit)
6. HITL checkpoints for critical clinical decisions
7. NL2SQL tool integration (from Health_Assistant)
8. Langfuse tracing instrumentation on all agent calls

### Phase 4: MCP & A2A Services (Week 4)
1. Node.js MCP server with full tool registry (8 tools from capstone)
2. MCP context builder (patient data, conversation history, tools, constraints)
3. Node.js A2A gateway with agent card registry (`.well-known/agent.json`)
4. A2A task delegation and routing protocol
5. Protocol versioning and backward compatibility

### Phase 5: Frontend — Stunning UI (Week 5-7)
1. Design system: TailwindCSS + shadcn/ui + custom healthcare theme (dark mode support)
2. Authentication flows (login, registration, 2FA, OAuth)
3. **Patient Portal**: vitals dashboard, medication management, appointment booking, secure messaging, health goals gamification
4. **Clinician Dashboard**: patient list with risk stratification, real-time vitals monitoring, AI recommendations panel, care gap alerts, HITL decision interface
5. **Agent Control Panel**: real-time agent status (25 agents), execution traces, Langfuse integration, agent trigger buttons
6. **Analytics Console**: population health Grafana embed, cohort analysis, predictive models visualization, fairness analysis (from AI-Healthcare-Embodiment)
7. **Research Interface**: natural language clinical Q&A, literature search, evidence synthesis display, clinical trial matching
8. **Admin Console**: tenant management, user management, system health (Prometheus embed)
9. **Alert Center**: notification inbox, escalation timeline, acknowledgment workflows
10. What-If simulator (from AI-Healthcare-Embodiment)
11. Mobile PWA configuration

### Phase 6: Monitoring & Observability (Week 6)
1. Prometheus metrics for: Django request latency, agent execution time, Celery queue depth, database query time, LLM token usage, critical alert counts
2. Grafana dashboards: Agent Operations, Clinical Overview, Population Health, System Health, LLM Cost Tracking
3. Alertmanager rules: critical patient thresholds, agent failures, service downtime
4. Langfuse integration: trace all LLM calls, agent evaluations, cost tracking
5. OpenTelemetry distributed tracing

### Phase 7: Enhancement & Polish (Week 7-8)
1. Telemedicine video integration (100ms WebRTC or Daily.co API)
2. Voice-to-text clinical documentation (Whisper API)
3. Digital twin patient simulation
4. Federated learning framework scaffold
5. Clinical trial matching with ClinicalTrials.gov API
6. Revenue cycle management (CPT billing, pre-authorization)
7. SDOH risk assessment integration (food/housing/transportation APIs)
8. IoT device simulator (from HealthCare-Agentic-Platform) for testing
9. Full API documentation (OpenAPI/Swagger, auto-generated)
10. Comprehensive test suite (unit + integration + e2e)

---

## 7. KEY TECHNICAL DECISIONS

### Multi-tenancy Strategy
- **django-tenants** with PostgreSQL schema-per-tenant isolation
- Shared database but schema-per-organization for HIPAA compliance
- Tenant routing via subdomain (hospital-a.inhealth.com) or JWT claim
- Tenant-scoped Neo4j labels for graph isolation

### Agent Orchestration: LangGraph
- LangGraph StateGraph as the master supervisor (replaces raw Celery chains)
- Celery retained for scheduled background jobs (monitoring loops, batch analytics)
- LangGraph handles complex conditional agent flows and HITL checkpoints
- LangChain tools wrap all data layer interactions (FHIR, Neo4j, Qdrant, ML)

### LLM Strategy
- **Primary**: Ollama/Llama 3.2 (local, HIPAA-safe, no data leaves server)
- **Fallback**: Claude API / OpenAI GPT-4o for complex reasoning (with PHI redaction)
- **Embeddings**: sentence-transformers (local) + OpenAI ada-002 (fallback)
- All LLM calls traced through Langfuse

### Frontend Architecture
- **Vite** build tool (fast HMR for development)
- **TailwindCSS** + **shadcn/ui** (beautiful, accessible component library)
- **Zustand** for state management (lightweight, TypeScript-first)
- **TanStack Query** for server state management (API caching, background refetch)
- **Recharts** + **D3** for clinical data visualizations
- **Socket.io** for real-time updates (vitals, agent notifications)

### Database Design
- PostgreSQL multi-schema: `public` (shared), `tenant_{slug}` (per-org)
- Neo4j shared instance with tenant-scoped node labels
- Qdrant shared with tenant metadata in payload filters
- Redis keyspace prefixes for tenant isolation

---

## 8. FHIR R4 RESOURCES IMPLEMENTED

| Resource | Usage |
|---|---|
| Patient | Demographics, identifiers (MRN), telecom, language |
| Observation | Vitals (LOINC), labs (LOINC), device readings |
| Condition | Diagnoses (ICD-10/SNOMED) |
| MedicationRequest | Prescriptions (RxNorm), dosage, status |
| DiagnosticReport | Lab panels, imaging reports, ECG reports |
| Appointment | Scheduling with status lifecycle |
| CarePlan | Treatment plans, goals, activities |
| AllergyIntolerance | Allergy records with criticality |
| Encounter | Clinical visits, admission/discharge |
| Procedure | Surgical, therapeutic procedures |
| Immunization | Vaccination records |
| DocumentReference | Clinical notes, images, PDFs |
| Bundle | FHIR document bundles |
| CapabilityStatement | Server capability declaration |

---

## 9. NEO4J KNOWLEDGE GRAPH SCHEMA

**Node Types** (with tenant isolation label):
```
(:Patient {id, mrn, tenant})
(:Disease {code, name, icd10, snomed})
(:Medication {rxnorm, name, drug_class, generic})
(:Symptom {code, name, snomed})
(:LabTest {loinc, name, unit, normal_range})
(:Gene {symbol, name, hgnc})
(:FamilyMember {relationship, patient_id})
(:ClinicalGuideline {source, version, evidence_level})
(:Hospital {id, name, lat, lon, capabilities})
(:Procedure {code, name, cpt})
(:DrugClass {name, mechanism})
```

**Relationships**:
```
(Patient)-[:HAS_CONDITION]->(Disease)
(Patient)-[:TAKES_MEDICATION]->(Medication)
(Patient)-[:HAS_SYMPTOM]->(Symptom)
(Patient)-[:HAD_LAB_TEST]->(LabTest)
(FamilyMember)-[:HAD_CONDITION]->(Disease)
(Medication)-[:INTERACTS_WITH]->(Medication)
(Medication)-[:CONTRAINDICATED_IN]->(Disease)
(Medication)-[:TREATS]->(Disease)
(Disease)-[:CAUSES_SYMPTOM]->(Symptom)
(Disease)-[:INCREASES_RISK_OF]->(Disease)
(Disease)-[:MONITORED_BY]->(LabTest)
(Gene)-[:INCREASES_RISK_OF]->(Disease)
(ClinicalGuideline)-[:RECOMMENDS]->(Medication)
(ClinicalGuideline)-[:APPLIES_TO]->(Disease)
(Hospital)-[:HAS_CAPABILITY]->(Procedure)
```

---

## 10. AI RESEARCH SYSTEM (Multi-Agent)

A standalone research pipeline built on LangGraph:

```
User Query → Classifier Agent
              ↓
         [Route by query type]
         ↙                   ↘
Literature Agent        Clinical Trial Agent
(PubMed/Semantic Scholar)  (ClinicalTrials.gov)
         ↘                   ↙
         Synthesis Agent (LLM evidence grading)
              ↓
         Safety/Accuracy Checker
              ↓
         Response with citations + evidence levels
```

Features:
- PubMed E-utilities API integration
- Semantic Scholar API integration
- ClinicalTrials.gov API for trial matching
- Evidence grading (Level A/B/C from USPSTF)
- Automatic citation generation
- Hallucination detection via RAG cross-check
- Research query history and saved searches

---

## 11. MULTI-TENANT FEATURES

- **Organization management**: hospitals, clinic networks, health systems
- **Schema isolation**: complete PostgreSQL schema per organization
- **Custom branding**: logo, colors, fonts, custom domain
- **Role hierarchy**: SuperAdmin → OrgAdmin → Provider → Patient
- **Subscription tiers**: Basic / Professional / Enterprise
- **Usage analytics**: API calls, agent executions, storage per tenant
- **Data export**: FHIR bulk export per organization
- **Audit trail**: complete per-tenant HIPAA audit log
- **API keys**: per-tenant API key management for integrations
- **Webhook subscriptions**: per-tenant event streaming

---

## 12. SECURITY & COMPLIANCE

- **HIPAA Technical Safeguards**: AES-256 at rest, TLS 1.3 in transit, key rotation
- **Authentication**: JWT access tokens (15min) + refresh tokens (7 days), OAuth2, 2FA (TOTP)
- **Authorization**: Role-based + Attribute-based access control (django-guardian)
- **PHI Protection**: Automatic PHI detection and redaction before LLM calls (presidio)
- **Audit Logging**: Every data access/modification logged to immutable audit table
- **Rate Limiting**: API rate limits per tenant and per user
- **SQL Injection**: Django ORM + parameterized queries only
- **Prompt Injection**: Input sanitization + guardrails on all LLM inputs
- **Network**: Docker network isolation, no direct container-to-internet (except LLM API calls)
- **Secrets**: Docker secrets / environment variables, never in code
- **CORS**: Strict origin whitelist
- **Content Security Policy**: Strict CSP headers via nginx

---

## 13. GRAFANA DASHBOARDS

1. **Agent Operations Dashboard**
   - Agent execution count per type (last 24h)
   - Agent latency (p50, p95, p99) per agent
   - Failed agent executions with error type
   - Celery queue depth per agent tier
   - A2A message throughput

2. **Clinical Overview Dashboard**
   - Active patient count by disease (COPD, Diabetes, CVD)
   - Critical alerts in last hour by type
   - Average risk score distribution (population)
   - Emergency protocol triggers (STEMI/Stroke/COPD)
   - Medication adherence rate

3. **Population Health Dashboard**
   - Risk stratification funnel (Low/Medium/High/Critical)
   - Disease prevalence by tenant
   - Predictive model confidence over time
   - Care gap rates by care category
   - SDOH risk score distribution

4. **System Health Dashboard**
   - API request rate and latency
   - Database connection pool status
   - Neo4j query latency
   - Qdrant search latency
   - Redis memory usage
   - Ollama inference latency

5. **LLM Cost & Quality Dashboard** (Langfuse data)
   - Total token usage per agent type
   - Estimated cost per agent/day
   - LLM response latency distribution
   - Trace success/failure rates
   - Evaluation scores (faithfulness, relevance)

---

## 14. FEATURES REUSED FROM EXTERNAL REPOS

### From InhealthUSA
- Patient demographics schema (40+ fields → adapted to FHIR Patient resource)
- Insurance information model
- E-prescribing workflow and pharmacy integration hooks
- ICD-10/ICD-11 dual coding on conditions
- CPT code billing tables
- Allergy management with severity classification

### From Health_Assistant
- NL2SQL tool (natural language queries against patient database)
- HITL (Human-in-the-Loop) agent pattern for write operations
- WebSocket notification architecture patterns
- SQL guardrails and prompt injection protection
- LangGraph + LangChain integration patterns

### From AI-Healthcare-Embodiment
- Explainable AI risk scoring with feature attribution weights
- Tiered autonomy system (4 action levels with policy thresholds)
- Safety governance module (PHI detection, contradiction flagging)
- What-If simulation interface
- Demographic fairness analysis for AI model outputs
- Zustand state management patterns
- Material-UI + Recharts component patterns

### From HealthCare-Agentic-Platform
- IoT device simulator for wearables testing (CGM, BP, pulse ox)
- Clinician dashboard layout patterns
- MCP integration architectural patterns
- Docker Compose multi-service patterns

---

## 15. IMPLEMENTATION FILE COUNT ESTIMATE

| Component | Files |
|---|---|
| docker-compose.yml + .env + Makefile | 5 |
| Nginx configuration | 4 |
| Django backend (all apps) | ~120 |
| LangGraph agents (25+ agents) | ~80 |
| MCP Server (Node.js/TypeScript) | ~20 |
| A2A Gateway (Node.js/TypeScript) | ~20 |
| Frontend (React/TypeScript) | ~150 |
| Database SQL/Cypher scripts | ~10 |
| Monitoring (Prometheus/Grafana/Alertmanager) | ~20 |
| Scripts (setup, seed) | ~10 |
| **Total** | **~440 files** |

---

## 16. WHAT MAKES THIS PROFESSIONAL GRADE

1. **Production-ready architecture**: Every component is containerized, health-checked, and gracefully degradable
2. **Full observability stack**: Metrics (Prometheus), Dashboards (Grafana), LLM Tracing (Langfuse), Distributed Tracing (OpenTelemetry)
3. **Healthcare interoperability**: FHIR R4 + HL7 v2 — plugs into any hospital system
4. **AI safety**: HITL checkpoints, tiered autonomy, PHI protection, hallucination detection
5. **Business model ready**: Multi-tenant SaaS with subscription tiers, usage analytics, API marketplace
6. **Scalable**: Horizontal scaling via Celery, stateless services, database connection pooling
7. **Stunning UI**: Modern design system, dark mode, mobile PWA, real-time updates
8. **Research-enabled**: Built-in clinical research assistant with evidence grading
9. **Explainable AI**: Every AI decision comes with feature attribution and evidence citations
10. **Compliance-first**: HIPAA audit trail, AES-256 encryption, PHI redaction, consent management

---

*Plan Version: 1.0 | Date: 2026-03-04 | Author: Claude Code*
*Awaiting user approval before implementation begins.*
