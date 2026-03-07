#!/usr/bin/env python3
"""
InHealth Chronic Care - AI Recommendations Seed Script

Populates the database with realistic AI recommendations from various agents
so the dashboard AI Recommendations panel has data to display.

Run after seed_patients.py:
  python3 scripts/seed_recommendations.py
  python3 scripts/seed_recommendations.py --no-docker
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

DJANGO_SERVICE = os.environ.get("DJANGO_SERVICE_NAME", "django")

# ---------------------------------------------------------------------------
# Recommendation definitions — realistic clinical AI recommendations
# ---------------------------------------------------------------------------

RECOMMENDATIONS = [
    {
        "agent_type": "medication",
        "title": "Potential Drug Interaction: Metformin + Furosemide",
        "recommendation": "Patient is on Metformin 500mg and Furosemide 40mg. Furosemide may increase blood glucose levels, potentially reducing Metformin efficacy. Consider monitoring blood glucose more frequently and adjusting Metformin dosage if A1c rises above target.",
        "evidence_level": "B",
        "confidence": 0.88,
        "source_guideline": "ADA Standards of Care 2024, Section 9",
        "category": "medication_safety",
        "priority": "soon",
        "condition_filter": ["T2DM", "CKD"],
        "feature_importance": [
            {"feature": "Drug Interaction Score", "value": 0.85, "direction": "negative"},
            {"feature": "A1c Level", "value": 0.72, "direction": "negative"},
            {"feature": "eGFR", "value": 0.45, "direction": "negative"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Overdue A1c Screening",
        "recommendation": "Patient with Type 2 Diabetes has not had an A1c test in the last 90 days. ADA guidelines recommend A1c testing every 3 months for patients not meeting glycemic goals. Schedule A1c lab work at next visit.",
        "evidence_level": "A",
        "confidence": 0.95,
        "source_guideline": "ADA Standards of Care 2024, Section 6",
        "category": "screening",
        "priority": "soon",
        "condition_filter": ["T2DM"],
        "feature_importance": [
            {"feature": "Days Since Last A1c", "value": 0.92, "direction": "negative"},
            {"feature": "Last A1c Value", "value": 0.65, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Blood Pressure Above ACC/AHA Target",
        "recommendation": "Patient's average systolic BP over last 3 readings is 152 mmHg, exceeding the ACC/AHA target of <130 mmHg. Consider uptitrating Lisinopril from 10mg to 20mg or adding a second antihypertensive agent. Recheck BP in 4 weeks.",
        "evidence_level": "A",
        "confidence": 0.91,
        "source_guideline": "ACC/AHA 2023 Hypertension Guidelines",
        "category": "chronic_management",
        "priority": "urgent",
        "condition_filter": ["HTN"],
        "feature_importance": [
            {"feature": "Avg Systolic BP", "value": 0.94, "direction": "negative"},
            {"feature": "Current Medication Dose", "value": 0.60, "direction": "positive"},
            {"feature": "Comorbidity Count", "value": 0.45, "direction": "negative"},
        ],
    },
    {
        "agent_type": "triage",
        "title": "Elevated Heart Failure Biomarker",
        "recommendation": "NT-proBNP level of 2,450 pg/mL significantly exceeds the upper normal limit of 125 pg/mL, suggesting decompensated heart failure. Recommend urgent cardiology consultation, assess fluid status, and consider diuretic adjustment. Monitor daily weights.",
        "evidence_level": "A",
        "confidence": 0.93,
        "source_guideline": "ACC/AHA 2023 Heart Failure Guidelines",
        "category": "urgent_care",
        "priority": "critical",
        "condition_filter": ["HF"],
        "feature_importance": [
            {"feature": "NT-proBNP Level", "value": 0.96, "direction": "negative"},
            {"feature": "Weight Change (7d)", "value": 0.72, "direction": "negative"},
            {"feature": "Ejection Fraction", "value": 0.55, "direction": "negative"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Declining Kidney Function — KDIGO Stage Progression Risk",
        "recommendation": "eGFR has declined from 48 to 38 mL/min/1.73m2 over the past 6 months, representing a >25% decline. Per KDIGO 2024 guidelines, refer to nephrology, check for reversible causes, and ensure ACE inhibitor/ARB is at maximum tolerated dose.",
        "evidence_level": "A",
        "confidence": 0.89,
        "source_guideline": "KDIGO 2024 CKD Guidelines",
        "category": "chronic_management",
        "priority": "urgent",
        "condition_filter": ["CKD"],
        "feature_importance": [
            {"feature": "eGFR Decline Rate", "value": 0.91, "direction": "negative"},
            {"feature": "Creatinine Trend", "value": 0.78, "direction": "negative"},
            {"feature": "Proteinuria", "value": 0.62, "direction": "negative"},
        ],
    },
    {
        "agent_type": "medication",
        "title": "NSAID Contraindication with CKD and Heart Failure",
        "recommendation": "Patient has CKD Stage 3 and Heart Failure. NSAIDs are contraindicated due to risk of acute kidney injury and fluid retention. If prescribed for pain, recommend switching to acetaminophen (max 2g/day given CKD) or topical analgesics.",
        "evidence_level": "A",
        "confidence": 0.96,
        "source_guideline": "KDIGO 2024 / ACC/AHA 2023",
        "category": "medication_safety",
        "priority": "critical",
        "condition_filter": ["CKD", "HF"],
        "feature_importance": [
            {"feature": "CKD Stage", "value": 0.88, "direction": "negative"},
            {"feature": "Heart Failure Status", "value": 0.85, "direction": "negative"},
            {"feature": "Current NSAID Use", "value": 0.92, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Atrial Fibrillation Stroke Risk — CHA2DS2-VASc Assessment",
        "recommendation": "Patient with AFib has CHA2DS2-VASc score of 4 (HTN, age, diabetes). Current anticoagulation with Apixaban 5mg BID is appropriate. Recommend annual renal function monitoring to ensure dose remains correct, and assess bleeding risk with HAS-BLED score.",
        "evidence_level": "A",
        "confidence": 0.87,
        "source_guideline": "ACC/AHA 2023 AFib Guidelines",
        "category": "chronic_management",
        "priority": "routine",
        "condition_filter": ["AFib"],
        "feature_importance": [
            {"feature": "CHA2DS2-VASc Score", "value": 0.90, "direction": "negative"},
            {"feature": "Current Anticoagulation", "value": 0.75, "direction": "positive"},
            {"feature": "Renal Function", "value": 0.60, "direction": "negative"},
        ],
    },
    {
        "agent_type": "triage",
        "title": "COPD Exacerbation Risk — Declining O2 Saturation",
        "recommendation": "O2 saturation trending downward: 94% → 91% → 89% over last 3 readings. Patient is at risk for acute COPD exacerbation. Consider short course of oral corticosteroids (prednisone 40mg x 5 days per GOLD 2024), increase bronchodilator frequency, and schedule pulmonology follow-up.",
        "evidence_level": "A",
        "confidence": 0.90,
        "source_guideline": "GOLD 2024 COPD Guidelines",
        "category": "urgent_care",
        "priority": "urgent",
        "condition_filter": ["COPD"],
        "feature_importance": [
            {"feature": "O2 Saturation Trend", "value": 0.93, "direction": "negative"},
            {"feature": "Exacerbation History", "value": 0.70, "direction": "negative"},
            {"feature": "Current Inhaler Compliance", "value": 0.55, "direction": "positive"},
        ],
    },
    {
        "agent_type": "diagnostic",
        "title": "Coronary Artery Disease — LDL Above Target",
        "recommendation": "LDL cholesterol is 145 mg/dL, well above the <70 mg/dL target for patients with established CAD. Consider increasing Atorvastatin from 40mg to 80mg daily, or adding Ezetimibe 10mg if already on maximum statin dose. Recheck lipids in 6-8 weeks.",
        "evidence_level": "A",
        "confidence": 0.92,
        "source_guideline": "ACC/AHA 2023 Cholesterol Guidelines",
        "category": "chronic_management",
        "priority": "soon",
        "condition_filter": ["CAD"],
        "feature_importance": [
            {"feature": "LDL Level", "value": 0.95, "direction": "negative"},
            {"feature": "Current Statin Dose", "value": 0.68, "direction": "positive"},
            {"feature": "ASCVD Risk Score", "value": 0.80, "direction": "negative"},
        ],
    },
    {
        "agent_type": "care_plan",
        "title": "Diabetes Self-Management Education Referral",
        "recommendation": "Patient with poorly controlled T2DM (A1c 9.2%) has not completed Diabetes Self-Management Education (DSME). Studies show DSME reduces A1c by 0.5-1.0%. Recommend referral to certified diabetes educator and nutritional counseling.",
        "evidence_level": "B",
        "confidence": 0.84,
        "source_guideline": "ADA Standards of Care 2024, Section 5",
        "category": "patient_education",
        "priority": "routine",
        "condition_filter": ["T2DM"],
        "feature_importance": [
            {"feature": "A1c Level", "value": 0.82, "direction": "negative"},
            {"feature": "DSME Completion", "value": 0.90, "direction": "positive"},
            {"feature": "Medication Adherence", "value": 0.65, "direction": "positive"},
        ],
    },
]

# Mapping from condition tags to which patients (by MRN) have them
PATIENT_CONDITIONS = {
    "MRN001": ["T2DM", "HTN", "CKD"],
    "MRN002": ["HTN", "HF"],
    "MRN003": ["T2DM", "CAD"],
    "MRN004": ["T2DM", "HTN", "COPD"],
    "MRN005": ["CAD", "HF", "AFib"],
    "MRN006": ["T2DM", "CKD"],
    "MRN007": ["HTN"],
    "MRN008": ["T2DM", "HTN", "CKD", "AFib"],
    "MRN009": ["HTN", "COPD"],
    "MRN010": ["T2DM", "CAD", "HF"],
    "MRN011": ["T2DM"],
    "MRN012": ["HTN", "HF", "CKD"],
    "MRN013": ["COPD"],
    "MRN014": ["T2DM", "HTN", "AFib"],
    "MRN015": ["HTN"],
    "MRN016": ["CAD", "T2DM", "CKD"],
    "MRN017": ["HTN"],
    "MRN018": ["T2DM", "HTN", "COPD", "CKD"],
    "MRN019": ["CAD", "HF"],
    "MRN020": ["T2DM", "HTN"],
}

# ---------------------------------------------------------------------------
# The seed script (runs inside Django's shell via subprocess)
# ---------------------------------------------------------------------------

SEED_SCRIPT = r"""
import os
import sys
import uuid
import random
import datetime

# Ensure backend dir is on Python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in dir() else '.')), 'backend')
if not os.path.isdir(backend_dir):
    backend_dir = os.path.join(os.getcwd(), 'backend')
if os.path.isdir(backend_dir):
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context

from apps.tenants.models import Organization
from apps.fhir.models import FHIRPatient, AgentActionLog

random.seed(99)

RECOMMENDATIONS = __RECOMMENDATIONS__
PATIENT_CONDITIONS = __PATIENT_CONDITIONS__

# Get the demo org
try:
    org = Organization.objects.get(slug="inhealth-demo")
except Organization.DoesNotExist:
    print("ERROR: Organization 'inhealth-demo' not found. Run seed_patients.py first.")
    sys.exit(1)

print(f"Using organization: {org.name} (schema: {org.schema_name})")

with schema_context(org.schema_name):
    # Get all seeded patients
    patients = list(FHIRPatient.objects.filter(tenant=org).order_by("mrn"))
    if not patients:
        print("ERROR: No patients found. Run seed_patients.py first.")
        sys.exit(1)
    print(f"Found {len(patients)} patients")

    # Clear any existing seed recommendations to avoid duplicates
    deleted, _ = AgentActionLog.objects.filter(
        tenant=org,
        action_type=AgentActionLog.ActionType.RECOMMENDATION,
        input_context__trigger_source="seed_script",
    ).delete()
    if deleted:
        print(f"CLEARED: {deleted} previous seed recommendations")

    created_count = 0

    for rec in RECOMMENDATIONS:
        # Find patients that match this recommendation's condition filter
        required_conditions = set(rec["condition_filter"])

        matching_patients = []
        for patient in patients:
            patient_conds = set(PATIENT_CONDITIONS.get(patient.mrn, []))
            if required_conditions.issubset(patient_conds):
                matching_patients.append(patient)

        if not matching_patients:
            print(f"SKIP: No matching patients for '{rec['title']}'")
            continue

        # Create recommendation for up to 2 matching patients
        for patient in matching_patients[:2]:
            hours_ago = random.randint(1, 72)
            created_time = timezone.now() - datetime.timedelta(hours=hours_ago)

            log = AgentActionLog(
                tenant=org,
                patient=patient,
                agent_type=rec["agent_type"],
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
                action_details={
                    "description": f"AI-generated recommendation for {patient.first_name} {patient.last_name}",
                    "trigger_source": "automated_analysis",
                },
                input_context={
                    "trigger_source": "seed_script",
                    "patient_mrn": patient.mrn,
                    "conditions": list(PATIENT_CONDITIONS.get(patient.mrn, [])),
                },
                output={
                    "title": rec["title"],
                    "recommendation": rec["recommendation"],
                    "evidence_level": rec["evidence_level"],
                    "confidence": rec["confidence"],
                    "source_guideline": rec["source_guideline"],
                    "category": rec["category"],
                    "priority": rec["priority"],
                    "feature_importance": rec.get("feature_importance", []),
                },
                model_used="claude-sonnet-4-20250514",
            )
            log.created_at = created_time
            log.save()

            # Manually set created_at (auto_now_add prevents setting it in create)
            AgentActionLog.objects.filter(pk=log.pk).update(created_at=created_time)

            created_count += 1

    print(f"SEEDED: {created_count} AI recommendations")
    print("")
    print("Recommendation breakdown:")
    for agent_type in ["triage", "medication", "diagnostic", "care_plan"]:
        count = AgentActionLog.objects.filter(
            tenant=org,
            action_type=AgentActionLog.ActionType.RECOMMENDATION,
            agent_type=agent_type,
        ).count()
        print(f"  {agent_type}: {count} recommendations")

    pending = AgentActionLog.objects.filter(
        tenant=org,
        action_type=AgentActionLog.ActionType.RECOMMENDATION,
        reviewed_by_id__isnull=True,
    ).count()
    print(f"\nPending review: {pending}")
"""


def run_seed(via_docker: bool = True, service: str = DJANGO_SERVICE) -> bool:
    script = (
        SEED_SCRIPT
        .replace("__RECOMMENDATIONS__", json.dumps(RECOMMENDATIONS))
        .replace("__PATIENT_CONDITIONS__", json.dumps(PATIENT_CONDITIONS))
    )

    if via_docker:
        cmd = ["docker", "compose", "exec", "-T", service, "python", "-c", script]
    else:
        cmd = ["python", "-c", script]

    result = subprocess.run(cmd, capture_output=False, text=True, cwd=str(PROJECT_DIR))
    return result.returncode == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed InHealth with sample AI recommendations")
    parser.add_argument("--no-docker", action="store_true", help="Run without Docker")
    parser.add_argument("--service", default=DJANGO_SERVICE, help="Docker Compose service name")
    args = parser.parse_args()

    via_docker = not args.no_docker

    logger.info("=" * 60)
    logger.info("InHealth - AI Recommendations Seed Script")
    logger.info("=" * 60)
    logger.info(f"Seeding recommendations via {'Docker' if via_docker else 'local Python'}...")
    logger.info("")

    ok = run_seed(via_docker=via_docker, service=args.service)
    if ok:
        logger.info("Seed complete.")
    else:
        logger.error("Seed failed — check Django logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
