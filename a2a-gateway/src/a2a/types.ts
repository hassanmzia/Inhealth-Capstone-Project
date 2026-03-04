// A2A Protocol Types for InHealth Chronic Care Platform

export interface A2AMessage {
  protocol: "A2A/1.0";
  message_id: string;
  timestamp: string;
  sender: AgentIdentifier;
  recipient: AgentIdentifier;
  message_type:
    | "ALERT"
    | "REQUEST"
    | "RESPONSE"
    | "DATA_UPDATE"
    | "ACTION_COMPLETE"
    | "ACTION_FAILED"
    | "STATUS_UPDATE";
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
  payload: Record<string, unknown>;
  requires_response: boolean;
  response_timeout: number; // milliseconds
  correlation_id?: string;
  ttl?: number; // time-to-live in seconds
  metadata?: A2AMessageMetadata;
}

export interface A2AMessageMetadata {
  patient_id?: string;
  session_id?: string;
  retry_count?: number;
  created_at?: string;
  source_system?: string;
  tags?: string[];
}

export interface AgentIdentifier {
  agent_id: number;
  agent_name: string;
  agent_type: AgentType;
  broadcast?: boolean;
}

export type AgentType =
  | "monitoring"
  | "diagnostic"
  | "risk"
  | "intervention"
  | "action"
  | "research"
  | "orchestration";

export interface AgentCard {
  id: number;
  name: string;
  type: AgentType;
  tier: number;
  description: string;
  capabilities: string[];
  subscribed_channels: string[];
  publishes_to: string[];
  endpoint: string;
  status: AgentStatus;
  last_heartbeat: string;
  version?: string;
  metadata?: Record<string, unknown>;
}

export type AgentStatus = "active" | "idle" | "error" | "offline" | "maintenance";

export interface AgentHeartbeat {
  agent_id: number;
  timestamp: string;
  status: AgentStatus;
  metrics?: {
    tasks_processed: number;
    avg_latency_ms: number;
    error_rate: number;
    queue_depth: number;
  };
}

export interface A2ATask {
  task_id: string;
  task_type: string;
  patient_id?: string;
  submitted_by: AgentIdentifier;
  assigned_to?: AgentIdentifier;
  status: TaskStatus;
  priority: A2AMessage["priority"];
  payload: Record<string, unknown>;
  result?: unknown;
  error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  timeout_at?: string;
}

export type TaskStatus =
  | "pending"
  | "assigned"
  | "in_progress"
  | "completed"
  | "failed"
  | "timeout"
  | "cancelled";

export interface ChannelSubscription {
  channel: A2AChannel;
  agent_id: number;
  subscribed_at: string;
}

export type A2AChannel =
  | "agent.monitoring"
  | "agent.diagnostic"
  | "agent.risk"
  | "agent.intervention"
  | "agent.action"
  | "agent.broadcast"
  | `agent.response.${number}`;

export const A2A_CHANNELS: A2AChannel[] = [
  "agent.monitoring",
  "agent.diagnostic",
  "agent.risk",
  "agent.intervention",
  "agent.action",
  "agent.broadcast",
];

export interface TaskRoutingRule {
  task_type_pattern: string | RegExp;
  target_agent_types: AgentType[];
  priority_override?: A2AMessage["priority"];
  requires_capabilities?: string[];
}

export interface A2AGatewayConfig {
  redis_url: string;
  message_ttl_seconds: number;
  task_timeout_seconds: number;
  max_retry_count: number;
  heartbeat_interval_seconds: number;
  websocket_ping_interval_ms: number;
}

export interface WebSocketAgentMessage {
  type: "subscribe" | "unsubscribe" | "message" | "heartbeat" | "register";
  agent_id?: number;
  channel?: string;
  message?: A2AMessage;
  heartbeat?: AgentHeartbeat;
  agent_card?: AgentCard;
}

export interface A2ADiscoveryDocument {
  gateway: {
    version: string;
    endpoint: string;
    websocket_endpoint: string;
    capabilities: string[];
  };
  agents: AgentCard[];
  channels: string[];
  task_types: string[];
  timestamp: string;
}

export interface TaskDelegationRequest {
  from_agent: AgentIdentifier;
  to_agent_type: AgentType;
  task_type: string;
  patient_id?: string;
  payload: Record<string, unknown>;
  priority?: A2AMessage["priority"];
  correlation_id?: string;
}

export interface A2AResponse {
  success: boolean;
  message_id?: string;
  task_id?: string;
  error?: string;
  timestamp: string;
}
