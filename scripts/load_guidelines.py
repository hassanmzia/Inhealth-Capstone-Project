#!/usr/bin/env python3
"""
InHealth Chronic Care - Clinical Guidelines Loader

Loads clinical guideline text into Qdrant for RAG-based
clinical decision support. Chunks guidelines into sections
and embeds each chunk using OpenAI text embeddings.

Guidelines loaded:
  - ADA 2024 Standards of Care in Diabetes
  - ACC/AHA 2022 Heart Failure Guidelines
  - KDIGO 2024 CKD Guidelines
  - GOLD 2024 COPD Guidelines
  - ACC/AHA 2023 Atrial Fibrillation Guidelines
  - ACC/AHA 2017 Hypertension Guidelines
"""

import os
import sys
import logging
import time
import hashlib
from pathlib import Path
from typing import Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
except ImportError:
    print("ERROR: qdrant-client not installed. Run: pip install qdrant-client")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path=None):
        pass

# ============================================================
# Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)

EMBEDDING_DIM = 1536
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "clinical_guidelines"
BATCH_SIZE = 10  # Number of texts to embed per API call
RATE_LIMIT_DELAY = 0.1  # Seconds between API calls

# ============================================================
# Clinical Guideline Content
# ============================================================
CLINICAL_GUIDELINES = [

    # --------------------------------------------------------
    # ADA 2024 Standards of Care in Diabetes
    # --------------------------------------------------------
    {
        "id": "ada2024-classification-diagnosis",
        "text": """ADA 2024 - Classification and Diagnosis of Diabetes:
Diabetes is classified into four main types:
1. Type 1 diabetes: Autoimmune beta cell destruction, usually leading to absolute insulin deficiency.
2. Type 2 diabetes: Progressive loss of adequate beta-cell insulin secretion in the setting of insulin resistance.
3. Gestational diabetes mellitus (GDM): Diagnosed in the second or third trimester of pregnancy.
4. Specific types due to other causes: Monogenic diabetes syndromes, diseases of exocrine pancreas, drug/chemical-induced.

Diagnosis criteria (any one of the following):
- Fasting plasma glucose ≥126 mg/dL (7.0 mmol/L)
- 2-h plasma glucose ≥200 mg/dL (11.1 mmol/L) during OGTT
- A1C ≥6.5% (48 mmol/mol)
- Random plasma glucose ≥200 mg/dL in a patient with symptoms of hyperglycemia

Prediabetes is defined as IFG (fasting 100-125 mg/dL), IGT (2-h 140-199 mg/dL), or A1C 5.7-6.4%.""",
        "metadata": {
            "guideline_id": "ada-2024-soc",
            "title": "ADA 2024 Standards of Care in Diabetes",
            "organization": "American Diabetes Association",
            "disease_codes": ["E11.9", "R73.03"],
            "section": "Classification and Diagnosis",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "ada2024-glycemic-targets",
        "text": """ADA 2024 - Glycemic Targets for Adults with Diabetes:
For many nonpregnant adults with T1DM or T2DM, an HbA1c target of <7% (53 mmol/mol) is recommended.
More or less stringent targets may be appropriate based on individual patient characteristics.

Target HbA1c less stringent (<8%, 64 mmol/mol) may be appropriate for:
- History of severe hypoglycemia
- Limited life expectancy or advanced age
- Long-standing diabetes with difficulty achieving target
- Multiple comorbidities
- Poor self-management resources

Target HbA1c more stringent (<6.5%, 48 mmol/mol) may be considered for:
- Short duration of diabetes, long life expectancy
- Treated with lifestyle or metformin only
- No significant CVD
- No hypoglycemia risk

Blood glucose targets: Preprandial 80-130 mg/dL; peak postprandial <180 mg/dL.
CGM targets: Time in range (70-180 mg/dL) >70%; time below range (<70 mg/dL) <4%.""",
        "metadata": {
            "guideline_id": "ada-2024-soc",
            "title": "ADA 2024 Standards of Care in Diabetes",
            "organization": "American Diabetes Association",
            "disease_codes": ["E11.9", "E11.65"],
            "section": "Glycemic Targets",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "ada2024-pharmacotherapy-t2dm",
        "text": """ADA 2024 - Pharmacologic Therapy for Type 2 Diabetes:
Metformin is the preferred initial pharmacologic agent unless contraindicated (eGFR <30) or not tolerated.

For patients with established CVD or at high CV risk (CHA2DS2-VASc ≥2), add:
- SGLT2 inhibitor with proven CV benefit: empagliflozin, canagliflozin, or dapagliflozin
- OR GLP-1 receptor agonist with proven CV benefit: semaglutide (SC), liraglutide, dulaglutide

For patients with heart failure (especially HFrEF), add:
- SGLT2 inhibitor (empagliflozin or dapagliflozin) regardless of T2DM

For patients with CKD (eGFR 20-60, albuminuria ≥30 mg/g):
- SGLT2 inhibitor (first-line with metformin)
- If not tolerated: GLP-1 receptor agonist
- Finerenone if residual albuminuria despite optimized ACEi/ARB

For weight reduction: GLP-1 receptor agonist or tirzepatide preferred
For cost considerations: sulfonylureas (glipizide, glimepiride) or pioglitazone remain options

Insulin initiation: when HbA1c >10%, symptomatic hyperglycemia, or at diagnosis if T1DM suspected.
Basal insulin (insulin glargine or detemir) preferred over NPH.""",
        "metadata": {
            "guideline_id": "ada-2024-soc",
            "title": "ADA 2024 Standards of Care in Diabetes",
            "organization": "American Diabetes Association",
            "disease_codes": ["E11.9"],
            "section": "Pharmacologic Therapy",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "ada2024-cardiovascular-disease",
        "text": """ADA 2024 - Cardiovascular Disease and Risk Management in Diabetes:
ASCVD risk assessment should be performed annually for all adults with diabetes.
10-year ASCVD risk calculation should guide statin therapy intensity.

Blood pressure management:
- Target BP: <130/80 mmHg for most adults with diabetes and hypertension
- ACE inhibitors or ARBs preferred for patients with albuminuria or prior CVD
- Multiple antihypertensive agents needed for most patients

Lipid management:
- High-intensity statin therapy for all patients with diabetes and ASCVD, or age 40-75 with additional risk factors
- Moderate-intensity statin for patients age 40-75 without additional risk factors
- LDL target: <70 mg/dL for high-risk; <55 mg/dL for very high-risk
- Add ezetimibe if LDL not at goal on maximum statin; consider PCSK9 inhibitor for very high-risk

Antiplatelet therapy:
- Aspirin 75-162 mg/day for secondary prevention (established ASCVD)
- Do NOT use aspirin for primary prevention routinely (risk of bleeding may exceed benefit)

Smoking cessation counseling at every visit.""",
        "metadata": {
            "guideline_id": "ada-2024-soc",
            "title": "ADA 2024 Standards of Care in Diabetes",
            "organization": "American Diabetes Association",
            "disease_codes": ["E11.9", "I25.10"],
            "section": "Cardiovascular Disease and Risk Management",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "ada2024-ckd-monitoring",
        "text": """ADA 2024 - Diabetic Kidney Disease:
Annual monitoring: eGFR and UACR (urine albumin-to-creatinine ratio) starting at T2DM diagnosis.
Staging: CKD defined as eGFR <60 or albuminuria (UACR ≥30 mg/g) for ≥3 months.

Treatment to slow CKD progression:
1. Glycemic control: HbA1c target appropriate for patient (often <7-8%)
2. Blood pressure: Target <130/80 mmHg; use ACEi or ARB if albuminuria present
3. SGLT2 inhibitor: For T2DM + CKD with eGFR ≥20 mL/min (first-line alongside metformin)
4. Finerenone (nonsteroidal MRA): For T2DM + CKD + UACR ≥30 mg/g despite optimized RAS blockade, eGFR 25-75
5. GLP-1 agonist: If SGLT2i not tolerated; also provides renal protection

Avoid nephrotoxic agents: NSAIDs, contrast media (hold metformin 48h post-contrast if eGFR <60).
Consider nephrology referral when eGFR <30 or rapidly declining.
Monitor for complications: anemia, acidosis, hyperkalemia, bone disease.""",
        "metadata": {
            "guideline_id": "ada-2024-soc",
            "title": "ADA 2024 Standards of Care in Diabetes",
            "organization": "American Diabetes Association",
            "disease_codes": ["E11.9", "E11.21", "N18.3"],
            "section": "Diabetic Kidney Disease",
            "year": 2024,
            "evidence_level": "A",
        }
    },

    # --------------------------------------------------------
    # ACC/AHA Heart Failure Guidelines 2022
    # --------------------------------------------------------
    {
        "id": "acc-aha-hf-2022-definition",
        "text": """ACC/AHA 2022 Heart Failure Guidelines - Definition and Classification:
Heart failure (HF) is a complex clinical syndrome resulting from structural and/or functional impairment
of ventricular filling or ejection of blood.

Classification by Ejection Fraction:
- HFrEF: LVEF ≤40% (Heart failure with reduced ejection fraction) - most evidence-based therapies available
- HFmrEF: LVEF 41-49% (Heart failure with mildly reduced EF) - limited specific evidence
- HFpEF: LVEF ≥50% (Heart failure with preserved EF) - most common in elderly women; treatment focused on symptoms and comorbidities
- HFimpEF: Previously ≤40%, now ≥50% with treatment

New York Heart Association (NYHA) Classification:
Class I: No symptoms with ordinary activity
Class II: Slight limitation; symptoms with moderate exertion
Class III: Marked limitation; symptoms with less than ordinary activity
Class IV: Symptoms at rest; unable to carry out any physical activity

ACC/AHA Stages:
Stage A: At-risk (risk factors present, no structural disease)
Stage B: Pre-HF (structural disease, no symptoms)
Stage C: Symptomatic HF
Stage D: Advanced HF (refractory, end-stage)""",
        "metadata": {
            "guideline_id": "acc-aha-hf-2022",
            "title": "ACC/AHA/HFSA Guideline for the Management of Heart Failure 2022",
            "organization": "American College of Cardiology",
            "disease_codes": ["I50.9", "I50.22"],
            "section": "Definition and Classification",
            "year": 2022,
            "evidence_level": "I",
        }
    },
    {
        "id": "acc-aha-hf-2022-gdmt-hfref",
        "text": """ACC/AHA 2022 Heart Failure - GDMT for HFrEF (LVEF ≤40%):
Four evidence-based drug classes reduce mortality in HFrEF (Class I, LOE A):

1. ACE Inhibitor / ARB / ARNI:
   - Sacubitril/valsartan (Entresto) is preferred over ACEi/ARB for all eligible HFrEF patients
   - ACEi (enalapril, lisinopril) or ARB (losartan, valsartan) if ARNI not tolerated
   - Contraindicated: bilateral renal artery stenosis, angioedema, pregnancy, K+ >5.5, eGFR <30

2. Beta-blocker (cardioselective, evidence-based):
   - Carvedilol, metoprolol succinate (Toprol-XL), or bisoprolol ONLY
   - Initiate at low dose; uptitrate over weeks to maximum tolerated dose
   - Initiate only when euvolemic (not during acute decompensation)

3. Mineralocorticoid Receptor Antagonist (MRA):
   - Spironolactone or eplerenone
   - Indicated for LVEF ≤35%, NYHA II-IV, eGFR >30, K+ <5.0
   - Monitor potassium (hyperkalemia risk, especially with ACEi/ARB)

4. SGLT2 Inhibitor:
   - Dapagliflozin (Farxiga) or empagliflozin (Jardiance)
   - Reduces HF hospitalizations and cardiovascular death
   - Benefit independent of diabetes status
   - Preferred in patients with concurrent T2DM or CKD

Additional therapies for selected patients:
- Hydralazine/nitrate: For AA patients, or ACEi/ARB/ARNI intolerant (Class I)
- Digoxin: For persistent symptoms despite GDMT or for rate control in AF (Class IIa)
- Ivabradine: If in sinus rhythm, LVEF ≤35%, heart rate ≥70 bpm on beta-blocker (Class IIa)
- Vericiguat: For recent HF hospitalization or IV diuretic, to reduce CV death/HF hospitalization (Class IIb)""",
        "metadata": {
            "guideline_id": "acc-aha-hf-2022",
            "title": "ACC/AHA/HFSA Guideline for the Management of Heart Failure 2022",
            "organization": "American College of Cardiology",
            "disease_codes": ["I50.9", "I50.22"],
            "section": "Pharmacologic Treatment of HFrEF",
            "year": 2022,
            "evidence_level": "A",
        }
    },
    {
        "id": "acc-aha-hf-2022-device",
        "text": """ACC/AHA 2022 Heart Failure - Device Therapy in HFrEF:
Implantable Cardioverter-Defibrillator (ICD):
- Recommended for LVEF ≤35%, NYHA II-III on optimal GDMT, with ≥1 year life expectancy (Class I, LOE A)
- For primary prevention of sudden cardiac death (SCD)
- Reassess LVEF after 3-6 months on GDMT before implanting (EF may improve)

Cardiac Resynchronization Therapy (CRT):
- Recommended for LVEF ≤35%, sinus rhythm, LBBB with QRS ≥150 ms, NYHA II-IV (Class I, LOE A)
- Consider for LVEF ≤35%, non-LBBB QRS ≥150 ms (Class IIa)
- CRT-D (combined with ICD) preferred when ICD indication also present

Left Ventricular Assist Device (LVAD):
- Recommended for advanced HF (Stage D) as bridge to transplantation or destination therapy
- Improves survival and functional status in selected patients with LVEF ≤25%

Heart Transplantation:
- Gold standard for end-stage HF refractory to medical and surgical therapy
- Appropriate for highly selected patients with Stage D HF""",
        "metadata": {
            "guideline_id": "acc-aha-hf-2022",
            "title": "ACC/AHA/HFSA Guideline for the Management of Heart Failure 2022",
            "organization": "American College of Cardiology",
            "disease_codes": ["I50.9", "I50.22", "I50.31"],
            "section": "Device Therapy",
            "year": 2022,
            "evidence_level": "A",
        }
    },

    # --------------------------------------------------------
    # KDIGO 2024 CKD Guidelines
    # --------------------------------------------------------
    {
        "id": "kdigo-2024-ckd-definition-staging",
        "text": """KDIGO 2024 - CKD Definition, Staging, and Risk Stratification:
Chronic kidney disease is defined as abnormalities of kidney structure or function present for >3 months.

Criteria (at least one present >3 months):
- Markers of kidney damage: albuminuria (ACR ≥30 mg/g), abnormal sediment, electrolyte/tubular disorders, histological abnormalities, structural abnormalities, kidney transplant history
- GFR <60 mL/min/1.73m2

GFR categories (G stages):
G1: ≥90 (normal or high)
G2: 60-89 (mildly decreased)
G3a: 45-59 (mild to moderately decreased)
G3b: 30-44 (moderately to severely decreased)
G4: 15-29 (severely decreased)
G5: <15 (kidney failure)

Albuminuria categories (A stages):
A1: <30 mg/g (normal or mildly increased)
A2: 30-300 mg/g (moderately increased)
A3: >300 mg/g (severely increased)

Risk stratification uses combined G and A stages (heat map):
- Low risk: G1-G2, A1
- Moderately increased: G1-G2, A2; G3a, A1
- High risk: G3a-G3b, A2; G3b-G4, A1
- Very high risk: G4-G5, any A; any G, A3""",
        "metadata": {
            "guideline_id": "kdigo-2024-ckd",
            "title": "KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
            "organization": "Kidney Disease: Improving Global Outcomes",
            "disease_codes": ["N18.3", "N18.4", "N18.5"],
            "section": "Definition and Staging",
            "year": 2024,
            "evidence_level": "1A",
        }
    },
    {
        "id": "kdigo-2024-ckd-progression-slowing",
        "text": """KDIGO 2024 - Slowing CKD Progression:
Evidence-based strategies to slow CKD progression:

1. Blood pressure control:
   - Target systolic BP <120 mmHg (using standardized measurement) - Grade 1B
   - ACE inhibitor or ARB for patients with CKD + diabetes + albuminuria ≥30 mg/g
   - ACE inhibitor or ARB for CKD without diabetes with albuminuria ≥300 mg/g

2. SGLT2 inhibitors (Grade 1A):
   - Recommended for adults with CKD and T2DM with eGFR ≥20
   - Recommended for adults with CKD and heart failure with eGFR ≥20
   - Suggested for other CKD patients with eGFR ≥20 (Grade 2B)
   - Continue even if eGFR falls <20 unless clinical reasons to stop

3. Finerenone (nonsteroidal MRA):
   - Recommended for T2DM + CKD with UACR ≥30 mg/g despite optimized RAS blockade
   - eGFR threshold: 25-75 mL/min/1.73m2 at initiation
   - Monitor potassium (risk of hyperkalemia)

4. GLP-1 receptor agonists:
   - Suggested for T2DM with CKD when additional glucose-lowering or CV protection needed
   - Semaglutide has shown kidney protection in FLOW trial

5. Lifestyle modifications:
   - Protein intake 0.8 g/kg/day for nondialysis CKD
   - Sodium <2 g/day (5 g NaCl)
   - Physical activity as tolerated
   - Smoking cessation""",
        "metadata": {
            "guideline_id": "kdigo-2024-ckd",
            "title": "KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
            "organization": "Kidney Disease: Improving Global Outcomes",
            "disease_codes": ["N18.3", "N18.4"],
            "section": "Slowing CKD Progression",
            "year": 2024,
            "evidence_level": "1A",
        }
    },

    # --------------------------------------------------------
    # GOLD 2024 COPD Guidelines
    # --------------------------------------------------------
    {
        "id": "gold2024-copd-diagnosis",
        "text": """GOLD 2024 - Diagnosis and Assessment of COPD:
COPD diagnosis requires: post-bronchodilator FEV1/FVC <0.70 AND compatible symptoms/exposures.
Spirometry is mandatory for diagnosis; clinical diagnosis alone is insufficient.

GOLD spirometric grades (post-bronchodilator):
GOLD 1 (Mild): FEV1 ≥80% predicted
GOLD 2 (Moderate): 50% ≤ FEV1 < 80% predicted
GOLD 3 (Severe): 30% ≤ FEV1 < 50% predicted
GOLD 4 (Very Severe): FEV1 < 30% predicted

Symptom assessment:
- mMRC dyspnea scale: 0-4 (0=dyspnea only with strenuous exercise; 4=too breathless to leave house)
- CAT (COPD Assessment Test): 0-40 (≥10 = high symptom burden)

Exacerbation history: Prior year exacerbations
- Low risk: 0-1 exacerbations NOT requiring hospitalization
- High risk: ≥2 exacerbations OR ≥1 leading to hospitalization

GOLD ABE classification (2023 update):
Group A: Low symptoms (mMRC 0-1, CAT <10), low risk
Group B: High symptoms (mMRC ≥2, CAT ≥10), low risk
Group E: High exacerbation risk (any symptom level)""",
        "metadata": {
            "guideline_id": "gold-copd-2024",
            "title": "GOLD 2024 Global Strategy for Prevention, Diagnosis and Management of COPD",
            "organization": "Global Initiative for Chronic Obstructive Lung Disease",
            "disease_codes": ["J44.1", "J44.0"],
            "section": "Diagnosis and Assessment",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "gold2024-copd-pharmacotherapy",
        "text": """GOLD 2024 - Pharmacotherapy for Stable COPD:
Initial therapy (based on GOLD group):
Group A: One bronchodilator (SABA, SAMA, LABA, or LAMA) as needed
Group B: LAMA (preferred) or LABA; if symptoms severe, LAMA+LABA combination
Group E: LAMA+LABA preferred; if blood eosinophils ≥300 cells/mcL, consider LAMA+LABA+ICS (triple therapy)

Escalation principles:
1. Start with LAMA for most Group B/E patients
2. Escalate to LAMA+LABA for persistent dyspnea
3. Add ICS only for frequent exacerbations + blood eosinophils ≥100 cells/mcL
4. ICS monotherapy NOT recommended (lower benefit, higher pneumonia risk)
5. Consider reducing ICS if eosinophils <100 or history of pneumonia

Key medications:
- LAMA: tiotropium, umeclidinium, aclidinium, glycopyrronium
- LABA: salmeterol, formoterol, indacaterol, olodaterol
- ICS: fluticasone, budesonide, beclomethasone
- Triple combos: fluticasone/umeclidinium/vilanterol (Trelegy); budesonide/glycopyrronium/formoterol (Breztri)

Non-pharmacologic:
- Smoking cessation (most effective intervention at all stages)
- Pulmonary rehabilitation for GOLD 2-4 or recent exacerbation
- Influenza vaccine annually; pneumococcal and COVID vaccines
- Oxygen therapy for resting SpO2 ≤88% at rest""",
        "metadata": {
            "guideline_id": "gold-copd-2024",
            "title": "GOLD 2024 Global Strategy for Prevention, Diagnosis and Management of COPD",
            "organization": "Global Initiative for Chronic Obstructive Lung Disease",
            "disease_codes": ["J44.1"],
            "section": "Stable COPD Pharmacotherapy",
            "year": 2024,
            "evidence_level": "A",
        }
    },
    {
        "id": "gold2024-copd-exacerbation",
        "text": """GOLD 2024 - COPD Exacerbation Management:
Exacerbation definition: Acute worsening of respiratory symptoms beyond normal day-to-day variation,
leading to change in medication.

Severity classification:
- Mild: Treated with short-acting bronchodilators only
- Moderate: Treated with SABDs plus antibiotics and/or oral corticosteroids
- Severe: Requires hospitalization or ED visit; may indicate respiratory failure

Treatment of exacerbations:
1. Short-acting bronchodilators: SABA ± SAMA (ipratropium) are first-line
2. Systemic corticosteroids: Prednisone 40 mg/day for 5 days
3. Antibiotics: For purulent sputum, increased sputum, or increased dyspnea (Anthonisen criteria)
   - Amoxicillin/clavulanate, azithromycin, or doxycycline for uncomplicated
   - Fluoroquinolone for complicated or severe
4. Supplemental oxygen: Target SpO2 88-92% (avoid hyperoxia)
5. NIV (BiPAP): For respiratory acidosis (pH <7.35) or respiratory failure
6. Hospital admission indications: Severe symptoms, new cyanosis, peripheral edema, acute confusion, no home support

Prevention of future exacerbations:
- Optimize maintenance inhaler therapy
- Roflumilast (PDE4 inhibitor) for FEV1 <50%, chronic bronchitis, frequent exacerbations
- Azithromycin 250 mg daily for selected patients""",
        "metadata": {
            "guideline_id": "gold-copd-2024",
            "title": "GOLD 2024 Global Strategy for Prevention, Diagnosis and Management of COPD",
            "organization": "Global Initiative for Chronic Obstructive Lung Disease",
            "disease_codes": ["J44.1"],
            "section": "Exacerbation Management",
            "year": 2024,
            "evidence_level": "A",
        }
    },

    # --------------------------------------------------------
    # ACC/AHA 2023 Atrial Fibrillation Guidelines
    # --------------------------------------------------------
    {
        "id": "acc-aha-afib-2023-stroke-risk",
        "text": """ACC/AHA 2023 Atrial Fibrillation - Stroke Risk Assessment:
CHA2DS2-VASc Scoring (for nonvalvular AF):
C - Congestive heart failure (or LVEF ≤40%): 1 point
H - Hypertension: 1 point
A2 - Age ≥75 years: 2 points
D - Diabetes mellitus: 1 point
S2 - Stroke/TIA history: 2 points
V - Vascular disease (prior MI, PAD, aortic plaque): 1 point
A - Age 65-74 years: 1 point
Sc - Sex category (female): 1 point

Anticoagulation recommendations:
- CHA2DS2-VASc ≥2 (men) or ≥3 (women): Oral anticoagulation recommended (Class I)
- CHA2DS2-VASc = 1 (men) or = 2 (women): Anticoagulation may be considered (Class IIb)
- CHA2DS2-VASc = 0 (men) or = 1 (women): No anticoagulation (Class III - harm)

DOAC vs Warfarin:
- DOACs (apixaban, rivaroxaban, dabigatran, edoxaban) preferred over warfarin for nonvalvular AF
- Warfarin preferred for: mechanical heart valve, moderate/severe mitral stenosis
- Apixaban has the lowest major bleeding risk among DOACs in meta-analyses

Annual stroke risk by CHA2DS2-VASc:
Score 0: ~0.2%; Score 1: ~0.6%; Score 2: ~2.2%; Score 3: ~3.2%; Score 4: ~4.0%; Score 5: ~6.7%""",
        "metadata": {
            "guideline_id": "acc-aha-afib-2023",
            "title": "ACC/AHA 2023 Atrial Fibrillation Guideline",
            "organization": "American College of Cardiology",
            "disease_codes": ["I48.91"],
            "section": "Stroke Risk Assessment and Prevention",
            "year": 2023,
            "evidence_level": "I",
        }
    },
    {
        "id": "acc-aha-afib-2023-rate-rhythm",
        "text": """ACC/AHA 2023 Atrial Fibrillation - Rate vs Rhythm Control:
Rate control strategy:
- Initial approach for most patients with persistent AF with adequate symptom control
- Target resting heart rate: <110 bpm (lenient) or <80 bpm (strict) - both acceptable
- Rate control medications (in order of preference):
  1. Beta-blockers (metoprolol, atenolol, carvedilol) - first-line
  2. Non-dihydropyridine CCBs (diltiazem, verapamil) - avoid in HFrEF
  3. Digoxin - for sedentary patients or adjunct
  4. Amiodarone - for refractory cases only (due to toxicity)

Rhythm control strategy:
- Preferred when: significant symptoms, younger patients, first-detected AF, or heart failure
- EAST-AFNET 4 trial: Early rhythm control reduces cardiovascular outcomes
- Methods:
  1. Antiarrhythmic drugs (AADs): Flecainide, propafenone (no structural disease); amiodarone, sotalol (HF/CAD)
  2. Catheter ablation: Superior to AADs for maintaining sinus rhythm; preferred over AADs in many patients
  3. Cardioversion (electrical or pharmacological): For acute or symptomatic AF

Long-term outcomes:
- Rhythm control does not eliminate stroke risk (continue anticoagulation)
- Catheter ablation reduces AF burden, hospitalizations, and possibly mortality in HFrEF""",
        "metadata": {
            "guideline_id": "acc-aha-afib-2023",
            "title": "ACC/AHA 2023 Atrial Fibrillation Guideline",
            "organization": "American College of Cardiology",
            "disease_codes": ["I48.91"],
            "section": "Rate and Rhythm Control",
            "year": 2023,
            "evidence_level": "A",
        }
    },
]


# ============================================================
# Embedding functions
# ============================================================
def get_embeddings_batch(texts: list, model: str = EMBEDDING_MODEL) -> list:
    """
    Get embeddings for a batch of texts using OpenAI.
    Returns list of embedding vectors (or empty list if API unavailable).
    """
    if not OPENAI_API_KEY:
        return []

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            input=texts,
            model=model,
            dimensions=EMBEDDING_DIM,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return []


def generate_point_id(chunk_id: str) -> int:
    """Generate a deterministic numeric ID from a string ID."""
    return int(hashlib.md5(chunk_id.encode()).hexdigest()[:16], 16) % (2**63)


# ============================================================
# Main loader
# ============================================================
def load_guidelines(
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    dry_run: bool = False,
    batch_size: int = BATCH_SIZE,
) -> dict:
    """
    Load clinical guidelines into Qdrant.
    Returns dict with counts.
    """
    url = qdrant_url or QDRANT_URL
    api_key = qdrant_api_key or QDRANT_API_KEY

    logger.info("=" * 60)
    logger.info("InHealth Chronic Care - Clinical Guidelines Loader")
    logger.info("=" * 60)
    logger.info(f"Qdrant URL:   {url}")
    logger.info(f"Collection:   {COLLECTION_NAME}")
    logger.info(f"Guidelines:   {len(CLINICAL_GUIDELINES)} chunks")
    logger.info(f"Dry run:      {dry_run}")
    logger.info(f"Embeddings:   {'OpenAI ' + EMBEDDING_MODEL if OPENAI_API_KEY else 'DISABLED (no API key)'}")
    logger.info("")

    results = {
        "total": len(CLINICAL_GUIDELINES),
        "embedded": 0,
        "upserted": 0,
        "skipped": 0,
        "errors": 0,
    }

    if dry_run:
        logger.info("DRY RUN - listing guideline chunks:")
        for item in CLINICAL_GUIDELINES:
            logger.info(f"  [{item['id']}] {item['metadata']['section']} ({item['metadata']['organization']})")
        return results

    if not OPENAI_API_KEY:
        logger.warning(
            "OPENAI_API_KEY not set. Chunks will be upserted WITHOUT embeddings "
            "(payload only, no vector search until embeddings are added)."
        )

    # Connect to Qdrant
    qdrant = QdrantClient(url=url, api_key=api_key, timeout=60)

    # Verify collection exists
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        logger.error(
            f"Collection '{COLLECTION_NAME}' does not exist. "
            "Run seed_vectors.py first to create collections."
        )
        return results

    # Process in batches
    texts = [item["text"] for item in CLINICAL_GUIDELINES]
    all_embeddings = []

    if OPENAI_API_KEY:
        logger.info(f"Generating embeddings in batches of {batch_size}...")
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = get_embeddings_batch(batch)

            if not batch_embeddings:
                logger.error(f"  Batch {i//batch_size + 1} failed - no embeddings returned")
                all_embeddings.extend([None] * len(batch))
            else:
                all_embeddings.extend(batch_embeddings)
                results["embedded"] += len(batch_embeddings)
                logger.info(f"  Batch {i//batch_size + 1}: {len(batch_embeddings)} embeddings generated")

            # Rate limit
            if i + batch_size < len(texts):
                time.sleep(RATE_LIMIT_DELAY)
    else:
        # Use zero vectors as placeholder (allows metadata storage without search)
        all_embeddings = [[0.0] * EMBEDDING_DIM] * len(CLINICAL_GUIDELINES)
        logger.warning("Using zero vectors (no API key) - similarity search will not work")

    # Build and upsert points
    logger.info("")
    logger.info("Upserting points to Qdrant...")

    points = []
    for i, item in enumerate(CLINICAL_GUIDELINES):
        embedding = all_embeddings[i] if i < len(all_embeddings) else None
        if embedding is None:
            results["skipped"] += 1
            continue

        point = PointStruct(
            id=generate_point_id(item["id"]),
            vector=embedding,
            payload={
                "chunk_id": item["id"],
                "text": item["text"],
                "text_length": len(item["text"]),
                **item["metadata"],
            }
        )
        points.append(point)

    # Upsert in batches
    upsert_batch_size = 50
    for i in range(0, len(points), upsert_batch_size):
        batch = points[i:i + upsert_batch_size]
        try:
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
                wait=True,
            )
            results["upserted"] += len(batch)
            logger.info(f"  Upserted batch {i//upsert_batch_size + 1}: {len(batch)} points")
        except Exception as e:
            logger.error(f"  Upsert batch failed: {e}")
            results["errors"] += len(batch)

    # Final stats
    collection_info = qdrant.get_collection(COLLECTION_NAME)
    logger.info("")
    logger.info("=" * 60)
    logger.info("Guidelines Loading Complete")
    logger.info("=" * 60)
    logger.info(f"  Total chunks:     {results['total']}")
    logger.info(f"  Embedded:         {results['embedded']}")
    logger.info(f"  Upserted:         {results['upserted']}")
    logger.info(f"  Skipped:          {results['skipped']}")
    logger.info(f"  Errors:           {results['errors']}")
    logger.info(f"  Collection total: {collection_info.vectors_count or 0} vectors")

    return results


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Load clinical guidelines into InHealth Qdrant vector store"
    )
    parser.add_argument("--url", default=QDRANT_URL, help="Qdrant URL")
    parser.add_argument("--api-key", default=QDRANT_API_KEY, help="Qdrant API key")
    parser.add_argument("--dry-run", action="store_true", help="List chunks without loading")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Embedding batch size")

    args = parser.parse_args()

    results = load_guidelines(
        qdrant_url=args.url,
        qdrant_api_key=args.api_key,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    success = results["errors"] == 0
    sys.exit(0 if success else 1)
