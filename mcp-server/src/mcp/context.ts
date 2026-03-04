import axios from "axios";
import { logger } from "../utils/logger";
import {
  MCPContext,
  PatientContext,
  PatientDemographics,
  Condition,
  Medication,
  Vital,
  Allergy,
  RiskScore,
  ClinicalConstraints,
  VectorSearchResult,
  Message,
} from "./types";
import { getToolDefinitions } from "./tools";

const DJANGO_BASE_URL = process.env.DJANGO_BASE_URL || "http://django-backend:8000";
const DJANGO_API_KEY = process.env.DJANGO_API_KEY || "";

const djangoClient = axios.create({
  baseURL: DJANGO_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": DJANGO_API_KEY,
  },
});

// Add response interceptor for error logging
djangoClient.interceptors.response.use(
  (response) => response,
  (error) => {
    logger.error("Django API call failed", {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
    });
    throw error;
  }
);

export interface FHIRPatientData {
  id: string;
  name?: Array<{ given?: string[]; family?: string; use?: string }>;
  birthDate?: string;
  gender?: string;
  address?: Array<{
    line?: string[];
    city?: string;
    state?: string;
    postalCode?: string;
    country?: string;
  }>;
  telecom?: Array<{ system?: string; value?: string; use?: string }>;
  identifier?: Array<{ system?: string; value?: string }>;
  communication?: Array<{ language?: { coding?: Array<{ code?: string }> } }>;
}

export async function fetchPatientFromFHIR(patientId: string): Promise<PatientContext> {
  logger.debug("fetchPatientFromFHIR: fetching patient data", { patient_id: patientId });

  try {
    // Fetch all patient data in parallel
    const [
      patientResponse,
      conditionsResponse,
      medicationsResponse,
      vitalsResponse,
      allergiesResponse,
      riskScoresResponse,
    ] = await Promise.all([
      djangoClient.get(`/api/fhir/Patient/${patientId}/`),
      djangoClient.get(`/api/fhir/query/`, {
        params: { patient_id: patientId, resource_type: "Condition", status: "active", limit: 50 },
      }),
      djangoClient.get(`/api/fhir/query/`, {
        params: { patient_id: patientId, resource_type: "MedicationRequest", status: "active", limit: 50 },
      }),
      djangoClient.get(`/api/fhir/query/`, {
        params: { patient_id: patientId, resource_type: "Observation", limit: 30, sort: "-date" },
      }),
      djangoClient.get(`/api/fhir/query/`, {
        params: { patient_id: patientId, resource_type: "AllergyIntolerance", limit: 50 },
      }),
      djangoClient.get(`/api/ml/risk-scores/${patientId}/`).catch(() => ({ data: { scores: [] } })),
    ]);

    const fhirPatient = patientResponse.data as FHIRPatientData;
    const demographics = parseFHIRDemographics(fhirPatient);
    const conditions = parseConditions(conditionsResponse.data);
    const medications = parseMedications(medicationsResponse.data);
    const vitals = parseVitals(vitalsResponse.data);
    const allergies = parseAllergies(allergiesResponse.data);
    const riskScores = parseRiskScores(riskScoresResponse.data);

    return {
      id: patientId,
      demographics,
      conditions,
      medications,
      recent_vitals: vitals,
      allergies,
      risk_scores: riskScores,
    };
  } catch (error) {
    logger.error("fetchPatientFromFHIR: failed", {
      patient_id: patientId,
      error: error instanceof Error ? error.message : String(error),
    });
    throw new Error(`Failed to fetch patient data for ${patientId}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function parseFHIRDemographics(fhirPatient: FHIRPatientData): PatientDemographics {
  const nameObj = fhirPatient.name?.find((n) => n.use === "official") || fhirPatient.name?.[0];
  const given = nameObj?.given?.join(" ") || "";
  const family = nameObj?.family || "";
  const fullName = `${given} ${family}`.trim() || "Unknown";

  const birthDate = fhirPatient.birthDate || "";
  const age = birthDate
    ? Math.floor(
        (Date.now() - new Date(birthDate).getTime()) / (365.25 * 24 * 60 * 60 * 1000)
      )
    : 0;

  const addressObj = fhirPatient.address?.[0];
  const address = addressObj
    ? {
        line: addressObj.line || [],
        city: addressObj.city || "",
        state: addressObj.state || "",
        postal_code: addressObj.postalCode || "",
        country: addressObj.country || "US",
      }
    : undefined;

  const phoneContact = fhirPatient.telecom?.find((t) => t.system === "phone");
  const emailContact = fhirPatient.telecom?.find((t) => t.system === "email");

  const mrnIdentifier = fhirPatient.identifier?.find((i) =>
    i.system?.includes("mrn") || i.system?.includes("MRN")
  );

  const language = fhirPatient.communication?.[0]?.language?.coding?.[0]?.code;

  return {
    name: fullName,
    date_of_birth: birthDate,
    gender: (fhirPatient.gender as PatientDemographics["gender"]) || "unknown",
    age,
    address,
    contact: {
      phone: phoneContact?.value,
      email: emailContact?.value,
    },
    mrn: mrnIdentifier?.value || fhirPatient.id || "UNKNOWN",
    language,
  };
}

interface FHIRConditionEntry {
  resource?: {
    id?: string;
    code?: { coding?: Array<{ code?: string; system?: string; display?: string }> };
    clinicalStatus?: { coding?: Array<{ code?: string }> };
    verificationStatus?: { coding?: Array<{ code?: string }> };
    onsetDateTime?: string;
    recordedDate?: string;
    severity?: { coding?: Array<{ display?: string }> };
    bodySite?: Array<{ coding?: Array<{ display?: string }> }>;
  };
}

function parseConditions(data: { entry?: FHIRConditionEntry[] }): Condition[] {
  const entries = data.entry || [];
  return entries
    .map((entry) => {
      const resource = entry.resource;
      if (!resource) return null;
      const coding = resource.code?.coding?.[0];
      return {
        id: resource.id || "",
        code: coding?.code || "",
        system: (coding?.system?.includes("snomed") ? "SNOMED-CT" : "ICD-10") as Condition["system"],
        display: coding?.display || "Unknown",
        status: (resource.clinicalStatus?.coding?.[0]?.code || "active") as Condition["status"],
        onset_date: resource.onsetDateTime,
        recorded_date: resource.recordedDate || new Date().toISOString(),
        severity: resource.severity?.coding?.[0]?.display?.toLowerCase() as Condition["severity"],
        body_site: resource.bodySite?.[0]?.coding?.[0]?.display,
        clinical_status: resource.clinicalStatus?.coding?.[0]?.code || "active",
        verification_status: (resource.verificationStatus?.coding?.[0]?.code || "confirmed") as Condition["verification_status"],
      } as Condition;
    })
    .filter((c): c is Condition => c !== null);
}

interface FHIRMedicationEntry {
  resource?: {
    id?: string;
    medicationCodeableConcept?: { coding?: Array<{ code?: string; display?: string }> };
    status?: string;
    dosageInstruction?: Array<{
      text?: string;
      doseAndRate?: Array<{ doseQuantity?: { value?: number; unit?: string } }>;
      timing?: { repeat?: { frequency?: number; period?: number; periodUnit?: string; boundsPeriod?: { start?: string; end?: string } } };
      route?: { coding?: Array<{ display?: string }> };
      asNeededBoolean?: boolean;
    }>;
    requester?: { display?: string };
    reasonCode?: Array<{ coding?: Array<{ display?: string }> }>;
  };
}

function parseMedications(data: { entry?: FHIRMedicationEntry[] }): Medication[] {
  const entries = data.entry || [];
  return entries
    .map((entry) => {
      const resource = entry.resource;
      if (!resource) return null;
      const coding = resource.medicationCodeableConcept?.coding?.[0];
      const dosageInstr = resource.dosageInstruction?.[0];
      const timing = dosageInstr?.timing?.repeat;

      return {
        id: resource.id || "",
        code: coding?.code || "",
        display: coding?.display || "Unknown",
        status: (resource.status || "active") as Medication["status"],
        dosage: {
          text: dosageInstr?.text || "",
          dose_quantity: dosageInstr?.doseAndRate?.[0]?.doseQuantity
            ? {
                value: dosageInstr.doseAndRate[0].doseQuantity.value || 0,
                unit: dosageInstr.doseAndRate[0].doseQuantity.unit || "",
              }
            : undefined,
          frequency: timing
            ? `${timing.frequency || 1}x per ${timing.period || 1} ${timing.periodUnit || "d"}`
            : "as directed",
          period: timing?.period,
          period_unit: timing?.periodUnit as Medication["dosage"]["period_unit"],
          as_needed: dosageInstr?.asNeededBoolean,
        },
        route: dosageInstr?.route?.coding?.[0]?.display,
        start_date: timing?.boundsPeriod?.start,
        end_date: timing?.boundsPeriod?.end,
        prescriber: resource.requester?.display,
        indication: resource.reasonCode?.[0]?.coding?.[0]?.display,
      } as Medication;
    })
    .filter((m): m is Medication => m !== null);
}

interface FHIRVitalEntry {
  resource?: {
    id?: string;
    code?: { coding?: Array<{ code?: string; display?: string }> };
    valueQuantity?: { value?: number; unit?: string };
    component?: Array<{
      code?: { coding?: Array<{ code?: string; display?: string }> };
      valueQuantity?: { value?: number; unit?: string };
    }>;
    effectiveDateTime?: string;
    performer?: Array<{ display?: string }>;
    status?: string;
    device?: { display?: string };
    interpretation?: Array<{ coding?: Array<{ code?: string }> }>;
    referenceRange?: Array<{ low?: { value?: number }; high?: { value?: number }; text?: string }>;
  };
}

const VITAL_CODE_MAP: Record<string, string> = {
  "85354-9": "blood_pressure",
  "8867-4": "heart_rate",
  "2339-0": "blood_glucose",
  "59408-5": "oxygen_saturation",
  "8310-5": "temperature",
  "29463-7": "weight",
  "8302-2": "height",
  "39156-5": "bmi",
  "9279-1": "respiratory_rate",
  "4548-4": "hba1c",
  "2093-3": "cholesterol",
  "33914-3": "egfr",
  "2160-0": "creatinine",
};

function parseVitals(data: { entry?: FHIRVitalEntry[] }): Vital[] {
  const entries = data.entry || [];
  return entries
    .map((entry) => {
      const resource = entry.resource;
      if (!resource) return null;
      const loincCode = resource.code?.coding?.[0]?.code || "";
      const vitalType = (VITAL_CODE_MAP[loincCode] || loincCode) as Vital["type"];

      const value = resource.component
        ? resource.component.map((c) => ({
            code: c.code?.coding?.[0]?.code || "",
            display: c.code?.coding?.[0]?.display || "",
            value: c.valueQuantity?.value || 0,
            unit: c.valueQuantity?.unit || "",
          }))
        : resource.valueQuantity?.value || 0;

      return {
        id: resource.id || "",
        type: vitalType,
        value,
        unit: resource.valueQuantity?.unit || "",
        recorded_at: resource.effectiveDateTime || new Date().toISOString(),
        recorded_by: resource.performer?.[0]?.display,
        status: (resource.status || "final") as Vital["status"],
        device: resource.device?.display,
        interpretation: resource.interpretation?.[0]?.coding?.[0]?.code as Vital["interpretation"],
        reference_range: resource.referenceRange?.[0]
          ? {
              low: resource.referenceRange[0].low?.value,
              high: resource.referenceRange[0].high?.value,
              text: resource.referenceRange[0].text,
            }
          : undefined,
      } as Vital;
    })
    .filter((v): v is Vital => v !== null);
}

interface FHIRAllergyEntry {
  resource?: {
    id?: string;
    code?: { coding?: Array<{ code?: string; system?: string; display?: string }> };
    category?: string[];
    criticality?: string;
    clinicalStatus?: { coding?: Array<{ code?: string }> };
    reaction?: Array<{
      substance?: { coding?: Array<{ display?: string }> };
      manifestation?: Array<{ coding?: Array<{ display?: string }> }>;
      severity?: string;
      description?: string;
    }>;
    onsetDateTime?: string;
    recordedDate?: string;
    note?: Array<{ text?: string }>;
  };
}

function parseAllergies(data: { entry?: FHIRAllergyEntry[] }): Allergy[] {
  const entries = data.entry || [];
  return entries
    .map((entry) => {
      const resource = entry.resource;
      if (!resource) return null;
      const coding = resource.code?.coding?.[0];

      return {
        id: resource.id || "",
        substance: coding?.display || "Unknown",
        substance_code: coding?.code,
        system: coding?.system,
        category: (resource.category?.[0] || "medication") as Allergy["category"],
        criticality: (resource.criticality || "unable-to-assess") as Allergy["criticality"],
        status: (resource.clinicalStatus?.coding?.[0]?.code || "active") as Allergy["status"],
        reactions: resource.reaction?.map((r) => ({
          substance: r.substance?.coding?.[0]?.display,
          manifestation: r.manifestation?.[0]?.coding?.[0]?.display || "Unknown reaction",
          severity: r.severity as Allergy["reactions"] extends Array<infer T> ? T["severity"] : never,
          description: r.description,
        })),
        onset_date: resource.onsetDateTime,
        recorded_date: resource.recordedDate || new Date().toISOString(),
        note: resource.note?.[0]?.text,
      } as Allergy;
    })
    .filter((a): a is Allergy => a !== null);
}

interface RiskScoresData {
  scores?: Array<{
    model: string;
    score: number;
    risk_level: string;
    calculated_at: string;
    factors: Array<{ name: string; value: string | number; weight: number; direction: string }>;
    recommendation: string;
    expires_at?: string;
  }>;
}

function parseRiskScores(data: RiskScoresData): RiskScore[] {
  const scores = data.scores || [];
  return scores.map((s) => ({
    model: s.model,
    score: s.score,
    risk_level: s.risk_level as RiskScore["risk_level"],
    calculated_at: s.calculated_at,
    factors: s.factors.map((f) => ({
      name: f.name,
      value: f.value,
      weight: f.weight,
      direction: f.direction as "positive" | "negative",
    })),
    recommendation: s.recommendation,
    expires_at: s.expires_at,
  }));
}

export async function fetchRelevantGuidelines(
  conditions: Condition[]
): Promise<ClinicalConstraints> {
  if (conditions.length === 0) {
    return {
      safety_rules: ["Always verify patient identity before taking clinical action"],
      clinical_guidelines: [],
      drug_contraindications: [],
    };
  }

  const conditionDisplays = conditions.map((c) => c.display).join(", ");

  logger.debug("fetchRelevantGuidelines: fetching guidelines", {
    condition_count: conditions.length,
    conditions: conditionDisplays.substring(0, 100),
  });

  try {
    const [guidelinesResponse, safetyRulesResponse, contraindicationsResponse] =
      await Promise.all([
        djangoClient.post("/api/vector/search/", {
          query: `clinical guidelines for ${conditionDisplays}`,
          collection: "clinical_guidelines",
          top_k: 10,
          score_threshold: 0.65,
        }),
        djangoClient.post("/api/vector/search/", {
          query: `safety rules contraindications for ${conditionDisplays}`,
          collection: "care_protocols",
          top_k: 5,
          score_threshold: 0.65,
        }),
        djangoClient.post("/api/vector/search/", {
          query: `drug contraindications for ${conditionDisplays}`,
          collection: "drug_information",
          top_k: 5,
          score_threshold: 0.65,
        }),
      ]);

    const guidelines = (guidelinesResponse.data.results || []) as VectorSearchResult[];
    const safetyRules = (safetyRulesResponse.data.results || []) as VectorSearchResult[];
    const contraindications = (contraindicationsResponse.data.results || []) as VectorSearchResult[];

    return {
      safety_rules: [
        "Always verify patient identity before taking clinical action",
        "Escalate critical findings to supervising clinician immediately",
        "Do not recommend treatment changes without physician approval",
        ...safetyRules.map((r) => r.payload.content),
      ],
      clinical_guidelines: guidelines.map(
        (g) => `[${g.payload.title || "Guideline"}]: ${g.payload.content}`
      ),
      drug_contraindications: contraindications.map((c) => c.payload.content),
    };
  } catch (error) {
    logger.warn("fetchRelevantGuidelines: failed to fetch guidelines, using defaults", {
      error: error instanceof Error ? error.message : String(error),
    });

    return {
      safety_rules: [
        "Always verify patient identity before taking clinical action",
        "Escalate critical findings to supervising clinician immediately",
        "Do not recommend treatment changes without physician approval",
      ],
      clinical_guidelines: [],
      drug_contraindications: [],
    };
  }
}

export async function buildMCPContext(
  patientId: string,
  agentId: string,
  conversationHistory: Message[]
): Promise<MCPContext> {
  logger.info("buildMCPContext: assembling context", { patient_id: patientId, agent_id: agentId });

  // Fetch patient data and guidelines in parallel
  const patientContext = await fetchPatientFromFHIR(patientId);
  const constraints = await fetchRelevantGuidelines(patientContext.conditions);
  const tools = getToolDefinitions();

  const context: MCPContext = {
    protocol: "MCP/1.0",
    context: {
      patient: patientContext,
      conversation_history: conversationHistory,
      available_tools: tools,
      constraints,
    },
  };

  logger.info("buildMCPContext: context assembled successfully", {
    patient_id: patientId,
    agent_id: agentId,
    conditions_count: patientContext.conditions.length,
    medications_count: patientContext.medications.length,
    tools_count: tools.length,
    history_messages: conversationHistory.length,
  });

  return context;
}
