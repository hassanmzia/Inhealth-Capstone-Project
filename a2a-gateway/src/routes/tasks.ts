import { Router, Request, Response } from "express";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { getA2AGateway } from "../a2a/gateway";
import {
  delegateTask,
  getTaskById,
  routeTask,
  handleTaskResult,
  buildAgentIdentifier,
} from "../a2a/router";
import { logger } from "../utils/logger";
import {
  a2aMessagesTotal,
  a2aFailedMessagesTotal,
} from "../utils/metrics";
import { A2AMessage } from "../a2a/types";

const router = Router();

const TaskSubmitSchema = z.object({
  task_type: z.string().min(1, "task_type is required"),
  patient_id: z.string().optional(),
  from_agent_id: z.number().int().positive("from_agent_id is required"),
  payload: z.record(z.unknown()).default({}),
  priority: z
    .enum(["CRITICAL", "HIGH", "NORMAL", "LOW"])
    .optional()
    .default("NORMAL"),
  to_agent_id: z.number().int().positive().optional(),
  to_agent_type: z
    .enum(["monitoring", "diagnostic", "risk", "intervention", "action", "research", "orchestration"])
    .optional(),
  correlation_id: z.string().optional(),
});

const MessageSchema = z.object({
  sender_agent_id: z.number().int().positive(),
  recipient_agent_id: z.number().int().positive().optional(),
  recipient_broadcast: z.boolean().optional().default(false),
  message_type: z.enum([
    "ALERT",
    "REQUEST",
    "RESPONSE",
    "DATA_UPDATE",
    "ACTION_COMPLETE",
    "ACTION_FAILED",
    "STATUS_UPDATE",
  ]),
  priority: z.enum(["CRITICAL", "HIGH", "NORMAL", "LOW"]).default("NORMAL"),
  payload: z.record(z.unknown()),
  requires_response: z.boolean().default(false),
  response_timeout: z.number().int().default(30000),
  correlation_id: z.string().optional(),
  patient_id: z.string().optional(),
});

// POST /a2a/tasks - submit a task to an agent
router.post("/a2a/tasks", async (req: Request, res: Response): Promise<void> => {
  const parseResult = TaskSubmitSchema.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({
      error: "Invalid task request",
      details: parseResult.error.flatten(),
    });
    return;
  }

  const {
    task_type,
    patient_id,
    from_agent_id,
    payload,
    priority,
    to_agent_id,
    to_agent_type,
    correlation_id,
  } = parseResult.data;

  try {
    // Build from agent identifier
    const fromAgent = buildAgentIdentifier(from_agent_id);

    // Determine target agent type
    let targetAgentType = to_agent_type;
    if (!targetAgentType) {
      if (to_agent_id) {
        // Look up agent type by ID
        const { getAgentById } = await import("../a2a/registry");
        const targetAgent = getAgentById(to_agent_id);
        if (!targetAgent) {
          res.status(404).json({ error: `Target agent ${to_agent_id} not found` });
          return;
        }
        targetAgentType = targetAgent.type;
      } else {
        // Auto-route based on task type
        const routed = routeTask(task_type);
        if (!routed) {
          res.status(422).json({
            error: `Unable to route task type: ${task_type}`,
            suggestion: "Provide to_agent_id or to_agent_type explicitly",
          });
          return;
        }
        targetAgentType = routed;
      }
    }

    const task = await delegateTask({
      from_agent: fromAgent,
      to_agent_type: targetAgentType!,
      task_type,
      patient_id,
      payload,
      priority,
      correlation_id,
    });

    logger.info("tasks route: task submitted", {
      task_id: task.task_id,
      task_type,
      from_agent: fromAgent.agent_name,
      assigned_to: task.assigned_to?.agent_name,
      priority,
      patient_id,
    });

    res.status(202).json({
      task_id: task.task_id,
      status: task.status,
      assigned_to: task.assigned_to,
      priority: task.priority,
      created_at: task.created_at,
      timeout_at: task.timeout_at,
    });
  } catch (error) {
    a2aFailedMessagesTotal
      .labels({ reason: "task_delegation_error", message_type: "REQUEST" })
      .inc();

    logger.error("tasks route: task submission failed", {
      task_type,
      error: error instanceof Error ? error.message : String(error),
    });

    const statusCode = error instanceof Error && error.message.includes("not found") ? 404 : 500;
    res.status(statusCode).json({
      error: error instanceof Error ? error.message : "Task submission failed",
    });
  }
});

// GET /a2a/tasks/:id - get task status
router.get("/a2a/tasks/:id", async (req: Request, res: Response): Promise<void> => {
  const { id } = req.params;

  if (!id) {
    res.status(400).json({ error: "Task ID is required" });
    return;
  }

  try {
    const task = await getTaskById(id);

    if (!task) {
      res.status(404).json({ error: `Task ${id} not found` });
      return;
    }

    res.status(200).json(task);
  } catch (error) {
    logger.error("tasks route: error fetching task", {
      task_id: id,
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to retrieve task status" });
  }
});

// POST /a2a/messages - send an A2A message directly
router.post("/a2a/messages", async (req: Request, res: Response): Promise<void> => {
  const parseResult = MessageSchema.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({
      error: "Invalid message",
      details: parseResult.error.flatten(),
    });
    return;
  }

  const {
    sender_agent_id,
    recipient_agent_id,
    recipient_broadcast,
    message_type,
    priority,
    payload,
    requires_response,
    response_timeout,
    correlation_id,
    patient_id,
  } = parseResult.data;

  try {
    const { getAgentById } = await import("../a2a/registry");

    // Build sender identifier
    const senderAgent = getAgentById(sender_agent_id);
    if (!senderAgent) {
      res.status(404).json({ error: `Sender agent ${sender_agent_id} not found` });
      return;
    }

    // Build recipient identifier
    let recipientAgent = getAgentById(0); // placeholder
    let isBroadcast = recipient_broadcast;

    if (recipient_broadcast) {
      isBroadcast = true;
      recipientAgent = undefined;
    } else if (recipient_agent_id) {
      recipientAgent = getAgentById(recipient_agent_id);
      if (!recipientAgent) {
        res.status(404).json({ error: `Recipient agent ${recipient_agent_id} not found` });
        return;
      }
    } else {
      res.status(400).json({
        error: "Either recipient_agent_id or recipient_broadcast must be provided",
      });
      return;
    }

    const message: A2AMessage = {
      protocol: "A2A/1.0",
      message_id: uuidv4(),
      timestamp: new Date().toISOString(),
      sender: {
        agent_id: senderAgent.id,
        agent_name: senderAgent.name,
        agent_type: senderAgent.type,
      },
      recipient: isBroadcast
        ? {
            agent_id: 0,
            agent_name: "ALL_AGENTS",
            agent_type: "monitoring",
            broadcast: true,
          }
        : {
            agent_id: recipientAgent!.id,
            agent_name: recipientAgent!.name,
            agent_type: recipientAgent!.type,
          },
      message_type,
      priority,
      payload: {
        ...payload,
        ...(patient_id ? { patient_id } : {}),
      },
      requires_response,
      response_timeout,
      correlation_id,
      metadata: {
        patient_id,
        source_system: "a2a-gateway-api",
      },
    };

    const gateway = getA2AGateway();

    if (isBroadcast) {
      await gateway.broadcastMessage(
        message.payload,
        message.sender,
        message_type,
        priority
      );
    } else {
      await gateway.sendMessage(message);
    }

    // Handle task completion messages
    if (message_type === "ACTION_COMPLETE" || message_type === "ACTION_FAILED") {
      await handleTaskResult(message);
    }

    a2aMessagesTotal.labels({ message_type, priority }).inc();

    logger.info("messages route: message sent", {
      message_id: message.message_id,
      message_type,
      sender: senderAgent.name,
      broadcast: isBroadcast,
    });

    res.status(202).json({
      success: true,
      message_id: message.message_id,
      timestamp: message.timestamp,
    });
  } catch (error) {
    a2aFailedMessagesTotal
      .labels({ reason: "send_error", message_type: parseResult.data.message_type })
      .inc();

    logger.error("messages route: error sending message", {
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(500).json({
      error: error instanceof Error ? error.message : "Message send failed",
    });
  }
});

// GET /a2a/messages/:id - retrieve a message from history
router.get("/a2a/messages/:id", async (req: Request, res: Response): Promise<void> => {
  const { id } = req.params;

  if (!id) {
    res.status(400).json({ error: "Message ID is required" });
    return;
  }

  try {
    const gateway = getA2AGateway();
    const message = await gateway.getMessage(id);

    if (!message) {
      res.status(404).json({ error: `Message ${id} not found` });
      return;
    }

    res.status(200).json(message);
  } catch (error) {
    logger.error("messages route: error fetching message", {
      message_id: id,
      error: error instanceof Error ? error.message : String(error),
    });
    res.status(500).json({ error: "Failed to retrieve message" });
  }
});

export default router;
