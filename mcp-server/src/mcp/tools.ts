import axios from "axios";
import neo4j, { Driver, Session } from "neo4j-driver";
import { logger } from "../utils/logger";
import {
  MCPTool,
  DrugInteraction,
  MLRiskResult,
  NotificationRequest,
  AppointmentRequest,
  HospitalSearchRequest,
  NL2SQLRequest,
} from "./types";

// Base URLs for Django backend services
const DJANGO_BASE_URL = process.env.DJANGO_BASE_URL || "http://django-backend:8000";
const DJANGO_API_KEY = process.env.DJANGO_API_KEY || "";

// Neo4j connection
const NEO4J_URI = process.env.NEO4J_URI || "bolt://neo4j:7687";
const NEO4J_USER = process.env.NEO4J_USER || "neo4j";
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || "password";

let neo4jDriver: Driver | null = null;

function getNeo4jDriver(): Driver {
  if (!neo4jDriver) {
    neo4jDriver = neo4j.driver(
      NEO4J_URI,
      neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD),
      {
        maxConnectionLifetime: 3 * 60 * 60 * 1000, // 3 hours
        maxConnectionPoolSize: 50,
        connectionAcquisitionTimeout: 2 * 60 * 1000, // 2 min
      }
    );
    logger.info("Neo4j driver initialized", { uri: NEO4J_URI });
  }
  return neo4jDriver;
}

export async function closeNeo4jDriver(): Promise<void> {
  if (neo4jDriver) {
    await neo4jDriver.close();
    neo4jDriver = null;
    logger.info("Neo4j driver closed");
  }
}

// Axios instance for Django API calls
const djangoClient = axios.create({
  baseURL: DJANGO_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": DJANGO_API_KEY,
  },
});

export interface ToolDefinition {
  description: string;
  schema: Record<string, unknown>;
  execute: (params: Record<string, unknown>) => Promise<unknown>;
}

export type ToolRegistry = Record<string, ToolDefinition>;

export const TOOL_REGISTRY: ToolRegistry = {
  query_fhir_database: {
    description: "Query patient FHIR records including observations, conditions, medications, and diagnostic reports",
    schema: {
      type: "object",
      properties: {
        patient_id: {
          type: "string",
          description: "The patient's FHIR resource ID",
        },
        resource_type: {
          type: "string",
          enum: [
            "Observation",
            "Condition",
            "MedicationRequest",
            "DiagnosticReport",
            "AllergyIntolerance",
            "Encounter",
            "Procedure",
            "Immunization",
            "CarePlan",
            "ServiceRequest",
          ],
          description: "FHIR resource type to query",
        },
        filters: {
          type: "object",
          description: "Additional FHIR search parameters",
          properties: {
            date_from: { type: "string", description: "ISO date string" },
            date_to: { type: "string", description: "ISO date string" },
            status: { type: "string" },
            code: { type: "string", description: "LOINC or SNOMED code" },
            category: { type: "string" },
          },
        },
        limit: {
          type: "integer",
          description: "Maximum number of results",
          default: 20,
        },
      },
      required: ["patient_id", "resource_type"],
    },
    execute: async (params: Record<string, unknown>) => {
      const { patient_id, resource_type, filters = {}, limit = 20 } = params;

      logger.debug("query_fhir_database: executing", { patient_id, resource_type });

      const response = await djangoClient.get("/api/fhir/query/", {
        params: {
          patient_id,
          resource_type,
          limit,
          ...filters,
        },
      });

      return response.data;
    },
  },

  query_graph_database: {
    description: "Execute a Cypher query on Neo4j knowledge graph for drug interactions, clinical pathways, and disease relationships",
    schema: {
      type: "object",
      properties: {
        cypher_query: {
          type: "string",
          description: "Valid Cypher query string (read-only MATCH queries only)",
        },
        parameters: {
          type: "object",
          description: "Named parameters for the Cypher query",
        },
        timeout_ms: {
          type: "integer",
          description: "Query timeout in milliseconds",
          default: 10000,
        },
      },
      required: ["cypher_query"],
    },
    execute: async (params: Record<string, unknown>) => {
      const { cypher_query, parameters = {}, timeout_ms = 10000 } = params;
      const query = cypher_query as string;

      // Safety check: only allow read queries
      const trimmedQuery = query.trim().toUpperCase();
      if (
        trimmedQuery.startsWith("CREATE") ||
        trimmedQuery.startsWith("DELETE") ||
        trimmedQuery.startsWith("MERGE") ||
        trimmedQuery.startsWith("SET") ||
        trimmedQuery.startsWith("REMOVE") ||
        trimmedQuery.startsWith("DROP")
      ) {
        throw new Error("Only read-only MATCH queries are permitted via this tool");
      }

      logger.debug("query_graph_database: executing Cypher query", {
        query: query.substring(0, 100),
      });

      const driver = getNeo4jDriver();
      const session: Session = driver.session({
        defaultAccessMode: neo4j.session.READ,
      });

      try {
        const result = await session.run(query, parameters as Record<string, unknown>, {
          timeout: timeout_ms as number,
        });

        const records = result.records.map((record) => {
          const obj: Record<string, unknown> = {};
          record.keys.forEach((key) => {
            const value = record.get(key);
            // Convert Neo4j integers to JS numbers
            if (neo4j.isInt(value)) {
              obj[key as string] = value.toNumber();
            } else if (value && typeof value === "object" && "properties" in value) {
              // Neo4j Node
              const nodeProps = (value as { properties: Record<string, unknown> }).properties;
              const converted: Record<string, unknown> = {};
              for (const [k, v] of Object.entries(nodeProps)) {
                converted[k] = neo4j.isInt(v) ? (v as neo4j.Integer).toNumber() : v;
              }
              obj[key as string] = converted;
            } else {
              obj[key as string] = value;
            }
          });
          return obj;
        });

        return {
          records,
          record_count: records.length,
          query_summary: result.summary.counters.updates(),
        };
      } finally {
        await session.close();
      }
    },
  },

  vector_search: {
    description: "Perform semantic similarity search in Qdrant vector store for clinical guidelines, research papers, and care protocols",
    schema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Natural language query for semantic search",
        },
        collection: {
          type: "string",
          enum: [
            "clinical_guidelines",
            "research_papers",
            "care_protocols",
            "drug_information",
            "icd_codes",
            "patient_education",
          ],
          description: "Qdrant collection to search in",
          default: "clinical_guidelines",
        },
        top_k: {
          type: "integer",
          description: "Number of top results to return",
          default: 5,
          minimum: 1,
          maximum: 20,
        },
        score_threshold: {
          type: "number",
          description: "Minimum similarity score (0.0 to 1.0)",
          default: 0.7,
        },
        filters: {
          type: "object",
          description: "Metadata filters for the search",
        },
      },
      required: ["query"],
    },
    execute: async (params: Record<string, unknown>) => {
      const {
        query,
        collection = "clinical_guidelines",
        top_k = 5,
        score_threshold = 0.7,
        filters = {},
      } = params;

      logger.debug("vector_search: executing", { query, collection, top_k });

      const response = await djangoClient.post("/api/vector/search/", {
        query,
        collection,
        top_k,
        score_threshold,
        filters,
      });

      return response.data;
    },
  },

  check_drug_interactions: {
    description: "Check for drug-drug interactions using Neo4j backtracking graph search across medication combinations",
    schema: {
      type: "object",
      properties: {
        medications: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Drug name" },
              rxnorm_code: { type: "string", description: "RxNorm code" },
            },
            required: ["name"],
          },
          description: "List of medications to check for interactions",
          minItems: 2,
        },
        severity_filter: {
          type: "string",
          enum: ["all", "contraindicated", "major", "moderate"],
          description: "Filter by minimum interaction severity",
          default: "all",
        },
      },
      required: ["medications"],
    },
    execute: async (params: Record<string, unknown>) => {
      const { medications, severity_filter = "all" } = params;
      const meds = medications as Array<{ name: string; rxnorm_code?: string }>;

      logger.debug("check_drug_interactions: checking", {
        medication_count: meds.length,
        severity_filter,
      });

      const driver = getNeo4jDriver();
      const session: Session = driver.session({
        defaultAccessMode: neo4j.session.READ,
      });

      try {
        // Build list of drug names for query
        const drugNames = meds.map((m) => m.name.toLowerCase());
        const rxnormCodes = meds.filter((m) => m.rxnorm_code).map((m) => m.rxnorm_code);

        // Backtracking search for all pairs
        const interactions: DrugInteraction[] = [];

        for (let i = 0; i < drugNames.length; i++) {
          for (let j = i + 1; j < drugNames.length; j++) {
            const query = `
              MATCH (d1:Drug)-[r:INTERACTS_WITH]->(d2:Drug)
              WHERE (toLower(d1.name) CONTAINS $drug1 OR d1.rxnorm IN $codes1)
                AND (toLower(d2.name) CONTAINS $drug2 OR d2.rxnorm IN $codes2)
              RETURN d1.name AS drug1, d2.name AS drug2,
                     r.severity AS severity, r.description AS description,
                     r.mechanism AS mechanism, r.management AS management
              UNION
              MATCH (d1:Drug)-[r:INTERACTS_WITH]->(d2:Drug)
              WHERE (toLower(d1.name) CONTAINS $drug2 OR d1.rxnorm IN $codes2)
                AND (toLower(d2.name) CONTAINS $drug1 OR d2.rxnorm IN $codes1)
              RETURN d1.name AS drug1, d2.name AS drug2,
                     r.severity AS severity, r.description AS description,
                     r.mechanism AS mechanism, r.management AS management
            `;

            const codes1 = rxnormCodes.length > 0 ? [rxnormCodes[i] || ""] : [""];
            const codes2 = rxnormCodes.length > 0 ? [rxnormCodes[j] || ""] : [""];

            const result = await session.run(query, {
              drug1: drugNames[i],
              drug2: drugNames[j],
              codes1,
              codes2,
            });

            for (const record of result.records) {
              const severity = record.get("severity") as string;
              if (
                severity_filter === "all" ||
                severity === severity_filter ||
                (severity_filter === "major" &&
                  (severity === "major" || severity === "contraindicated")) ||
                (severity_filter === "moderate" &&
                  (severity === "moderate" ||
                    severity === "major" ||
                    severity === "contraindicated"))
              ) {
                interactions.push({
                  drug1: record.get("drug1") as string,
                  drug2: record.get("drug2") as string,
                  severity: severity as DrugInteraction["severity"],
                  description: record.get("description") as string,
                  mechanism: record.get("mechanism") as string | undefined,
                  management: record.get("management") as string | undefined,
                });
              }
            }
          }
        }

        const contraindicated = interactions.filter((i) => i.severity === "contraindicated");
        const major = interactions.filter((i) => i.severity === "major");
        const moderate = interactions.filter((i) => i.severity === "moderate");
        const minor = interactions.filter((i) => i.severity === "minor");

        return {
          total_interactions: interactions.length,
          contraindicated_count: contraindicated.length,
          major_count: major.length,
          moderate_count: moderate.length,
          minor_count: minor.length,
          interactions,
          safe_to_combine: contraindicated.length === 0 && major.length === 0,
          checked_medications: drugNames,
        };
      } finally {
        await session.close();
      }
    },
  },

  calculate_risk_score: {
    description: "Run machine learning risk model to calculate patient risk scores for specific conditions",
    schema: {
      type: "object",
      properties: {
        patient_id: {
          type: "string",
          description: "Patient ID to calculate risk for",
        },
        model_type: {
          type: "string",
          enum: [
            "diabetes_complication",
            "cardiovascular",
            "readmission_30day",
            "sepsis",
            "kidney_disease_progression",
            "hypoglycemia",
            "fall_risk",
            "medication_adherence",
          ],
          description: "Type of risk model to run",
        },
        override_features: {
          type: "object",
          description: "Optional feature overrides for what-if scenarios",
        },
      },
      required: ["patient_id", "model_type"],
    },
    execute: async (params: Record<string, unknown>) => {
      const { patient_id, model_type, override_features = {} } = params;

      logger.debug("calculate_risk_score: executing", { patient_id, model_type });

      const response = await djangoClient.post("/api/ml/risk-score/", {
        patient_id,
        model_type,
        override_features,
      });

      const result = response.data as MLRiskResult;
      return result;
    },
  },

  send_notification: {
    description: "Send a notification to a patient, provider, or care team member via SMS, email, push notification, or in-app message",
    schema: {
      type: "object",
      properties: {
        recipient_type: {
          type: "string",
          enum: ["patient", "provider", "care_team"],
          description: "Type of notification recipient",
        },
        recipient_id: {
          type: "string",
          description: "ID of the recipient",
        },
        notification_type: {
          type: "string",
          enum: ["sms", "email", "push", "in_app"],
          description: "Notification delivery channel",
        },
        priority: {
          type: "string",
          enum: ["low", "normal", "high", "urgent"],
          description: "Notification priority level",
          default: "normal",
        },
        subject: {
          type: "string",
          description: "Notification subject/title",
        },
        body: {
          type: "string",
          description: "Notification message body",
        },
        patient_id: {
          type: "string",
          description: "Associated patient ID if applicable",
        },
        metadata: {
          type: "object",
          description: "Additional metadata for the notification",
        },
      },
      required: ["recipient_type", "recipient_id", "notification_type", "subject", "body"],
    },
    execute: async (params: Record<string, unknown>) => {
      const notification = params as unknown as NotificationRequest;

      logger.debug("send_notification: executing", {
        recipient_type: notification.recipient_type,
        notification_type: notification.notification_type,
        priority: notification.priority,
      });

      const response = await djangoClient.post("/api/notifications/send/", notification);
      return response.data;
    },
  },

  schedule_appointment: {
    description: "Schedule a medical appointment for a patient with a provider",
    schema: {
      type: "object",
      properties: {
        patient_id: {
          type: "string",
          description: "Patient ID",
        },
        provider_id: {
          type: "string",
          description: "Provider ID (optional - system will find available provider if not specified)",
        },
        appointment_type: {
          type: "string",
          enum: [
            "follow_up",
            "urgent_care",
            "specialist_referral",
            "lab_work",
            "imaging",
            "telehealth",
            "annual_wellness",
            "chronic_care_management",
            "diabetes_education",
            "cardiac_rehab",
          ],
          description: "Type of appointment",
        },
        preferred_date: {
          type: "string",
          description: "Preferred appointment date in ISO format (YYYY-MM-DD)",
        },
        preferred_time: {
          type: "string",
          description: "Preferred time slot (e.g., 'morning', 'afternoon', 'HH:MM')",
        },
        duration_minutes: {
          type: "integer",
          description: "Expected appointment duration in minutes",
          default: 30,
        },
        reason: {
          type: "string",
          description: "Reason for the appointment",
        },
        urgency: {
          type: "string",
          enum: ["routine", "urgent", "emergency"],
          description: "Appointment urgency level",
          default: "routine",
        },
        notes: {
          type: "string",
          description: "Additional notes for the appointment",
        },
      },
      required: ["patient_id", "appointment_type", "reason"],
    },
    execute: async (params: Record<string, unknown>) => {
      const appointmentRequest = params as unknown as AppointmentRequest;

      logger.debug("schedule_appointment: executing", {
        patient_id: appointmentRequest.patient_id,
        appointment_type: appointmentRequest.appointment_type,
        urgency: appointmentRequest.urgency,
      });

      const response = await djangoClient.post(
        "/api/scheduling/appointments/",
        appointmentRequest
      );
      return response.data;
    },
  },

  find_hospital: {
    description: "Find nearest hospitals or healthcare facilities based on patient location and required specialties",
    schema: {
      type: "object",
      properties: {
        patient_id: {
          type: "string",
          description: "Patient ID to use their registered address",
        },
        latitude: {
          type: "number",
          description: "Latitude coordinate (overrides patient address if provided)",
        },
        longitude: {
          type: "number",
          description: "Longitude coordinate (overrides patient address if provided)",
        },
        radius_km: {
          type: "number",
          description: "Search radius in kilometers",
          default: 25,
        },
        specialties: {
          type: "array",
          items: { type: "string" },
          description: "Required medical specialties",
        },
        emergency_capable: {
          type: "boolean",
          description: "Filter for emergency department capability",
          default: false,
        },
        insurance_accepted: {
          type: "string",
          description: "Insurance plan ID to filter accepted facilities",
        },
      },
      required: [],
    },
    execute: async (params: Record<string, unknown>) => {
      const searchRequest = params as unknown as HospitalSearchRequest;

      // Validate that either patient_id or coordinates are provided
      if (!searchRequest.patient_id && (searchRequest.latitude === undefined || searchRequest.longitude === undefined)) {
        throw new Error("Either patient_id or latitude/longitude coordinates must be provided");
      }

      logger.debug("find_hospital: executing", {
        patient_id: searchRequest.patient_id,
        radius_km: searchRequest.radius_km,
        emergency_capable: searchRequest.emergency_capable,
      });

      const response = await djangoClient.post(
        "/api/geospatial/find-hospital/",
        searchRequest
      );
      return response.data;
    },
  },

  nl2sql_query: {
    description: "Convert a natural language question about patient data into a SQL query and execute it against the clinical database",
    schema: {
      type: "object",
      properties: {
        natural_language_query: {
          type: "string",
          description: "Natural language question to convert to SQL",
        },
        patient_id: {
          type: "string",
          description: "Patient ID to scope the query (adds WHERE patient_id = ? automatically)",
        },
        context: {
          type: "string",
          description: "Additional context to help with query generation",
        },
        allowed_tables: {
          type: "array",
          items: { type: "string" },
          description: "Restrict query to specific tables for safety",
        },
      },
      required: ["natural_language_query"],
    },
    execute: async (params: Record<string, unknown>) => {
      const nl2sqlRequest = params as unknown as NL2SQLRequest;

      logger.debug("nl2sql_query: executing", {
        query_preview: nl2sqlRequest.natural_language_query.substring(0, 100),
        patient_id: nl2sqlRequest.patient_id,
      });

      const response = await djangoClient.post(
        "/api/nl2sql/query/",
        nl2sqlRequest
      );
      return response.data;
    },
  },
};

export function getToolDefinitions(): MCPTool[] {
  return Object.entries(TOOL_REGISTRY).map(([name, def]) => ({
    name,
    description: def.description,
    parameters: def.schema,
  }));
}

export async function executeTool(
  toolName: string,
  params: Record<string, unknown>
): Promise<{ result: unknown; execution_time_ms: number }> {
  const tool = TOOL_REGISTRY[toolName];

  if (!tool) {
    throw new Error(`Unknown tool: ${toolName}. Available tools: ${Object.keys(TOOL_REGISTRY).join(", ")}`);
  }

  const startTime = Date.now();

  try {
    const result = await tool.execute(params);
    const execution_time_ms = Date.now() - startTime;

    logger.info("Tool executed successfully", {
      tool_name: toolName,
      execution_time_ms,
    });

    return { result, execution_time_ms };
  } catch (error) {
    const execution_time_ms = Date.now() - startTime;

    logger.error("Tool execution failed", {
      tool_name: toolName,
      execution_time_ms,
      error: error instanceof Error ? error.message : String(error),
    });

    throw error;
  }
}
