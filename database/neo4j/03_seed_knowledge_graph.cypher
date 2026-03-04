// ============================================================
// InHealth Chronic Care - Clinical Knowledge Graph Seed Data
// Neo4j Cypher script with real clinical data
// ============================================================

// ============================================================
// DISEASES (ICD-10 codes)
// ============================================================
MERGE (d1:Disease {icd10: "E11.9"}) SET d1 += {name: "Type 2 Diabetes Mellitus", category: "Endocrine", icd10_prefix: "E11", chronic: true, description: "Type 2 diabetes mellitus without complications"};
MERGE (d2:Disease {icd10: "I10"}) SET d2 += {name: "Essential Hypertension", category: "Cardiovascular", icd10_prefix: "I10", chronic: true, description: "Primary hypertension"};
MERGE (d3:Disease {icd10: "I25.10"}) SET d3 += {name: "Atherosclerotic Heart Disease", category: "Cardiovascular", icd10_prefix: "I25", chronic: true, description: "Coronary artery disease without angina pectoris"};
MERGE (d4:Disease {icd10: "N18.3"}) SET d4 += {name: "Chronic Kidney Disease Stage 3", category: "Renal", icd10_prefix: "N18", chronic: true, description: "CKD stage 3 (GFR 30-59 mL/min)"};
MERGE (d5:Disease {icd10: "J44.1"}) SET d5 += {name: "COPD with Acute Exacerbation", category: "Pulmonary", icd10_prefix: "J44", chronic: true, description: "Chronic obstructive pulmonary disease with acute exacerbation"};
MERGE (d6:Disease {icd10: "I50.9"}) SET d6 += {name: "Heart Failure Unspecified", category: "Cardiovascular", icd10_prefix: "I50", chronic: true, description: "Heart failure, unspecified"};
MERGE (d7:Disease {icd10: "E78.5"}) SET d7 += {name: "Hyperlipidemia", category: "Endocrine", icd10_prefix: "E78", chronic: true, description: "Hyperlipidemia, unspecified"};
MERGE (d8:Disease {icd10: "E66.9"}) SET d8 += {name: "Obesity", category: "Endocrine", icd10_prefix: "E66", chronic: true, description: "Obesity, unspecified"};
MERGE (d9:Disease {icd10: "J45.909"}) SET d9 += {name: "Asthma", category: "Pulmonary", icd10_prefix: "J45", chronic: true, description: "Unspecified asthma, uncomplicated"};
MERGE (d10:Disease {icd10: "N18.4"}) SET d10 += {name: "Chronic Kidney Disease Stage 4", category: "Renal", icd10_prefix: "N18", chronic: true, description: "CKD stage 4 (GFR 15-29 mL/min)"};
MERGE (d11:Disease {icd10: "N18.5"}) SET d11 += {name: "Chronic Kidney Disease Stage 5", category: "Renal", icd10_prefix: "N18", chronic: true, description: "CKD stage 5 (GFR <15 mL/min)"};
MERGE (d12:Disease {icd10: "I63.9"}) SET d12 += {name: "Cerebral Infarction", category: "Neurological", icd10_prefix: "I63", chronic: false, description: "Cerebral infarction, unspecified (stroke)"};
MERGE (d13:Disease {icd10: "I48.91"}) SET d13 += {name: "Atrial Fibrillation", category: "Cardiovascular", icd10_prefix: "I48", chronic: true, description: "Unspecified atrial fibrillation"};
MERGE (d14:Disease {icd10: "M06.9"}) SET d14 += {name: "Rheumatoid Arthritis", category: "Musculoskeletal", icd10_prefix: "M06", chronic: true, description: "Rheumatoid arthritis, unspecified"};
MERGE (d15:Disease {icd10: "K21.0"}) SET d15 += {name: "GERD with Esophagitis", category: "Gastrointestinal", icd10_prefix: "K21", chronic: true, description: "Gastro-esophageal reflux disease with esophagitis"};
MERGE (d16:Disease {icd10: "F32.9"}) SET d16 += {name: "Major Depressive Disorder", category: "Mental Health", icd10_prefix: "F32", chronic: true, description: "Major depressive disorder, single episode, unspecified"};
MERGE (d17:Disease {icd10: "F41.1"}) SET d17 += {name: "Generalized Anxiety Disorder", category: "Mental Health", icd10_prefix: "F41", chronic: true, description: "Generalized anxiety disorder"};
MERGE (d18:Disease {icd10: "E11.65"}) SET d18 += {name: "T2DM with Hyperglycemia", category: "Endocrine", icd10_prefix: "E11", chronic: true, description: "Type 2 diabetes mellitus with hyperglycemia"};
MERGE (d19:Disease {icd10: "E11.40"}) SET d19 += {name: "T2DM with Diabetic Neuropathy", category: "Endocrine", icd10_prefix: "E11", chronic: true, description: "Type 2 diabetes mellitus with diabetic neuropathy, unspecified"};
MERGE (d20:Disease {icd10: "E11.319"}) SET d20 += {name: "T2DM with Diabetic Retinopathy", category: "Endocrine", icd10_prefix: "E11", chronic: true, description: "Type 2 diabetes mellitus with unspecified diabetic retinopathy"};
MERGE (d21:Disease {icd10: "E11.21"}) SET d21 += {name: "T2DM with Diabetic Nephropathy", category: "Endocrine", icd10_prefix: "E11", chronic: true, description: "Type 2 diabetes mellitus with diabetic nephropathy"};
MERGE (d22:Disease {icd10: "I73.9"}) SET d22 += {name: "Peripheral Vascular Disease", category: "Cardiovascular", icd10_prefix: "I73", chronic: true, description: "Peripheral vascular disease, unspecified"};
MERGE (d23:Disease {icd10: "G47.33"}) SET d23 += {name: "Obstructive Sleep Apnea", category: "Pulmonary", icd10_prefix: "G47", chronic: true, description: "Obstructive sleep apnea (adult)"};
MERGE (d24:Disease {icd10: "K76.0"}) SET d24 += {name: "Fatty Liver Disease", category: "Gastrointestinal", icd10_prefix: "K76", chronic: true, description: "Fatty change of liver, not elsewhere classified (NAFLD)"};
MERGE (d25:Disease {icd10: "M81.0"}) SET d25 += {name: "Osteoporosis", category: "Musculoskeletal", icd10_prefix: "M81", chronic: true, description: "Age-related osteoporosis without current pathological fracture"};
MERGE (d26:Disease {icd10: "I21.9"}) SET d26 += {name: "STEMI", category: "Cardiovascular", icd10_prefix: "I21", chronic: false, description: "Acute ST elevation myocardial infarction"};
MERGE (d27:Disease {icd10: "N40.0"}) SET d27 += {name: "Benign Prostatic Hyperplasia", category: "Urological", icd10_prefix: "N40", chronic: true, description: "Benign prostatic hyperplasia without lower urinary tract symptoms"};
MERGE (d28:Disease {icd10: "E03.9"}) SET d28 += {name: "Hypothyroidism", category: "Endocrine", icd10_prefix: "E03", chronic: true, description: "Hypothyroidism, unspecified"};
MERGE (d29:Disease {icd10: "M79.3"}) SET d29 += {name: "Fibromyalgia", category: "Musculoskeletal", icd10_prefix: "M79", chronic: true, description: "Panniculitis, unspecified / Fibromyalgia"};
MERGE (d30:Disease {icd10: "L40.9"}) SET d30 += {name: "Psoriasis", category: "Dermatological", icd10_prefix: "L40", chronic: true, description: "Psoriasis, unspecified"};
MERGE (d31:Disease {icd10: "I50.22"}) SET d31 += {name: "Systolic Heart Failure Chronic", category: "Cardiovascular", icd10_prefix: "I50", chronic: true, description: "Chronic systolic (congestive) heart failure"};
MERGE (d32:Disease {icd10: "N18.2"}) SET d32 += {name: "Chronic Kidney Disease Stage 2", category: "Renal", icd10_prefix: "N18", chronic: true, description: "CKD stage 2 (GFR 60-89 mL/min)"};

// ============================================================
// MEDICATIONS (RxNorm codes)
// ============================================================

// Diabetes medications
MERGE (m1:Medication {rxnorm: "6809"}) SET m1 += {name: "Metformin", generic_name: "metformin", brand_names: "Glucophage,Glumetza,Fortamet", drug_class: "Biguanide", route: "oral", controlled: false, high_alert: false};
MERGE (m2:Medication {rxnorm: "1545146"}) SET m2 += {name: "Empagliflozin", generic_name: "empagliflozin", brand_names: "Jardiance", drug_class: "SGLT2 Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m3:Medication {rxnorm: "1100699"}) SET m3 += {name: "Linagliptin", generic_name: "linagliptin", brand_names: "Tradjenta", drug_class: "DPP-4 Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m4:Medication {rxnorm: "203289"}) SET m4 += {name: "Sitagliptin", generic_name: "sitagliptin", brand_names: "Januvia", drug_class: "DPP-4 Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m5:Medication {rxnorm: "2200625"}) SET m5 += {name: "Semaglutide oral", generic_name: "semaglutide", brand_names: "Rybelsus,Ozempic,Wegovy", drug_class: "GLP-1 Agonist", route: "oral/injectable", controlled: false, high_alert: false};
MERGE (m6:Medication {rxnorm: "274783"}) SET m6 += {name: "Insulin Glargine", generic_name: "insulin glargine", brand_names: "Lantus,Basaglar,Toujeo", drug_class: "Long-acting Insulin", route: "subcutaneous", controlled: false, high_alert: true};
MERGE (m7:Medication {rxnorm: "86009"}) SET m7 += {name: "Insulin Lispro", generic_name: "insulin lispro", brand_names: "Humalog,Admelog", drug_class: "Rapid-acting Insulin", route: "subcutaneous", controlled: false, high_alert: true};
MERGE (m8:Medication {rxnorm: "1372736"}) SET m8 += {name: "Dulaglutide", generic_name: "dulaglutide", brand_names: "Trulicity", drug_class: "GLP-1 Agonist", route: "injectable", controlled: false, high_alert: false};
MERGE (m9:Medication {rxnorm: "1860485"}) SET m9 += {name: "Canagliflozin", generic_name: "canagliflozin", brand_names: "Invokana", drug_class: "SGLT2 Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m10:Medication {rxnorm: "1486436"}) SET m10 += {name: "Dapagliflozin", generic_name: "dapagliflozin", brand_names: "Farxiga,Forxiga", drug_class: "SGLT2 Inhibitor", route: "oral", controlled: false, high_alert: false};

// Cardiovascular medications
MERGE (m11:Medication {rxnorm: "29046"}) SET m11 += {name: "Lisinopril", generic_name: "lisinopril", brand_names: "Prinivil,Zestril", drug_class: "ACE Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m12:Medication {rxnorm: "17767"}) SET m12 += {name: "Amlodipine", generic_name: "amlodipine", brand_names: "Norvasc", drug_class: "Calcium Channel Blocker", route: "oral", controlled: false, high_alert: false};
MERGE (m13:Medication {rxnorm: "83367"}) SET m13 += {name: "Atorvastatin", generic_name: "atorvastatin", brand_names: "Lipitor", drug_class: "Statin", route: "oral", controlled: false, high_alert: false};
MERGE (m14:Medication {rxnorm: "6918"}) SET m14 += {name: "Metoprolol Succinate", generic_name: "metoprolol", brand_names: "Toprol-XL", drug_class: "Beta Blocker", route: "oral", controlled: false, high_alert: false};
MERGE (m15:Medication {rxnorm: "20352"}) SET m15 += {name: "Carvedilol", generic_name: "carvedilol", brand_names: "Coreg", drug_class: "Alpha-Beta Blocker", route: "oral", controlled: false, high_alert: false};
MERGE (m16:Medication {rxnorm: "4603"}) SET m16 += {name: "Furosemide", generic_name: "furosemide", brand_names: "Lasix", drug_class: "Loop Diuretic", route: "oral/injectable", controlled: false, high_alert: false};
MERGE (m17:Medication {rxnorm: "11289"}) SET m17 += {name: "Warfarin", generic_name: "warfarin", brand_names: "Coumadin,Jantoven", drug_class: "Vitamin K Antagonist", route: "oral", controlled: false, high_alert: true};
MERGE (m18:Medication {rxnorm: "1191"}) SET m18 += {name: "Aspirin", generic_name: "aspirin", brand_names: "Bayer,Ecotrin", drug_class: "Antiplatelet/NSAID", route: "oral", controlled: false, high_alert: false};
MERGE (m19:Medication {rxnorm: "32968"}) SET m19 += {name: "Clopidogrel", generic_name: "clopidogrel", brand_names: "Plavix", drug_class: "P2Y12 Antiplatelet", route: "oral", controlled: false, high_alert: false};
MERGE (m20:Medication {rxnorm: "1593775"}) SET m20 += {name: "Ticagrelor", generic_name: "ticagrelor", brand_names: "Brilinta", drug_class: "P2Y12 Antiplatelet", route: "oral", controlled: false, high_alert: true};
MERGE (m21:Medication {rxnorm: "41493"}) SET m21 += {name: "Losartan", generic_name: "losartan", brand_names: "Cozaar", drug_class: "ARB", route: "oral", controlled: false, high_alert: false};
MERGE (m22:Medication {rxnorm: "41207"}) SET m22 += {name: "Spironolactone", generic_name: "spironolactone", brand_names: "Aldactone", drug_class: "Potassium-sparing Diuretic", route: "oral", controlled: false, high_alert: false};
MERGE (m23:Medication {rxnorm: "1656340"}) SET m23 += {name: "Sacubitril/Valsartan", generic_name: "sacubitril/valsartan", brand_names: "Entresto", drug_class: "ARNI", route: "oral", controlled: false, high_alert: false};
MERGE (m24:Medication {rxnorm: "36567"}) SET m24 += {name: "Simvastatin", generic_name: "simvastatin", brand_names: "Zocor", drug_class: "Statin", route: "oral", controlled: false, high_alert: false};
MERGE (m25:Medication {rxnorm: "301542"}) SET m25 += {name: "Rosuvastatin", generic_name: "rosuvastatin", brand_names: "Crestor", drug_class: "Statin", route: "oral", controlled: false, high_alert: false};
MERGE (m26:Medication {rxnorm: "1747262"}) SET m26 += {name: "Apixaban", generic_name: "apixaban", brand_names: "Eliquis", drug_class: "Factor Xa Inhibitor", route: "oral", controlled: false, high_alert: true};
MERGE (m27:Medication {rxnorm: "1599538"}) SET m27 += {name: "Rivaroxaban", generic_name: "rivaroxaban", brand_names: "Xarelto", drug_class: "Factor Xa Inhibitor", route: "oral", controlled: false, high_alert: true};
MERGE (m28:Medication {rxnorm: "1037045"}) SET m28 += {name: "Dabigatran", generic_name: "dabigatran", brand_names: "Pradaxa", drug_class: "Direct Thrombin Inhibitor", route: "oral", controlled: false, high_alert: true};
MERGE (m29:Medication {rxnorm: "72435"}) SET m29 += {name: "Digoxin", generic_name: "digoxin", brand_names: "Lanoxin", drug_class: "Cardiac Glycoside", route: "oral", controlled: false, high_alert: true};
MERGE (m30:Medication {rxnorm: "1011"}) SET m30 += {name: "Amiodarone", generic_name: "amiodarone", brand_names: "Cordarone,Pacerone", drug_class: "Antiarrhythmic Class III", route: "oral/injectable", controlled: false, high_alert: true};

// Pulmonary medications
MERGE (m31:Medication {rxnorm: "435"}) SET m31 += {name: "Albuterol", generic_name: "albuterol", brand_names: "ProAir,Ventolin,Proventil", drug_class: "SABA", route: "inhaled", controlled: false, high_alert: false};
MERGE (m32:Medication {rxnorm: "41126"}) SET m32 += {name: "Fluticasone", generic_name: "fluticasone", brand_names: "Flovent,Flonase", drug_class: "Inhaled Corticosteroid", route: "inhaled", controlled: false, high_alert: false};
MERGE (m33:Medication {rxnorm: "274783"}) SET m33 += {name: "Tiotropium", generic_name: "tiotropium", brand_names: "Spiriva", drug_class: "LAMA", route: "inhaled", controlled: false, high_alert: false};
MERGE (m34:Medication {rxnorm: "1812189"}) SET m34 += {name: "Fluticasone/Salmeterol", generic_name: "fluticasone/salmeterol", brand_names: "Advair", drug_class: "ICS/LABA Combination", route: "inhaled", controlled: false, high_alert: false};
MERGE (m35:Medication {rxnorm: "2123141"}) SET m35 += {name: "Budesonide/Formoterol", generic_name: "budesonide/formoterol", brand_names: "Symbicort", drug_class: "ICS/LABA Combination", route: "inhaled", controlled: false, high_alert: false};
MERGE (m36:Medication {rxnorm: "1367447"}) SET m36 += {name: "Umeclidinium/Vilanterol", generic_name: "umeclidinium/vilanterol", brand_names: "Anoro Ellipta", drug_class: "LAMA/LABA Combination", route: "inhaled", controlled: false, high_alert: false};

// Renal/other medications
MERGE (m37:Medication {rxnorm: "3498"}) SET m37 += {name: "Erythropoietin alfa", generic_name: "epoetin alfa", brand_names: "Epogen,Procrit", drug_class: "Erythropoiesis Stimulating Agent", route: "injectable", controlled: false, high_alert: true};
MERGE (m38:Medication {rxnorm: "1162634"}) SET m38 += {name: "Sevelamer", generic_name: "sevelamer carbonate", brand_names: "Renvela", drug_class: "Phosphate Binder", route: "oral", controlled: false, high_alert: false};
MERGE (m39:Medication {rxnorm: "2200636"}) SET m39 += {name: "Dapagliflozin (Heart Failure)", generic_name: "dapagliflozin", brand_names: "Farxiga", drug_class: "SGLT2 Inhibitor", route: "oral", controlled: false, high_alert: false};

// Other medications
MERGE (m40:Medication {rxnorm: "41493"}) SET m40 += {name: "Levothyroxine", generic_name: "levothyroxine", brand_names: "Synthroid,Levoxyl", drug_class: "Thyroid Hormone", route: "oral", controlled: false, high_alert: false};
MERGE (m41:Medication {rxnorm: "7258"}) SET m41 += {name: "Omeprazole", generic_name: "omeprazole", brand_names: "Prilosec", drug_class: "Proton Pump Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m42:Medication {rxnorm: "194000"}) SET m42 += {name: "Pantoprazole", generic_name: "pantoprazole", brand_names: "Protonix", drug_class: "Proton Pump Inhibitor", route: "oral/injectable", controlled: false, high_alert: false};
MERGE (m43:Medication {rxnorm: "9068"}) SET m43 += {name: "Prednisone", generic_name: "prednisone", brand_names: "Deltasone", drug_class: "Systemic Corticosteroid", route: "oral", controlled: false, high_alert: true};
MERGE (m44:Medication {rxnorm: "321988"}) SET m44 += {name: "Methotrexate", generic_name: "methotrexate", brand_names: "Trexall,Rheumatrex", drug_class: "DMARD/Antimetabolite", route: "oral/injectable", controlled: false, high_alert: true};
MERGE (m45:Medication {rxnorm: "41493"}) SET m45 += {name: "Hydroxychloroquine", generic_name: "hydroxychloroquine", brand_names: "Plaquenil", drug_class: "Antimalarial/DMARD", route: "oral", controlled: false, high_alert: false};
MERGE (m46:Medication {rxnorm: "1043567"}) SET m46 += {name: "Allopurinol", generic_name: "allopurinol", brand_names: "Zyloprim", drug_class: "Xanthine Oxidase Inhibitor", route: "oral", controlled: false, high_alert: false};
MERGE (m47:Medication {rxnorm: "596"}) SET m47 += {name: "Acetaminophen", generic_name: "acetaminophen", brand_names: "Tylenol", drug_class: "Analgesic/Antipyretic", route: "oral", controlled: false, high_alert: false};
MERGE (m48:Medication {rxnorm: "5640"}) SET m48 += {name: "Ibuprofen", generic_name: "ibuprofen", brand_names: "Advil,Motrin", drug_class: "NSAID", route: "oral", controlled: false, high_alert: false};
MERGE (m49:Medication {rxnorm: "7052"}) SET m49 += {name: "Naproxen", generic_name: "naproxen", brand_names: "Aleve,Naprosyn", drug_class: "NSAID", route: "oral", controlled: false, high_alert: false};
MERGE (m50:Medication {rxnorm: "22660"}) SET m50 += {name: "Gabapentin", generic_name: "gabapentin", brand_names: "Neurontin", drug_class: "Anticonvulsant/Neuropathic", route: "oral", controlled: false, high_alert: false};
MERGE (m51:Medication {rxnorm: "114979"}) SET m51 += {name: "Sertraline", generic_name: "sertraline", brand_names: "Zoloft", drug_class: "SSRI", route: "oral", controlled: false, high_alert: false};
MERGE (m52:Medication {rxnorm: "36437"}) SET m52 += {name: "Duloxetine", generic_name: "duloxetine", brand_names: "Cymbalta", drug_class: "SNRI", route: "oral", controlled: false, high_alert: false};

// ============================================================
// DRUG-DISEASE TREATMENT RELATIONSHIPS
// ============================================================
MATCH (m:Medication {rxnorm: "6809"}), (d:Disease {icd10: "E11.9"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ADA 2024"}]->(d);

MATCH (m:Medication {rxnorm: "1545146"}), (d:Disease {icd10: "E11.9"})
MERGE (m)-[:TREATS {first_line: false, evidence: "A", guideline: "ADA 2024", additional_benefit: "cardiovascular_renal_protection"}]->(d);

MATCH (m:Medication {rxnorm: "1545146"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:TREATS {first_line: false, evidence: "A", guideline: "ACC/AHA 2022", indication: "HFrEF with T2DM"}]->(d);

MATCH (m:Medication {rxnorm: "1486436"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:TREATS {first_line: false, evidence: "A", guideline: "ACC/AHA 2022"}]->(d);

MATCH (m:Medication {rxnorm: "29046"}), (d:Disease {icd10: "I10"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "JNC8/ACC/AHA 2017"}]->(d);

MATCH (m:Medication {rxnorm: "29046"}), (d:Disease {icd10: "N18.3"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "KDIGO 2024", indication: "Proteinuria reduction"}]->(d);

MATCH (m:Medication {rxnorm: "83367"}), (d:Disease {icd10: "E78.5"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ACC/AHA Cholesterol 2018"}]->(d);

MATCH (m:Medication {rxnorm: "14602"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ACC/AHA HF 2022"}]->(d);

MATCH (m:Medication {rxnorm: "20352"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ACC/AHA HF 2022"}]->(d);

MATCH (m:Medication {rxnorm: "435"}), (d:Disease {icd10: "J45.909"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "GINA 2023", use: "rescue"}]->(d);

MATCH (m:Medication {rxnorm: "435"}), (d:Disease {icd10: "J44.1"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "GOLD 2024", use: "rescue"}]->(d);

MATCH (m:Medication {rxnorm: "274783"}), (d:Disease {icd10: "J44.1"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "GOLD 2024"}]->(d);

MATCH (m:Medication {rxnorm: "11289"}), (d:Disease {icd10: "I48.91"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ACC/AHA AFib 2023", use: "anticoagulation"}]->(d);

MATCH (m:Medication {rxnorm: "1747262"}), (d:Disease {icd10: "I48.91"})
MERGE (m)-[:TREATS {first_line: true, evidence: "A", guideline: "ACC/AHA AFib 2023", preferred: true}]->(d);

// ============================================================
// DRUG-DRUG INTERACTIONS (clinically significant)
// ============================================================

// Warfarin + Aspirin = increased bleeding
MATCH (m1:Medication {rxnorm: "11289"}), (m2:Medication {rxnorm: "1191"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Increased bleeding risk", mechanism: "Additive anticoagulant and antiplatelet effects", management: "Avoid combination unless benefit outweighs risk; monitor closely"}]->(m2);

// Warfarin + NSAIDs
MATCH (m1:Medication {rxnorm: "11289"}), (m2:Medication {rxnorm: "5640"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Increased bleeding risk with GI bleed", mechanism: "NSAIDs inhibit platelet aggregation and may cause GI ulceration", management: "Avoid combination; use acetaminophen instead"}]->(m2);

MATCH (m1:Medication {rxnorm: "11289"}), (m2:Medication {rxnorm: "7052"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Increased bleeding risk", mechanism: "NSAIDs inhibit platelet aggregation", management: "Avoid combination"}]->(m2);

// Aspirin + Clopidogrel (dual antiplatelet - major bleeding risk)
MATCH (m1:Medication {rxnorm: "1191"}), (m2:Medication {rxnorm: "32968"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Dual antiplatelet therapy - increased bleeding risk", mechanism: "Additive antiplatelet effects", management: "Only indicated post-ACS/stent; limit to guideline-recommended duration"}]->(m2);

// ACE inhibitor + ARB (dual RAAS blockade)
MATCH (m1:Medication {rxnorm: "29046"}), (m2:Medication {rxnorm: "41493"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Dual RAAS blockade - hyperkalemia and acute kidney injury", mechanism: "Additive renin-angiotensin-aldosterone system blockade", management: "Avoid combination; not recommended except specific CKD proteinuria cases"}]->(m2);

// Metformin + Contrast media (hold for AKI risk)
MATCH (m1:Medication {rxnorm: "6809"}), (m2:Medication {rxnorm: "41493"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Risk of metformin-associated lactic acidosis if AKI occurs from contrast", mechanism: "Contrast-induced nephropathy with metformin accumulation", management: "Hold metformin before and 48h after iodinated contrast if eGFR <60"}]->(m2);

// Spironolactone + ACE inhibitor (hyperkalemia)
MATCH (m1:Medication {rxnorm: "22660"}), (m2:Medication {rxnorm: "29046"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Hyperkalemia risk", mechanism: "Both agents reduce potassium excretion", management: "Monitor serum potassium closely; risk increased in CKD"}]->(m2);

// Digoxin + Amiodarone (digoxin toxicity)
MATCH (m1:Medication {rxnorm: "72435"}), (m2:Medication {rxnorm: "1011"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Digoxin toxicity - amiodarone increases digoxin levels 70-100%", mechanism: "Amiodarone inhibits P-gp and reduces renal digoxin clearance", management: "Reduce digoxin dose by 50% when starting amiodarone; monitor levels"}]->(m2);

// Metoprolol + Amiodarone (bradycardia/heart block)
MATCH (m1:Medication {rxnorm: "6918"}), (m2:Medication {rxnorm: "1011"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Additive bradycardia and AV block", mechanism: "Additive negative chronotropic effects on SA and AV nodes", management: "Monitor heart rate and rhythm closely; reduce beta-blocker dose"}]->(m2);

// SSRI + Warfarin (increased INR)
MATCH (m1:Medication {rxnorm: "114979"}), (m2:Medication {rxnorm: "11289"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Increased INR and bleeding risk", mechanism: "SSRIs inhibit platelet serotonin reuptake and may inhibit CYP2C9 metabolism of warfarin", management: "Monitor INR closely when starting/stopping SSRI; adjust warfarin dose"}]->(m2);

// Methotrexate + NSAIDs (toxicity)
MATCH (m1:Medication {rxnorm: "321988"}), (m2:Medication {rxnorm: "5640"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Methotrexate toxicity - bone marrow suppression, mucositis", mechanism: "NSAIDs reduce renal methotrexate clearance", management: "Avoid NSAIDs with high-dose methotrexate; caution with low dose in RA"}]->(m2);

// ACE Inhibitor + Potassium-sparing diuretic
MATCH (m1:Medication {rxnorm: "29046"}), (m2:Medication {rxnorm: "41207"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Hyperkalemia - potentially life-threatening", mechanism: "Additive reduction in aldosterone-mediated potassium excretion", management: "Use with caution in CKD; monitor serum potassium frequently"}]->(m2);

// Statin (simvastatin) + Amiodarone (myopathy risk)
MATCH (m1:Medication {rxnorm: "36567"}), (m2:Medication {rxnorm: "1011"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Statin myopathy and rhabdomyolysis risk", mechanism: "Amiodarone inhibits CYP3A4 increasing statin blood levels", management: "Limit simvastatin dose to 20mg/day with amiodarone; use rosuvastatin or pravastatin"}]->(m2);

// Furosemide + Digoxin (toxicity via hypokalemia)
MATCH (m1:Medication {rxnorm: "4603"}), (m2:Medication {rxnorm: "72435"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Loop diuretic-induced hypokalemia potentiates digoxin toxicity", mechanism: "Hypokalemia increases myocardial sensitivity to digoxin", management: "Monitor serum potassium; supplement if needed; check digoxin levels"}]->(m2);

// NSAID + ACE inhibitor (acute kidney injury)
MATCH (m1:Medication {rxnorm: "5640"}), (m2:Medication {rxnorm: "29046"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Acute kidney injury risk - Triple whammy syndrome with diuretic", mechanism: "NSAIDs block prostaglandin-mediated afferent arteriole dilation; ACEi blocks efferent constriction", management: "Avoid combination; particularly dangerous in elderly or dehydrated patients"}]->(m2);

// Dabigatran + Ibuprofen (bleeding)
MATCH (m1:Medication {rxnorm: "1037045"}), (m2:Medication {rxnorm: "5640"})
MERGE (m1)-[:INTERACTS_WITH {severity: "major", description: "Increased bleeding risk", mechanism: "NSAID antiplatelet effect combined with anticoagulation", management: "Avoid combination; use acetaminophen for analgesia"}]->(m2);

// Warfarin + Prednisone (complex interaction)
MATCH (m1:Medication {rxnorm: "11289"}), (m2:Medication {rxnorm: "9068"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Variable INR changes with corticosteroids", mechanism: "Corticosteroids induce CYP2C9 and affect clotting factor synthesis", management: "Monitor INR closely when starting or stopping steroids"}]->(m2);

// Metformin + Furosemide (metformin levels)
MATCH (m1:Medication {rxnorm: "6809"}), (m2:Medication {rxnorm: "4603"})
MERGE (m1)-[:INTERACTS_WITH {severity: "minor", description: "Furosemide may increase metformin levels", mechanism: "Competition for renal tubular secretion", management: "Monitor renal function; watch for lactic acidosis signs"}]->(m2);

// Apixaban + Aspirin (increased bleeding)
MATCH (m1:Medication {rxnorm: "1747262"}), (m2:Medication {rxnorm: "1191"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Increased bleeding risk with concomitant antiplatelet", mechanism: "Additive anticoagulation/antiplatelet effects", management: "Combination may be necessary post-ACS; use lowest effective aspirin dose (81mg)"}]->(m2);

// Gabapentin + Opioids (CNS depression)
MATCH (m1:Medication {rxnorm: "22660"}), (m2:Medication {rxnorm: "7052"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Enhanced CNS and respiratory depression", mechanism: "Additive CNS depressant effects", management: "Use lowest effective doses; monitor respiratory status; avoid in high-risk patients"}]->(m2);

// Metformin + Levothyroxine (absorption)
MATCH (m1:Medication {rxnorm: "6809"}), (m2:Medication {rxnorm: "40041"})
MERGE (m1)-[:INTERACTS_WITH {severity: "minor", description: "Metformin may reduce levothyroxine absorption", mechanism: "Possible binding in GI tract", management: "Separate administration by at least 4 hours"}]->(m2);

// Hydroxychloroquine + Digoxin (increased digoxin levels)
MATCH (m1:Medication {rxnorm: "5757"}) , (m2:Medication {rxnorm: "72435"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Hydroxychloroquine may increase digoxin levels", mechanism: "P-glycoprotein inhibition", management: "Monitor digoxin levels and signs of toxicity"}]->(m2);

// ACEi + Allopurinol (hypersensitivity)
MATCH (m1:Medication {rxnorm: "29046"}), (m2:Medication {rxnorm: "1043567"})
MERGE (m1)-[:INTERACTS_WITH {severity: "moderate", description: "Increased risk of Stevens-Johnson syndrome and toxic epidermal necrolysis", mechanism: "Unclear; possibly immune-mediated", management: "Monitor for hypersensitivity reactions, particularly in renal impairment"}]->(m2);

// ============================================================
// DRUG-DISEASE CONTRAINDICATIONS
// ============================================================

// Metformin contraindicated in CKD Stage 4-5
MATCH (m:Medication {rxnorm: "6809"}), (d:Disease {icd10: "N18.4"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "absolute", reason: "Risk of lactic acidosis due to metformin accumulation", threshold: "eGFR < 30 mL/min/1.73m2", alternative: "Switch to insulin or GLP-1 agonist"}]->(d);

MATCH (m:Medication {rxnorm: "6809"}), (d:Disease {icd10: "N18.5"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "absolute", reason: "Risk of fatal lactic acidosis", threshold: "eGFR < 15 mL/min/1.73m2", alternative: "Insulin therapy required"}]->(d);

// NSAIDs contraindicated in CKD
MATCH (m:Medication {rxnorm: "5640"}), (d:Disease {icd10: "N18.3"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "NSAIDs reduce renal prostaglandins and can precipitate acute-on-chronic kidney injury", threshold: "eGFR < 30 increases risk significantly", alternative: "Use acetaminophen for analgesia"}]->(d);

MATCH (m:Medication {rxnorm: "7052"}), (d:Disease {icd10: "N18.3"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "NSAIDs reduce renal blood flow and worsen kidney function", alternative: "Acetaminophen preferred"}]->(d);

// NSAIDs contraindicated in Heart Failure
MATCH (m:Medication {rxnorm: "5640"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "NSAIDs cause fluid retention and may exacerbate heart failure; associated with HF hospitalization", alternative: "Acetaminophen for analgesia; topical NSAIDs for local pain"}]->(d);

MATCH (m:Medication {rxnorm: "7052"}), (d:Disease {icd10: "I50.9"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "NSAIDs cause sodium and fluid retention worsening HF", alternative: "Acetaminophen preferred"}]->(d);

// Albuterol caution in heart disease
MATCH (m:Medication {rxnorm: "435"}), (d:Disease {icd10: "I25.10"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Albuterol causes tachycardia which may precipitate ischemia in CAD", management: "Use at lowest effective dose; consider ipratropium alternative; monitor heart rate"}]->(d);

// Beta-blocker caution in COPD
MATCH (m:Medication {rxnorm: "6918"}), (d:Disease {icd10: "J44.1"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Non-selective beta-blockers may cause bronchospasm in COPD; cardioselective beta-1 blockers (metoprolol) preferred", management: "Use cardioselective beta-1 blocker at low dose; monitor respiratory function; benefits usually outweigh risks in HF/post-MI"}]->(d);

// ACE Inhibitors contraindicated in pregnancy
MATCH (m:Medication {rxnorm: "29046"}), (d:Disease {icd10: "I10"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Absolutely contraindicated in pregnancy (2nd/3rd trimester - fetal renal toxicity); switch to methyldopa or labetalol in pregnancy", management: "Discontinue immediately if pregnancy confirmed; use alternative antihypertensive"}]->(d);

// Digoxin caution in CKD
MATCH (m:Medication {rxnorm: "72435"}), (d:Disease {icd10: "N18.3"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Digoxin is renally cleared; CKD leads to drug accumulation and toxicity risk", management: "Reduce dose; target serum level 0.5-0.9 ng/mL; monitor levels and renal function frequently"}]->(d);

// Spironolactone contraindicated in severe CKD
MATCH (m:Medication {rxnorm: "41207"}), (d:Disease {icd10: "N18.4"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "High risk of life-threatening hyperkalemia in CKD stage 4", threshold: "eGFR < 30 or K+ > 5.0 mEq/L", alternative: "Patiromer or sodium zirconium cyclosilicate for hyperkalemia"}]->(d);

// Hydroxychloroquine caution in retinopathy
MATCH (m:Medication {rxnorm: "5757"}), (d:Disease {icd10: "E11.319"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Hydroxychloroquine can cause retinal toxicity; CKD increases drug accumulation and retinal risk", management: "Annual ophthalmology screening; reduce dose in renal impairment"}]->(d);

// Prednisone contraindicated in uncontrolled diabetes
MATCH (m:Medication {rxnorm: "9068"}), (d:Disease {icd10: "E11.65"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Corticosteroids cause significant hyperglycemia especially in afternoon/evening", management: "Monitor blood glucose frequently; may need insulin; consider steroid-sparing agents"}]->(d);

// SGLT2 inhibitors contraindicated in severe CKD (historical - some now approved for CKD treatment)
MATCH (m:Medication {rxnorm: "1545146"}), (d:Disease {icd10: "N18.5"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "absolute", reason: "Insufficient glycemic efficacy when GFR <30; risk of euglycemic DKA", threshold: "eGFR < 20 mL/min", alternative: "Insulin therapy required"}]->(d);

// Warfarin caution in liver disease
MATCH (m:Medication {rxnorm: "11289"}), (d:Disease {icd10: "K76.0"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Liver disease alters vitamin K-dependent clotting factor synthesis; INR more labile and unpredictable", management: "Monitor INR more frequently; consider direct oral anticoagulant if appropriate"}]->(d);

// Methotrexate contraindicated in hepatic disease
MATCH (m:Medication {rxnorm: "321988"}), (d:Disease {icd10: "K76.0"})
MERGE (m)-[:CONTRAINDICATED_IN {severity: "relative", reason: "Methotrexate is hepatotoxic; underlying liver disease increases risk of cirrhosis", threshold: "Avoid in significant hepatic fibrosis/cirrhosis", alternative: "Use alternative DMARD (sulfasalazine, leflunomide)"}]->(d);

// Bisphosphonates caution in severe CKD
MATCH (m:Medication {rxnorm: "1043567"}), (d:Disease {icd10: "N18.4"})
MERGE (m)-[:USE_WITH_CAUTION_IN {reason: "Bisphosphonates accumulate in renal impairment and may worsen renal function; also risk of adynamic bone disease in CKD-MBD", management: "Generally avoid if eGFR < 30; use denosumab as alternative for osteoporosis"}]->(d);

// ============================================================
// DISEASE-DISEASE RISK RELATIONSHIPS
// ============================================================

MATCH (d1:Disease {icd10: "E11.9"}), (d2:Disease {icd10: "N18.3"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.35, mechanism: "Hyperglycemia causes glomerular hyperfiltration and nephron loss; AGE deposition in glomerular basement membrane", timeframe_years: 10, prevention: "HbA1c < 7%; ACE inhibitor/ARB; SGLT2 inhibitor"}]->(d2);

MATCH (d1:Disease {icd10: "E11.9"}), (d2:Disease {icd10: "I25.10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.45, mechanism: "Hyperglycemia accelerates atherosclerosis; promotes inflammation, oxidative stress, and endothelial dysfunction", timeframe_years: 5, prevention: "Aggressive cardiovascular risk factor modification; statin therapy; aspirin in high-risk patients"}]->(d2);

MATCH (d1:Disease {icd10: "E11.9"}), (d2:Disease {icd10: "I10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.30, mechanism: "Insulin resistance increases sodium retention and sympathetic nervous system activity", timeframe_years: 5}]->(d2);

MATCH (d1:Disease {icd10: "I10"}), (d2:Disease {icd10: "I63.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.40, mechanism: "Hypertension accelerates cerebral atherosclerosis and increases embolic stroke risk; also increases hemorrhagic stroke risk", timeframe_years: 10, prevention: "Blood pressure < 130/80 mmHg; antiplatelet therapy in high-risk patients"}]->(d2);

MATCH (d1:Disease {icd10: "I10"}), (d2:Disease {icd10: "I50.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.35, mechanism: "Chronic pressure overload leads to LV hypertrophy and diastolic dysfunction; accelerated coronary atherosclerosis", timeframe_years: 10, prevention: "Optimal blood pressure control; ACE inhibitor/ARB; beta-blocker"}]->(d2);

MATCH (d1:Disease {icd10: "I10"}), (d2:Disease {icd10: "N18.3"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.25, mechanism: "Hypertension causes nephrosclerosis through ischemic injury; also exacerbates diabetic nephropathy", timeframe_years: 10}]->(d2);

MATCH (d1:Disease {icd10: "J44.1"}), (d2:Disease {icd10: "I50.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.25, mechanism: "Chronic hypoxemia causes pulmonary hypertension and right heart failure (cor pulmonale); systemic inflammation affects left heart", timeframe_years: 7}]->(d2);

MATCH (d1:Disease {icd10: "E66.9"}), (d2:Disease {icd10: "E11.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.50, mechanism: "Adipose tissue-derived inflammatory cytokines cause insulin resistance; ectopic fat deposition in liver and muscle impairs glucose metabolism", timeframe_years: 5}]->(d2);

MATCH (d1:Disease {icd10: "E66.9"}), (d2:Disease {icd10: "I10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.40, mechanism: "Obesity activates RAAS system; increases sympathetic tone; physically obstructs venous return raising blood pressure", timeframe_years: 5}]->(d2);

MATCH (d1:Disease {icd10: "E78.5"}), (d2:Disease {icd10: "I25.10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.40, mechanism: "LDL deposits in arterial wall initiating atherosclerotic plaque; elevated TG is independent risk factor", timeframe_years: 10, prevention: "Statin therapy; LDL < 70 mg/dL in high-risk patients"}]->(d2);

MATCH (d1:Disease {icd10: "I25.10"}), (d2:Disease {icd10: "I50.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.45, mechanism: "Ischemic cardiomyopathy from myocardial infarctions; chronic ischemia causes ventricular remodeling and systolic dysfunction", timeframe_years: 5}]->(d2);

MATCH (d1:Disease {icd10: "I48.91"}), (d2:Disease {icd10: "I63.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.50, mechanism: "Atrial fibrillation causes blood stasis in left atrial appendage promoting thrombus formation and cardioembolic stroke", timeframe_years: 1, prevention: "Anticoagulation (DOAC preferred); CHA2DS2-VASc score guided therapy"}]->(d2);

MATCH (d1:Disease {icd10: "N18.3"}), (d2:Disease {icd10: "I25.10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.35, mechanism: "Uremia promotes atherosclerosis via oxidative stress, dyslipidemia, chronic inflammation, and vascular calcification", timeframe_years: 5}]->(d2);

MATCH (d1:Disease {icd10: "G47.33"}), (d2:Disease {icd10: "I10"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.30, mechanism: "Sleep apnea causes repeated nocturnal hypoxemia activating sympathetic nervous system; increases aldosterone; impairs baroreflex sensitivity", timeframe_years: 3}]->(d2);

MATCH (d1:Disease {icd10: "G47.33"}), (d2:Disease {icd10: "I48.91"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.25, mechanism: "Nocturnal hypoxia and autonomic dysregulation promote atrial remodeling and fibrosis predisposing to atrial fibrillation", timeframe_years: 3}]->(d2);

MATCH (d1:Disease {icd10: "F32.9"}), (d2:Disease {icd10: "E11.9"})
MERGE (d1)-[:INCREASES_RISK_OF {weight: 0.20, mechanism: "Depression associated with poor health behaviors (physical inactivity, poor diet); HPA axis dysregulation promotes insulin resistance; antidepressants may affect glucose metabolism", timeframe_years: 5}]->(d2);

// ============================================================
// CLINICAL GUIDELINES
// ============================================================
MERGE (g1:ClinicalGuideline {id: "ada-2024-soc"}) SET g1 += {
    title: "ADA Standards of Care in Diabetes 2024",
    issuing_organization: "American Diabetes Association",
    publication_year: 2024,
    version: "2024",
    url: "https://doi.org/10.2337/dc24-S001",
    summary: "Comprehensive evidence-based recommendations for the diagnosis and treatment of diabetes including lifestyle, pharmacotherapy, monitoring, and complication prevention",
    key_recommendations: ["HbA1c target <7% for most adults", "BP target <130/80 mmHg", "Statin therapy for most patients with T2DM >40 years", "SGLT2i or GLP-1 agonist with proven CVD benefit for high-risk patients", "Annual eGFR and urine albumin monitoring"],
    evidence_grading: "A/B/C/E"
};

MERGE (g2:ClinicalGuideline {id: "acc-aha-hf-2022"}) SET g2 += {
    title: "ACC/AHA/HFSA Guideline for the Management of Heart Failure 2022",
    issuing_organization: "American College of Cardiology/American Heart Association",
    publication_year: 2022,
    version: "2022",
    url: "https://doi.org/10.1016/j.jacc.2021.12.012",
    summary: "Evidence-based recommendations for diagnosis, evaluation, and management of heart failure with reduced and preserved ejection fraction",
    key_recommendations: ["Quadruple therapy for HFrEF: ACEi/ARB/ARNI + beta-blocker + MRA + SGLT2i", "Diuretics for fluid management", "ICD for EF <35%", "CRT for EF <35% with LBBB"],
    evidence_grading: "I/IIa/IIb/III"
};

MERGE (g3:ClinicalGuideline {id: "kdigo-2024-ckd"}) SET g3 += {
    title: "KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
    issuing_organization: "Kidney Disease: Improving Global Outcomes",
    publication_year: 2024,
    version: "2024",
    url: "https://www.kidney-international.org",
    summary: "Recommendations for evaluation, staging, and management of CKD including slowing progression, managing complications, and preparation for kidney replacement therapy",
    key_recommendations: ["ACE inhibitor/ARB for CKD with proteinuria", "SGLT2 inhibitor for CKD with or without T2DM when eGFR >=20", "Finerenone for CKD with T2DM", "BP target <120 mmHg systolic", "LDL-lowering therapy for all CKD patients"],
    evidence_grading: "1A/1B/1C/2A/2B/2C"
};

MERGE (g4:ClinicalGuideline {id: "gold-copd-2024"}) SET g4 += {
    title: "GOLD 2024 Global Strategy for Prevention, Diagnosis and Management of COPD",
    issuing_organization: "Global Initiative for Chronic Obstructive Lung Disease",
    publication_year: 2024,
    version: "2024",
    url: "https://goldcopd.org/2024-gold-report/",
    summary: "Evidence-based strategy for COPD prevention, diagnosis, and management including pharmacological and non-pharmacological therapies",
    key_recommendations: ["LAMA preferred initial maintenance therapy for most patients", "ICS/LABA for patients with frequent exacerbations or eosinophils >300", "Smoking cessation as top priority", "Annual influenza and pneumococcal vaccination", "Pulmonary rehabilitation for symptomatic patients"],
    evidence_grading: "A/B/C/D"
};

MERGE (g5:ClinicalGuideline {id: "acc-aha-cholesterol-2018"}) SET g5 += {
    title: "ACC/AHA Guideline on the Management of Blood Cholesterol 2018",
    issuing_organization: "American College of Cardiology/American Heart Association",
    publication_year: 2018,
    version: "2018",
    url: "https://doi.org/10.1016/j.jacc.2018.11.003",
    summary: "Risk-based approach to cholesterol management including statins, ezetimibe, and PCSK9 inhibitors for ASCVD risk reduction",
    key_recommendations: ["High-intensity statin for ASCVD; moderate-intensity for primary prevention in 40-75 age with 10-year risk >=7.5%", "LDL <70 mg/dL for very high-risk; <55 mg/dL for extreme risk", "Add ezetimibe if LDL not at goal on max statin"],
    evidence_grading: "I/IIa/IIb/III"
};

MERGE (g6:ClinicalGuideline {id: "acc-aha-htn-2017"}) SET g6 += {
    title: "ACC/AHA High Blood Pressure Guideline 2017",
    issuing_organization: "American College of Cardiology/American Heart Association",
    publication_year: 2017,
    version: "2017",
    url: "https://doi.org/10.1161/HYP.0000000000000065",
    summary: "Comprehensive hypertension guidelines redefining high blood pressure as >=130/80 and recommending intensive treatment targets",
    key_recommendations: ["BP target <130/80 for most adults", "Lifestyle modification for all", "Antihypertensives for Stage 2 or Stage 1 with high CVD risk", "Thiazide, ACEi/ARB, or CCB as first-line"],
    evidence_grading: "I/IIa/IIb/III"
};

MERGE (g7:ClinicalGuideline {id: "gina-2023"}) SET g7 += {
    title: "GINA 2023 Global Strategy for Asthma Management and Prevention",
    issuing_organization: "Global Initiative for Asthma",
    publication_year: 2023,
    version: "2023",
    url: "https://ginasthma.org/gina-reports/",
    summary: "Evidence-based strategy for asthma diagnosis, assessment, and management across all age groups",
    key_recommendations: ["ICS-containing inhaler as preferred controller for all patients", "Low-dose ICS-formoterol as preferred reliever (MART strategy)", "Avoid SABA-only treatment", "Assess and treat comorbidities"],
    evidence_grading: "A/B/C/D"
};

MERGE (g8:ClinicalGuideline {id: "acc-aha-afib-2023"}) SET g8 += {
    title: "ACC/AHA Atrial Fibrillation Guideline 2023",
    issuing_organization: "American College of Cardiology/American Heart Association",
    publication_year: 2023,
    version: "2023",
    url: "https://www.acc.org/",
    summary: "Comprehensive AF management including stroke risk stratification, anticoagulation, rate and rhythm control",
    key_recommendations: ["CHA2DS2-VASc >=2 in men, >=3 in women warrants anticoagulation", "DOAC preferred over warfarin", "Rate control target <110 bpm at rest", "Catheter ablation for rhythm control"],
    evidence_grading: "I/IIa/IIb/III"
};

MERGE (g9:ClinicalGuideline {id: "kdigo-2017-anemia-ckd"}) SET g9 += {
    title: "KDIGO Clinical Practice Guideline on Anaemia in CKD 2012 (Updated 2017)",
    issuing_organization: "Kidney Disease: Improving Global Outcomes",
    publication_year: 2017,
    version: "2017",
    url: "https://www.kidney-international.org",
    summary: "Recommendations for evaluation and management of anemia in chronic kidney disease including ESA therapy and iron supplementation",
    key_recommendations: ["Hemoglobin target 10-11.5 g/dL with ESA therapy", "Iron supplementation to maintain transferrin saturation >20% and ferritin >100 ng/mL", "ESA only for Hgb <10 g/dL"],
    evidence_grading: "1A/1B/2A/2B"
};

MERGE (g10:ClinicalGuideline {id: "acr-ra-2022"}) SET g10 += {
    title: "ACR Guideline for the Treatment of Rheumatoid Arthritis 2021",
    issuing_organization: "American College of Rheumatology",
    publication_year: 2021,
    version: "2021",
    url: "https://www.rheumatology.org/",
    summary: "Recommendations for DMARD therapy and treat-to-target strategy in rheumatoid arthritis",
    key_recommendations: ["Methotrexate as preferred first DMARD", "Treat-to-target strategy with low disease activity or remission goal", "bDMARD or tsDMARD if MTX insufficient", "Glucocorticoids at lowest effective dose for shortest duration"],
    evidence_grading: "Conditional/Strong"
};

// ============================================================
// GUIDELINES LINKED TO DISEASES
// ============================================================
MATCH (g:ClinicalGuideline {id: "ada-2024-soc"}), (d:Disease {icd10: "E11.9"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acc-aha-hf-2022"}), (d:Disease {icd10: "I50.9"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acc-aha-hf-2022"}), (d:Disease {icd10: "I50.22"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "kdigo-2024-ckd"}), (d:Disease {icd10: "N18.3"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "kdigo-2024-ckd"}), (d:Disease {icd10: "N18.4"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "kdigo-2024-ckd"}), (d:Disease {icd10: "N18.5"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "gold-copd-2024"}), (d:Disease {icd10: "J44.1"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acc-aha-cholesterol-2018"}), (d:Disease {icd10: "E78.5"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acc-aha-htn-2017"}), (d:Disease {icd10: "I10"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "gina-2023"}), (d:Disease {icd10: "J45.909"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acc-aha-afib-2023"}), (d:Disease {icd10: "I48.91"})
MERGE (g)-[:APPLIES_TO]->(d);

MATCH (g:ClinicalGuideline {id: "acr-ra-2022"}), (d:Disease {icd10: "M06.9"})
MERGE (g)-[:APPLIES_TO]->(d);
