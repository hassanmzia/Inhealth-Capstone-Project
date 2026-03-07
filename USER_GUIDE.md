# InHealth Chronic Care Platform — User Guide

**Version 1.0 | March 2026**

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Getting Started](#2-getting-started)
   - 2.1 [Registration & Login](#21-registration--login)
   - 2.2 [Two-Factor Authentication](#22-two-factor-authentication)
   - 2.3 [Role-Based Access](#23-role-based-access)
3. [Clinician Dashboard](#3-clinician-dashboard)
4. [Patient Dashboard](#4-patient-dashboard)
5. [Patient Management](#5-patient-management)
   - 5.1 [Patient List](#51-patient-list)
   - 5.2 [Patient Detail](#52-patient-detail)
   - 5.3 [Adding a New Patient](#53-adding-a-new-patient)
6. [Clinical Workspace](#6-clinical-workspace)
7. [AI Agents](#7-ai-agents)
   - 7.1 [Agent Status Grid](#71-agent-status-grid)
   - 7.2 [Triggering Agents](#72-triggering-agents)
   - 7.3 [Human-in-the-Loop (HITL) Approvals](#73-human-in-the-loop-hitl-approvals)
   - 7.4 [Execution History](#74-execution-history)
8. [Research (AI)](#8-research-ai)
9. [Alerts & Notifications](#9-alerts--notifications)
10. [Analytics](#10-analytics)
    - 10.1 [Population Health Analytics](#101-population-health-analytics)
    - 10.2 [Fairness Analysis](#102-fairness-analysis)
    - 10.3 [What-If Simulator](#103-what-if-simulator)
11. [Vitals Monitoring](#11-vitals-monitoring)
12. [Telemedicine](#12-telemedicine)
13. [Secure Messaging](#13-secure-messaging)
14. [Billing & Revenue Cycle](#14-billing--revenue-cycle)
15. [Settings](#15-settings)
16. [Organization Administration](#16-organization-administration)
17. [Technical Setup Guide (Admin/Developer)](#17-technical-setup-guide-admindeveloper)
    - 17.1 [Architecture Overview](#171-architecture-overview)
    - 17.2 [Prerequisites](#172-prerequisites)
    - 17.3 [Environment Configuration](#173-environment-configuration)
    - 17.4 [Docker Deployment](#174-docker-deployment)
    - 17.5 [Database Seeding](#175-database-seeding)
    - 17.6 [Service Ports Reference](#176-service-ports-reference)
    - 17.7 [API Reference](#177-api-reference)
    - 17.8 [Monitoring & Observability](#178-monitoring--observability)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Platform Overview

InHealth Chronic Care is an enterprise clinical decision-support platform for managing patients with chronic diseases such as diabetes, cardiovascular disease, chronic kidney disease, and COPD. The platform combines:

- **25 AI Agents** organized in a 5-tier pipeline for autonomous clinical workflows
- **Real-Time Vital Sign Monitoring** from IoT devices and wearables
- **Evidence-Based Research** with AI-powered literature search and clinical trial matching
- **Population Health Analytics** with fairness and bias detection
- **HIPAA-Compliant Messaging** and telemedicine
- **Revenue Cycle Management** with CPT/ICD-10 coding support

The system is designed for multi-tenant healthcare organizations with role-based access for physicians, nurses, pharmacists, researchers, billing staff, and patients.

---

## 2. Getting Started

### 2.1 Registration & Login

1. Navigate to the application URL in your browser.
2. **New users**: Click **"Register"** and fill in your details — name, email, password, role, and organization.
3. **Existing users**: Enter your email, password, and optionally your TOTP code if two-factor authentication is enabled.
4. After login you are redirected to your role-specific dashboard.

**Demo Accounts** (if seeded):

| Role | Email | Password |
|------|-------|----------|
| Physician | dr.smith@inhealth.dev | demodemo1 |
| Nurse | nurse.jones@inhealth.dev | demodemo1 |
| Patient | john.doe@inhealth.dev | demodemo1 |

### 2.2 Two-Factor Authentication

1. Go to **Settings > Security & 2FA**.
2. Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.).
3. Enter the 6-digit verification code and click **Enable 2FA**.
4. On subsequent logins, you will be prompted for your TOTP code.

### 2.3 Role-Based Access

Different roles see different pages and features:

| Page | Physician | Nurse | Pharmacist | Researcher | Patient | Billing | Admin |
|------|:---------:|:-----:|:----------:|:----------:|:-------:|:-------:|:-----:|
| Clinician Dashboard | Yes | Yes | — | — | — | — | Yes |
| Patient Dashboard | — | — | — | — | Yes | — | — |
| Patient List | Yes | Yes | Yes | — | — | — | Yes |
| Clinical Workspace | Yes | Yes | — | — | — | — | Yes |
| AI Agents | Yes | — | — | — | — | — | Yes |
| Research (AI) | Yes | — | — | Yes | — | — | Yes |
| Analytics | Yes | — | — | Yes | — | — | Yes |
| Fairness Analysis | Yes | — | — | Yes | — | — | Yes |
| What-If Simulator | Yes | — | — | Yes | — | — | Yes |
| Vitals Monitoring | Yes | Yes | — | — | — | — | Yes |
| Telemedicine | Yes | Yes | — | — | Yes | — | — |
| Billing (RCM) | Yes | — | — | — | — | Yes | Yes |
| Secure Messaging | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Alerts | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Settings | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Organization Admin | — | — | — | — | — | — | Yes |

---

## 3. Clinician Dashboard

**Route:** `/dashboard`

The Clinician Dashboard is the primary landing page for physicians, nurses, and administrators. It provides a real-time overview of your patient population.

### Key Sections

- **Stat Cards** — Four KPI tiles showing Total Patients, Critical Alerts, Active Agents, and Open Care Gaps with trend percentages.
- **High-Risk Patients** — A sortable table of patients with critical or high risk scores. Click any patient name to open their detail page.
- **Recent Alerts** — Color-coded feed of the latest clinical alerts. Critical alerts pulse with a red animation.
- **Agent Activity Timeline** — A 24-hour visual timeline of AI agent executions across all tiers.
- **Population Risk Pyramid** — Bar chart breaking down patient population by risk level (critical, high, medium, low).
- **AI Recommendations** — Pending recommendations from AI agents awaiting your review (approve or reject).
- **Today's Appointments** — Upcoming scheduled appointments with virtual visit indicators.

### Actions

- Click the **Critical Alerts** button (pulsing red) to jump to the Alerts page.
- Click a **patient name** in any table to open their Patient Detail page.
- Click **Approve** or **Reject** on an AI recommendation to submit your HITL decision.

---

## 4. Patient Dashboard

**Route:** `/dashboard/patient`

The Patient Dashboard is the personal health hub for patients.

### Key Sections

- **Health Score** — A large animated circular indicator (0–100) showing your overall health status.
- **Quick Vitals** — Cards displaying your latest blood pressure, heart rate, and glucose readings.
- **Health Goals** — Progress bars for daily steps, glucose control, medication adherence, and weight targets.
- **Medication Calendar** — A 30-day grid showing taken (green) vs. missed (red) medication doses.
- **AI Health Tips** — Three personalized health tips generated by AI based on your clinical data.
- **Upcoming Appointment** — Your next scheduled appointment with provider and date.
- **Messages** — Recent messages from your care team.
- **Achievements** — Badges earned for streaks and milestones (7-Day Streak, Medication Star, etc.).

---

## 5. Patient Management

### 5.1 Patient List

**Route:** `/patients`

A searchable, filterable roster of all patients in your organization.

- **Search** — Type a name, MRN, or date of birth to filter the list in real time.
- **Filters** — Filter by risk level (Critical, High, Medium, Low), care gap status, and alert status.
- **Sorting** — Click any column header (Name, Risk Score, Last Contact, Care Gaps) to sort ascending or descending.
- **Export** — Click the export button to download patient data.
- **Add Patient** — Click "Add Patient" to enroll a new patient.

Click any row to open that patient's detail page.

### 5.2 Patient Detail

**Route:** `/patients/:patientId`

A comprehensive patient record organized across eight tabs:

| Tab | Contents |
|-----|----------|
| **Overview** | Vitals monitor, care gap list, and AI recommendations panel |
| **Vitals** | 24-hour vital sign trends and glucose charts with time-in-range (TIR) and prediction curves |
| **Medications** | Current medication list with dosing, frequency, and adherence status |
| **Clinical** | Care gaps, quality measures (HEDIS), and clinical notes |
| **AI Agents** | Agent control panel for this patient — trigger agents, view recommendations |
| **Research** | Matched clinical trials and relevant literature for this patient's conditions |
| **SDOH** | Eight Social Determinants of Health domains (food security, housing, transportation, financial, social, education, safety, substance use) with risk levels and community resource referrals |
| **Documents** | Patient documents with type, date, author, and upload capability |

**Patient Header** shows at the top of all tabs: name, age, gender, MRN, risk score badge, active conditions, contact info, and next appointment.

### 5.3 Adding a New Patient

**Route:** `/patients/new`

Fill in the patient enrollment form with demographics, insurance, primary conditions, and assign a primary care provider. The patient will appear in the Patient List after creation.

---

## 6. Clinical Workspace

**Route:** `/clinical-workspace`

A workflow hub with six quick-access cards:

| Card | Destination | Description |
|------|-------------|-------------|
| Patient Roster | `/patients` | View all patients |
| Care Gaps | `/patients?filter=care_gaps` | Patients with open care gaps |
| Critical Alerts | `/alerts` | Critical/urgent alert queue |
| Appointments | `/telemedicine` | Today's appointments and virtual visits |
| AI Agents | `/agents` | Agent monitoring and control |
| High Risk Patients | `/patients?risk_level=critical,high` | Critical and high-risk patients only |

The page also shows a real-time stats strip (Total Patients, Critical Alerts, Open Care Gaps, Today's Appointments) and a risk distribution breakdown.

---

## 7. AI Agents

**Route:** `/agents`

The AI Agents page lets you monitor and control 25 autonomous AI agents organized in a 5-tier pipeline.

### 7.1 Agent Status Grid

All 25 agents are displayed in a grid grouped by tier:

| Tier | Agents | Purpose |
|------|--------|---------|
| **Tier 1 — Data Ingestion** | FHIR Ingestion, EHR Sync, Lab Result, Vital Signs, CGM Data | Ingest and validate clinical data from EHRs, devices, and labs |
| **Tier 2 — Analysis** | Risk Stratification, Predictive Analytics, NLP Notes, Drug Interaction, Population Health | Analyze data for risk scores, predictions, and interactions |
| **Tier 3 — Clinical Intelligence** | Clinical Guidelines, Diagnosis Support, Treatment Optimizer, Care Gap Detection, Medication Adherence | Apply evidence-based guidelines and generate clinical recommendations |
| **Tier 4 — Care Coordination** | Care Plan, Appointment Scheduler, Referral, SDOH Assessment, Billing & Coding | Coordinate care plans, referrals, scheduling, and billing |
| **Tier 5 — Patient Engagement** | Patient Education, Health Coaching, Notification, Telemedicine, Research Matching | Engage patients through education, coaching, and trial matching |

Each agent card shows:
- **Status** — idle, running, active, error, or paused
- **Last Run** — timestamp of the most recent execution
- **Executions Today** — count of runs in the last 24 hours
- **Success Rate** — percentage of successful executions

### 7.2 Triggering Agents

1. Select a **tier** from the filter tabs.
2. Choose an **agent** from the dropdown.
3. Optionally select a **patient** and **priority** level.
4. Click **Trigger Agent** to start an execution.

You can also **pause** or **resume** individual agents or all monitoring for a specific patient.

### 7.3 Human-in-the-Loop (HITL) Approvals

Some agents (especially Tier 3 and Tier 4) require physician approval before their recommendations take effect. These appear in the **HITL Queue**.

Each HITL request shows:
- Agent name and tier
- Patient name
- Recommendation details
- Evidence level (A, B, C, D) and confidence score
- Urgency (routine, soon, urgent, critical)

**Actions:** Approve, Reject, Modify, Escalate, or Defer.

### 7.4 Execution History

The **Execution Log** tab shows a paginated history of all agent runs with:
- Agent name and tier (color-coded)
- Patient name
- Status (completed, failed, queued, cancelled)
- Trigger source and timestamp
- Expandable details for input/output data

Use filters to narrow by agent, status, or patient.

---

## 8. Research (AI)

**Route:** `/research`

The Research page provides AI-powered clinical evidence search with four query modes:

| Mode | What it searches | Results |
|------|-----------------|---------|
| **Literature** | PubMed medical evidence database | Articles with title, authors, journal, abstract, evidence level, citation count |
| **Clinical Trials** | ClinicalTrials.gov registry | Trials with NCT ID, title, phase, status, eligibility, sponsor |
| **Guidelines** | High-level evidence (Level A) | Systematic reviews and guideline documents |
| **AI Q&A** | Literature + AI-generated answer | AI summary with source citations and relevance scores |

### How to Use

1. Select a **query type** tab (Literature, Trials, Guidelines, or AI Q&A).
2. Type your clinical question in the search box (e.g., "SGLT2 inhibitors heart failure").
3. Press **Search** or hit Enter.
4. Browse results — each card shows title, abstract excerpt, evidence level, and relevance score.
5. Click a result to expand full details.

### Search Tips

The database is seeded with evidence covering: **diabetes, cardiovascular disease, chronic kidney disease, COPD, atrial fibrillation, and hypertension**. Example queries that return results:

- `diabetes SGLT2` — SGLT2 inhibitor literature
- `heart failure empagliflozin` — Heart failure trials
- `kidney CKD eGFR` — Kidney disease guidelines
- `COPD bronchodilator` — COPD treatment evidence
- `atrial fibrillation ablation` — AFib management
- `hypertension blood pressure` — BP control studies
- `metformin insulin` — Diabetes medication evidence

### Recent Searches

Your last 10 searches are saved and displayed below the search bar for quick re-access.

---

## 9. Alerts & Notifications

**Route:** `/alerts`

The Notification Center displays all clinical alerts organized by severity.

### Severity Levels

| Level | Color | Examples |
|-------|-------|----------|
| **Critical** | Red (pulsing) | Glucose < 54 mg/dL, troponin elevation, BP > 180/120 |
| **Urgent** | Orange | HbA1c > 10%, medication interaction detected |
| **Soon** | Blue | Overdue screening, upcoming care gap deadline |
| **Routine** | Gray | Annual wellness reminder, lab due |

### Actions

- **Acknowledge** — Mark an alert as seen (shows acknowledger name).
- **Mark Read** — Remove the unread indicator.
- **View Patient** — Navigate to the patient's detail page.
- **Filter tabs** — Switch between All, Critical, Urgent, Soon, and Routine.
- **Show/Hide Acknowledged** — Toggle visibility of already-acknowledged alerts.
- **Mark All Read** / **Acknowledge All** — Bulk actions.

---

## 10. Analytics

### 10.1 Population Health Analytics

**Route:** `/analytics`

Dashboards for population-level clinical metrics:

- **Risk Distribution Pyramid** — Breakdown of patients by risk category with counts and percentages.
- **Disease Prevalence Charts** — Bar charts showing condition prevalence across your patient population.
- **Care Gap Closure Rates** — Trend charts tracking quality measure improvement over time.
- **Medication Adherence Trends** — Line charts showing adherence rates by month.
- **HEDIS Quality Measures** — Performance on standard healthcare quality metrics.
- **Agent Activity Timeline** — 24-hour overview of AI agent execution patterns.
- **Grafana Dashboard** — Optional embedded Grafana panels for custom metrics.

### 10.2 Fairness Analysis

**Route:** `/fairness`

Analyzes AI model outputs for demographic bias and equity:

- **Dimension Toggle** — Switch between Age Groups, Sex, and Diagnosis analysis.
- **Subgroup Performance Table** — Accuracy, sensitivity, specificity, and PPV by demographic subgroup.
- **Disparity Detection** — Four fairness metrics:
  - Statistical Parity
  - Equalized Odds
  - Predictive Parity
  - Calibration
- **Status Indicators** — Pass (green), Warning (yellow), or Fail (red) for each metric.
- **Risk Distribution by Subgroup** — Visualization of how risk scores distribute across demographics.

### 10.3 What-If Simulator

**Route:** `/simulator`

Simulate how changing clinical parameters would affect a patient's risk score.

**Steps:**
1. Select a **patient** from the dropdown.
2. Adjust the **parameter sliders**:
   - HbA1c Threshold (5.0–14.0%)
   - Systolic BP Target (100–180 mmHg)
   - Diastolic BP Target (60–110 mmHg)
   - Medication Adherence (0–100%)
   - Weekly Exercise (0–300 min)
   - BMI Target (18–45 kg/m²)
   - LDL Cholesterol (40–200 mg/dL)
   - Smoking Cessation (0–100%)
3. Click **Run Simulation**.
4. Review the **results panel** showing baseline vs. simulated risk scores, risk delta, and per-factor impact analysis.
5. Click **Reset** to restore default parameters.

---

## 11. Vitals Monitoring

### Real-Time Vitals

**Route:** `/vitals`

Monitor patient vital signs in real time from connected IoT devices:

- **Vital Sign Cards** — Heart Rate, Blood Pressure, SpO2, Temperature, Respiratory Rate, and Weight with live values, status indicators (normal/warning/critical), and sparkline trends.
- **Detailed Charts** — Full-size line charts with normal range reference lines and hover tooltips.
- **Connection Status** — WiFi icon showing WebSocket connection state.
- **Critical Alerts** — Automatic alerts when vitals exceed configured thresholds.

### Vitals Simulator

**Route:** `/vitals-simulator`

A testing tool to simulate vital sign scenarios for clinical training:

- Select a patient and input simulated vital values.
- The system processes the values through the AI pipeline and generates alerts.
- Useful for training and demonstrating the alert system.

---

## 12. Telemedicine

**Route:** `/telemedicine`

Manage virtual visits and conduct video consultations.

### For Clinicians

1. **Start Instant Call** — Begin an unscheduled video call with a patient.
2. **Schedule Visit** — Create a new telemedicine appointment.
3. **Test Connection** — Verify camera, microphone, and network status.
4. **Scheduled Visits** — List of upcoming virtual appointments with **Join** buttons.

### For Patients

1. View your upcoming virtual visits.
2. Click **Join** when it's time for your appointment.
3. The system checks your camera and microphone before connecting.

### Video Call Controls

During a call you have access to:
- **Mute/Unmute** microphone
- **Video On/Off** camera toggle
- **Screen Share** for showing documents or images
- **End Call** (red button)
- **Chat** sidebar for text messaging during the call
- **Self-view** picture-in-picture in the bottom-right corner

---

## 13. Secure Messaging

**Route:** `/messages`

HIPAA-compliant messaging for care team coordination.

### Layout

- **Left Panel** — Conversation thread list with participant name, role, last message preview, timestamp, unread count, and online status (green dot).
- **Right Panel** — Active chat with message history, sender avatars, and timestamps. Your messages appear right-aligned.

### Features

- **Search** conversations by participant name.
- **New Message** — Start a conversation with any care team member.
- **Attachments** — Attach files to messages.
- **Role Color Coding** — Messages are color-coded by role (physician = blue, nurse = green, pharmacist = purple).
- **Typing Indicators** — See when someone is typing.
- **Unread Badges** — Conversation list shows unread message counts.

---

## 14. Billing & Revenue Cycle

**Route:** `/billing`

Revenue Cycle Management (RCM) dashboard for claims processing.

### Key Sections

- **KPI Cards** — Total Claims, Pending Amount, Approved Amount, Denied Amount.
- **Claims by Status** — Bar chart showing claim counts across statuses: Draft, Submitted, Pending, Approved, Denied, Paid.
- **RPM Monitoring** — Remote Patient Monitoring episode tracker showing minutes logged vs. target per patient with billing code and progress bars.
- **Claims Table** — Filterable table with claim number, patient, payer, CPT codes, amount, submission date, and status badge.

### Claim Status Colors

| Status | Color |
|--------|-------|
| Draft | Gray |
| Submitted | Blue |
| Pending | Yellow |
| Approved | Green |
| Denied | Red |
| Paid | Purple |

---

## 15. Settings

**Route:** `/settings`

Personal account and system preferences organized in five tabs:

| Tab | Options |
|-----|---------|
| **Profile** | Edit name, email, specialty, NPI number, avatar |
| **Notifications** | Toggle email, SMS, and push notifications |
| **Security & 2FA** | Change password, enable/disable two-factor authentication |
| **Appearance** | Theme (Light/Dark/System), Language (English, Spanish, French, German, Portuguese, Chinese) |
| **Clinical Prefs** | Default unit system (Metric/Imperial), glucose unit (mg/dL or mmol/L), default patient view |

---

## 16. Organization Administration

**Route:** `/admin` (org_admin and admin roles only)

Manage your organization's settings and users.

### Tabs

| Tab | Features |
|-----|----------|
| **Overview** | KPI cards (patients, users, API calls, agent executions), storage usage, subscription tier |
| **User Management** | User table with name, email, role, last login, active status; edit/deactivate users |
| **API Keys** | Generate, view, and revoke API keys for integrations |
| **Org Settings** | Organization details, branding (logo, colors), domain configuration |

---

## 17. Technical Setup Guide (Admin/Developer)

### 17.1 Architecture Overview

The platform consists of the following components:

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx (Reverse Proxy)                 │
│                       Port 80/443                        │
├───────────────┬─────────────────┬───────────────────────┤
│   Frontend    │   Django API    │   Agents API          │
│   (React)     │   (REST)        │   (FastAPI)           │
│   Port 3000   │   Port 8000     │   Port 8001           │
├───────────────┴─────────────────┴───────────────────────┤
│              Celery Workers + Beat Scheduler             │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ Postgres │  Redis   │  Qdrant  │  Neo4j   │   MinIO     │
│ (pg16)   │  (7)     │ (Vector) │ (Graph)  │   (S3)      │
│ :5432    │  :6379   │  :6333   │  :7687   │   :9000     │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│              Monitoring Stack                            │
│   Prometheus  │  Grafana  │  Alertmanager  │  Langfuse   │
│   :9090       │  :3100    │  :9093         │  :3488      │
└─────────────────────────────────────────────────────────┘
```

### 17.2 Prerequisites

- **Docker** 24+ and **Docker Compose** v2+
- **Git**
- At least **8 GB RAM** and **20 GB disk space** (16 GB RAM recommended)
- (Optional) **Ollama** running locally for LLM inference
- (Optional) **OpenAI** or **Anthropic** API keys for cloud LLM fallback

### 17.3 Environment Configuration

Copy the example environment file and customize:

```bash
cp .env.example .env
```

Key environment variable groups:

| Category | Variables | Notes |
|----------|-----------|-------|
| **Database** | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL 16 with pgvector |
| **Redis** | `REDIS_PASSWORD`, `REDIS_MAX_MEMORY` | Cache, Celery broker, WebSocket channels |
| **Neo4j** | `NEO4J_USER`, `NEO4J_PASSWORD` | Graph DB for comorbidity relationships |
| **Qdrant** | `QDRANT_API_KEY`, `QDRANT_VECTOR_SIZE` | Vector store for RAG (default: 1536 dims) |
| **Django** | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django configuration |
| **LLM** | `DEFAULT_LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | AI model configuration |
| **Langfuse** | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Agent observability |
| **MinIO** | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | S3-compatible object storage |
| **Security** | `FIELD_ENCRYPTION_KEY`, `JWT_SECRET_KEY` | PHI encryption and auth |

### 17.4 Docker Deployment

**Start all services:**

```bash
docker compose up -d
```

**Start specific services only:**

```bash
# Infrastructure only
docker compose up -d postgres redis qdrant neo4j

# Backend + Frontend
docker compose up -d django celery-worker celery-beat frontend nginx

# Full stack with monitoring
docker compose up -d
```

**View logs:**

```bash
docker compose logs -f django        # Django API logs
docker compose logs -f celery-worker  # Celery task logs
docker compose logs -f agents-api    # AI agents service logs
docker compose logs -f frontend      # React frontend logs
```

**Restart a service:**

```bash
docker compose restart django
```

### 17.5 Database Seeding

After starting the services, seed the database with sample data:

```bash
# Run Django migrations
docker compose exec django python manage.py migrate

# Create a superuser
docker compose exec django python manage.py createsuperuser

# Seed sample patients, clinical data, and research evidence
docker compose exec django python manage.py seed_fhir_data
docker compose exec django python manage.py seed_research
```

Available management commands:

| Command | Description |
|---------|-------------|
| `seed_fhir_data` | Creates sample patients, conditions, observations, and medications |
| `seed_research` | Loads 8 clinical trials and 12 medical evidence records |
| `sync_clinical_guidelines` | Syncs clinical guideline documents into the vector store |
| `createsuperuser` | Creates an admin user account |

### 17.6 Service Ports Reference

| Service | Container Port | Default Host Port | URL |
|---------|:--------------:|:-----------------:|-----|
| **Nginx** (entry point) | 80 | **80** | http://localhost |
| **Frontend** (React) | 3000 | 3000 | http://localhost:3000 |
| **Django API** | 8000 | 8000 | http://localhost:8000/api/v1/ |
| **Agents API** (FastAPI) | 8001 | 8001 | http://localhost:8001/docs |
| **PostgreSQL** | 5432 | 5588 | — |
| **Redis** | 6379 | 6489 | — |
| **Neo4j Browser** | 7474 | 7588 | http://localhost:7588 |
| **Neo4j Bolt** | 7687 | 7688 | — |
| **Qdrant** | 6333 | 6388 | http://localhost:6388/dashboard |
| **MinIO Console** | 9001 | 9001 | http://localhost:9001 |
| **Prometheus** | 9090 | 9190 | http://localhost:9190 |
| **Grafana** | 3000 | 3100 | http://localhost:3100 |
| **Alertmanager** | 9093 | 9193 | http://localhost:9193 |
| **Langfuse** | 3000 | 3488 | http://localhost:3488 |

### 17.7 API Reference

The API is versioned under `/api/v1/`. Interactive documentation is available at:

- **Swagger UI:** `/api/v1/docs/`
- **ReDoc:** `/api/v1/redoc/`
- **OpenAPI Schema:** `/api/v1/schema/`

#### Key Endpoint Groups

| Prefix | Description |
|--------|-------------|
| `/api/v1/auth/` | Authentication (login, register, token refresh, 2FA) |
| `/api/v1/patients/` | Patient CRUD, vitals, medications, care gaps |
| `/api/v1/agents/` | Agent status, trigger, HITL, recommendations, executions |
| `/api/v1/research/` | Literature search, clinical trials, guidelines, AI Q&A |
| `/api/v1/analytics/` | Population health, fairness analysis, simulation |
| `/api/v1/clinical/` | Clinical workflows, monitoring |
| `/api/v1/dashboard/` | Dashboard statistics and aggregations |
| `/api/v1/notifications/` | Alert management |
| `/api/v1/billing/` | Claims, RPM episodes |
| `/api/v1/fhir/` | FHIR R4 REST API |
| `/api/v1/telemedicine/` | Telemedicine sessions |
| `/api/v1/sdoh/` | SDOH assessments |
| `/api/v1/mcp/` | MCP context and tool execution |
| `/api/v1/a2a/` | Agent-to-agent messaging |
| `/api/v1/tenants/` | Tenant/organization management |
| `/api/health/` | Health check (no auth) |

### 17.8 Monitoring & Observability

#### Langfuse (AI Agent Tracing)

Access Langfuse at `http://localhost:3488` to view:
- Execution traces for every AI agent run
- Token usage and cost tracking
- Latency analysis
- Input/output inspection

#### Prometheus + Grafana

- **Prometheus** (`http://localhost:9190`) scrapes metrics from Django and the Agents API.
- **Grafana** (`http://localhost:3100`) provides dashboards for:
  - API request latency and throughput
  - Agent execution counts and success rates
  - Database query performance
  - Celery task queue depth

#### Alertmanager

Configured at `http://localhost:9193` for automated alerting on:
- High error rates
- Slow response times
- Service health failures

---

## 18. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Login fails with 401** | Verify credentials. If using 2FA, ensure your TOTP code is current. Check that the Django service is running. |
| **Dashboard shows no data** | Run the seed commands (`seed_fhir_data`, `seed_research`). Verify PostgreSQL is healthy. |
| **Research returns no results** | The database is seeded with diabetes/CVD/CKD/COPD data. Try queries like "diabetes", "heart failure", or "SGLT2". |
| **Agent status shows all idle** | This is normal if no agents have been triggered. Use the Agent Control page to manually trigger an agent. |
| **Vitals not updating** | Check WebSocket connection status (WiFi icon). Verify Redis is running for the channel layer. |
| **Video call fails** | Click "Test Connection" first. Ensure browser has camera/microphone permissions. |
| **502 Bad Gateway** | The Django or frontend service may still be starting. Check `docker compose logs -f nginx`. |
| **Database connection error** | Verify PostgreSQL is running: `docker compose ps postgres`. Check connection settings in `.env`. |
| **Celery tasks not running** | Check Celery worker logs: `docker compose logs -f celery-worker`. Verify Redis connectivity. |

### Getting Help

- **API Docs:** `/api/v1/docs/` (Swagger UI)
- **Health Check:** `GET /api/health/` — returns `{"status": "healthy"}` if the API is running
- **Django Admin:** `/admin/` — for direct database inspection (superuser required)

---

*InHealth Chronic Care Platform — Built for precision medicine at scale.*
