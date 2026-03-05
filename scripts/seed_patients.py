#!/usr/bin/env python3
"""
InHealth Chronic Care - Patient Seed Script

Populates the database with realistic sample patients, conditions,
observations, medications, and risk scores for development/demo use.

Run after create_superuser.py:
  python3 scripts/seed_patients.py
  python3 scripts/seed_patients.py --no-docker   # if running outside Docker
  python3 scripts/seed_patients.py --count 50    # seed N patients (default 20)
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
# Seed data definitions
# ---------------------------------------------------------------------------

PATIENTS = [
    dict(first="James", last="Morrison", dob="1952-03-14", gender="male",   mrn="MRN001", phone="555-201-0001", city="Chicago",     state="IL", zip="60601", conditions=["T2DM","HTN","CKD"],         risk="critical"),
    dict(first="Maria", last="Gonzalez", dob="1965-07-22", gender="female", mrn="MRN002", phone="555-201-0002", city="Houston",     state="TX", zip="77001", conditions=["HTN","HF"],                 risk="high"),
    dict(first="Robert",last="Chen",     dob="1958-11-05", gender="male",   mrn="MRN003", phone="555-201-0003", city="Los Angeles", state="CA", zip="90001", conditions=["T2DM","CAD"],                risk="high"),
    dict(first="Linda", last="Patel",    dob="1970-02-18", gender="female", mrn="MRN004", phone="555-201-0004", city="New York",    state="NY", zip="10001", conditions=["T2DM","HTN","COPD"],         risk="critical"),
    dict(first="William",last="Thompson",dob="1945-09-30", gender="male",   mrn="MRN005", phone="555-201-0005", city="Phoenix",     state="AZ", zip="85001", conditions=["CAD","HF","AFib"],           risk="critical"),
    dict(first="Susan", last="Williams", dob="1962-04-11", gender="female", mrn="MRN006", phone="555-201-0006", city="Philadelphia",state="PA", zip="19101", conditions=["T2DM","CKD"],                risk="medium"),
    dict(first="David", last="Johnson",  dob="1978-06-25", gender="male",   mrn="MRN007", phone="555-201-0007", city="San Antonio", state="TX", zip="78201", conditions=["HTN"],                       risk="low"),
    dict(first="Jennifer",last="Brown",  dob="1955-12-03", gender="female", mrn="MRN008", phone="555-201-0008", city="San Diego",   state="CA", zip="92101", conditions=["T2DM","HTN","CKD","AFib"],   risk="critical"),
    dict(first="Michael",last="Davis",   dob="1980-08-17", gender="male",   mrn="MRN009", phone="555-201-0009", city="Dallas",      state="TX", zip="75201", conditions=["HTN","COPD"],                risk="medium"),
    dict(first="Patricia",last="Miller", dob="1948-01-29", gender="female", mrn="MRN010", phone="555-201-0010", city="San Jose",    state="CA", zip="95101", conditions=["T2DM","CAD","HF"],           risk="critical"),
    dict(first="Thomas", last="Wilson",  dob="1967-05-08", gender="male",   mrn="MRN011", phone="555-201-0011", city="Austin",      state="TX", zip="78701", conditions=["T2DM"],                      risk="medium"),
    dict(first="Barbara",last="Moore",   dob="1953-10-14", gender="female", mrn="MRN012", phone="555-201-0012", city="Jacksonville",state="FL", zip="32099", conditions=["HTN","HF","CKD"],           risk="high"),
    dict(first="Charles",last="Taylor",  dob="1972-03-21", gender="male",   mrn="MRN013", phone="555-201-0013", city="Fort Worth",  state="TX", zip="76101", conditions=["COPD"],                      risk="medium"),
    dict(first="Margaret",last="Anderson",dob="1960-07-16",gender="female", mrn="MRN014", phone="555-201-0014", city="Columbus",    state="OH", zip="43085", conditions=["T2DM","HTN","AFib"],         risk="high"),
    dict(first="Joseph", last="Jackson", dob="1975-11-02", gender="male",   mrn="MRN015", phone="555-201-0015", city="Charlotte",   state="NC", zip="28201", conditions=["HTN"],                       risk="low"),
    dict(first="Dorothy",last="Harris",  dob="1950-09-27", gender="female", mrn="MRN016", phone="555-201-0016", city="Indianapolis",state="IN", zip="46201", conditions=["CAD","T2DM","CKD"],          risk="critical"),
    dict(first="Daniel", last="Martin",  dob="1983-02-14", gender="male",   mrn="MRN017", phone="555-201-0017", city="San Francisco",state="CA",zip="94102", conditions=["HTN"],                       risk="low"),
    dict(first="Helen",  last="Garcia",  dob="1957-06-09", gender="female", mrn="MRN018", phone="555-201-0018", city="Seattle",     state="WA", zip="98101", conditions=["T2DM","HTN","COPD","CKD"],   risk="critical"),
    dict(first="Paul",   last="Martinez",dob="1969-04-23", gender="male",   mrn="MRN019", phone="555-201-0019", city="Denver",      state="CO", zip="80201", conditions=["CAD","HF"],                  risk="high"),
    dict(first="Nancy",  last="Robinson",dob="1963-08-31", gender="female", mrn="MRN020", phone="555-201-0020", city="Nashville",   state="TN", zip="37201", conditions=["T2DM","HTN"],                risk="medium"),
]

# ICD-10 codes and LOINC observations per condition tag
CONDITIONS_MAP = {
    "T2DM": {
        "code": "E11.9", "display": "Type 2 Diabetes Mellitus", "snomed": "44054006",
        "observations": [
            {"loinc": "4548-4", "name": "Hemoglobin A1c",         "unit": "%",     "values": (7.5, 11.2), "ref_low": 4.0, "ref_high": 5.7},
            {"loinc": "2345-7", "name": "Glucose [Mass/volume]",   "unit": "mg/dL", "values": (120, 280),  "ref_low": 70,  "ref_high": 100},
        ],
        "medications": [
            {"rxnorm": "861007", "display": "Metformin 500mg oral tablet",     "dose": 500,  "unit": "mg", "freq": "twice daily", "route": "oral", "days": 90},
            {"rxnorm": "316255", "display": "Glipizide 5mg oral tablet",       "dose": 5,    "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
        ],
    },
    "HTN": {
        "code": "I10", "display": "Essential Hypertension", "snomed": "59621000",
        "observations": [
            {"loinc": "55284-4", "name": "Blood Pressure", "unit": "mmHg", "values": (125, 165), "ref_low": 90, "ref_high": 120, "is_bp": True},
        ],
        "medications": [
            {"rxnorm": "197361", "display": "Lisinopril 10mg oral tablet",     "dose": 10,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
            {"rxnorm": "153165", "display": "Amlodipine 5mg oral tablet",      "dose": 5,    "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
        ],
    },
    "CKD": {
        "code": "N18.3", "display": "Chronic Kidney Disease, Stage 3", "snomed": "433144002",
        "observations": [
            {"loinc": "33914-3", "name": "eGFR",                   "unit": "mL/min/1.73m2", "values": (30, 58), "ref_low": 60, "ref_high": 120},
            {"loinc": "2160-0", "name": "Creatinine [Mass/volume]","unit": "mg/dL",          "values": (1.4, 3.2),"ref_low": 0.6,"ref_high": 1.2},
        ],
        "medications": [
            {"rxnorm": "197884", "display": "Furosemide 40mg oral tablet",     "dose": 40,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 30},
        ],
    },
    "HF": {
        "code": "I50.9", "display": "Heart Failure, Unspecified", "snomed": "84114007",
        "observations": [
            {"loinc": "33762-6", "name": "NT-proBNP",              "unit": "pg/mL", "values": (500, 4000), "ref_low": 0, "ref_high": 125},
        ],
        "medications": [
            {"rxnorm": "203155", "display": "Carvedilol 12.5mg oral tablet",   "dose": 12.5, "unit": "mg", "freq": "twice daily", "route": "oral", "days": 90},
            {"rxnorm": "197884", "display": "Furosemide 40mg oral tablet",     "dose": 40,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 30},
        ],
    },
    "CAD": {
        "code": "I25.10", "display": "Coronary Artery Disease", "snomed": "53741008",
        "observations": [
            {"loinc": "2093-3", "name": "Cholesterol [Mass/volume]","unit": "mg/dL","values": (160, 280),  "ref_low": 0,   "ref_high": 200},
            {"loinc": "13457-7","name": "LDL Cholesterol",          "unit": "mg/dL","values": (90, 190),   "ref_low": 0,   "ref_high": 100},
        ],
        "medications": [
            {"rxnorm": "861007", "display": "Atorvastatin 40mg oral tablet",   "dose": 40,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
            {"rxnorm": "315242", "display": "Aspirin 81mg oral tablet",        "dose": 81,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
        ],
    },
    "COPD": {
        "code": "J44.1", "display": "COPD with Acute Exacerbation", "snomed": "13645005",
        "observations": [
            {"loinc": "19994-3", "name": "O2 Saturation",          "unit": "%",    "values": (88, 96),  "ref_low": 95, "ref_high": 100},
        ],
        "medications": [
            {"rxnorm": "745679", "display": "Tiotropium 18mcg inhaler",        "dose": 18,   "unit": "mcg","freq": "once daily",  "route": "inhalation", "days": 30},
            {"rxnorm": "351264", "display": "Albuterol 90mcg/actuation inhaler","dose": 90,  "unit": "mcg","freq": "as needed",   "route": "inhalation", "days": 30},
        ],
    },
    "AFib": {
        "code": "I48.91", "display": "Atrial Fibrillation", "snomed": "49436004",
        "observations": [
            {"loinc": "8867-4", "name": "Heart Rate",              "unit": "beats/min", "values": (68, 112), "ref_low": 60, "ref_high": 100},
        ],
        "medications": [
            {"rxnorm": "855332", "display": "Apixaban 5mg oral tablet",        "dose": 5,    "unit": "mg", "freq": "twice daily", "route": "oral", "days": 30},
            {"rxnorm": "203155", "display": "Metoprolol succinate 50mg",       "dose": 50,   "unit": "mg", "freq": "once daily",  "route": "oral", "days": 90},
        ],
    },
}

RISK_SCORE_MAP = {
    "critical": (0.82, 0.99),
    "high":     (0.62, 0.79),
    "medium":   (0.32, 0.59),
    "low":      (0.05, 0.29),
}

SCORE_TYPES = [
    "7_day_hospitalization",
    "30_day_readmission",
    "medication_nonadherence",
]

# ---------------------------------------------------------------------------
# The seed script (runs inside Django's shell via subprocess)
# ---------------------------------------------------------------------------

SEED_SCRIPT = r"""
import os
import sys
import uuid
import random
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context

from apps.tenants.models import Organization, Domain
from apps.accounts.models import User
from apps.fhir.models import (
    FHIRPatient, FHIRCondition, FHIRObservation, FHIRMedicationRequest,
)
from apps.analytics.models import RiskScore, ClinicalKPI

random.seed(42)

# ---- constants injected from outer script ----
PATIENTS     = __PATIENTS__
CONDITIONS_MAP = __CONDITIONS_MAP__
RISK_SCORE_MAP = __RISK_SCORE_MAP__
SCORE_TYPES  = __SCORE_TYPES__
PATIENT_COUNT = __PATIENT_COUNT__

patients_to_seed = PATIENTS[:PATIENT_COUNT]

# -----------------------------------------------
# 1. Ensure a demo Organization exists
# -----------------------------------------------
org, created = Organization.objects.get_or_create(
    slug="inhealth-demo",
    defaults={
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "InHealth Demo Organization",
        "schema_name": "inhealth_demo",
        "subscription_tier": "enterprise",
        "is_active": True,
        "max_patients": 5000,
        "max_providers": 500,
    },
)
if created:
    print(f"CREATED: Organization '{org.name}' (schema: {org.schema_name})")
    # Create a domain entry so tenant middleware resolves correctly
    Domain.objects.get_or_create(
        domain="localhost",
        defaults={"tenant": org, "is_primary": True},
    )
else:
    print(f"EXISTS:  Organization '{org.name}'")

# -----------------------------------------------
# 2. Ensure a physician user exists in that org
# -----------------------------------------------
with schema_context(org.schema_name):
    physician, ph_created = User.objects.get_or_create(
        username="dr.demo",
        defaults={
            "email": "dr.demo@inhealth.io",
            "first_name": "Demo",
            "last_name": "Physician",
            "role": User.Role.PHYSICIAN,
            "tenant": org,
            "is_active": True,
        },
    )
    if ph_created:
        physician.set_password("InHealth2024!")
        physician.save()
        print(f"CREATED: Physician user 'dr.demo'  (password: InHealth2024!)")
    else:
        print(f"EXISTS:  Physician user 'dr.demo'")

    # -----------------------------------------------
    # 3. Seed patients + clinical data
    # -----------------------------------------------
    def rnd_float(lo, hi):
        return round(random.uniform(lo, hi), 2)

    def days_ago(n):
        return timezone.now() - datetime.timedelta(days=n)

    created_count = 0
    skipped_count = 0

    for p in patients_to_seed:
        if FHIRPatient.objects.filter(mrn=p["mrn"], tenant=org).exists():
            skipped_count += 1
            continue

        # ---- Patient ----
        patient = FHIRPatient.objects.create(
            tenant=org,
            fhir_id=str(uuid.uuid4()),
            mrn=p["mrn"],
            first_name=p["first"],
            last_name=p["last"],
            birth_date=datetime.date.fromisoformat(p["dob"]),
            gender=p["gender"],
            phone=p["phone"],
            address_line1=f"{random.randint(100,9999)} Main St",
            city=p["city"],
            state=p["state"],
            postal_code=p["zip"],
            country="US",
            primary_care_provider=physician,
            active=True,
        )

        # ---- Conditions ----
        for cond_key in p["conditions"]:
            cdef = CONDITIONS_MAP[cond_key]
            onset = days_ago(random.randint(90, 1800))
            FHIRCondition.objects.create(
                tenant=org,
                fhir_id=str(uuid.uuid4()),
                patient=patient,
                clinical_status="active",
                verification_status="confirmed",
                code=cdef["code"],
                display=cdef["display"],
                snomed_code=cdef.get("snomed", ""),
                category="encounter-diagnosis",
                onset_datetime=onset,
                recorded_date=onset,
            )

            # ---- Observations for this condition ----
            for obs_def in cdef.get("observations", []):
                # 4 observations spread over last 12 months
                for month_offset in [11, 8, 4, 1]:
                    eff_dt = days_ago(month_offset * 30 + random.randint(-5, 5))
                    val = rnd_float(*obs_def["values"])

                    if obs_def.get("is_bp"):
                        # Blood pressure stored as components
                        systolic = val
                        diastolic = rnd_float(70, 95)
                        FHIRObservation.objects.create(
                            tenant=org,
                            fhir_id=str(uuid.uuid4()),
                            patient=patient,
                            status="final",
                            code=obs_def["loinc"],
                            display=obs_def["name"],
                            value_quantity=systolic,
                            value_unit="mmHg",
                            reference_range_low=obs_def.get("ref_low"),
                            reference_range_high=obs_def.get("ref_high"),
                            interpretation="H" if systolic > obs_def["ref_high"] else "N",
                            effective_datetime=eff_dt,
                            components=[
                                {"code": "8480-6", "display": "Systolic BP",  "value": systolic,  "unit": "mmHg"},
                                {"code": "8462-4", "display": "Diastolic BP", "value": diastolic, "unit": "mmHg"},
                            ],
                        )
                    else:
                        ref_high = obs_def.get("ref_high")
                        interp = "H" if (ref_high and val > ref_high) else "N"
                        FHIRObservation.objects.create(
                            tenant=org,
                            fhir_id=str(uuid.uuid4()),
                            patient=patient,
                            status="final",
                            code=obs_def["loinc"],
                            display=obs_def["name"],
                            value_quantity=val,
                            value_unit=obs_def["unit"],
                            reference_range_low=obs_def.get("ref_low"),
                            reference_range_high=ref_high,
                            interpretation=interp,
                            effective_datetime=eff_dt,
                        )

            # ---- Medications ----
            for med in cdef.get("medications", []):
                authored = days_ago(random.randint(30, 365))
                FHIRMedicationRequest.objects.create(
                    tenant=org,
                    fhir_id=str(uuid.uuid4()),
                    patient=patient,
                    status="active",
                    intent="order",
                    medication_code=med["rxnorm"],
                    medication_display=med["display"],
                    dosage_text=f"{med['dose']} {med['unit']} {med['freq']}",
                    dose_quantity=med["dose"],
                    dose_unit=med["unit"],
                    frequency=med["freq"],
                    route=med["route"],
                    days_supply=med["days"],
                    authored_on=authored,
                    requester_id=physician.id,
                )

        # ---- Risk scores ----
        score_lo, score_hi = RISK_SCORE_MAP[p["risk"]]
        for score_type in SCORE_TYPES:
            score_val = rnd_float(score_lo, score_hi)
            RiskScore.objects.create(
                patient=patient,
                tenant=org,
                score_type=score_type,
                score=score_val,
                risk_level=p["risk"],
                features={
                    "age":            round((datetime.date.today() - datetime.date.fromisoformat(p["dob"])).days / 365.25, 1),
                    "comorbidities":  len(p["conditions"]),
                    "a1c_value":      rnd_float(6.5, 10.0) if "T2DM" in p["conditions"] else None,
                    "bp_systolic":    rnd_float(130, 170)  if "HTN"  in p["conditions"] else None,
                },
                model_version="xgboost_v1",
                valid_until=timezone.now() + datetime.timedelta(days=30),
            )

        created_count += 1

    print(f"SEEDED:  {created_count} patients, skipped {skipped_count} (already existed)")

    # -----------------------------------------------
    # 4. Seed ClinicalKPI metrics (6 months of data)
    # -----------------------------------------------
    import datetime as dt

    kpi_defs = [
        ("pct_a1c_controlled",       [68, 69, 67, 70, 71, 72], "%"),
        ("pct_bp_controlled",         [65, 67, 66, 68, 70, 71], "%"),
        ("medication_adherence_rate", [76, 78, 74, 80, 82, 85], "%"),
        ("care_gap_closure_rate",     [60, 62, 61, 64, 66, 68], "%"),
        ("readmission_rate_30d",      [9.1, 8.8, 9.3, 8.5, 8.3, 8.2], "%"),
    ]

    today = dt.date.today()
    kpi_created = 0
    for metric_name, monthly_values, unit in kpi_defs:
        for i, value in enumerate(monthly_values):
            metric_date = today.replace(day=1) - dt.timedelta(days=30 * (5 - i))
            _, created_kpi = ClinicalKPI.objects.get_or_create(
                tenant=org,
                metric_name=metric_name,
                metric_date=metric_date,
                defaults={
                    "metric_value": value,
                    "unit": unit,
                    "metadata": {
                        "breakdown": {
                            "Preventive":   {"open_gaps": 312, "closure_rate": 68},
                            "Screening":    {"open_gaps": 184, "closure_rate": 72},
                            "Chronic Mgmt": {"open_gaps": 247, "closure_rate": 61},
                            "Medication":   {"open_gaps": 89,  "closure_rate": 81},
                            "Follow-up":    {"open_gaps": 156, "closure_rate": 74},
                        }
                    } if metric_name == "care_gap_closure_rate" else {},
                },
            )
            if created_kpi:
                kpi_created += 1

    print(f"SEEDED:  {kpi_created} KPI data points")
    print("")
    print("Done! Login credentials:")
    print("  Physician:  dr.demo / InHealth2024!")
    print("  Admin:      admin   / InHealth2024!  (if created via create_superuser.py)")
"""


def run_seed(via_docker: bool = True, service: str = DJANGO_SERVICE, count: int = 20) -> bool:
    patients_slice = PATIENTS[:count]

    script = (
        SEED_SCRIPT
        .replace("__PATIENTS__",      json.dumps(patients_slice))
        .replace("__CONDITIONS_MAP__", json.dumps(CONDITIONS_MAP))
        .replace("__RISK_SCORE_MAP__", json.dumps(RISK_SCORE_MAP))
        .replace("__SCORE_TYPES__",    json.dumps(SCORE_TYPES))
        .replace("__PATIENT_COUNT__",  str(count))
    )

    if via_docker:
        cmd = ["docker", "compose", "exec", "-T", service, "python", "-c", script]
    else:
        cmd = ["python", "-c", script]

    result = subprocess.run(cmd, capture_output=False, text=True, cwd=str(PROJECT_DIR))
    return result.returncode == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed InHealth with sample patient data")
    parser.add_argument("--no-docker", action="store_true", help="Run without Docker")
    parser.add_argument("--service",   default=DJANGO_SERVICE, help="Docker Compose service name")
    parser.add_argument("--count",     type=int, default=20, help="Number of patients to seed (max 20)")
    args = parser.parse_args()

    count = min(args.count, len(PATIENTS))
    via_docker = not args.no_docker

    logger.info("=" * 60)
    logger.info("InHealth - Patient Seed Script")
    logger.info("=" * 60)
    logger.info(f"Seeding {count} patients via {'Docker' if via_docker else 'local Python'}...")
    logger.info("")

    ok = run_seed(via_docker=via_docker, service=args.service, count=count)
    if ok:
        logger.info("Seed complete.")
    else:
        logger.error("Seed failed — check Django logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
