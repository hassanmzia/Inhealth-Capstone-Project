# InHealth Chronic Care — User Guide

**Step-by-Step Navigation Guide for All User Roles**

---

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication & Account Setup](#authentication--account-setup)
- [Role-Based Dashboards](#role-based-dashboards)
- [Patient Portal (Patient Role)](#patient-portal-patient-role)
- [Clinician Dashboard (Physician/Nurse Role)](#clinician-dashboard-physiciannurse-role)
- [Patient Management](#patient-management)
- [Clinical Workspace](#clinical-workspace)
- [Vitals Monitoring](#vitals-monitoring)
- [AI Agent Control Panel](#ai-agent-control-panel)
- [Research Interface](#research-interface)
- [Analytics & Population Health](#analytics--population-health)
- [Telemedicine](#telemedicine)
- [Alerts & Notifications](#alerts--notifications)
- [Billing & Revenue Cycle](#billing--revenue-cycle)
- [Admin Console (Org Admin Role)](#admin-console-org-admin-role)
- [Settings & Preferences](#settings--preferences)
- [Fairness Analysis](#fairness-analysis)
- [What-If Simulator](#what-if-simulator)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Platform

1. Open your browser and navigate to **http://localhost:8788** (or your organization's custom domain)
2. You will see the **Login Page**

### Supported Browsers

- Google Chrome 100+ (recommended)
- Mozilla Firefox 100+
- Microsoft Edge 100+
- Safari 16+

### Mobile Access (PWA)

The platform is a Progressive Web App. To install on mobile:
1. Open the URL in your mobile browser
2. Tap **"Add to Home Screen"** from the browser menu
3. The app icon will appear on your home screen with offline support

---

## Authentication & Account Setup

### Step 1: Register a New Account

1. Click **"Create Account"** on the login page
2. Fill in the registration form:
   - **Email**: Your work email address
   - **First Name** / **Last Name**
   - **Password**: Minimum 8 characters, must include uppercase, lowercase, and a number
   - **Confirm Password**: Re-enter your password
   - **Role**: Select your role (Patient, Physician, Nurse, etc.)
   - **Organization**: Select your hospital/clinic from the dropdown
3. Click **"Register"**
4. Check your email for a **verification link** and click it

### Step 2: Log In

1. Navigate to the login page
2. Enter your **Email** and **Password**
3. Click **"Sign In"**
4. If 2FA is enabled, enter the **6-digit code** from your authenticator app (Google Authenticator, Authy)

### Step 3: Enable Two-Factor Authentication (Recommended)

1. After login, go to **Settings** (gear icon in the sidebar)
2. Click **"Security"** tab
3. Click **"Enable 2FA"**
4. Scan the QR code with your authenticator app
5. Enter the 6-digit verification code
6. Save your **backup codes** in a secure location

### Password Recovery

1. Click **"Forgot Password?"** on the login page
2. Enter your registered email
3. Check your email for a reset link
4. Set a new password

---

## Role-Based Dashboards

After login, you are automatically directed to the dashboard for your role:

| Role | Default Dashboard | Sidebar Sections |
|------|------------------|-----------------|
| **Patient** | Patient Dashboard | Vitals, Medications, Appointments, Messages, Health Goals |
| **Physician** | Clinician Dashboard | Patients, Clinical, Vitals, Agents, Research, Analytics |
| **Nurse** | Clinician Dashboard | Patients, Vitals, Clinical, Alerts |
| **Org Admin** | Admin Console | Tenants, Users, System Health, Billing |
| **Researcher** | Researcher Dashboard | Research, Analytics, Patients (de-identified) |
| **Pharmacist** | Clinician Dashboard | Medications, Drug Interactions, Patients |
| **Billing** | Billing Dashboard | Claims, RPM Episodes, Billing Codes |

---

## Patient Portal (Patient Role)

### Viewing Your Dashboard

After login, you'll see your personal health dashboard with:

1. **Vitals Summary Cards** — Latest readings for blood pressure, heart rate, glucose, SpO2, temperature
2. **Medication List** — Current medications with dosage and schedule
3. **Upcoming Appointments** — Next scheduled visits
4. **Health Goals** — Gamified health targets with progress bars
5. **Recent Alerts** — Notifications from your care team

### Viewing Your Vitals

1. Click **"Vitals"** in the sidebar
2. See real-time charts for:
   - Blood glucose (if CGM connected)
   - Blood pressure trends
   - Heart rate over time
   - SpO2 levels
   - Weight tracking
3. Use the **date range picker** to view historical data
4. Click any data point for details

### Managing Medications

1. Click **"Medications"** in the Patient Dashboard
2. View your active medications with:
   - Drug name and dosage
   - Prescribing physician
   - Refill status
   - Next dose reminder
3. Click a medication for detailed instructions
4. Report side effects using the **"Report Issue"** button

### Booking Appointments

1. Click **"Appointments"** in the sidebar
2. Click **"Book New Appointment"**
3. Select:
   - **Provider**: Choose your physician
   - **Type**: In-person, Telehealth, or Follow-up
   - **Date/Time**: Pick from available slots
4. Click **"Confirm Booking"**
5. You'll receive a confirmation email and push notification

### Secure Messaging

1. Click **"Messages"** in the sidebar
2. Click **"New Message"** to contact your care team
3. Select the recipient (physician, nurse, care coordinator)
4. Type your message and click **"Send"**
5. Messages are encrypted and HIPAA-compliant

---

## Clinician Dashboard (Physician/Nurse Role)

### Overview

The clinician dashboard provides a comprehensive view of your patient panel:

1. **Risk-Stratified Patient List** — Patients sorted by risk level (Critical > High > Medium > Low)
   - Each row shows: Name, MRN, Age, Conditions, Risk Score, Last Visit, Open Care Gaps
   - Color-coded risk badges (red = critical, orange = high, yellow = medium, green = low)
2. **AI Recommendations Panel** — Latest AI-generated clinical recommendations
3. **Care Gap Alerts** — Patients overdue for preventive care
4. **Active Alerts** — Real-time notifications from monitoring agents

### Viewing a Patient

1. Click on any patient name in the list
2. The **Patient Detail Page** opens with tabs:
   - **Overview**: Demographics, conditions, medications, allergies
   - **Vitals**: Real-time and historical vital signs
   - **Encounters**: Visit history with SOAP notes
   - **Labs**: Laboratory results with trends
   - **Medications**: Active prescriptions with interaction alerts
   - **Care Gaps**: Overdue preventive actions
   - **Risk**: AI risk score with feature attribution (explainable AI)
   - **Timeline**: Complete clinical timeline

### Reviewing AI Recommendations

1. In the Patient Detail page, look at the **AI Recommendations** sidebar
2. Each recommendation shows:
   - **Action**: What the AI suggests (e.g., "Order HbA1c test")
   - **Reasoning**: Why (e.g., "Last A1C 3.5 months ago, patient has uncontrolled DM")
   - **Evidence Level**: A/B/C based on clinical guidelines
   - **Source**: Guideline reference (e.g., ADA 2026 Standards of Care)
3. Click **"Accept"** to create the order, or **"Modify"** to adjust
4. For critical decisions, the system requires **explicit approval** (HITL)

### Handling HITL (Human-in-the-Loop) Requests

When the AI system needs human approval for a critical action:

1. A **yellow banner** appears at the top of the dashboard
2. Click **"Review Decision"**
3. You'll see:
   - The proposed action (e.g., medication change)
   - Patient context and risk assessment
   - Evidence supporting the recommendation
   - Alternative options
4. Choose: **Approve**, **Modify**, or **Reject**
5. Add an optional comment for the audit trail
6. Click **"Submit Decision"**

---

## Patient Management

### Searching for Patients

1. Click **"Patients"** in the sidebar
2. Use the **search bar** to find patients by:
   - Name
   - MRN (Medical Record Number)
   - Date of birth
3. Use **filters** to narrow results:
   - Risk level (Critical, High, Medium, Low)
   - Condition (Diabetes, COPD, CVD, CKD, HF)
   - Provider assignment
   - Care gap status

### Registering a New Patient

1. Click **"Patients"** → **"+ New Patient"**
2. Complete the registration form:
   - **Demographics**: Name, DOB, Gender, SSN (encrypted), Language
   - **Contact**: Address, Phone, Email
   - **Insurance**: Provider, Policy Number, Group Number
   - **Emergency Contact**: Name, Relationship, Phone
   - **Medical History**: Conditions, Allergies, Surgeries, Family History
3. Click **"Register Patient"**
4. A FHIR Patient resource is automatically created
5. The patient appears in your patient list

### Editing Patient Information

1. Open the patient's detail page
2. Click **"Edit"** (pencil icon) next to the section you want to update
3. Make changes and click **"Save"**
4. All changes are audit-logged

---

## Clinical Workspace

### Creating an Encounter

1. Open a patient's detail page
2. Click **"New Encounter"**
3. Select encounter type: Outpatient, Inpatient, Emergency, Telehealth
4. The SOAP note editor opens with sections:
   - **Chief Complaint**: Why the patient is here
   - **HPI**: History of present illness (free text)
   - **Review of Systems**: Checklist by body system
   - **Physical Exam**: Structured exam findings
   - **Assessment**: Diagnosis with ICD-10 coding (auto-suggest)
   - **Plan**: Treatment plan, orders, follow-up
5. The AI Scribe can auto-generate notes from voice input (click microphone icon)
6. Click **"Complete Encounter"** when done

### Using Smart Order Sets

1. During an encounter, click **"Order Set"** button
2. Select the condition (e.g., "Type 2 Diabetes — Initial Workup")
3. The AI-generated order set appears with:
   - **Labs**: HbA1c, Fasting Glucose, Lipid Panel, etc.
   - **Medications**: Metformin 500mg BID (with alternatives)
   - **Referrals**: Endocrinology, Ophthalmology (diabetic eye exam)
   - **Patient Education**: Diabetes management handout
4. Check/uncheck items as needed
5. Click **"Place Orders"**
6. Each order is linked to the encounter with evidence level

### Viewing Care Gaps

1. Click **"Care Gaps"** in the clinical sidebar
2. View gaps by priority: Critical > High > Medium > Low
3. Each gap shows:
   - Gap type (e.g., "A1C Test Overdue")
   - Patient name and MRN
   - Due date
   - Days overdue
   - AI recommendation
4. Click **"Resolve"** to document the action taken
5. Click **"Defer"** with a reason if not actionable now

---

## Vitals Monitoring

### Real-Time Monitoring

1. Click **"Vitals"** in the sidebar
2. The vitals dashboard shows real-time data from connected devices:
   - **Blood Glucose** (CGM): Continuous line chart with target range
   - **Blood Pressure**: Systolic/diastolic trend with threshold alerts
   - **Heart Rate**: BPM with arrhythmia detection markers
   - **SpO2**: Oxygen saturation with desaturation alerts
   - **Temperature**: Body temperature tracking
3. Red markers indicate values outside safe ranges
4. Click any alert marker for agent analysis details

### Connecting IoT Devices

The platform supports:
- **CGM** (Continuous Glucose Monitor): Dexcom, FreeStyle Libre
- **Smartwatch**: Apple Watch, Fitbit (heart rate, activity)
- **Pulse Oximeter**: Bluetooth-enabled pulse ox devices
- **Blood Pressure Monitor**: Omron, Withings

Setup:
1. Go to **Settings** → **Connected Devices**
2. Click **"+ Add Device"**
3. Select device type and follow pairing instructions
4. Data flows automatically to the vitals dashboard

---

## AI Agent Control Panel

### Viewing Agent Status

1. Click **"Agents"** in the sidebar
2. The **Agent Status Grid** shows all 25+ agents:
   - Green = Active/Running
   - Yellow = Idle
   - Red = Error/Stopped
   - Blue = Processing
3. Each agent card shows:
   - Agent name and tier
   - Last execution time
   - Success rate (24h)
   - Current task (if running)

### Viewing Execution Logs

1. Click on any agent in the grid
2. The **Execution Log** panel opens showing:
   - Timestamp
   - Input data (patient context)
   - Agent reasoning steps
   - Output (recommendation, alert, action)
   - Duration (ms)
   - LLM tokens used
3. Click **"View in Langfuse"** for detailed trace

### Triggering an Agent Manually

1. In the Agent Control Panel, click **"Trigger"** on any agent
2. Select the target patient
3. Provide optional context (e.g., "Check latest lab results")
4. Click **"Execute"**
5. Watch the execution in real-time in the log panel

### Agent Activity Timeline

The bottom of the Agent Control page shows a timeline of all agent executions across the system, color-coded by tier.

---

## Research Interface

### Asking Clinical Questions

1. Click **"Research"** in the sidebar
2. Type a clinical question in natural language, for example:
   - *"What is the latest evidence for SGLT2 inhibitors in heart failure?"*
   - *"Find clinical trials for metformin in CKD patients"*
   - *"What are the ADA 2026 guidelines for A1C targets in elderly patients?"*
3. Click **"Search"** or press Enter
4. The research system processes your query through multiple agents:
   - **Literature Agent**: Searches PubMed and Semantic Scholar
   - **Guideline Agent**: Checks current clinical guidelines
   - **Trial Matching Agent**: Searches ClinicalTrials.gov
5. Results appear with:
   - **Evidence Summary**: Synthesized answer with citations
   - **Evidence Level**: A/B/C rating
   - **Source Articles**: Links to PubMed/journals
   - **Clinical Trials**: Matching active trials
   - **Guideline References**: Relevant guideline excerpts

### Saving Research

1. Click **"Save"** on any research result
2. It's stored in your research history
3. Access saved searches from the **"History"** tab

---

## Analytics & Population Health

### Population Overview

1. Click **"Analytics"** in the sidebar
2. The dashboard shows:
   - **Risk Stratification Pyramid**: Low / Medium / High / Critical patient counts
   - **Disease Prevalence**: Bar chart by condition (Diabetes, COPD, CVD, CKD, HF)
   - **Care Gap Summary**: Overdue preventive care by type
   - **Trend Lines**: Risk score trends over time

### Cohort Analysis

1. Click **"Create Cohort"**
2. Define criteria:
   - Conditions (e.g., ICD-10: E11 — Type 2 Diabetes)
   - Age range
   - Risk level
   - SDOH factors
3. Click **"Generate Cohort"**
4. View cohort statistics, risk distribution, and outcomes

### Grafana Dashboards

For advanced analytics, click **"Open Grafana"** to access:
- Agent Operations Dashboard
- Clinical Overview Dashboard
- System Health Dashboard
- Population Health Dashboard
- LLM Cost Tracking Dashboard

---

## Telemedicine

### Starting a Video Consultation

1. Click **"Telemedicine"** in the sidebar
2. Click **"New Session"**
3. Select the patient from the dropdown
4. Click **"Start Call"**
5. The video interface opens with:
   - Video/audio of the patient
   - Patient vitals sidebar (real-time)
   - AI note-taking panel
   - Screen sharing capability
6. During the call, the AI scribe generates notes automatically
7. Click **"End Call"** when done
8. Review and edit the AI-generated notes
9. Click **"Save to Encounter"** to attach notes to the patient record

### Scheduling a Telehealth Appointment

1. Open a patient's detail page
2. Click **"Schedule Appointment"**
3. Select **"Telehealth"** as the visit type
4. Choose date/time
5. The patient receives a link via email and SMS

---

## Alerts & Notifications

### Notification Center

1. Click the **bell icon** in the top navigation bar
2. Or click **"Alerts"** in the sidebar
3. Notifications are organized by priority:
   - **CRITICAL** (red): Requires immediate action (e.g., STEMI detected, glucose < 40)
   - **URGENT** (orange): Action needed within 1 hour (e.g., lab result abnormal)
   - **SOON** (yellow): Action needed within 24 hours (e.g., care gap due)
   - **ROUTINE** (blue): Informational (e.g., appointment reminder)

### Managing Alerts

1. Click on any alert to view details
2. Options:
   - **Acknowledge**: Mark as seen
   - **Take Action**: Opens relevant patient page/order
   - **Escalate**: Forward to another provider
   - **Dismiss**: Close with reason
3. All actions are audit-logged

### Notification Preferences

1. Go to **Settings** → **Notifications**
2. Configure per channel:
   - **In-App**: Always on
   - **Email**: Choose which priority levels
   - **SMS**: Choose which priority levels
   - **Push**: Enable/disable browser push notifications
3. Set **quiet hours** (e.g., no SMS between 10 PM — 7 AM unless CRITICAL)

---

## Billing & Revenue Cycle

### Claims Management

1. Click **"Billing"** in the sidebar
2. View claims by status: Draft, Submitted, Pending, Approved, Denied, Paid
3. Click **"New Claim"** to create:
   - Select patient and encounter
   - ICD-10 diagnosis codes (auto-populated from encounter)
   - CPT procedure codes
   - Insurance information
4. Click **"Submit Claim"**

### RPM Billing

Remote Patient Monitoring episodes are automatically tracked:

1. Go to **Billing** → **RPM Episodes**
2. View active RPM episodes with:
   - Patient name
   - Device type (CGM, BP monitor, etc.)
   - Data transmission days this month
   - Eligible billing codes (99453, 99454, 99457, 99458)
   - Revenue estimate
3. CMS requires 16+ days of data per month for billing eligibility

### Billing Codes Reference

The platform supports:
- **CPT** codes for office visits, procedures, RPM
- **ICD-10/ICD-11** for diagnosis coding
- **HCPCS** for medical supplies and DME

---

## Admin Console (Org Admin Role)

### Managing Users

1. Click **"Admin"** → **"Users"**
2. View all users in your organization
3. **Add User**: Click "+" and fill in email, name, role
4. **Edit User**: Click on a user to modify role, status, permissions
5. **Deactivate User**: Toggle the active switch (does not delete data)

### Organization Settings

1. Click **"Admin"** → **"Organization"**
2. Configure:
   - **Name & Contact**: Organization name, address, phone
   - **Branding**: Logo, primary color, custom domain
   - **Subscription**: View current tier and usage
   - **API Keys**: Generate and manage API keys for integrations
   - **Webhook Subscriptions**: Configure event webhooks

### System Health

1. Click **"Admin"** → **"System Health"**
2. View:
   - Service status (all 20 Docker services)
   - Database connection counts
   - API request rates
   - Error rates
   - Embedded Prometheus/Grafana metrics

---

## Settings & Preferences

### Personal Settings

1. Click the **gear icon** in the sidebar or top nav
2. Available settings:
   - **Profile**: Update name, email, phone, photo
   - **Security**: Change password, enable/disable 2FA
   - **Notifications**: Configure alert preferences per channel
   - **Display**: Dark mode toggle, language preference
   - **Connected Devices**: Manage IoT device connections

### Dark Mode

1. Go to **Settings** → **Display**
2. Toggle **"Dark Mode"** on/off
3. Or click the **sun/moon icon** in the top navigation bar
4. The preference is saved and persists across sessions

---

## Fairness Analysis

### Assessing AI Bias

1. Click **"Fairness"** in the sidebar (available to Physicians, Researchers, Admins)
2. Select an AI model to analyze (e.g., XGBoost 7-Day Risk)
3. Choose demographic subgroups:
   - **Sex**: Male vs. Female
   - **Age Groups**: 18-40, 41-64, 65+
   - **Diagnosis**: By primary condition
4. View:
   - Performance metrics per subgroup (accuracy, sensitivity, specificity)
   - Disparity indicators
   - Recommended calibration adjustments
5. Export the fairness report as PDF

---

## What-If Simulator

### Running Simulations

1. Click **"Simulator"** in the sidebar
2. Select a patient or use a synthetic profile
3. Adjust clinical parameters:
   - Modify lab values (A1C, creatinine, etc.)
   - Change medication list
   - Adjust vital signs
   - Toggle conditions on/off
4. Click **"Simulate"**
5. The system recalculates:
   - Risk score change
   - Predicted outcomes
   - Recommended interventions
6. Compare "current" vs. "simulated" side by side

### Policy Threshold Editing

1. In the simulator, click **"Policy Thresholds"**
2. Adjust the AI autonomy levels:
   - **Level 0**: No autonomous action (all recommendations require approval)
   - **Level 1**: Auto-order routine labs
   - **Level 2**: Auto-order + auto-notify patient
   - **Level 3**: Full autonomous action (emergency only)
3. See how changing thresholds affects alert volume and clinical workload
4. Save threshold changes (requires Org Admin approval)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Global search |
| `Ctrl/Cmd + N` | New patient / New encounter |
| `Ctrl/Cmd + /` | Toggle sidebar |
| `Ctrl/Cmd + D` | Toggle dark mode |
| `Escape` | Close modal / panel |
| `Enter` | Confirm action in dialog |

---

## Troubleshooting

### Common Issues

**Cannot log in**
- Verify your email is confirmed (check spam folder)
- Reset your password via "Forgot Password"
- Contact your organization admin if your account is deactivated

**No vitals data showing**
- Check that IoT devices are connected (Settings → Connected Devices)
- Verify the device is transmitting (green status indicator)
- Check the date range filter on the vitals page

**AI recommendations not appearing**
- Verify the agent system is running (check Agent Control Panel)
- The patient may not have enough data for risk assessment
- Check that LLM service (Ollama) is healthy in System Health

**Slow page loading**
- Clear browser cache
- Check internet connection
- Contact your admin to verify server health

**Notification not received**
- Check Settings → Notifications to verify channel is enabled
- Check quiet hours configuration
- Verify phone number / email is correct in your profile

### Getting Help

- **In-App**: Click the **"?"** icon in the bottom-right corner
- **Admin Support**: Contact your organization administrator
- **Technical Issues**: Report at https://github.com/hassanmzia/Inhealth-Capstone-Project/issues

---

*InHealth Chronic Care — User Guide v1.0*
*Last Updated: March 2026*
