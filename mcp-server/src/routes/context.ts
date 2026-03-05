import { Router, Response } from "express";
import { z } from "zod";
import { AuthenticatedRequest } from "../middleware/auth";
import { getMCPServer } from "../mcp/server";
import { logger } from "../utils/logger";
import {
  mcpContextRequestsTotal,
  mcpContextBuildDurationSeconds,
} from "../utils/metrics";

const router = Router();

const ContextRequestSchema = z.object({
  patient_id: z.string().min(1, "patient_id is required"),
  agent_id: z.string().min(1, "agent_id is required"),
  include_history: z.boolean().optional().default(true),
  history_limit: z.number().int().min(1).max(100).optional().default(20),
  tool_filter: z.array(z.string()).optional(),
});

// POST /mcp/context
router.post("/context", async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  const startTime = Date.now();
  let patientId = "unknown";
  let agentId = "unknown";

  try {
    const parseResult = ContextRequestSchema.safeParse(req.body);
    if (!parseResult.success) {
      res.status(400).json({
        error: "Invalid request body",
        details: parseResult.error.flatten(),
      });
      return;
    }

    const { patient_id, agent_id, include_history, history_limit } = parseResult.data;
    patientId = patient_id;
    agentId = agent_id;

    // Authorization: ensure the requesting agent/user has access to this patient
    const user = req.user;
    if (user?.patient_id && user.patient_id !== patient_id) {
      logger.warn("context route: patient_id mismatch", {
        requested_patient: patient_id,
        token_patient: user.patient_id,
        agent_id,
      });
      res.status(403).json({ error: "Access denied: patient_id mismatch" });
      return;
    }

    const mcpServer = getMCPServer();

    // Check Redis cache first
    const cacheKey = `mcp_context:${patient_id}:${agent_id}`;
    const cachedContext = await mcpServer.getCachedContext(cacheKey);

    if (cachedContext) {
      const duration = (Date.now() - startTime) / 1000;
      mcpContextRequestsTotal.labels({ status: "cache_hit", agent_id }).inc();
      mcpContextBuildDurationSeconds.observe(duration);

      logger.debug("context route: returning cached context", {
        patient_id,
        agent_id,
        duration_ms: Date.now() - startTime,
      });

      res.status(200).json({
        ...cachedContext,
        _meta: {
          cache: "hit",
          duration_ms: Date.now() - startTime,
        },
      });
      return;
    }

    // Build full context
    logger.info("context route: building MCP context", { patient_id, agent_id });

    const historyLimit = include_history ? history_limit : 0;
    const context = await mcpServer.buildFullContext(patient_id, agent_id, historyLimit);

    // Cache for 60 seconds
    await mcpServer.cacheContext(cacheKey, context, 60);

    const duration = (Date.now() - startTime) / 1000;
    mcpContextRequestsTotal.labels({ status: "success", agent_id }).inc();
    mcpContextBuildDurationSeconds.observe(duration);

    logger.info("context route: context built successfully", {
      patient_id,
      agent_id,
      duration_ms: Date.now() - startTime,
      conditions_count: context.context.patient.conditions.length,
      medications_count: context.context.patient.medications.length,
    });

    res.status(200).json({
      ...context,
      _meta: {
        cache: "miss",
        duration_ms: Date.now() - startTime,
      },
    });
  } catch (error) {
    const duration = (Date.now() - startTime) / 1000;
    mcpContextRequestsTotal.labels({ status: "error", agent_id: agentId }).inc();
    mcpContextBuildDurationSeconds.observe(duration);

    logger.error("context route: error building context", {
      patient_id: patientId,
      agent_id: agentId,
      error: error instanceof Error ? error.message : String(error),
      duration_ms: Date.now() - startTime,
    });

    if (error instanceof Error && error.message.includes("not found")) {
      res.status(404).json({ error: error.message });
    } else {
      res.status(500).json({
        error: "Failed to build MCP context",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }
});

// DELETE /mcp/context/:patientId - invalidate cache
router.delete(
  "/context/:patientId",
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    const { patientId } = req.params;

    // Require admin role for cache invalidation
    const user = req.user;
    if (!user?.roles.includes("admin") && !user?.roles.includes("system")) {
      res.status(403).json({ error: "Insufficient permissions to invalidate cache" });
      return;
    }

    try {
      const mcpServer = getMCPServer();
      await mcpServer.invalidatePatientCache(patientId);

      logger.info("context route: cache invalidated", {
        patient_id: patientId,
        invalidated_by: user.sub,
      });

      res.status(200).json({
        message: `Cache invalidated for patient ${patientId}`,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error("context route: cache invalidation failed", {
        patient_id: patientId,
        error: error instanceof Error ? error.message : String(error),
      });
      res.status(500).json({ error: "Cache invalidation failed" });
    }
  }
);

// GET /mcp/conversation/:patientId/:agentId - get conversation history
router.get(
  "/conversation/:patientId/:agentId",
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    const { patientId, agentId } = req.params;
    const limitStr = req.query["limit"] as string | undefined;
    const limit = limitStr ? parseInt(limitStr, 10) : 20;

    try {
      const mcpServer = getMCPServer();
      const history = await mcpServer.getConversationHistory(patientId, agentId, limit);

      res.status(200).json({
        patient_id: patientId,
        agent_id: agentId,
        messages: history,
        count: history.length,
      });
    } catch (error) {
      logger.error("context route: failed to get conversation history", {
        patient_id: patientId,
        agent_id: agentId,
        error: error instanceof Error ? error.message : String(error),
      });
      res.status(500).json({ error: "Failed to retrieve conversation history" });
    }
  }
);

export default router;
