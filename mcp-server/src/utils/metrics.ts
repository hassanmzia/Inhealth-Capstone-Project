import client from "prom-client";

// Initialize default metrics collection
const register = new client.Registry();
client.collectDefaultMetrics({ register });

// Counter: total MCP context requests
export const mcpContextRequestsTotal = new client.Counter({
  name: "mcp_context_requests_total",
  help: "Total number of MCP context build requests",
  labelNames: ["status", "agent_id"] as const,
  registers: [register],
});

// Counter: total tool executions, labeled by tool name
export const mcpToolExecutionsTotal = new client.Counter({
  name: "mcp_tool_executions_total",
  help: "Total number of MCP tool executions",
  labelNames: ["tool_name", "status"] as const,
  registers: [register],
});

// Histogram: tool execution duration in seconds
export const mcpToolExecutionDurationSeconds = new client.Histogram({
  name: "mcp_tool_execution_duration_seconds",
  help: "Duration of MCP tool executions in seconds",
  labelNames: ["tool_name"] as const,
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [register],
});

// Gauge: active Redis connections
export const mcpRedisConnectionsActive = new client.Gauge({
  name: "mcp_redis_connections_active",
  help: "Number of active Redis connections",
  registers: [register],
});

// Counter: auth failures
export const mcpAuthFailuresTotal = new client.Counter({
  name: "mcp_auth_failures_total",
  help: "Total number of JWT authentication failures",
  labelNames: ["reason"] as const,
  registers: [register],
});

// Histogram: context build duration
export const mcpContextBuildDurationSeconds = new client.Histogram({
  name: "mcp_context_build_duration_seconds",
  help: "Duration of MCP context build operations in seconds",
  buckets: [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
  registers: [register],
});

export { register };
export default register;
