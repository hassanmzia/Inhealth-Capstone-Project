"""
Smart AI-generated clinical order sets.
Maps diagnoses to evidence-based orders using clinical guidelines and AI.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("clinical.order_sets")

# Pre-defined evidence-based order set templates by ICD-10 category
ORDER_SET_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # Type 2 Diabetes Mellitus
    "E11": {
        "name": "Type 2 Diabetes Management",
        "condition_display": "Type 2 Diabetes Mellitus",
        "evidence_level": "A",
        "source_guideline": "ADA Standards of Medical Care in Diabetes 2024",
        "orders": {
            "medications": [
                {"name": "Metformin 500mg", "sig": "BID with meals, titrate to 1000mg BID", "rxnorm": "860975"},
                {"name": "Empagliflozin 10mg", "sig": "Daily (if eGFR ≥30)", "rxnorm": "1545149"},
            ],
            "labs": [
                {"name": "HbA1c", "loinc": "4548-4", "frequency": "every 3 months"},
                {"name": "Comprehensive Metabolic Panel", "loinc": "24323-8", "frequency": "every 6 months"},
                {"name": "Lipid Panel", "loinc": "24331-1", "frequency": "annually"},
                {"name": "Urine Albumin-to-Creatinine Ratio", "loinc": "9318-7", "frequency": "annually"},
                {"name": "eGFR", "loinc": "48642-3", "frequency": "annually"},
            ],
            "imaging": [],
            "referrals": [
                {"specialty": "Ophthalmology", "reason": "Diabetic retinopathy screening", "frequency": "annually"},
                {"specialty": "Podiatry", "reason": "Diabetic foot exam", "frequency": "annually"},
                {"specialty": "Diabetes Education", "reason": "DSMES program", "frequency": "initial + annual"},
            ],
            "patient_education": [
                "Blood glucose self-monitoring",
                "Carbohydrate counting",
                "Hypoglycemia recognition and treatment",
                "Foot care",
            ],
        },
    },
    # Essential Hypertension
    "I10": {
        "name": "Hypertension Management",
        "condition_display": "Essential Hypertension",
        "evidence_level": "A",
        "source_guideline": "ACC/AHA 2017 Guideline for High Blood Pressure",
        "orders": {
            "medications": [
                {"name": "Lisinopril 10mg", "sig": "Daily, titrate to BP goal <130/80", "rxnorm": "104375"},
                {"name": "Amlodipine 5mg", "sig": "Daily (add if not at goal)", "rxnorm": "197361"},
            ],
            "labs": [
                {"name": "Comprehensive Metabolic Panel", "loinc": "24323-8", "frequency": "baseline, 2 weeks after start"},
                {"name": "Potassium", "loinc": "2823-3", "frequency": "2 weeks after ACEi start"},
                {"name": "Urinalysis", "loinc": "24357-6", "frequency": "annually"},
            ],
            "imaging": [
                {"name": "ECG", "reason": "Baseline LVH screening"},
            ],
            "referrals": [],
            "patient_education": [
                "DASH diet",
                "Sodium restriction (<2300mg/day)",
                "Home blood pressure monitoring",
                "Regular exercise (150 min/week)",
            ],
        },
    },
    # COPD
    "J44": {
        "name": "COPD Management",
        "condition_display": "Chronic Obstructive Pulmonary Disease",
        "evidence_level": "A",
        "source_guideline": "GOLD 2024 Report",
        "orders": {
            "medications": [
                {"name": "Tiotropium 18mcg inhaler", "sig": "1 puff daily", "rxnorm": "274535"},
                {"name": "Albuterol 90mcg MDI", "sig": "2 puffs Q4-6H PRN SOB", "rxnorm": "801092"},
                {"name": "Prednisone 40mg", "sig": "Daily x5 days (acute exacerbation)", "rxnorm": "763179"},
            ],
            "labs": [
                {"name": "CBC", "loinc": "57021-8", "frequency": "annually"},
                {"name": "Alpha-1 Antitrypsin", "loinc": "6770-3", "frequency": "once if young onset"},
            ],
            "imaging": [
                {"name": "Chest X-ray", "reason": "Baseline/exacerbation evaluation"},
                {"name": "CT Chest", "reason": "If lung cancer screening criteria met"},
            ],
            "referrals": [
                {"specialty": "Pulmonology", "reason": "Spirometry and COPD staging"},
                {"specialty": "Pulmonary Rehabilitation", "reason": "GOLD Group B-D"},
            ],
            "patient_education": [
                "Inhaler technique",
                "Smoking cessation",
                "Recognizing exacerbation symptoms",
                "Pneumococcal and influenza vaccination",
            ],
        },
    },
    # Heart Failure
    "I50": {
        "name": "Heart Failure Management (HFrEF)",
        "condition_display": "Heart Failure",
        "evidence_level": "A",
        "source_guideline": "ACC/AHA/HFSA 2022 Guideline for Heart Failure",
        "orders": {
            "medications": [
                {"name": "Sacubitril/Valsartan 24-26mg", "sig": "BID, titrate to 97-103mg BID", "rxnorm": "1656340"},
                {"name": "Carvedilol 3.125mg", "sig": "BID, titrate to 25mg BID", "rxnorm": "200031"},
                {"name": "Spironolactone 25mg", "sig": "Daily (if eGFR >30, K <5.0)", "rxnorm": "198222"},
                {"name": "Dapagliflozin 10mg", "sig": "Daily", "rxnorm": "1488564"},
                {"name": "Furosemide 20mg", "sig": "Daily PRN volume overload", "rxnorm": "200801"},
            ],
            "labs": [
                {"name": "BNP", "loinc": "42637-9", "frequency": "baseline and PRN"},
                {"name": "Comprehensive Metabolic Panel", "loinc": "24323-8", "frequency": "every 3 months"},
                {"name": "CBC", "loinc": "57021-8", "frequency": "every 6 months"},
                {"name": "Iron Studies", "loinc": "2498-4", "frequency": "annually"},
            ],
            "imaging": [
                {"name": "Echocardiogram", "reason": "Baseline EF assessment, repeat annually"},
            ],
            "referrals": [
                {"specialty": "Cardiology", "reason": "HF management and device evaluation"},
                {"specialty": "Cardiac Rehabilitation", "reason": "Exercise training"},
                {"specialty": "Dietitian", "reason": "Sodium and fluid restriction counseling"},
            ],
            "patient_education": [
                "Daily weight monitoring",
                "Sodium restriction (<1500mg/day)",
                "Fluid restriction (1.5-2L/day)",
                "Recognizing decompensation signs",
            ],
        },
    },
    # Chronic Kidney Disease
    "N18": {
        "name": "Chronic Kidney Disease Management",
        "condition_display": "Chronic Kidney Disease",
        "evidence_level": "A",
        "source_guideline": "KDIGO 2024 CKD Guideline",
        "orders": {
            "medications": [
                {"name": "Lisinopril 5mg", "sig": "Daily (if proteinuria present)", "rxnorm": "104375"},
                {"name": "Dapagliflozin 10mg", "sig": "Daily (if eGFR ≥20)", "rxnorm": "1488564"},
                {"name": "Sodium Bicarbonate 650mg", "sig": "TID (if bicarb <22)", "rxnorm": "8818"},
            ],
            "labs": [
                {"name": "eGFR/Creatinine", "loinc": "48642-3", "frequency": "every 3-6 months"},
                {"name": "Urine ACR", "loinc": "9318-7", "frequency": "every 6-12 months"},
                {"name": "Electrolytes", "loinc": "24326-1", "frequency": "every 3-6 months"},
                {"name": "Phosphorus", "loinc": "2777-1", "frequency": "every 6 months (stage 3+)"},
                {"name": "PTH", "loinc": "2731-8", "frequency": "annually (stage 3+)"},
                {"name": "Vitamin D", "loinc": "1989-3", "frequency": "annually"},
            ],
            "imaging": [
                {"name": "Renal Ultrasound", "reason": "Baseline kidney size assessment"},
            ],
            "referrals": [
                {"specialty": "Nephrology", "reason": "eGFR <30 or rapid decline or proteinuria"},
                {"specialty": "Dietitian", "reason": "Renal diet counseling"},
                {"specialty": "Vascular Surgery", "reason": "AV fistula planning (eGFR <20)"},
            ],
            "patient_education": [
                "Kidney-friendly diet",
                "Avoiding nephrotoxic medications (NSAIDs)",
                "Blood pressure targets",
                "Recognizing fluid overload",
            ],
        },
    },
}


def get_order_set_for_condition(icd10_code: str) -> Optional[Dict[str, Any]]:
    """
    Look up a pre-defined order set template by ICD-10 code.
    Matches on the first 3 characters (category level).
    """
    category = icd10_code[:3]
    return ORDER_SET_TEMPLATES.get(category)


def get_order_sets_for_patient(patient) -> List[Dict[str, Any]]:
    """
    Return all applicable order set templates for a patient based on their active conditions.
    """
    active_conditions = patient.conditions.filter(
        clinical_status="active"
    ).values_list("code", flat=True)

    seen_categories = set()
    order_sets = []

    for code in active_conditions:
        category = code[:3] if code else ""
        if category and category not in seen_categories:
            template = ORDER_SET_TEMPLATES.get(category)
            if template:
                seen_categories.add(category)
                order_sets.append({
                    "icd10_code": code,
                    **template,
                })

    return order_sets


def generate_ai_order_set(
    condition_code: str,
    patient_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a personalized order set using AI, adjusting the base template
    for patient-specific factors (allergies, renal function, age, etc.).

    This is called by the agents layer to create context-aware orders.
    """
    base_template = get_order_set_for_condition(condition_code)

    if not base_template:
        return {
            "name": f"Custom Order Set for {condition_code}",
            "condition": condition_code,
            "orders": {"medications": [], "labs": [], "imaging": [], "referrals": [], "patient_education": []},
            "evidence_level": "D",
            "note": "No pre-defined template — requires AI generation via agent system.",
        }

    personalized = {**base_template, "condition": condition_code, "personalization_applied": True}

    # Adjust medications for renal function
    egfr = patient_context.get("egfr")
    if egfr and egfr < 30:
        meds = personalized["orders"].get("medications", [])
        personalized["orders"]["medications"] = [
            {**m, "note": "CAUTION: Renal dose adjustment needed (eGFR <30)"}
            if m.get("rxnorm") in ("860975",)  # Metformin contraindicated
            else m
            for m in meds
        ]

    # Adjust for age
    age = patient_context.get("age", 0)
    if age >= 80:
        personalized["orders"].setdefault("notes", [])
        personalized["orders"]["notes"] = ["Consider less aggressive targets for elderly patient (age ≥80)"]

    # Flag allergies
    allergies = patient_context.get("allergies", [])
    if allergies:
        meds = personalized["orders"].get("medications", [])
        for med in meds:
            for allergy in allergies:
                if allergy.lower() in med.get("name", "").lower():
                    med["contraindicated"] = True
                    med["contraindication_reason"] = f"Patient allergy: {allergy}"

    return personalized
