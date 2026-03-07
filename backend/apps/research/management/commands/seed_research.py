"""
Django management command to seed clinical trials and medical evidence.

Usage:
  python manage.py seed_research
  docker compose exec django python manage.py seed_research
"""

import random

from django.core.management.base import BaseCommand

from apps.research.models import ClinicalTrial, MedicalEvidence


CLINICAL_TRIALS = [
    {
        "nct_id": "NCT05432101",
        "title": "SGLT2 Inhibitor vs. GLP-1 Receptor Agonist for Type 2 Diabetes with CKD Stage 3",
        "brief_summary": "A randomized, double-blind, phase 3 trial comparing Dapagliflozin 10mg vs Semaglutide 1mg weekly in patients with Type 2 Diabetes and CKD Stage 3 (eGFR 30-59). Primary endpoint is eGFR decline over 36 months. Secondary endpoints include A1c reduction, cardiovascular events, and kidney failure.",
        "condition": "Type 2 Diabetes Mellitus, Chronic Kidney Disease",
        "phase": "Phase 3",
        "sponsor": "National Kidney Foundation / AstraZeneca",
        "primary_outcome": "Rate of eGFR decline at 36 months",
        "enrollment_target": 4200,
        "start_date": "2024-03-15",
        "completion_date": "2028-06-30",
        "eligibility_criteria": {"inclusion": ["Age 40-80", "T2DM diagnosis", "eGFR 30-59", "A1c 7.0-11.0%"], "exclusion": ["Type 1 DM", "Active dialysis", "Kidney transplant"], "age_min": 40, "age_max": 80},
        "locations": [{"facility": "Cleveland Clinic", "city": "Cleveland", "state": "OH", "country": "US"}],
        "contact": {"name": "Dr. Sarah Chen", "email": "research@ckd-trial.org", "phone": "800-555-0101"},
    },
    {
        "nct_id": "NCT05876234",
        "title": "Early Empagliflozin Initiation in Acute Heart Failure (EMPA-ACUTE)",
        "brief_summary": "Multicenter RCT evaluating early (within 24h of admission) Empagliflozin 10mg vs placebo in acute decompensated heart failure. Primary endpoints: days alive out of hospital at 60 days, change in NT-proBNP. Includes subgroup analysis for patients with concurrent CKD and diabetes.",
        "condition": "Heart Failure, Acute Decompensated",
        "phase": "Phase 3",
        "sponsor": "Boehringer Ingelheim / American Heart Association",
        "primary_outcome": "Days alive and out of hospital at 60 days",
        "enrollment_target": 3600,
        "start_date": "2024-01-10",
        "completion_date": "2027-12-31",
        "eligibility_criteria": {"inclusion": ["Age 18+", "Acute HF requiring hospitalization", "NT-proBNP >600 pg/mL", "eGFR >20"], "exclusion": ["Cardiogenic shock", "Type 1 DM", "Prior SGLT2i use"], "age_min": 18, "age_max": 90},
        "locations": [{"facility": "Mayo Clinic", "city": "Rochester", "state": "MN", "country": "US"}],
        "contact": {"name": "Dr. James Morton", "email": "empa-acute@mayo.edu", "phone": "507-555-0102"},
    },
    {
        "nct_id": "NCT06012345",
        "title": "AI-Guided Antihypertensive Titration vs Standard Care (AI-HTN)",
        "brief_summary": "Pragmatic RCT comparing AI-assisted medication titration algorithm vs standard guideline-based management for resistant hypertension. The AI system analyzes home BP readings, medication history, and patient characteristics to recommend personalized antihypertensive adjustments.",
        "condition": "Hypertension, Resistant",
        "phase": "Phase 4",
        "sponsor": "NIH / Google Health",
        "primary_outcome": "Proportion achieving BP <130/80 mmHg at 12 months",
        "enrollment_target": 2400,
        "start_date": "2024-06-01",
        "completion_date": "2026-12-31",
        "eligibility_criteria": {"inclusion": ["Age 30-80", "Resistant HTN on 3+ medications", "Home BP monitor capable"], "exclusion": ["Secondary HTN", "CKD Stage 5", "Pregnancy"], "age_min": 30, "age_max": 80},
        "locations": [{"facility": "Johns Hopkins Medical Center", "city": "Baltimore", "state": "MD", "country": "US"}],
        "contact": {"name": "Dr. Lisa Park", "email": "ai-htn@jhu.edu", "phone": "410-555-0103"},
    },
    {
        "nct_id": "NCT05998877",
        "title": "Continuous Glucose Monitoring-Driven Insulin Optimization in Hospitalized T2DM Patients",
        "brief_summary": "Evaluating CGM-guided insulin dosing versus point-of-care glucose testing for glycemic management in hospitalized patients with Type 2 Diabetes. Focuses on time in range (70-180 mg/dL), hypoglycemia events, and length of stay.",
        "condition": "Type 2 Diabetes Mellitus",
        "phase": "Phase 3",
        "sponsor": "Dexcom / Eli Lilly",
        "primary_outcome": "Time in glucose range 70-180 mg/dL during hospitalization",
        "enrollment_target": 1800,
        "start_date": "2024-04-01",
        "completion_date": "2026-09-30",
        "eligibility_criteria": {"inclusion": ["Age 18+", "T2DM on insulin", "Expected stay >48h"], "exclusion": ["DKA", "ICU admission", "Pregnancy"], "age_min": 18, "age_max": 85},
        "locations": [{"facility": "UCSF Medical Center", "city": "San Francisco", "state": "CA", "country": "US"}],
        "contact": {"name": "Dr. Ana Rivera", "email": "cgm-study@ucsf.edu", "phone": "415-555-0104"},
    },
    {
        "nct_id": "NCT06123456",
        "title": "Dual Bronchodilator + ICS vs Triple Therapy in Severe COPD with Frequent Exacerbations",
        "brief_summary": "Head-to-head comparison of LAMA/LABA vs LAMA/LABA/ICS triple therapy in COPD patients with >=2 moderate or >=1 severe exacerbation in prior year. Evaluates exacerbation rate, FEV1 change, pneumonia risk, and patient-reported outcomes over 52 weeks.",
        "condition": "Chronic Obstructive Pulmonary Disease",
        "phase": "Phase 3",
        "sponsor": "GlaxoSmithKline / GOLD Foundation",
        "primary_outcome": "Annual rate of moderate-to-severe COPD exacerbations",
        "enrollment_target": 5400,
        "start_date": "2024-02-15",
        "completion_date": "2026-06-30",
        "eligibility_criteria": {"inclusion": ["Age 40+", "COPD GOLD Stage D", ">=2 exacerbations in prior year", "FEV1 <50% predicted"], "exclusion": ["Active asthma", "Current pneumonia", "Lung cancer"], "age_min": 40, "age_max": 85},
        "locations": [{"facility": "Duke University Medical Center", "city": "Durham", "state": "NC", "country": "US"}],
        "contact": {"name": "Dr. Michael Brooks", "email": "copd-triple@duke.edu", "phone": "919-555-0105"},
    },
    {
        "nct_id": "NCT06234567",
        "title": "Catheter Ablation vs. Rate Control in Elderly Patients with Persistent Atrial Fibrillation",
        "brief_summary": "Randomized trial comparing catheter ablation strategy vs rate control with beta-blockers in patients aged 70+ with persistent AFib. Primary endpoint is composite of stroke, heart failure hospitalization, and death at 3 years. Includes quality of life and cognitive function assessments.",
        "condition": "Atrial Fibrillation",
        "phase": "Phase 3",
        "sponsor": "American College of Cardiology / Medtronic",
        "primary_outcome": "Composite of stroke, HF hospitalization, and all-cause death at 3 years",
        "enrollment_target": 3000,
        "start_date": "2024-05-01",
        "completion_date": "2028-12-31",
        "eligibility_criteria": {"inclusion": ["Age 70+", "Persistent AFib >7 days", "CHA2DS2-VASc >=2"], "exclusion": ["Prior ablation", "Valvular AFib", "Life expectancy <1 year"], "age_min": 70, "age_max": 95},
        "locations": [{"facility": "Cedars-Sinai Medical Center", "city": "Los Angeles", "state": "CA", "country": "US"}],
        "contact": {"name": "Dr. Robert Kim", "email": "afib-elderly@cedars-sinai.org", "phone": "310-555-0106"},
    },
    {
        "nct_id": "NCT06345678",
        "title": "Finerenone + SGLT2i Combination Therapy for Diabetic Kidney Disease",
        "brief_summary": "Evaluating the safety and efficacy of adding Finerenone to existing SGLT2 inhibitor therapy in patients with T2DM and albuminuric CKD. Assesses kidney composite endpoint (sustained eGFR decline >40%, kidney failure, renal death) and cardiovascular outcomes.",
        "condition": "Diabetic Kidney Disease, Type 2 Diabetes",
        "phase": "Phase 3",
        "sponsor": "Bayer AG / KDIGO",
        "primary_outcome": "Kidney composite endpoint at 36 months",
        "enrollment_target": 6000,
        "start_date": "2024-07-01",
        "completion_date": "2029-06-30",
        "eligibility_criteria": {"inclusion": ["Age 18+", "T2DM", "eGFR 25-75", "UACR 30-5000 mg/g", "On SGLT2i >3 months"], "exclusion": ["Known AKI in past 12 weeks", "Potassium >5.0", "Adrenal insufficiency"], "age_min": 18, "age_max": 80},
        "locations": [{"facility": "Massachusetts General Hospital", "city": "Boston", "state": "MA", "country": "US"}],
        "contact": {"name": "Dr. Emily Watson", "email": "dkd-combo@mgh.harvard.edu", "phone": "617-555-0107"},
    },
    {
        "nct_id": "NCT06456789",
        "title": "Tirzepatide vs Insulin Glargine for T2DM with Cardiovascular Disease",
        "brief_summary": "Comparing Tirzepatide (dual GIP/GLP-1 agonist) vs Insulin Glargine in T2DM patients with established ASCVD. Evaluates A1c reduction, weight loss, MACE (major adverse cardiovascular events), and heart failure hospitalization over 104 weeks.",
        "condition": "Type 2 Diabetes Mellitus, Cardiovascular Disease",
        "phase": "Phase 3",
        "sponsor": "Eli Lilly / American Diabetes Association",
        "primary_outcome": "A1c change from baseline at 52 weeks and MACE at 104 weeks",
        "enrollment_target": 8500,
        "start_date": "2024-09-01",
        "completion_date": "2028-03-31",
        "eligibility_criteria": {"inclusion": ["Age 40+", "T2DM", "A1c 7.5-12%", "Established ASCVD or high CV risk"], "exclusion": ["Type 1 DM", "History of pancreatitis", "MTC family history"], "age_min": 40, "age_max": 80},
        "locations": [{"facility": "Mount Sinai Hospital", "city": "New York", "state": "NY", "country": "US"}],
        "contact": {"name": "Dr. Priya Patel", "email": "tirz-cv@mountsinai.org", "phone": "212-555-0108"},
    },
]

MEDICAL_EVIDENCE = [
    {
        "pubmed_id": "38901234",
        "title": "SGLT2 Inhibitors Reduce All-Cause Mortality in Heart Failure Regardless of Diabetes Status: Updated Meta-Analysis of 15 RCTs",
        "abstract": "Background: SGLT2 inhibitors have emerged as a cornerstone therapy for heart failure. We conducted an updated systematic review and meta-analysis of 15 randomized controlled trials (n=45,913) evaluating SGLT2 inhibitors in heart failure patients. Results: SGLT2i reduced all-cause mortality (HR 0.87, 95% CI 0.82-0.93, p<0.001), cardiovascular death (HR 0.86, 95% CI 0.80-0.93), and heart failure hospitalization (HR 0.72, 95% CI 0.67-0.77). Benefits were consistent regardless of diabetes status, ejection fraction, and baseline eGFR. Conclusion: SGLT2 inhibitors should be considered for all heart failure patients regardless of diabetes status.",
        "authors": ["Chen WJ", "Patel SK", "Morrison A", "Williams R", "Thompson LM"],
        "journal": "Journal of the American College of Cardiology",
        "year": 2024,
        "doi": "10.1016/j.jacc.2024.03.001",
        "evidence_level": "A",
        "conditions": ["I50.9", "E11.9"],
        "mesh_terms": ["SGLT2 Inhibitors", "Heart Failure", "Meta-Analysis", "Mortality"],
        "citation_count": 342,
    },
    {
        "pubmed_id": "38765432",
        "title": "ADA 2024 Standards of Care: Updated Glycemic Targets and Treatment Algorithms for Type 2 Diabetes",
        "abstract": "The American Diabetes Association released updated 2024 Standards of Medical Care. Key changes include: individualized A1c targets (generally <7% but <8% for elderly/frail), earlier use of GLP-1 RAs and SGLT2i independent of A1c, emphasis on cardiorenal protection, and integration of CGM data for treatment decisions. Weight management is now a primary treatment goal alongside glycemic control. DSME recommended for all newly diagnosed patients.",
        "authors": ["American Diabetes Association Professional Practice Committee"],
        "journal": "Diabetes Care",
        "year": 2024,
        "doi": "10.2337/dc24-S001",
        "evidence_level": "A",
        "conditions": ["E11.9"],
        "mesh_terms": ["Type 2 Diabetes", "Clinical Practice Guideline", "Glycemic Control", "ADA Standards"],
        "citation_count": 1250,
    },
    {
        "pubmed_id": "38654321",
        "title": "KDIGO 2024 Clinical Practice Guideline for CKD Evaluation and Management",
        "abstract": "Updated KDIGO guideline emphasizes: (1) eGFR and UACR for CKD staging, (2) SGLT2 inhibitors for all CKD patients with eGFR 20-75 and albuminuria, (3) Finerenone for T2DM with albuminuric CKD on max RAS blockade, (4) BP target <120 mmHg systolic in CKD without diabetes, (5) Avoid NSAIDs in CKD Stage 3+, (6) Renal dosing adjustments for metformin when eGFR <30. New evidence supports combination of SGLT2i + Finerenone for additive kidney protection.",
        "authors": ["Kidney Disease: Improving Global Outcomes (KDIGO) CKD Work Group"],
        "journal": "Kidney International",
        "year": 2024,
        "doi": "10.1016/j.kint.2024.01.003",
        "evidence_level": "A",
        "conditions": ["N18.3", "E11.9"],
        "mesh_terms": ["Chronic Kidney Disease", "Clinical Practice Guideline", "SGLT2 Inhibitors", "Finerenone"],
        "citation_count": 890,
    },
    {
        "pubmed_id": "38543210",
        "title": "Intensive Blood Pressure Control in CKD: The SPRINT-CKD Subgroup Analysis",
        "abstract": "Post-hoc analysis of the SPRINT trial focusing on 2,646 participants with CKD (eGFR 20-59). Intensive BP target (<120 mmHg systolic) vs standard (<140 mmHg) reduced composite cardiovascular events by 24% (HR 0.76, 95% CI 0.63-0.92) without accelerating eGFR decline. AKI events were slightly higher in the intensive group (4.1% vs 2.5%) but mostly reversible. Results support intensive BP control in CKD patients, consistent with KDIGO 2024 recommendations.",
        "authors": ["Cheung AK", "Rahman M", "Reboussin DM", "Craven TE", "Greene JB"],
        "journal": "New England Journal of Medicine",
        "year": 2024,
        "doi": "10.1056/NEJMoa2314567",
        "evidence_level": "A",
        "conditions": ["N18.3", "I10"],
        "mesh_terms": ["Blood Pressure", "Chronic Kidney Disease", "SPRINT Trial", "Cardiovascular Events"],
        "citation_count": 567,
    },
    {
        "pubmed_id": "38432109",
        "title": "GOLD 2024 Report: Updated Recommendations for COPD Pharmacotherapy and Exacerbation Prevention",
        "abstract": "The 2024 GOLD Report updates COPD management: (1) Initial therapy based on exacerbation history and dyspnea (groups A-E), (2) Blood eosinophils >300 cells/uL predict ICS response, (3) Triple therapy (LAMA/LABA/ICS) for frequent exacerbators with eosinophilia, (4) Roflumilast or azithromycin for persistent exacerbations despite triple therapy, (5) Biologic therapies (anti-IL-5) now recommended for eosinophilic COPD. Pulmonary rehabilitation remains strongly recommended for all symptomatic patients.",
        "authors": ["Global Initiative for Chronic Obstructive Lung Disease"],
        "journal": "American Journal of Respiratory and Critical Care Medicine",
        "year": 2024,
        "doi": "10.1164/rccm.202401-0001SO",
        "evidence_level": "A",
        "conditions": ["J44.1"],
        "mesh_terms": ["COPD", "Clinical Practice Guideline", "Exacerbation", "Bronchodilators"],
        "citation_count": 723,
    },
    {
        "pubmed_id": "38321098",
        "title": "Machine Learning-Based Early Warning Scores Outperform NEWS2 for In-Hospital Deterioration Prediction",
        "abstract": "Retrospective cohort study of 128,456 hospital admissions comparing ML-based early warning scores (using vital signs, lab results, and nursing notes via NLP) vs National Early Warning Score 2 (NEWS2). The ML model achieved AUROC 0.94 vs 0.78 for NEWS2 in predicting ICU transfer or death within 24 hours. The ML score provided 6.2 hours earlier warning on average. Integrated into EHR workflow, it reduced rapid response team calls by 18% while improving outcomes.",
        "authors": ["Rajkomar A", "Chen GH", "Sutton JP", "Beam AL", "Shah NH"],
        "journal": "Nature Medicine",
        "year": 2024,
        "doi": "10.1038/s41591-024-02901-x",
        "evidence_level": "B",
        "conditions": [],
        "mesh_terms": ["Machine Learning", "Early Warning Score", "Patient Deterioration", "Clinical Decision Support"],
        "citation_count": 456,
    },
    {
        "pubmed_id": "38210987",
        "title": "Polypharmacy and Adverse Drug Events in Elderly Patients with Heart Failure and CKD: A Prospective Cohort Study",
        "abstract": "Prospective cohort of 3,420 patients aged 65+ with HF and CKD (eGFR <60) followed for 2 years. Patients on >=10 medications had 3.2x higher risk of ADE-related hospitalization (HR 3.21, 95% CI 2.45-4.21). Most common ADEs: hyperkalemia (RAS inhibitors + K-sparing diuretics), hypoglycemia (sulfonylureas with declining eGFR), and bleeding (anticoagulants with antiplatelet agents). AI-assisted medication review reduced ADEs by 34% in a nested intervention substudy.",
        "authors": ["Steinman MA", "Hanlon JT", "Boyd CM", "Lund BC", "Schmader KE"],
        "journal": "Annals of Internal Medicine",
        "year": 2024,
        "doi": "10.7326/M24-0456",
        "evidence_level": "B",
        "conditions": ["I50.9", "N18.3"],
        "mesh_terms": ["Polypharmacy", "Adverse Drug Events", "Heart Failure", "Chronic Kidney Disease", "Elderly"],
        "citation_count": 298,
    },
    {
        "pubmed_id": "38109876",
        "title": "ACC/AHA 2023 Guideline for Management of Patients with Chronic Coronary Disease: Focused Update",
        "abstract": "Key updates to CAD management: (1) High-intensity statin for all patients with ASCVD (LDL target <70 mg/dL, consider <55 mg/dL for very high risk), (2) Add ezetimibe or PCSK9 inhibitor if LDL not at goal, (3) SGLT2 inhibitors for CAD patients with T2DM or HF, (4) Colchicine 0.5mg daily for residual inflammatory risk, (5) Dual antiplatelet duration guided by bleeding risk scores, (6) Cardiac rehabilitation strongly recommended. Emphasis on shared decision-making for invasive vs conservative strategy.",
        "authors": ["Virani SS", "Newby LK", "Arnold SV", "Bittner V", "Brewer LC"],
        "journal": "Circulation",
        "year": 2023,
        "doi": "10.1161/CIR.0000000000001168",
        "evidence_level": "A",
        "conditions": ["I25.10"],
        "mesh_terms": ["Coronary Artery Disease", "Clinical Practice Guideline", "Statin Therapy", "Antiplatelet"],
        "citation_count": 934,
    },
    {
        "pubmed_id": "38098765",
        "title": "GLP-1 Receptor Agonists for Weight Management and Cardiovascular Risk Reduction in T2DM: Systematic Review",
        "abstract": "Systematic review of 23 RCTs (n=52,789) evaluating GLP-1 RAs in T2DM. Results: Mean A1c reduction 1.0-1.8%, weight loss 3-7 kg, MACE reduction 14% (HR 0.86, 95% CI 0.80-0.93). Semaglutide 2.4mg achieved greatest weight loss (mean 15.3% body weight). Benefits on kidney outcomes (UACR reduction 24%). Common adverse effects: nausea (15-20%), diarrhea (8-12%). No increased pancreatitis risk. GLP-1 RAs recommended as first-line injectable therapy before insulin in most T2DM patients.",
        "authors": ["Nauck MA", "Quast DR", "Wefers J", "Meier JJ"],
        "journal": "The Lancet Diabetes & Endocrinology",
        "year": 2024,
        "doi": "10.1016/S2213-8587(24)00050-3",
        "evidence_level": "A",
        "conditions": ["E11.9"],
        "mesh_terms": ["GLP-1 Receptor Agonists", "Type 2 Diabetes", "Weight Loss", "Cardiovascular Risk"],
        "citation_count": 678,
    },
    {
        "pubmed_id": "37987654",
        "title": "Remote Patient Monitoring for Chronic Disease Management: Meta-Analysis of 42 RCTs",
        "abstract": "Meta-analysis of 42 RCTs (n=19,456) evaluating RPM interventions for diabetes, hypertension, heart failure, and COPD. RPM reduced: A1c by 0.5% in T2DM, systolic BP by 4.7 mmHg in HTN, HF hospitalizations by 25%, and COPD exacerbations by 21%. AI-augmented RPM systems showed larger effect sizes than basic telemonitoring. Cost-effectiveness analyses showed $2,400 savings per patient-year. Barriers: digital literacy, insurance coverage, alert fatigue in clinical staff.",
        "authors": ["Ding X", "Clifton D", "Ji N", "Lovell NH", "Bonato P"],
        "journal": "The BMJ",
        "year": 2024,
        "doi": "10.1136/bmj-2024-078456",
        "evidence_level": "A",
        "conditions": ["E11.9", "I10", "I50.9", "J44.1"],
        "mesh_terms": ["Remote Patient Monitoring", "Telemedicine", "Chronic Disease", "Digital Health"],
        "citation_count": 412,
    },
    {
        "pubmed_id": "37876543",
        "title": "Metformin Dose Adjustment in CKD: Safety Analysis from the UK Biobank Cohort",
        "abstract": "Analysis of 24,890 metformin users with CKD from the UK Biobank. Key findings: (1) Metformin safe to continue at reduced dose when eGFR 30-45 (max 1000mg/day), (2) Should be stopped when eGFR <30, (3) Risk of lactic acidosis: 3.2 per 100,000 patient-years at eGFR 30-45 vs 2.1 at eGFR >60 (no significant difference), (4) Cardiovascular mortality benefit maintained at eGFR 30-45 (HR 0.78, 95% CI 0.68-0.89). Supports KDIGO recommendation to continue metformin with dose adjustment in moderate CKD.",
        "authors": ["Lalau JD", "Arnouts P", "Sharber A", "De Broe ME"],
        "journal": "Kidney International",
        "year": 2024,
        "doi": "10.1016/j.kint.2024.02.008",
        "evidence_level": "B",
        "conditions": ["N18.3", "E11.9"],
        "mesh_terms": ["Metformin", "Chronic Kidney Disease", "Drug Safety", "Lactic Acidosis"],
        "citation_count": 245,
    },
    {
        "pubmed_id": "37765432",
        "title": "Apixaban Dosing in Atrial Fibrillation with CKD: Real-World Evidence from 86,000 Patients",
        "abstract": "Retrospective cohort study of 86,413 patients with AFib and CKD on apixaban. Appropriate dose reduction (2.5mg BID when >=2 of: age >=80, weight <=60kg, creatinine >=1.5) vs inappropriate underdosing. Inappropriate dose reduction occurred in 17.3% and was associated with 32% higher stroke risk (HR 1.32, 95% CI 1.18-1.47) without reducing bleeding. Full-dose apixaban (5mg BID) was safe down to eGFR 25. Results support careful adherence to dose criteria rather than empiric dose reduction.",
        "authors": ["Yao X", "Shah ND", "Sangaralingham LR", "Gersh BJ", "Noseworthy PA"],
        "journal": "European Heart Journal",
        "year": 2024,
        "doi": "10.1093/eurheartj/ehad789",
        "evidence_level": "B",
        "conditions": ["I48.91", "N18.3"],
        "mesh_terms": ["Apixaban", "Atrial Fibrillation", "Chronic Kidney Disease", "Anticoagulation"],
        "citation_count": 389,
    },
]


class Command(BaseCommand):
    help = "Seed clinical trials and medical evidence for the AI Research interface"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        random.seed(42)

        if options["clear"]:
            ct_del, _ = ClinicalTrial.objects.all().delete()
            me_del, _ = MedicalEvidence.objects.all().delete()
            self.stdout.write(f"Cleared {ct_del} trials, {me_del} evidence records")

        # Seed Clinical Trials
        trial_count = 0
        for t in CLINICAL_TRIALS:
            _, created = ClinicalTrial.objects.get_or_create(
                nct_id=t["nct_id"],
                defaults={
                    "title": t["title"],
                    "brief_summary": t["brief_summary"],
                    "condition": t["condition"],
                    "status": ClinicalTrial.Status.RECRUITING,
                    "phase": t["phase"],
                    "sponsor": t["sponsor"],
                    "primary_outcome": t["primary_outcome"],
                    "enrollment_target": t["enrollment_target"],
                    "start_date": t.get("start_date"),
                    "completion_date": t.get("completion_date"),
                    "eligibility_criteria": t.get("eligibility_criteria", {}),
                    "locations": t.get("locations", []),
                    "contact": t.get("contact", {}),
                },
            )
            if created:
                trial_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {trial_count} clinical trials"))

        # Seed Medical Evidence
        evidence_count = 0
        for e in MEDICAL_EVIDENCE:
            _, created = MedicalEvidence.objects.get_or_create(
                pubmed_id=e["pubmed_id"],
                defaults={
                    "title": e["title"],
                    "abstract": e["abstract"],
                    "authors": e["authors"],
                    "journal": e["journal"],
                    "year": e["year"],
                    "doi": e.get("doi", ""),
                    "evidence_level": e.get("evidence_level", "B"),
                    "conditions": e.get("conditions", []),
                    "mesh_terms": e.get("mesh_terms", []),
                    "citation_count": e.get("citation_count", 0),
                    "relevance_score": round(random.uniform(0.7, 0.98), 2),
                },
            )
            if created:
                evidence_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {evidence_count} medical evidence records"))

        # Summary
        total_trials = ClinicalTrial.objects.count()
        total_evidence = MedicalEvidence.objects.count()
        self.stdout.write(f"\nTotal in database: {total_trials} trials, {total_evidence} evidence records")
