import express, { Request, Response, NextFunction } from "express";
import { createServer } from "http";
import WebSocket, { WebSocketServer } from "ws";
import { v4 as uuidv4 } from "uuid";
import jwt from "jsonwebtoken";
import { register } from "./utils/metrics";
import { logger } from "./utils/logger";
import { getA2AGateway } from "./a2a/gateway";
import { AGENT_REGISTRY } from "./a2a/registry";
import {
  a2aMessagesTotal,
  a2aWebSocketConnections,
} from "./utils/metrics";
import healthRouter from "./routes/health";
import agentsRouter from "./routes/agents";
import tasksRouter from "./routes/tasks";
import {
  A2AMessage,
  WebSocketAgentMessage,
  AgentCard,
  A2AChannel,
} from "./a2a/types";

const PORT = parseInt(process.env.PORT || "3002", 10);
const HOST = process.env.HOST || "0.0.0.0";
const JWT_SECRET = process.env.JWT_SECRET || "inhealth-a2a-secret-key-change-in-production";
const JWT_ISSUER = process.env.JWT_ISSUER || "inhealth-platform";

const app = express();
const httpServer = createServer(app);

// ─── Middleware ───────────────────────────────────────────────────────────────

app.use(express.json({ limit: "5mb" }));
app.use(express.urlencoded({ extended: true, limit: "5mb" }));

// CORS middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const allowedOrigins = (process.env.CORS_ORIGINS || "*").split(",");
  const origin = req.headers.origin || "";

  if (allowedOrigins.includes("*") || allowedOrigins.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", allowedOrigins.includes("*") ? "*" : origin);
  }

  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key");
  res.setHeader("Access-Control-Max-Age", "86400");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  next();
});

// Request logging
app.use((req: Request, _res: Response, next: NextFunction) => {
  logger.debug("Incoming request", {
    method: req.method,
    path: req.path,
    ip: req.ip,
  });
  next();
});

// ─── Routes ───────────────────────────────────────────────────────────────────

app.use("/", healthRouter);
app.use("/", agentsRouter);
app.use("/", tasksRouter);

// Prometheus metrics
app.get("/metrics", async (_req: Request, res: Response) => {
  try {
    res.set("Content-Type", register.contentType);
    const metrics = await register.metrics();
    res.end(metrics);
  } catch (error) {
    logger.error("Metrics endpoint error", { error });
    res.status(500).end();
  }
});

// 404 handler
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: "Not Found" });
});

// Global error handler
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  logger.error("Unhandled error", { error: err.message, stack: err.stack });
  res.status(500).json({ error: "Internal Server Error" });
});

// ─── WebSocket Server ─────────────────────────────────────────────────────────

interface AgentWebSocket extends WebSocket {
  agentId?: number;
  agentCard?: AgentCard;
  subscribedChannels: Set<string>;
  isAlive: boolean;
  connectionId: string;
}

const wss = new WebSocketServer({ server: httpServer, path: "/ws" });

// Track connected agents
const connectedAgents = new Map<number, AgentWebSocket>();
const allConnections = new Map<string, AgentWebSocket>();

// Ping interval to detect dead connections
const pingInterval = setInterval(() => {
  wss.clients.forEach((ws) => {
    const agentWs = ws as AgentWebSocket;
    if (!agentWs.isAlive) {
      logger.warn("WebSocket: terminating dead connection", {
        connection_id: agentWs.connectionId,
        agent_id: agentWs.agentId,
      });
      agentWs.terminate();
      return;
    }
    agentWs.isAlive = false;
    agentWs.ping();
  });
}, parseInt(process.env.WS_PING_INTERVAL_MS || "30000", 10));

wss.on("connection", (ws: WebSocket, req) => {
  const agentWs = ws as AgentWebSocket;
  agentWs.connectionId = uuidv4();
  agentWs.subscribedChannels = new Set();
  agentWs.isAlive = true;

  // Attempt JWT authentication from query param or header
  const url = new URL(req.url || "/", `ws://${req.headers.host}`);
  const token = url.searchParams.get("token");

  if (token) {
    try {
      jwt.verify(token, JWT_SECRET, { issuer: JWT_ISSUER });
    } catch {
      logger.warn("WebSocket: invalid JWT token, closing connection");
      agentWs.close(1008, "Invalid token");
      return;
    }
  }

  aWebSocketConnections().inc();
  allConnections.set(agentWs.connectionId, agentWs);

  logger.info("WebSocket: new connection", {
    connection_id: agentWs.connectionId,
    remote_addr: req.socket.remoteAddress,
  });

  // Send welcome message
  const welcomeMsg = {
    type: "connected",
    connection_id: agentWs.connectionId,
    timestamp: new Date().toISOString(),
    available_channels: [
      "agent.monitoring",
      "agent.diagnostic",
      "agent.risk",
      "agent.intervention",
      "agent.action",
      "agent.broadcast",
    ],
  };
  agentWs.send(JSON.stringify(welcomeMsg));

  agentWs.on("pong", () => {
    agentWs.isAlive = true;
  });

  agentWs.on("message", async (data: WebSocket.RawData) => {
    let parsed: WebSocketAgentMessage;

    try {
      parsed = JSON.parse(data.toString()) as WebSocketAgentMessage;
    } catch {
      agentWs.send(
        JSON.stringify({ type: "error", error: "Invalid JSON message" })
      );
      return;
    }

    try {
      await handleWebSocketMessage(agentWs, parsed);
    } catch (err) {
      logger.error("WebSocket: error handling message", {
        connection_id: agentWs.connectionId,
        type: parsed.type,
        error: err instanceof Error ? err.message : String(err),
      });
      agentWs.send(
        JSON.stringify({
          type: "error",
          error: err instanceof Error ? err.message : "Message handling failed",
        })
      );
    }
  });

  agentWs.on("close", (code, reason) => {
    aWebSocketConnections().dec();
    allConnections.delete(agentWs.connectionId);

    if (agentWs.agentId) {
      connectedAgents.delete(agentWs.agentId);
    }

    logger.info("WebSocket: connection closed", {
      connection_id: agentWs.connectionId,
      agent_id: agentWs.agentId,
      code,
      reason: reason.toString(),
    });
  });

  agentWs.on("error", (err) => {
    logger.error("WebSocket: connection error", {
      connection_id: agentWs.connectionId,
      agent_id: agentWs.agentId,
      error: err.message,
    });
  });
});

async function handleWebSocketMessage(
  ws: AgentWebSocket,
  msg: WebSocketAgentMessage
): Promise<void> {
  const gateway = getA2AGateway();

  switch (msg.type) {
    case "register": {
      if (!msg.agent_card) {
        ws.send(JSON.stringify({ type: "error", error: "agent_card required for registration" }));
        return;
      }

      ws.agentId = msg.agent_card.id;
      ws.agentCard = msg.agent_card;
      connectedAgents.set(msg.agent_card.id, ws);

      // Register in Redis
      await gateway.registerAgent(msg.agent_card);

      // Auto-subscribe to agent's declared channels
      for (const channel of msg.agent_card.subscribed_channels) {
        ws.subscribedChannels.add(channel);

        // Set up gateway → WS forwarding
        await gateway.subscribeToChannel(channel as A2AChannel, (message: A2AMessage) => {
          // Forward messages intended for this agent
          if (
            message.recipient.broadcast ||
            message.recipient.agent_id === msg.agent_card!.id
          ) {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "message", message }));
            }
          }
        });
      }

      logger.info("WebSocket: agent registered", {
        agent_id: msg.agent_card.id,
        agent_name: msg.agent_card.name,
        connection_id: ws.connectionId,
        subscribed_channels: msg.agent_card.subscribed_channels,
      });

      ws.send(
        JSON.stringify({
          type: "registered",
          agent_id: msg.agent_card.id,
          subscribed_channels: msg.agent_card.subscribed_channels,
          timestamp: new Date().toISOString(),
        })
      );
      break;
    }

    case "subscribe": {
      if (!msg.channel) {
        ws.send(JSON.stringify({ type: "error", error: "channel required for subscribe" }));
        return;
      }

      ws.subscribedChannels.add(msg.channel);

      await gateway.subscribeToChannel(msg.channel as A2AChannel, (message: A2AMessage) => {
        if (
          message.recipient.broadcast ||
          (ws.agentId && message.recipient.agent_id === ws.agentId)
        ) {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "message", message }));
          }
        }
      });

      ws.send(
        JSON.stringify({
          type: "subscribed",
          channel: msg.channel,
          timestamp: new Date().toISOString(),
        })
      );
      break;
    }

    case "unsubscribe": {
      if (!msg.channel) {
        ws.send(JSON.stringify({ type: "error", error: "channel required for unsubscribe" }));
        return;
      }

      ws.subscribedChannels.delete(msg.channel);

      ws.send(
        JSON.stringify({
          type: "unsubscribed",
          channel: msg.channel,
          timestamp: new Date().toISOString(),
        })
      );
      break;
    }

    case "message": {
      if (!msg.message) {
        ws.send(JSON.stringify({ type: "error", error: "message required" }));
        return;
      }

      // Ensure the message has required fields
      const a2aMessage: A2AMessage = {
        ...msg.message,
        message_id: msg.message.message_id || uuidv4(),
        timestamp: msg.message.timestamp || new Date().toISOString(),
        protocol: "A2A/1.0",
      };

      await gateway.sendMessage(a2aMessage);

      a2aMessagesTotal
        .labels({
          message_type: a2aMessage.message_type,
          priority: a2aMessage.priority,
        })
        .inc();

      ws.send(
        JSON.stringify({
          type: "message_sent",
          message_id: a2aMessage.message_id,
          timestamp: new Date().toISOString(),
        })
      );
      break;
    }

    case "heartbeat": {
      if (!msg.heartbeat) {
        ws.send(JSON.stringify({ type: "error", error: "heartbeat data required" }));
        return;
      }

      await gateway.updateAgentHeartbeat(msg.heartbeat);

      ws.send(
        JSON.stringify({
          type: "heartbeat_ack",
          timestamp: new Date().toISOString(),
        })
      );
      break;
    }

    default: {
      ws.send(
        JSON.stringify({
          type: "error",
          error: `Unknown message type: ${(msg as { type: string }).type}`,
        })
      );
    }
  }
}

// Helper to access metric with gauge operations
function aWebSocketConnections() {
  return {
    inc: () => a2aWebSocketConnections.inc(),
    dec: () => a2aWebSocketConnections.dec(),
  };
}

// ─── Server Startup ───────────────────────────────────────────────────────────

async function start(): Promise<void> {
  try {
    // Connect A2A gateway to Redis
    const gateway = getA2AGateway();
    await gateway.connect();
    logger.info("A2A Gateway: Redis connected");

    // Pre-register all agents from static registry to Redis
    logger.info("A2A Gateway: pre-registering agents from static registry");
    for (const agent of AGENT_REGISTRY) {
      try {
        await gateway.registerAgent(agent);
      } catch (err) {
        logger.warn("A2A Gateway: failed to pre-register agent", {
          agent_id: agent.id,
          agent_name: agent.name,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
    logger.info(`A2A Gateway: pre-registered ${AGENT_REGISTRY.length} agents`);

    // Start HTTP + WebSocket server
    httpServer.listen(PORT, HOST, () => {
      logger.info("InHealth A2A Gateway started", {
        host: HOST,
        port: PORT,
        environment: process.env.NODE_ENV || "development",
        pid: process.pid,
        websocket_path: "/ws",
      });
    });

    // ─── Graceful Shutdown ─────────────────────────────────────────────────

    const gracefulShutdown = async (signal: string): Promise<void> => {
      logger.info(`A2A Gateway: received ${signal}, starting graceful shutdown`);

      // Stop accepting new WebSocket connections
      clearInterval(pingInterval);

      // Close all WebSocket connections
      for (const ws of allConnections.values()) {
        ws.close(1001, "Server shutting down");
      }

      wss.close((err) => {
        if (err) {
          logger.error("A2A Gateway: error closing WebSocket server", { error: err.message });
        }
      });

      httpServer.close(async (err) => {
        if (err) {
          logger.error("A2A Gateway: error during HTTP server close", { error: err.message });
        }

        try {
          await gateway.disconnect();
          logger.info("A2A Gateway: Redis disconnected");
          logger.info("A2A Gateway: graceful shutdown complete");
          process.exit(0);
        } catch (shutdownErr) {
          logger.error("A2A Gateway: error during shutdown", {
            error: shutdownErr instanceof Error ? shutdownErr.message : String(shutdownErr),
          });
          process.exit(1);
        }
      });

      // Force exit after 30 seconds
      setTimeout(() => {
        logger.error("A2A Gateway: forced shutdown after timeout");
        process.exit(1);
      }, 30000);
    };

    process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
    process.on("SIGINT", () => gracefulShutdown("SIGINT"));

    process.on("uncaughtException", (err) => {
      logger.error("A2A Gateway: uncaught exception", {
        error: err.message,
        stack: err.stack,
      });
      gracefulShutdown("uncaughtException").catch(() => process.exit(1));
    });

    process.on("unhandledRejection", (reason) => {
      logger.error("A2A Gateway: unhandled promise rejection", {
        reason: reason instanceof Error ? reason.message : String(reason),
      });
    });
  } catch (error) {
    logger.error("A2A Gateway: failed to start", {
      error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }
}

start();

export default app;
