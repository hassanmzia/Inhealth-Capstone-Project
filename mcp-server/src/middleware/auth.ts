import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { logger } from "../utils/logger";
import { mcpAuthFailuresTotal } from "../utils/metrics";

export interface AuthenticatedRequest extends Request {
  user?: {
    sub: string;
    agent_id?: string;
    patient_id?: string;
    roles: string[];
    iat: number;
    exp: number;
  };
}

const JWT_SECRET = process.env.JWT_SECRET || "inhealth-mcp-secret-key-change-in-production";
const JWT_ISSUER = process.env.JWT_ISSUER || "inhealth-platform";

export function authMiddleware(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    mcpAuthFailuresTotal.labels({ reason: "missing_header" }).inc();
    logger.warn("Auth middleware: missing Authorization header", {
      path: req.path,
      method: req.method,
      ip: req.ip,
    });
    res.status(401).json({ error: "Authorization header is required" });
    return;
  }

  const parts = authHeader.split(" ");
  if (parts.length !== 2 || parts[0] !== "Bearer") {
    mcpAuthFailuresTotal.labels({ reason: "invalid_format" }).inc();
    logger.warn("Auth middleware: invalid Authorization header format", {
      path: req.path,
      ip: req.ip,
    });
    res.status(401).json({ error: "Authorization header must be in format: Bearer <token>" });
    return;
  }

  const token = parts[1];

  try {
    const decoded = jwt.verify(token, JWT_SECRET, {
      issuer: JWT_ISSUER,
    }) as AuthenticatedRequest["user"];

    req.user = decoded;

    logger.debug("Auth middleware: token verified", {
      sub: decoded?.sub,
      agent_id: decoded?.agent_id,
      path: req.path,
    });

    next();
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      mcpAuthFailuresTotal.labels({ reason: "token_expired" }).inc();
      logger.warn("Auth middleware: token expired", { path: req.path });
      res.status(401).json({ error: "Token has expired" });
    } else if (err instanceof jwt.JsonWebTokenError) {
      mcpAuthFailuresTotal.labels({ reason: "invalid_token" }).inc();
      logger.warn("Auth middleware: invalid token", {
        path: req.path,
        error: (err as Error).message,
      });
      res.status(401).json({ error: "Invalid token" });
    } else {
      mcpAuthFailuresTotal.labels({ reason: "unknown" }).inc();
      logger.error("Auth middleware: unexpected error", { error: err });
      res.status(500).json({ error: "Internal server error during authentication" });
    }
  }
}

export function generateToken(payload: {
  sub: string;
  agent_id?: string;
  patient_id?: string;
  roles: string[];
}): string {
  return jwt.sign(payload, JWT_SECRET, {
    issuer: JWT_ISSUER,
    expiresIn: process.env.JWT_EXPIRES_IN || "1h",
  } as jwt.SignOptions);
}
