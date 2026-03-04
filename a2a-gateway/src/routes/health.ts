import { Router, Request, Response } from "express";
import { getA2AGateway } from "../a2a/gateway";
import { AGENT_REGISTRY } from "../a2a/registry";
import { logger } from "../utils/logger";

const router = Router();

router.get("/health", async (_req: Request, res: Response): Promise<void> => {
  const startTime = Date.now();

  try {
    const gateway = getA2AGateway();
    const redisAlive = await gateway.ping();

    // Get registered agent count from Redis
    let activeAgentCount = 0;
    try {
      const allAgents = await gateway.getAllAgents();
      activeAgentCount = allAgents.filter(
        (a) => a.status === "active" || a.status === "idle"
      ).length;
    } catch {
      activeAgentCount = AGENT_REGISTRY.length; // Fall back to registry count
    }

    const status = {
      service: "inhealth-a2a-gateway",
      version: "1.0.0",
      status: redisAlive ? "healthy" : "degraded",
      timestamp: new Date().toISOString(),
      uptime_seconds: Math.floor(process.uptime()),
      checks: {
        redis: {
          status: redisAlive ? "up" : "down",
          latency_ms: Date.now() - startTime,
        },
        agents: {
          status: "up",
          registered_in_registry: AGENT_REGISTRY.length,
          active_in_redis: activeAgentCount,
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
      logger.warn("A2A Gateway health check returning degraded status", {
        redis_alive: redisAlive,
      });
    }

    res.status(httpStatus).json(status);
  } catch (error) {
    logger.error("Health check error", {
      error: error instanceof Error ? error.message : String(error),
    });

    res.status(503).json({
      service: "inhealth-a2a-gateway",
      status: "unhealthy",
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Health check failed",
    });
  }
});

export default router;
