# Clinical Workflow Documentation

## Agent Tiers

| Tier | Name | Agents | Purpose |
|------|------|--------|---------|
| T1 | Monitoring | Glucose, Cardiac, Activity, Temperature | Continuous vital sign monitoring |
| T2 | Diagnostic | ECG, Kidney, Imaging, Lab | Clinical data interpretation |
| T3 | Risk Assessment | Comorbidity, Prediction, Family History, SDOH, ML Ensemble | Multi-factor risk scoring |
| T4 | Intervention | Coaching, Prescription, Contraindication, Triage | Treatment recommendations |
| T5 | Action | Physician Notify, Patient Notify, Scheduling, EHR Integration, Billing | Automated clinical actions |

## FHIR R4 Resources

14 resource types: Patient, Observation, Condition, MedicationRequest,
DiagnosticReport, Appointment, CarePlan, AllergyIntolerance, Encounter,
Procedure, Immunization, DocumentReference, Bundle, CapabilityStatement.

## HL7 v2 Integration

Supported message types: ADT, ORU, ORM.

## Emergency Protocols

STEMI, Stroke, COPD Exacerbation — each triggers geospatial hospital routing.

## Research System

5 agents: Literature Search, Evidence Synthesis, Clinical Trial Matching,
Guideline Updates, Clinical Q&A with RAG.
