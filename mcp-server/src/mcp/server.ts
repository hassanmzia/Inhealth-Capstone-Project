import { createClient, RedisClientType } from "redis";
import axios from "axios";
import { logger } from "../utils/logger";
import {
  MCPContext,
  PatientContext,
  ClinicalConstraints,
  Message,
} from "./types";
import { fetchPatientFromFHIR, fetchRelevantGuidelines } from "./context";
import { getToolDefinitions } from "./tools";

const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";
const DJANGO_BASE_URL = process.env.DJANGO_BASE_URL || "http://django-backend:8000";
const DJANGO_API_KEY = process.env.DJANGO_API_KEY || "";

const CONVERSATION_HISTORY_TTL = 60 * 60 * 2; // 2 hours in seconds
const CONVERSATION_MAX_MESSAGES = 100;

const djangoClient = axios.create({
  baseURL: DJANGO_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": DJANGO_API_KEY,
  },
});

export class MCPServer {
  private redisClient: RedisClientType;
  private isConnected: boolean = false;

  constructor() {
    this.redisClient = createClient({
      url: REDIS_URL,
      socket: {
        reconnectStrategy: (retries) => {
          if (retries > 10) {
            logger.error("MCPServer: Redis max reconnect attempts reached");
            return new Error("Redis reconnect failed");
          }
          return Math.min(retries * 100, 3000);
        },
      },
    }) as RedisClientType;

    this.redisClient.on("error", (err) => {
      logger.error("MCPServer: Redis client error", { error: err.message });
      this.isConnected = false;
    });

    this.redisClient.on("connect", () => {
      logger.info("MCPServer: Redis connected");
      this.isConnected = true;
    });

    this.redisClient.on("reconnecting", () => {
      logger.warn("MCPServer: Redis reconnecting");
      this.isConnected = false;
    });
  }

  async connect(): Promise<void> {
    await this.redisClient.connect();
    logger.info("MCPServer: Redis connection established", { url: REDIS_URL });
  }

  async disconnect(): Promise<void> {
    await this.redisClient.quit();
    logger.info("MCPServer: Redis connection closed");
  }

  async buildPatientContext(patientId: string): Promise<PatientContext> {
    const cacheKey = `patient_context:${patientId}`;

    try {
      // Check cache first
      const cached = await this.redisClient.get(cacheKey);
      if (cached) {
        logger.debug("buildPatientContext: cache hit", { patient_id: patientId });
        return JSON.parse(cached) as PatientContext;
      }
    } catch (err) {
      logger.warn("buildPatientContext: cache lookup failed", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }

    logger.debug("buildPatientContext: cache miss, fetching from FHIR API", {
      patient_id: patientId,
    });

    const patientContext = await fetchPatientFromFHIR(patientId);

    // Cache for 5 minutes
    try {
      await this.redisClient.setEx(cacheKey, 300, JSON.stringify(patientContext));
    } catch (err) {
      logger.warn("buildPatientContext: failed to cache patient context", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }

    return patientContext;
  }

  async buildConstraints(patientId: string): Promise<ClinicalConstraints> {
    const cacheKey = `constraints:${patientId}`;

    try {
      const cached = await this.redisClient.get(cacheKey);
      if (cached) {
        logger.debug("buildConstraints: cache hit", { patient_id: patientId });
        return JSON.parse(cached) as ClinicalConstraints;
      }
    } catch (err) {
      logger.warn("buildConstraints: cache lookup failed", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }

    // Get patient conditions first
    let conditions: PatientContext["conditions"] = [];
    try {
      const conditionsResponse = await djangoClient.get("/api/fhir/query/", {
        params: {
          patient_id: patientId,
          resource_type: "Condition",
          status: "active",
          limit: 50,
        },
      });

      const entries = conditionsResponse.data.entry || [];
      conditions = entries.map(
        (entry: {
          resource?: {
            id?: string;
            code?: { coding?: Array<{ code?: string; system?: string; display?: string }> };
            clinicalStatus?: { coding?: Array<{ code?: string }> };
            verificationStatus?: { coding?: Array<{ code?: string }> };
            recordedDate?: string;
          };
        }) => {
          const resource = entry.resource || {};
          const coding = resource.code?.coding?.[0] || {};
          return {
            id: resource.id || "",
            code: coding.code || "",
            system: (coding.system?.includes("snomed") ? "SNOMED-CT" : "ICD-10") as "ICD-10" | "SNOMED-CT",
            display: coding.display || "Unknown",
            status: resource.clinicalStatus?.coding?.[0]?.code || "active",
            recorded_date: resource.recordedDate || new Date().toISOString(),
            clinical_status: resource.clinicalStatus?.coding?.[0]?.code || "active",
            verification_status:
              resource.verificationStatus?.coding?.[0]?.code || "confirmed",
          };
        }
      );
    } catch (err) {
      logger.warn("buildConstraints: failed to fetch conditions", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }

    const constraints = await fetchRelevantGuidelines(conditions);

    // Cache for 10 minutes
    try {
      await this.redisClient.setEx(cacheKey, 600, JSON.stringify(constraints));
    } catch (err) {
      logger.warn("buildConstraints: failed to cache constraints", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }

    return constraints;
  }

  async getConversationHistory(
    patientId: string,
    agentId: string,
    limit: number = 20
  ): Promise<Message[]> {
    const historyKey = `conversation:${patientId}:${agentId}`;

    try {
      const raw = await this.redisClient.lRange(historyKey, 0, limit - 1);

      const messages: Message[] = raw
        .map((item) => {
          try {
            return JSON.parse(item) as Message;
          } catch {
            return null;
          }
        })
        .filter((m): m is Message => m !== null)
        .reverse(); // lRange returns newest first, we want chronological

      logger.debug("getConversationHistory: fetched", {
        patient_id: patientId,
        agent_id: agentId,
        message_count: messages.length,
      });

      return messages;
    } catch (err) {
      logger.error("getConversationHistory: Redis error", {
        patient_id: patientId,
        agent_id: agentId,
        error: err instanceof Error ? err.message : String(err),
      });
      return [];
    }
  }

  async appendConversationMessage(
    patientId: string,
    agentId: string,
    message: Message
  ): Promise<void> {
    const historyKey = `conversation:${patientId}:${agentId}`;

    try {
      await this.redisClient.lPush(historyKey, JSON.stringify(message));
      // Keep only the last N messages
      await this.redisClient.lTrim(historyKey, 0, CONVERSATION_MAX_MESSAGES - 1);
      // Refresh TTL
      await this.redisClient.expire(historyKey, CONVERSATION_HISTORY_TTL);
    } catch (err) {
      logger.error("appendConversationMessage: Redis error", {
        patient_id: patientId,
        agent_id: agentId,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  async clearConversationHistory(patientId: string, agentId: string): Promise<void> {
    const historyKey = `conversation:${patientId}:${agentId}`;
    try {
      await this.redisClient.del(historyKey);
      logger.info("clearConversationHistory: cleared", {
        patient_id: patientId,
        agent_id: agentId,
      });
    } catch (err) {
      logger.error("clearConversationHistory: Redis error", {
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  buildToolRegistry() {
    return getToolDefinitions();
  }

  async buildFullContext(
    patientId: string,
    agentId: string,
    historyLimit: number = 20
  ): Promise<MCPContext> {
    const [patientContext, constraints, conversationHistory] = await Promise.all([
      this.buildPatientContext(patientId),
      this.buildConstraints(patientId),
      this.getConversationHistory(patientId, agentId, historyLimit),
    ]);

    const tools = this.buildToolRegistry();

    return {
      protocol: "MCP/1.0",
      context: {
        patient: patientContext,
        conversation_history: conversationHistory,
        available_tools: tools,
        constraints,
      },
    };
  }

  async cacheContext(
    cacheKey: string,
    context: MCPContext,
    ttlSeconds: number = 60
  ): Promise<void> {
    try {
      await this.redisClient.setEx(cacheKey, ttlSeconds, JSON.stringify(context));
    } catch (err) {
      logger.warn("cacheContext: failed to cache", {
        cache_key: cacheKey,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  async getCachedContext(cacheKey: string): Promise<MCPContext | null> {
    try {
      const cached = await this.redisClient.get(cacheKey);
      if (cached) {
        return JSON.parse(cached) as MCPContext;
      }
    } catch (err) {
      logger.warn("getCachedContext: failed", {
        cache_key: cacheKey,
        error: err instanceof Error ? err.message : String(err),
      });
    }
    return null;
  }

  async invalidatePatientCache(patientId: string): Promise<void> {
    try {
      const keys = await this.redisClient.keys(`*:${patientId}:*`);
      const patientKeys = await this.redisClient.keys(`patient_context:${patientId}`);
      const constraintKeys = await this.redisClient.keys(`constraints:${patientId}`);

      const allKeys = [...keys, ...patientKeys, ...constraintKeys];
      if (allKeys.length > 0) {
        await this.redisClient.del(allKeys);
        logger.info("invalidatePatientCache: invalidated", {
          patient_id: patientId,
          keys_deleted: allKeys.length,
        });
      }
    } catch (err) {
      logger.error("invalidatePatientCache: error", {
        patient_id: patientId,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  isRedisConnected(): boolean {
    return this.isConnected;
  }

  async ping(): Promise<boolean> {
    try {
      const result = await this.redisClient.ping();
      return result === "PONG";
    } catch {
      return false;
    }
  }
}

// Singleton instance
let mcpServerInstance: MCPServer | null = null;

export function getMCPServer(): MCPServer {
  if (!mcpServerInstance) {
    mcpServerInstance = new MCPServer();
  }
  return mcpServerInstance;
}
