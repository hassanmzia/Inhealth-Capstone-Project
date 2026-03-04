import { createClient, RedisClientType } from "redis";
import { v4 as uuidv4 } from "uuid";
import { logger } from "../utils/logger";
import {
  a2aMessagesTotal,
  a2aFailedMessagesTotal,
  a2aActiveAgentsCount,
  a2aAgentRegistrationsTotal,
} from "../utils/metrics";
import {
  A2AMessage,
  AgentCard,
  AgentHeartbeat,
  AgentStatus,
  A2AChannel,
  A2A_CHANNELS,
} from "./types";

const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";
const MESSAGE_TTL_SECONDS = parseInt(process.env.MESSAGE_TTL_SECONDS || "3600", 10);
const AGENT_HEARTBEAT_TTL = parseInt(process.env.AGENT_HEARTBEAT_TTL || "60", 10);

export type ChannelHandler = (message: A2AMessage) => void | Promise<void>;

export class A2AGateway {
  private publishClient: RedisClientType;
  private subscribeClient: RedisClientType;
  private channelHandlers: Map<string, Set<ChannelHandler>> = new Map();
  private isConnected: boolean = false;

  constructor() {
    const redisConfig = {
      url: REDIS_URL,
      socket: {
        reconnectStrategy: (retries: number) => {
          if (retries > 10) return new Error("Redis reconnect failed");
          return Math.min(retries * 100, 3000);
        },
      },
    };

    this.publishClient = createClient(redisConfig) as RedisClientType;
    this.subscribeClient = createClient(redisConfig) as RedisClientType;

    this.publishClient.on("error", (err) => {
      logger.error("A2AGateway: publish client error", { error: err.message });
      this.isConnected = false;
    });

    this.subscribeClient.on("error", (err) => {
      logger.error("A2AGateway: subscribe client error", { error: err.message });
    });

    this.publishClient.on("connect", () => {
      logger.info("A2AGateway: publish client connected");
      this.isConnected = true;
    });
  }

  async connect(): Promise<void> {
    await Promise.all([
      this.publishClient.connect(),
      this.subscribeClient.connect(),
    ]);

    // Subscribe to all standard A2A channels
    for (const channel of A2A_CHANNELS) {
      await this.setupChannelSubscription(channel);
    }

    logger.info("A2AGateway: connected to Redis and subscribed to all channels", {
      channels: A2A_CHANNELS,
    });
  }

  async disconnect(): Promise<void> {
    await Promise.all([
      this.publishClient.quit(),
      this.subscribeClient.quit(),
    ]);
    logger.info("A2AGateway: disconnected from Redis");
  }

  private async setupChannelSubscription(channel: string): Promise<void> {
    try {
      await this.subscribeClient.subscribe(channel, async (rawMessage: string) => {
        let message: A2AMessage;
        try {
          message = JSON.parse(rawMessage) as A2AMessage;
        } catch (parseErr) {
          logger.error("A2AGateway: failed to parse channel message", {
            channel,
            error: parseErr instanceof Error ? parseErr.message : String(parseErr),
          });
          return;
        }

        logger.debug("A2AGateway: received message on channel", {
          channel,
          message_id: message.message_id,
          message_type: message.message_type,
          sender: message.sender.agent_name,
        });

        a2aMessagesTotal
          .labels({
            message_type: message.message_type,
            priority: message.priority,
          })
          .inc();

        // Invoke all registered handlers for this channel
        const handlers = this.channelHandlers.get(channel) || new Set();
        for (const handler of handlers) {
          try {
            await handler(message);
          } catch (handlerErr) {
            logger.error("A2AGateway: channel handler error", {
              channel,
              message_id: message.message_id,
              error: handlerErr instanceof Error ? handlerErr.message : String(handlerErr),
            });
          }
        }
      });
    } catch (err) {
      logger.error("A2AGateway: failed to subscribe to channel", {
        channel,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  async registerAgent(agentCard: AgentCard): Promise<void> {
    const agentKey = `agent:${agentCard.id}`;
    const agentData = {
      ...agentCard,
      last_heartbeat: new Date().toISOString(),
      status: "active" as AgentStatus,
    };

    await this.publishClient.setEx(
      agentKey,
      AGENT_HEARTBEAT_TTL * 10, // keep registration 10x longer than heartbeat
      JSON.stringify(agentData)
    );

    // Add to agent type index
    await this.publishClient.sAdd(`agents:type:${agentCard.type}`, String(agentCard.id));

    // Add to tier index
    await this.publishClient.sAdd(`agents:tier:${agentCard.tier}`, String(agentCard.id));

    // Add to main agents set
    await this.publishClient.sAdd("agents:all", String(agentCard.id));

    a2aAgentRegistrationsTotal.labels({ agent_type: agentCard.type, action: "register" }).inc();

    // Update active agent count gauge
    const allAgentIds = await this.publishClient.sMembers("agents:all");
    a2aActiveAgentsCount.labels({ agent_type: agentCard.type }).set(allAgentIds.length);

    logger.info("A2AGateway: agent registered", {
      agent_id: agentCard.id,
      agent_name: agentCard.name,
      agent_type: agentCard.type,
    });
  }

  async deregisterAgent(agentId: number): Promise<void> {
    const agentKey = `agent:${agentId}`;
    const agentData = await this.publishClient.get(agentKey);

    if (agentData) {
      const agent = JSON.parse(agentData) as AgentCard;

      await this.publishClient.del(agentKey);
      await this.publishClient.sRem(`agents:type:${agent.type}`, String(agentId));
      await this.publishClient.sRem(`agents:tier:${agent.tier}`, String(agentId));
      await this.publishClient.sRem("agents:all", String(agentId));

      a2aAgentRegistrationsTotal
        .labels({ agent_type: agent.type, action: "deregister" })
        .inc();

      logger.info("A2AGateway: agent deregistered", {
        agent_id: agentId,
        agent_name: agent.name,
      });
    }
  }

  async sendMessage(message: A2AMessage): Promise<void> {
    const startTime = Date.now();

    try {
      // Determine the target channel based on recipient agent type
      let targetChannel: string;

      if (message.recipient.broadcast) {
        targetChannel = "agent.broadcast";
      } else if (message.message_type === "RESPONSE") {
        // Response messages go to agent-specific response channel
        targetChannel = `agent.response.${message.recipient.agent_id}`;
      } else {
        targetChannel = `agent.${message.recipient.agent_type}`;
      }

      const serialized = JSON.stringify(message);

      // Publish to Redis channel
      const subscriberCount = await this.publishClient.publish(targetChannel, serialized);

      // Store message in history with TTL
      const historyKey = `message_history:${message.message_id}`;
      await this.publishClient.setEx(historyKey, MESSAGE_TTL_SECONDS, serialized);

      // If message requires response, add to pending responses tracking
      if (message.requires_response) {
        const pendingKey = `pending_response:${message.message_id}`;
        await this.publishClient.setEx(
          pendingKey,
          Math.ceil(message.response_timeout / 1000),
          JSON.stringify({
            message_id: message.message_id,
            sender: message.sender,
            recipient: message.recipient,
            timestamp: message.timestamp,
            correlation_id: message.correlation_id,
          })
        );
      }

      const latency = (Date.now() - startTime) / 1000;
      logger.info("A2AGateway: message sent", {
        message_id: message.message_id,
        message_type: message.message_type,
        priority: message.priority,
        channel: targetChannel,
        subscriber_count: subscriberCount,
        latency_ms: latency * 1000,
      });
    } catch (error) {
      a2aFailedMessagesTotal
        .labels({ reason: "send_error", message_type: message.message_type })
        .inc();

      logger.error("A2AGateway: failed to send message", {
        message_id: message.message_id,
        error: error instanceof Error ? error.message : String(error),
      });

      throw error;
    }
  }

  async broadcastMessage(
    payload: Record<string, unknown>,
    sender: A2AMessage["sender"],
    messageType: A2AMessage["message_type"] = "ALERT",
    priority: A2AMessage["priority"] = "HIGH"
  ): Promise<void> {
    const message: A2AMessage = {
      protocol: "A2A/1.0",
      message_id: uuidv4(),
      timestamp: new Date().toISOString(),
      sender,
      recipient: {
        agent_id: 0,
        agent_name: "ALL_AGENTS",
        agent_type: "monitoring",
        broadcast: true,
      },
      message_type: messageType,
      priority,
      payload,
      requires_response: false,
      response_timeout: 0,
    };

    const serialized = JSON.stringify(message);
    await this.publishClient.publish("agent.broadcast", serialized);

    // Store in history
    await this.publishClient.setEx(
      `message_history:${message.message_id}`,
      MESSAGE_TTL_SECONDS,
      serialized
    );

    a2aMessagesTotal
      .labels({ message_type: messageType, priority })
      .inc();

    logger.info("A2AGateway: broadcast message sent", {
      message_id: message.message_id,
      message_type: messageType,
      priority,
    });
  }

  async subscribeToChannel(channel: A2AChannel, handler: ChannelHandler): Promise<void> {
    if (!this.channelHandlers.has(channel)) {
      this.channelHandlers.set(channel, new Set());

      // Subscribe to dynamic channels (like agent.response.N) if not already subscribed
      if (!A2A_CHANNELS.includes(channel)) {
        await this.setupChannelSubscription(channel);
      }
    }

    const handlers = this.channelHandlers.get(channel)!;
    handlers.add(handler);

    logger.debug("A2AGateway: handler registered for channel", {
      channel,
      handler_count: handlers.size,
    });
  }

  unsubscribeFromChannel(channel: A2AChannel, handler: ChannelHandler): void {
    const handlers = this.channelHandlers.get(channel);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  async getAgentStatus(agentId: number): Promise<AgentCard | null> {
    const agentKey = `agent:${agentId}`;
    const data = await this.publishClient.get(agentKey);

    if (!data) return null;

    const agent = JSON.parse(data) as AgentCard;

    // Check if heartbeat has expired (agent may be offline)
    const lastHeartbeat = new Date(agent.last_heartbeat);
    const secondsSinceHeartbeat =
      (Date.now() - lastHeartbeat.getTime()) / 1000;

    if (secondsSinceHeartbeat > AGENT_HEARTBEAT_TTL) {
      agent.status = "offline";
    }

    return agent;
  }

  async updateAgentHeartbeat(heartbeat: AgentHeartbeat): Promise<void> {
    const agentKey = `agent:${heartbeat.agent_id}`;
    const existing = await this.publishClient.get(agentKey);

    if (existing) {
      const agent = JSON.parse(existing) as AgentCard;
      agent.last_heartbeat = heartbeat.timestamp;
      agent.status = heartbeat.status;

      await this.publishClient.setEx(
        agentKey,
        AGENT_HEARTBEAT_TTL * 10,
        JSON.stringify(agent)
      );

      logger.debug("A2AGateway: agent heartbeat updated", {
        agent_id: heartbeat.agent_id,
        status: heartbeat.status,
      });
    }
  }

  async getAllAgents(): Promise<AgentCard[]> {
    const agentIds = await this.publishClient.sMembers("agents:all");
    const agents: AgentCard[] = [];

    for (const idStr of agentIds) {
      const agent = await this.getAgentStatus(parseInt(idStr, 10));
      if (agent) {
        agents.push(agent);
      }
    }

    return agents;
  }

  async getAgentsByType(type: string): Promise<AgentCard[]> {
    const agentIds = await this.publishClient.sMembers(`agents:type:${type}`);
    const agents: AgentCard[] = [];

    for (const idStr of agentIds) {
      const agent = await this.getAgentStatus(parseInt(idStr, 10));
      if (agent) {
        agents.push(agent);
      }
    }

    return agents;
  }

  async getMessage(messageId: string): Promise<A2AMessage | null> {
    const data = await this.publishClient.get(`message_history:${messageId}`);
    if (!data) return null;
    return JSON.parse(data) as A2AMessage;
  }

  async getActiveChannels(): Promise<string[]> {
    return [...A2A_CHANNELS, ...Array.from(this.channelHandlers.keys())];
  }

  async ping(): Promise<boolean> {
    try {
      const result = await this.publishClient.ping();
      return result === "PONG";
    } catch {
      return false;
    }
  }

  isRedisConnected(): boolean {
    return this.isConnected;
  }
}

// Singleton gateway instance
let gatewayInstance: A2AGateway | null = null;

export function getA2AGateway(): A2AGateway {
  if (!gatewayInstance) {
    gatewayInstance = new A2AGateway();
  }
  return gatewayInstance;
}
