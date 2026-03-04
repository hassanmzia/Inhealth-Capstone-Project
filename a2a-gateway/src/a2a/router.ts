import { v4 as uuidv4 } from "uuid";
import { logger } from "../utils/logger";
import { a2aTaskDelegationsTotal } from "../utils/metrics";
import {
  A2AMessage,
  A2ATask,
  AgentIdentifier,
  AgentType,
  TaskDelegationRequest,
  TaskRoutingRule,
} from "./types";
import { AGENT_REGISTRY, getAgentsByType, getAgentsByCapability } from "./registry";
import { getA2AGateway } from "./gateway";

// Task type → agent type routing rules
const ROUTING_RULES: TaskRoutingRule[] = [
  // Monitoring tasks
  {
    task_type_pattern: /glucose|cgm|blood.sugar|hba1c/i,
    target_agent_types: ["monitoring"],
    requires_capabilities: ["realtime_glucose_monitoring"],
  },
  {
    task_type_pattern: /cardiac|ecg|arrhythmia|heart.rate|blood.pressure/i,
    target_agent_types: ["monitoring"],
    requires_capabilities: ["ecg_analysis"],
  },
  {
    task_type_pattern: /vital|spo2|respiratory|temperature|weight/i,
    target_agent_types: ["monitoring"],
    requires_capabilities: ["vitals_aggregation"],
  },
  {
    task_type_pattern: /lab|laboratory|result|test.result/i,
    target_agent_types: ["monitoring"],
    requires_capabilities: ["lab_result_ingestion"],
  },
  {
    task_type_pattern: /adherence|medication.compliance|missed.dose/i,
    target_agent_types: ["monitoring"],
    requires_capabilities: ["adherence_tracking"],
  },

  // Diagnostic tasks
  {
    task_type_pattern: /drug.interaction|medication.interaction|contraindication/i,
    target_agent_types: ["diagnostic"],
    requires_capabilities: ["drug_interaction_checking"],
  },
  {
    task_type_pattern: /pattern|anomaly|deterioration|early.warning/i,
    target_agent_types: ["diagnostic"],
    requires_capabilities: ["multivariate_pattern_detection"],
  },
  {
    task_type_pattern: /comorbidity|disease.interaction|complication/i,
    target_agent_types: ["diagnostic"],
    requires_capabilities: ["comorbidity_mapping"],
  },
  {
    task_type_pattern: /symptom|complaint|assessment/i,
    target_agent_types: ["diagnostic"],
    requires_capabilities: ["nlp_symptom_extraction"],
  },
  {
    task_type_pattern: /imaging|radiology|pathology|scan|report/i,
    target_agent_types: ["diagnostic"],
    requires_capabilities: ["radiology_report_analysis"],
  },

  // Risk assessment tasks
  {
    task_type_pattern: /diabetes.risk|diabetic.complication/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["diabetes_complication_risk"],
  },
  {
    task_type_pattern: /cardiovascular.risk|cardiac.risk|ascvd|heart.attack.risk/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["ascvd_risk_calculation"],
  },
  {
    task_type_pattern: /readmission|discharge.risk/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["readmission_prediction"],
  },
  {
    task_type_pattern: /mental.health|depression|anxiety|suicide.risk/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["depression_screening"],
    priority_override: "HIGH",
  },
  {
    task_type_pattern: /kidney|renal|ckd|egfr|nephropathy/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["ckd_staging"],
  },
  {
    task_type_pattern: /fall.risk|morse.fall/i,
    target_agent_types: ["risk"],
    requires_capabilities: ["morse_fall_scale"],
  },

  // Intervention tasks
  {
    task_type_pattern: /prescription|medication.recommendation|dose.adjustment/i,
    target_agent_types: ["intervention"],
    requires_capabilities: ["medication_recommendations"],
  },
  {
    task_type_pattern: /triage|acuity|care.setting|emergency.routing/i,
    target_agent_types: ["intervention"],
    requires_capabilities: ["acuity_scoring"],
    priority_override: "HIGH",
  },
  {
    task_type_pattern: /care.plan|treatment.plan|care.goal/i,
    target_agent_types: ["intervention"],
    requires_capabilities: ["care_plan_generation"],
  },
  {
    task_type_pattern: /education|patient.education|health.literacy/i,
    target_agent_types: ["intervention"],
    requires_capabilities: ["personalized_content_delivery"],
  },

  // Action tasks
  {
    task_type_pattern: /notification|alert|message|sms|email/i,
    target_agent_types: ["action"],
    requires_capabilities: ["sms_notifications"],
  },
  {
    task_type_pattern: /appointment|schedule|booking|referral/i,
    target_agent_types: ["action"],
    requires_capabilities: ["appointment_booking"],
  },
  {
    task_type_pattern: /ehr|clinical.note|fhir.write|documentation/i,
    target_agent_types: ["action"],
    requires_capabilities: ["fhir_resource_creation"],
  },
  {
    task_type_pattern: /emergency|911|crisis|critical.alert/i,
    target_agent_types: ["action"],
    requires_capabilities: ["emergency_escalation"],
    priority_override: "CRITICAL",
  },
  {
    task_type_pattern: /billing|authorization|prior.auth|insurance/i,
    target_agent_types: ["action"],
    requires_capabilities: ["prior_authorization"],
  },

  // Research tasks
  {
    task_type_pattern: /literature|research|evidence|guideline.search/i,
    target_agent_types: ["research"],
    requires_capabilities: ["pubmed_search"],
  },
  {
    task_type_pattern: /cohort|population|similar.patient/i,
    target_agent_types: ["research"],
    requires_capabilities: ["cohort_identification"],
  },
  {
    task_type_pattern: /clinical.trial|trial.matching|study.enrollment/i,
    target_agent_types: ["research"],
    requires_capabilities: ["trial_eligibility_matching"],
  },
];

export function routeTask(taskType: string): AgentType | null {
  for (const rule of ROUTING_RULES) {
    const pattern = rule.task_type_pattern;
    const matches =
      typeof pattern === "string"
        ? taskType.toLowerCase().includes(pattern.toLowerCase())
        : pattern.test(taskType);

    if (matches) {
      // Find the first target agent type with available agents
      for (const agentType of rule.target_agent_types) {
        const candidates = rule.requires_capabilities
          ? getAgentsByCapability(rule.requires_capabilities[0]).filter(
              (a) => a.type === agentType
            )
          : getAgentsByType(agentType);

        if (candidates.length > 0) {
          return agentType;
        }
      }
    }
  }

  logger.warn("routeTask: no routing rule matched", { task_type: taskType });
  return null;
}

export function getRoutingRule(taskType: string): TaskRoutingRule | null {
  for (const rule of ROUTING_RULES) {
    const pattern = rule.task_type_pattern;
    const matches =
      typeof pattern === "string"
        ? taskType.toLowerCase().includes(pattern.toLowerCase())
        : pattern.test(taskType);

    if (matches) return rule;
  }
  return null;
}

export async function delegateTask(request: TaskDelegationRequest): Promise<A2ATask> {
  const { from_agent, to_agent_type, task_type, patient_id, payload, priority, correlation_id } =
    request;

  // Find target agent from registry
  const rule = getRoutingRule(task_type);
  let targetAgents = getAgentsByType(to_agent_type);

  if (rule?.requires_capabilities && rule.requires_capabilities.length > 0) {
    const capableAgents = getAgentsByCapability(rule.requires_capabilities[0]).filter(
      (a) => a.type === to_agent_type
    );
    if (capableAgents.length > 0) {
      targetAgents = capableAgents;
    }
  }

  if (targetAgents.length === 0) {
    throw new Error(`No agents available for type: ${to_agent_type}`);
  }

  // Simple round-robin or pick first active agent
  const activeAgents = targetAgents.filter(
    (a) => a.status === "active" || a.status === "idle"
  );
  const targetAgent = activeAgents[0] || targetAgents[0];

  if (!targetAgent) {
    throw new Error(`No active agents found for type: ${to_agent_type}`);
  }

  const taskId = uuidv4();
  const now = new Date().toISOString();
  const effectivePriority = rule?.priority_override || priority || "NORMAL";

  const task: A2ATask = {
    task_id: taskId,
    task_type,
    patient_id,
    submitted_by: from_agent,
    assigned_to: {
      agent_id: targetAgent.id,
      agent_name: targetAgent.name,
      agent_type: targetAgent.type,
    },
    status: "assigned",
    priority: effectivePriority,
    payload,
    created_at: now,
    updated_at: now,
    timeout_at: new Date(Date.now() + 300000).toISOString(), // 5 min timeout
  };

  // Build and send A2A REQUEST message
  const a2aMessage: A2AMessage = {
    protocol: "A2A/1.0",
    message_id: uuidv4(),
    timestamp: now,
    sender: from_agent,
    recipient: {
      agent_id: targetAgent.id,
      agent_name: targetAgent.name,
      agent_type: targetAgent.type,
    },
    message_type: "REQUEST",
    priority: effectivePriority,
    payload: {
      task_id: taskId,
      task_type,
      patient_id,
      task_payload: payload,
    },
    requires_response: true,
    response_timeout: 300000, // 5 minutes
    correlation_id: correlation_id || taskId,
    metadata: {
      patient_id,
      session_id: taskId,
    },
  };

  const gateway = getA2AGateway();
  await gateway.sendMessage(a2aMessage);

  // Track the task in Redis
  await storeTask(task);

  a2aTaskDelegationsTotal
    .labels({
      from_agent_type: from_agent.agent_type,
      to_agent_type: targetAgent.type,
    })
    .inc();

  logger.info("delegateTask: task delegated", {
    task_id: taskId,
    task_type,
    from_agent: from_agent.agent_name,
    to_agent: targetAgent.name,
    priority: effectivePriority,
    patient_id,
  });

  return task;
}

export async function handleTaskResult(
  completionMessage: A2AMessage
): Promise<A2ATask | null> {
  const correlationId = completionMessage.correlation_id;
  if (!correlationId) {
    logger.warn("handleTaskResult: no correlation_id in completion message", {
      message_id: completionMessage.message_id,
    });
    return null;
  }

  const task = await getTaskById(correlationId);
  if (!task) {
    logger.warn("handleTaskResult: task not found", { correlation_id: correlationId });
    return null;
  }

  const updatedTask: A2ATask = {
    ...task,
    status:
      completionMessage.message_type === "ACTION_COMPLETE" ? "completed" : "failed",
    result: completionMessage.message_type === "ACTION_COMPLETE"
      ? completionMessage.payload
      : undefined,
    error: completionMessage.message_type === "ACTION_FAILED"
      ? (completionMessage.payload.error as string) || "Task failed"
      : undefined,
    completed_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  await storeTask(updatedTask);

  logger.info("handleTaskResult: task result processed", {
    task_id: task.task_id,
    status: updatedTask.status,
    from_agent: completionMessage.sender.agent_name,
  });

  return updatedTask;
}

async function storeTask(task: A2ATask): Promise<void> {
  const gateway = getA2AGateway();
  // Access Redis via gateway's internal client by re-using gateway infrastructure
  // Store task as a hash in Redis with a 24-hour TTL
  const taskKey = `task:${task.task_id}`;
  // We use the gateway's publish client indirectly via a new Redis client
  // For simplicity, we serialize to string and use the standard set approach
  const { createClient } = await import("redis");
  const client = createClient({ url: process.env.REDIS_URL || "redis://redis:6379" }) as ReturnType<typeof createClient>;
  try {
    await client.connect();
    await client.setEx(taskKey, 86400, JSON.stringify(task)); // 24 hours
    // Index by patient
    if (task.patient_id) {
      await client.lPush(`patient_tasks:${task.patient_id}`, task.task_id);
      await client.expire(`patient_tasks:${task.patient_id}`, 86400);
    }
  } finally {
    await client.quit();
  }
}

export async function getTaskById(taskId: string): Promise<A2ATask | null> {
  const { createClient } = await import("redis");
  const client = createClient({ url: process.env.REDIS_URL || "redis://redis:6379" }) as ReturnType<typeof createClient>;
  try {
    await client.connect();
    const data = await client.get(`task:${taskId}`);
    if (!data) return null;
    return JSON.parse(data) as A2ATask;
  } finally {
    await client.quit();
  }
}

export function buildAgentIdentifier(agentId: number): AgentIdentifier {
  const agent = AGENT_REGISTRY.find((a) => a.id === agentId);
  if (!agent) {
    throw new Error(`Agent not found: ${agentId}`);
  }
  return {
    agent_id: agent.id,
    agent_name: agent.name,
    agent_type: agent.type,
  };
}
