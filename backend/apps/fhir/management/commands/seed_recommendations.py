"""
Django management command to seed AI recommendations into AgentActionLog.

Usage:
  python manage.py seed_recommendations
  docker compose exec django python manage.py seed_recommendations
"""

import datetime
import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.fhir.models import AgentActionLog, FHIRPatient
from apps.tenants.models import Organization


# Realistic clinical AI recommendations
RECOMMENDATIONS = [
    {
        "agent_type": "medication",
        "title": "Potential Drug Interaction: Metformin + Furosemide",
        "recommendation": (
            "Patient is on Metformin 500mg and Furosemide 40mg. Furosemide may increase "
            "blood glucose levels, potentially reducing Metformin efficacy. Consider "
            "monitoring blood glucose more frequently and adjusting Metformin dosage if "
            "A1c rises above target."
        ),
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
        "recommendation": (
            "Patient with Type 2 Diabetes has not had an A1c test in the last 90 days. "
            "ADA guidelines recommend A1c testing every 3 months for patients not meeting "
            "glycemic goals. Schedule A1c lab work at next visit."
        ),
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
        "recommendation": (
            "Patient's average systolic BP over last 3 readings is 152 mmHg, exceeding "
            "the ACC/AHA target of <130 mmHg. Consider uptitrating Lisinopril from 10mg "
            "to 20mg or adding a second antihypertensive agent. Recheck BP in 4 weeks."
        ),
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
        "recommendation": (
            "NT-proBNP level of 2,450 pg/mL significantly exceeds the upper normal limit "
            "of 125 pg/mL, suggesting decompensated heart failure. Recommend urgent "
            "cardiology consultation, assess fluid status, and consider diuretic adjustment."
        ),
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
        "recommendation": (
            "eGFR has declined from 48 to 38 mL/min/1.73m2 over the past 6 months, "
            "representing a >25% decline. Per KDIGO 2024 guidelines, refer to nephrology, "
            "check for reversible causes, and ensure ACE inhibitor/ARB is at maximum "
            "tolerated dose."
        ),
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
        "recommendation": (
            "Patient has CKD Stage 3 and Heart Failure. NSAIDs are contraindicated due to "
            "risk of acute kidney injury and fluid retention. If prescribed for pain, "
            "recommend switching to acetaminophen (max 2g/day given CKD) or topical "
            "analgesics."
        ),
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
        "recommendation": (
            "Patient with AFib has CHA2DS2-VASc score of 4 (HTN, age, diabetes). Current "
            "anticoagulation with Apixaban 5mg BID is appropriate. Recommend annual renal "
            "function monitoring to ensure dose remains correct."
        ),
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
        "recommendation": (
            "O2 saturation trending downward: 94%→91%→89% over last 3 readings. "
            "Consider short course of oral corticosteroids (prednisone 40mg x 5 days "
            "per GOLD 2024), increase bronchodilator frequency, and schedule pulmonology "
            "follow-up."
        ),
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
        "recommendation": (
            "LDL cholesterol is 145 mg/dL, well above the <70 mg/dL target for patients "
            "with established CAD. Consider increasing Atorvastatin from 40mg to 80mg "
            "daily, or adding Ezetimibe 10mg. Recheck lipids in 6-8 weeks."
        ),
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
        "recommendation": (
            "Patient with poorly controlled T2DM (A1c 9.2%) has not completed Diabetes "
            "Self-Management Education (DSME). Studies show DSME reduces A1c by 0.5-1.0%. "
            "Recommend referral to certified diabetes educator and nutritional counseling."
        ),
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

# Mapping from condition ICD-10 codes to condition tags
ICD10_TO_TAG = {
    "E11": "T2DM", "E11.9": "T2DM",
    "I10": "HTN",
    "N18": "CKD", "N18.3": "CKD",
    "I50": "HF", "I50.9": "HF",
    "I25": "CAD", "I25.10": "CAD",
    "J44": "COPD", "J44.1": "COPD",
    "I48": "AFib", "I48.91": "AFib",
}


class Command(BaseCommand):
    help = "Seed AI recommendations into AgentActionLog for dashboard display"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            default="inhealth-demo",
            help="Organization slug (default: inhealth-demo)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seed recommendations before seeding",
        )

    def handle(self, *args, **options):
        org_slug = options["org_slug"]
        random.seed(99)

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"Organization '{org_slug}' not found. Run seed_patients.py first.")
            )
            return

        self.stdout.write(f"Using organization: {org.name} (schema: {org.schema_name})")

        with schema_context(org.schema_name):
            patients = list(FHIRPatient.objects.filter(tenant=org).order_by("mrn"))
            if not patients:
                self.stderr.write(self.style.ERROR("No patients found. Run seed_patients.py first."))
                return

            self.stdout.write(f"Found {len(patients)} patients")

            if options["clear"]:
                deleted, _ = AgentActionLog.objects.filter(
                    tenant=org,
                    action_type=AgentActionLog.ActionType.RECOMMENDATION,
                    input_context__trigger_source="seed_script",
                ).delete()
                if deleted:
                    self.stdout.write(f"Cleared {deleted} previous seed recommendations")

            # Build patient condition map from actual FHIR data
            from apps.fhir.models import FHIRCondition

            patient_conditions = {}
            for patient in patients:
                conditions = FHIRCondition.objects.filter(
                    patient=patient, clinical_status="active"
                ).values_list("code", flat=True)
                tags = set()
                for code in conditions:
                    # Match against ICD-10 codes (full and prefix)
                    if code in ICD10_TO_TAG:
                        tags.add(ICD10_TO_TAG[code])
                    else:
                        prefix = code.split(".")[0]
                        if prefix in ICD10_TO_TAG:
                            tags.add(ICD10_TO_TAG[prefix])
                patient_conditions[patient.id] = tags

            created_count = 0

            for rec in RECOMMENDATIONS:
                required = set(rec["condition_filter"])

                matching = [p for p in patients if required.issubset(patient_conditions.get(p.id, set()))]
                if not matching:
                    self.stdout.write(f"  SKIP: No matching patients for '{rec['title']}'")
                    continue

                for patient in matching[:2]:
                    hours_ago = random.randint(1, 72)
                    created_time = timezone.now() - datetime.timedelta(hours=hours_ago)

                    log = AgentActionLog.objects.create(
                        tenant=org,
                        patient=patient,
                        agent_type=rec["agent_type"],
                        action_type=AgentActionLog.ActionType.RECOMMENDATION,
                        action_details={
                            "description": f"AI recommendation for {patient.first_name} {patient.last_name}",
                        },
                        input_context={
                            "trigger_source": "seed_script",
                            "patient_conditions": list(patient_conditions.get(patient.id, [])),
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

                    # Update created_at to simulate historical data
                    AgentActionLog.objects.filter(pk=log.pk).update(created_at=created_time)
                    created_count += 1

            self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} AI recommendations"))

            # Print breakdown
            for agent_type in ["triage", "medication", "diagnostic", "care_plan"]:
                count = AgentActionLog.objects.filter(
                    tenant=org,
                    action_type=AgentActionLog.ActionType.RECOMMENDATION,
                    agent_type=agent_type,
                ).count()
                self.stdout.write(f"  {agent_type}: {count} recommendations")

            pending = AgentActionLog.objects.filter(
                tenant=org,
                action_type=AgentActionLog.ActionType.RECOMMENDATION,
                reviewed_by_id__isnull=True,
            ).count()
            self.stdout.write(f"  Pending review: {pending}")
