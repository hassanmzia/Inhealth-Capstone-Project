import { Router, Request, Response } from "express";
import { z } from "zod";
import {
  AGENT_REGISTRY,
  getAgentById,
  getAgentsByType,
  getAgentsByTier,
} from "../a2a/registry";
import { getA2AGateway } from "../a2a/gateway";
import { logger } from "../utils/logger";
import { A2ADiscoveryDocument, AgentCard } from "../a2a/types";
import { A2A_CHANNELS } from "../a2a/types";

const router = Router();

const GATEWAY_VERSION = "1.0.0";
const GATEWAY_ENDPOINT = process.env.GATEWAY_ENDPOINT || "http://a2a-gateway:3002";

// Standard A2A agent discovery endpoint
// GET /.well-known/agent.json
router.get("/.well-known/agent.json", async (_req: Request, res: Response): Promise<void> => {
  const gateway = getA2AGateway();

  // Try to get live agent statuses from Redis, fall back to static registry
  let agents: AgentCard[] = AGENT_REGISTRY;
  try {
    const liveAgents = await gateway.getAllAgents();
    if (liveAgents.length > 0) {
      agents = liveAgents;
    }
  } catch (err) {
    logger.warn("agent discovery: could not fetch live agent statuses", {
      error: err instanceof Error ? err.message : String(err),
    });
  }

  const discoveryDoc: A2ADiscoveryDocument = {
    gateway: {
      version: GATEWAY_VERSION,
      endpoint: GATEWAY_ENDPOINT,
      websocket_endpoint: GATEWAY_ENDPOINT.replace("http", "ws") + "/ws",
      capabilities: [
        "message_routing",
        "task_delegation",
        "agent_registry",
        "websocket_streaming",
        "redis_pubsub",
        "agent_discovery",
      ],
    },
    agents,
    channels: [...A2A_CHANNELS],
    task_types: [
      "glucose_monitoring",
      "cardiac_monitoring",
      "vital_signs",
      "lab_results",
      "medication_adherence",
      "drug_interaction_check",
      "pattern_recognition",
      "comorbidity_analysis",
      "symptom_assessment",
      "imaging_analysis",
      "diabetes_risk",
      "cardiovascular_risk",
      "readmission_risk",
      "mental_health_risk",
      "kidney_disease_risk",
      "fall_risk",
      "prescription_recommendation",
      "triage",
      "care_plan",
      "patient_education",
      "send_notification",
      "schedule_appointment",
      "ehr_write",
      "emergency_response",
      "billing_authorization",
      "literature_search",
      "cohort_analysis",
      "clinical_trial_matching",
    ],
    timestamp: new Date().toISOString(),
  };

  res.status(200).json(discoveryDoc);
});

// GET /a2a/agents - list all registered agents
router.get("/a2a/agents", async (req: Request, res: Response): Promise<void> => {
  const { type, tier, status, capability } = req.query;
  const gateway = getA2AGateway();

  try {
    // Try to get live statuses from Redis
    let agents: AgentCard[] = AGENT_REGISTRY;
    try {
      const liveAgents = await gateway.getAllAgents();
      if (liveAgents.length > 0) {
        agents = liveAgents;
      }
    } catch {
      // Use static registry as fallback
    }

    // Apply filters
    if (type && typeof type === "string") {
      agents = agents.filter((a) => a.type === type);
    }

    if (tier && typeof tier === "string") {
      const tierNum = parseInt(tier, 10);
      agents = agents.filter((a) => a.tier === tierNum);
    }

    if (status && typeof status === "string") {
      agents = agents.filter((a) => a.status === status);
    }

    if (capability && typeof capability === "string") {
      agents = agents.filter((a) => a.capabilities.includes(capability));
    }

    res.status(200).json({
      agents,
      count: agents.length,
      total: AGENT_REGISTRY.length,
      filters: { type, tier, status, capability },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    logger.error("agents route: error listing agents", {
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to retrieve agents" });
  }
});

// GET /a2a/agents/:id - get specific agent card
router.get("/a2a/agents/:id", async (req: Request, res: Response): Promise<void> => {
  const agentId = parseInt(req.params["id"] || "0", 10);

  if (isNaN(agentId) || agentId <= 0) {
    res.status(400).json({ error: "Invalid agent ID" });
    return;
  }

  const gateway = getA2AGateway();

  try {
    // Try live status first
    let agent: AgentCard | null | undefined = await gateway.getAgentStatus(agentId);

    // Fall back to static registry
    if (!agent) {
      agent = getAgentById(agentId);
    }

    if (!agent) {
      res.status(404).json({
        error: `Agent ${agentId} not found`,
        available_ids: AGENT_REGISTRY.map((a) => a.id),
      });
      return;
    }

    res.status(200).json(agent);
  } catch (error) {
    logger.error("agents route: error fetching agent", {
      agent_id: agentId,
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to retrieve agent" });
  }
});

// POST /a2a/agents/register - register a new agent or update existing
router.post("/a2a/agents/register", async (req: Request, res: Response): Promise<void> => {
  const AgentCardSchema = z.object({
    id: z.number().int().positive(),
    name: z.string().min(1),
    type: z.enum(["monitoring", "diagnostic", "risk", "intervention", "action", "research", "orchestration"]),
    tier: z.number().int().min(1).max(6),
    description: z.string().min(1),
    capabilities: z.array(z.string()),
    subscribed_channels: z.array(z.string()),
    publishes_to: z.array(z.string()),
    endpoint: z.string().url(),
    status: z.enum(["active", "idle", "error", "offline", "maintenance"]),
    last_heartbeat: z.string(),
  });

  const parseResult = AgentCardSchema.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({
      error: "Invalid agent card",
      details: parseResult.error.flatten(),
    });
    return;
  }

  const gateway = getA2AGateway();

  try {
    await gateway.registerAgent(parseResult.data);

    res.status(201).json({
      message: "Agent registered successfully",
      agent_id: parseResult.data.id,
      agent_name: parseResult.data.name,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    logger.error("agents route: error registering agent", {
      agent_id: req.body.id,
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to register agent" });
  }
});

// POST /a2a/agents/:id/heartbeat - update agent heartbeat
router.post("/a2a/agents/:id/heartbeat", async (req: Request, res: Response): Promise<void> => {
  const agentId = parseInt(req.params["id"] || "0", 10);

  if (isNaN(agentId) || agentId <= 0) {
    res.status(400).json({ error: "Invalid agent ID" });
    return;
  }

  const gateway = getA2AGateway();

  try {
    await gateway.updateAgentHeartbeat({
      agent_id: agentId,
      timestamp: new Date().toISOString(),
      status: req.body.status || "active",
      metrics: req.body.metrics,
    });

    res.status(200).json({
      message: "Heartbeat recorded",
      agent_id: agentId,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    logger.error("agents route: error updating heartbeat", {
      agent_id: agentId,
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to update heartbeat" });
  }
});

// GET /a2a/agents/type/:type - get agents by type
router.get("/a2a/agents/type/:type", async (req: Request, res: Response): Promise<void> => {
  const { type } = req.params;
  const validTypes = ["monitoring", "diagnostic", "risk", "intervention", "action", "research", "orchestration"];

  if (!validTypes.includes(type || "")) {
    res.status(400).json({
      error: `Invalid agent type: ${type}`,
      valid_types: validTypes,
    });
    return;
  }

  const agents = getAgentsByType(type as AgentCard["type"]);

  res.status(200).json({
    type,
    agents,
    count: agents.length,
  });
});

// GET /a2a/agents/tier/:tier - get agents by tier
router.get("/a2a/agents/tier/:tier", async (req: Request, res: Response): Promise<void> => {
  const tier = parseInt(req.params["tier"] || "0", 10);

  if (isNaN(tier) || tier < 1 || tier > 6) {
    res.status(400).json({
      error: "Tier must be between 1 and 6",
      tier_descriptions: {
        1: "Monitoring Agents",
        2: "Diagnostic Agents",
        3: "Risk Assessment Agents",
        4: "Intervention Agents",
        5: "Action Agents",
        6: "Research System Agents",
      },
    });
    return;
  }

  const agents = getAgentsByTier(tier);

  res.status(200).json({
    tier,
    agents,
    count: agents.length,
  });
});

export default router;
