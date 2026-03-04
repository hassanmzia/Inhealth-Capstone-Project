import { Router, Request, Response } from "express";
import { getMCPServer } from "../mcp/server";
import { logger } from "../utils/logger";

const router = Router();

router.get("/health", async (_req: Request, res: Response): Promise<void> => {
  const startTime = Date.now();

  const mcpServer = getMCPServer();
  const redisAlive = await mcpServer.ping();

  const status = {
    service: "inhealth-mcp-server",
    version: "1.0.0",
    status: redisAlive ? "healthy" : "degraded",
    timestamp: new Date().toISOString(),
    uptime_seconds: Math.floor(process.uptime()),
    checks: {
      redis: {
        status: redisAlive ? "up" : "down",
        latency_ms: Date.now() - startTime,
      },
      memory: {
        status: "up",
        heap_used_mb: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        heap_total_mb: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        rss_mb: Math.round(process.memoryUsage().rss / 1024 / 1024),
      },
    },
    environment: process.env.NODE_ENV || "development",
  };

  const httpStatus = redisAlive ? 200 : 503;

  if (httpStatus !== 200) {
    logger.warn("Health check returning degraded status", {
      redis_alive: redisAlive,
    });
  }

  res.status(httpStatus).json(status);
});

export default router;
