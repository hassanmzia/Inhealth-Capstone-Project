import client from "prom-client";

const register = new client.Registry();
client.collectDefaultMetrics({ register });

// Counter: total A2A messages, labeled by type and priority
export const a2aMessagesTotal = new client.Counter({
  name: "a2a_messages_total",
  help: "Total number of A2A protocol messages processed",
  labelNames: ["message_type", "priority"] as const,
  registers: [register],
});

// Histogram: message end-to-end latency in seconds
export const a2aMessageLatencySeconds = new client.Histogram({
  name: "a2a_message_latency_seconds",
  help: "End-to-end latency of A2A messages in seconds",
  labelNames: ["message_type"] as const,
  buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
  registers: [register],
});

// Gauge: number of active registered agents
export const a2aActiveAgentsCount = new client.Gauge({
  name: "a2a_active_agents_count",
  help: "Number of currently active/registered agents",
  labelNames: ["agent_type"] as const,
  registers: [register],
});

// Counter: failed messages
export const a2aFailedMessagesTotal = new client.Counter({
  name: "a2a_failed_messages_total",
  help: "Total number of failed A2A messages",
  labelNames: ["reason", "message_type"] as const,
  registers: [register],
});

// Counter: task delegations
export const a2aTaskDelegationsTotal = new client.Counter({
  name: "a2a_task_delegations_total",
  help: "Total number of task delegations between agents",
  labelNames: ["from_agent_type", "to_agent_type"] as const,
  registers: [register],
});

// Gauge: WebSocket connections
export const a2aWebSocketConnections = new client.Gauge({
  name: "a2a_websocket_connections",
  help: "Number of active WebSocket connections",
  registers: [register],
});

// Counter: agent registrations
export const a2aAgentRegistrationsTotal = new client.Counter({
  name: "a2a_agent_registrations_total",
  help: "Total number of agent registration events",
  labelNames: ["agent_type", "action"] as const,
  registers: [register],
});

// Histogram: task completion time
export const a2aTaskCompletionDurationSeconds = new client.Histogram({
  name: "a2a_task_completion_duration_seconds",
  help: "Duration from task submission to completion in seconds",
  labelNames: ["agent_type"] as const,
  buckets: [0.1, 0.5, 1, 5, 10, 30, 60, 120, 300],
  registers: [register],
});

export { register };
export default register;
