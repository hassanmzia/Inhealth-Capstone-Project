import express, { Request, Response, NextFunction } from "express";
import { register } from "./utils/metrics";
import { logger } from "./utils/logger";
import { authMiddleware } from "./middleware/auth";
import { getMCPServer } from "./mcp/server";
import { closeNeo4jDriver } from "./mcp/tools";
import healthRouter from "./routes/health";
import contextRouter from "./routes/context";
import toolsRouter from "./routes/tools";

const PORT = parseInt(process.env.PORT || "3001", 10);
const HOST = process.env.HOST || "0.0.0.0";

const app = express();

// ─── Middleware ───────────────────────────────────────────────────────────────

// JSON body parser with size limit
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// CORS middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  const allowedOrigins = (process.env.CORS_ORIGINS || "*").split(",");
  const origin = req.headers.origin || "";

  if (allowedOrigins.includes("*") || allowedOrigins.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", allowedOrigins.includes("*") ? "*" : origin);
  }

  res.setHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, PUT, DELETE, PATCH, OPTIONS"
  );
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-API-Key, X-Correlation-ID"
  );
  res.setHeader("Access-Control-Max-Age", "86400");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  next();
});

// Request logging middleware
app.use((req: Request, _res: Response, next: NextFunction) => {
  logger.debug("Incoming request", {
    method: req.method,
    path: req.path,
    ip: req.ip,
    user_agent: req.get("User-Agent"),
  });
  next();
});

// ─── Public Routes (no auth required) ────────────────────────────────────────

// Health check endpoint
app.use("/", healthRouter);

// Prometheus metrics endpoint
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

// ─── Protected Routes (JWT auth required) ────────────────────────────────────

app.use("/mcp", authMiddleware, contextRouter);
app.use("/mcp", authMiddleware, toolsRouter);

// ─── 404 Handler ─────────────────────────────────────────────────────────────

app.use((_req: Request, res: Response) => {
  res.status(404).json({
    error: "Not Found",
    message: "The requested endpoint does not exist",
  });
});

// ─── Global Error Handler ─────────────────────────────────────────────────────

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  logger.error("Unhandled error", {
    error: err.message,
    stack: err.stack,
  });
  res.status(500).json({
    error: "Internal Server Error",
    message: process.env.NODE_ENV === "production" ? "An unexpected error occurred" : err.message,
  });
});

// ─── Server Startup ───────────────────────────────────────────────────────────

async function start(): Promise<void> {
  try {
    // Connect to Redis
    const mcpServer = getMCPServer();
    await mcpServer.connect();
    logger.info("MCP Server: Redis connected");

    // Start HTTP server
    const server = app.listen(PORT, HOST, () => {
      logger.info("InHealth MCP Server started", {
        host: HOST,
        port: PORT,
        environment: process.env.NODE_ENV || "development",
        pid: process.pid,
      });
    });

    // ─── Graceful Shutdown ────────────────────────────────────────────────────

    const gracefulShutdown = async (signal: string): Promise<void> => {
      logger.info(`MCP Server: received ${signal}, starting graceful shutdown`);

      // Stop accepting new connections
      server.close(async (err) => {
        if (err) {
          logger.error("MCP Server: error during HTTP server close", { error: err.message });
        } else {
          logger.info("MCP Server: HTTP server closed");
        }

        try {
          // Disconnect Redis
          await mcpServer.disconnect();
          logger.info("MCP Server: Redis disconnected");

          // Close Neo4j driver
          await closeNeo4jDriver();
          logger.info("MCP Server: Neo4j driver closed");

          logger.info("MCP Server: graceful shutdown complete");
          process.exit(0);
        } catch (shutdownErr) {
          logger.error("MCP Server: error during shutdown", {
            error: shutdownErr instanceof Error ? shutdownErr.message : String(shutdownErr),
          });
          process.exit(1);
        }
      });

      // Force exit after 30 seconds
      setTimeout(() => {
        logger.error("MCP Server: forced shutdown after timeout");
        process.exit(1);
      }, 30000);
    };

    process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
    process.on("SIGINT", () => gracefulShutdown("SIGINT"));

    // Handle uncaught exceptions and unhandled rejections
    process.on("uncaughtException", (err) => {
      logger.error("MCP Server: uncaught exception", {
        error: err.message,
        stack: err.stack,
      });
      gracefulShutdown("uncaughtException").catch(() => process.exit(1));
    });

    process.on("unhandledRejection", (reason) => {
      logger.error("MCP Server: unhandled promise rejection", {
        reason: reason instanceof Error ? reason.message : String(reason),
      });
    });
  } catch (error) {
    logger.error("MCP Server: failed to start", {
      error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }
}

start();

export default app;
