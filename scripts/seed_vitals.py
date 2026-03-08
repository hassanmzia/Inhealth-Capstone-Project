#!/usr/bin/env python3
"""
InHealth - Simulated Vitals Seed Script

Generates realistic vital-sign FHIRObservation records (HR, BP, SpO2, Temp,
RR, Weight) for every active FHIRPatient in the demo tenant.

Run after seed_patients.py:
  python3 scripts/seed_vitals.py
  python3 scripts/seed_vitals.py --no-docker
  python3 scripts/seed_vitals.py --hours 48   # generate 48h of data (default 24)
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
# Vital sign definitions (LOINC codes the frontend vitals endpoint expects)
# ---------------------------------------------------------------------------

VITAL_DEFS = [
    {
        "loinc": "8867-4",
        "display": "Heart Rate",
        "unit": "bpm",
        "normal_range": [60, 100],
        "sim_range": [58, 105],
        "ref_low": 60,
        "ref_high": 100,
    },
    {
        "loinc": "8480-6",
        "display": "Systolic Blood Pressure",
        "unit": "mmHg",
        "normal_range": [90, 120],
        "sim_range": [105, 165],
        "ref_low": 90,
        "ref_high": 120,
        "is_bp_systolic": True,
    },
    {
        "loinc": "8462-4",
        "display": "Diastolic Blood Pressure",
        "unit": "mmHg",
        "normal_range": [60, 80],
        "sim_range": [60, 95],
        "ref_low": 60,
        "ref_high": 80,
        "is_bp_diastolic": True,
    },
    {
        "loinc": "59408-5",
        "display": "Oxygen Saturation (SpO2)",
        "unit": "%",
        "normal_range": [95, 100],
        "sim_range": [92, 100],
        "ref_low": 95,
        "ref_high": 100,
    },
    {
        "loinc": "8310-5",
        "display": "Body Temperature",
        "unit": "°F",
        "normal_range": [97.0, 99.0],
        "sim_range": [96.8, 100.4],
        "ref_low": 97.0,
        "ref_high": 99.0,
    },
    {
        "loinc": "9279-1",
        "display": "Respiratory Rate",
        "unit": "breaths/min",
        "normal_range": [12, 20],
        "sim_range": [12, 24],
        "ref_low": 12,
        "ref_high": 20,
    },
    {
        "loinc": "29463-7",
        "display": "Body Weight",
        "unit": "kg",
        "normal_range": [50, 100],
        "sim_range": [55, 120],
        "ref_low": 50,
        "ref_high": 100,
        "interval_hours": 24,  # weight measured once daily
    },
]

# ---------------------------------------------------------------------------
# The actual seed script (runs inside Django shell)
# ---------------------------------------------------------------------------

SEED_SCRIPT = r"""
import os, sys, uuid, random, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from apps.tenants.models import Organization
from apps.fhir.models import FHIRPatient, FHIRObservation

random.seed()

VITAL_DEFS = __VITAL_DEFS__
HOURS = __HOURS__

# Find the demo org
try:
    org = Organization.objects.get(slug="inhealth-demo")
except Organization.DoesNotExist:
    org = Organization.objects.filter(is_active=True).first()

if not org:
    print("ERROR: No active organization found. Run seed_patients.py first.")
    sys.exit(1)

print(f"ORG:     {org.name} (schema: {org.schema_name})")

with schema_context(org.schema_name):
    patients = list(FHIRPatient.objects.filter(tenant=org, active=True))
    print(f"FOUND:   {len(patients)} active patients")

    if not patients:
        print("ERROR: No patients found. Run seed_patients.py first.")
        sys.exit(1)

    now = timezone.now()
    total_created = 0

    for patient in patients:
        patient_seed = hash(str(patient.id)) % 10000
        for vdef in VITAL_DEFS:
            interval_hours = vdef.get("interval_hours", 1)
            num_readings = max(1, HOURS // interval_hours)

            # Give each patient a slightly different baseline
            rng_lo, rng_hi = vdef["sim_range"]
            mid = (rng_lo + rng_hi) / 2
            # Patient-specific offset for realistic variation
            offset = (patient_seed % 20 - 10) * (rng_hi - rng_lo) / 100
            p_lo = max(rng_lo, mid - (mid - rng_lo) + offset)
            p_hi = min(rng_hi, mid + (rng_hi - mid) + offset)

            for i in range(num_readings):
                hours_ago = i * interval_hours
                eff_dt = now - datetime.timedelta(
                    hours=hours_ago,
                    minutes=random.randint(0, 15),
                )

                val = round(random.uniform(p_lo, p_hi), 1)

                # Integer for HR, RR, SpO2
                if vdef["unit"] in ("bpm", "breaths/min", "%"):
                    val = round(val)

                # Interpretation
                ref_high = vdef.get("ref_high")
                ref_low = vdef.get("ref_low")
                if ref_high and val > ref_high * 1.2:
                    interp = "HH"
                elif ref_high and val > ref_high:
                    interp = "H"
                elif ref_low and val < ref_low * 0.8:
                    interp = "LL"
                elif ref_low and val < ref_low:
                    interp = "L"
                else:
                    interp = "N"

                FHIRObservation.objects.create(
                    tenant=org,
                    fhir_id=str(uuid.uuid4()),
                    patient=patient,
                    status="final",
                    code=vdef["loinc"],
                    display=vdef["display"],
                    value_quantity=val,
                    value_unit=vdef["unit"],
                    reference_range_low=ref_low,
                    reference_range_high=ref_high,
                    interpretation=interp,
                    effective_datetime=eff_dt,
                )
                total_created += 1

    print(f"SEEDED:  {total_created} vital-sign observations across {len(patients)} patients")
    print(f"         ({HOURS}h of data, ~{total_created // len(patients)} readings/patient)")
    print("Done!")
"""


def run_seed(via_docker: bool = True, service: str = DJANGO_SERVICE, hours: int = 24) -> bool:
    script = (
        SEED_SCRIPT
        .replace("__VITAL_DEFS__", json.dumps(VITAL_DEFS))
        .replace("__HOURS__", str(hours))
    )

    if via_docker:
        cmd = ["docker", "compose", "exec", "-T", service, "python", "-c", script]
    else:
        cmd = ["python", "-c", script]

    result = subprocess.run(cmd, capture_output=False, text=True, cwd=str(PROJECT_DIR))
    return result.returncode == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed simulated vital signs for all patients")
    parser.add_argument("--no-docker", action="store_true", help="Run without Docker")
    parser.add_argument("--service", default=DJANGO_SERVICE, help="Docker Compose service name")
    parser.add_argument("--hours", type=int, default=24, help="Hours of vitals data to generate (default 24)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("InHealth - Vitals Seed Script")
    logger.info("=" * 60)
    logger.info(f"Generating {args.hours}h of simulated vitals...")
    logger.info("")

    ok = run_seed(via_docker=not args.no_docker, service=args.service, hours=args.hours)
    if ok:
        logger.info("Vitals seed complete.")
    else:
        logger.error("Vitals seed failed — check Django logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
