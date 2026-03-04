import { Router, Response } from "express";
import { z } from "zod";
import { AuthenticatedRequest } from "../middleware/auth";
import { executeTool, TOOL_REGISTRY } from "../mcp/tools";
import { logger } from "../utils/logger";
import {
  mcpToolExecutionsTotal,
  mcpToolExecutionDurationSeconds,
} from "../utils/metrics";
import { AuditLog } from "../mcp/types";

const router = Router();

const ToolExecuteRequestSchema = z.object({
  tool_name: z.string().min(1, "tool_name is required"),
  parameters: z.record(z.unknown()).default({}),
  patient_id: z.string().optional(),
  agent_id: z.string().min(1, "agent_id is required"),
  correlation_id: z.string().optional(),
});

async function writeAuditLog(auditEntry: AuditLog): Promise<void> {
  // In production, write to a persistent audit store (PostgreSQL audit table)
  // For now, log via Winston with a structured audit marker
  logger.info("AUDIT", {
    audit: true,
    ...auditEntry,
  });
}

// POST /mcp/tools/execute
router.post("/tools/execute", async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  const startTime = Date.now();
  let toolName = "unknown";
  let agentId = "unknown";

  try {
    const parseResult = ToolExecuteRequestSchema.safeParse(req.body);
    if (!parseResult.success) {
      res.status(400).json({
        error: "Invalid request body",
        details: parseResult.error.flatten(),
      });
      return;
    }

    const { tool_name, parameters, patient_id, agent_id, correlation_id } = parseResult.data;
    toolName = tool_name;
    agentId = agent_id;

    // Validate tool exists
    if (!TOOL_REGISTRY[tool_name]) {
      res.status(404).json({
        error: `Tool '${tool_name}' not found`,
        available_tools: Object.keys(TOOL_REGISTRY),
      });
      return;
    }

    logger.info("tools route: executing tool", {
      tool_name,
      agent_id,
      patient_id,
      correlation_id,
      ip: req.ip,
    });

    // Execute the tool
    const { result, execution_time_ms } = await executeTool(tool_name, parameters);

    // Record metrics
    mcpToolExecutionsTotal.labels({ tool_name, status: "success" }).inc();
    mcpToolExecutionDurationSeconds.labels({ tool_name }).observe(execution_time_ms / 1000);

    // Write audit log
    await writeAuditLog({
      event_type: "tool_execution",
      agent_id,
      patient_id,
      tool_name,
      parameters: sanitizeParamsForAudit(parameters),
      result_summary: summarizeResult(result),
      success: true,
      execution_time_ms,
      timestamp: new Date().toISOString(),
      ip_address: req.ip,
      correlation_id,
    });

    const response = {
      tool_name,
      result,
      success: true,
      execution_time_ms,
      timestamp: new Date().toISOString(),
      correlation_id,
    };

    res.status(200).json(response);
  } catch (error) {
    const execution_time_ms = Date.now() - startTime;

    mcpToolExecutionsTotal.labels({ tool_name: toolName, status: "error" }).inc();
    mcpToolExecutionDurationSeconds
      .labels({ tool_name: toolName })
      .observe(execution_time_ms / 1000);

    const errorMessage = error instanceof Error ? error.message : String(error);

    // Write audit log for failure
    await writeAuditLog({
      event_type: "tool_execution",
      agent_id: agentId,
      tool_name: toolName,
      success: false,
      error: errorMessage,
      execution_time_ms,
      timestamp: new Date().toISOString(),
      ip_address: req.ip,
    });

    logger.error("tools route: tool execution failed", {
      tool_name: toolName,
      agent_id: agentId,
      error: errorMessage,
      execution_time_ms,
    });

    const statusCode = errorMessage.includes("not found")
      ? 404
      : errorMessage.includes("not permitted") || errorMessage.includes("Access denied")
      ? 403
      : 500;

    res.status(statusCode).json({
      tool_name: toolName,
      success: false,
      error: errorMessage,
      execution_time_ms,
      timestamp: new Date().toISOString(),
    });
  }
});

// GET /mcp/tools - list all available tools
router.get("/tools", async (_req: AuthenticatedRequest, res: Response): Promise<void> => {
  const tools = Object.entries(TOOL_REGISTRY).map(([name, def]) => ({
    name,
    description: def.description,
    parameters: def.schema,
  }));

  res.status(200).json({
    tools,
    count: tools.length,
    timestamp: new Date().toISOString(),
  });
});

// GET /mcp/tools/:toolName - get specific tool definition
router.get("/tools/:toolName", async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  const { toolName } = req.params;
  const tool = TOOL_REGISTRY[toolName];

  if (!tool) {
    res.status(404).json({
      error: `Tool '${toolName}' not found`,
      available_tools: Object.keys(TOOL_REGISTRY),
    });
    return;
  }

  res.status(200).json({
    name: toolName,
    description: tool.description,
    parameters: tool.schema,
  });
});

function sanitizeParamsForAudit(
  params: Record<string, unknown>
): Record<string, unknown> {
  const sensitiveKeys = ["password", "token", "secret", "key", "ssn", "dob"];
  const sanitized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(params)) {
    if (sensitiveKeys.some((sk) => key.toLowerCase().includes(sk))) {
      sanitized[key] = "[REDACTED]";
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

function summarizeResult(result: unknown): string {
  if (result === null || result === undefined) return "null";
  if (typeof result === "string") return result.substring(0, 200);
  if (typeof result === "number" || typeof result === "boolean") return String(result);
  if (Array.isArray(result)) return `Array[${result.length}]`;
  if (typeof result === "object") {
    const keys = Object.keys(result as object);
    return `Object{${keys.slice(0, 5).join(", ")}${keys.length > 5 ? "..." : ""}}`;
  }
  return "unknown";
}

export default router;
