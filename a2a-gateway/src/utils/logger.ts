import winston from "winston";

const { combine, timestamp, json, errors, colorize, simple } = winston.format;

const isDevelopment = process.env.NODE_ENV !== "production";

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || "info",
  format: combine(
    errors({ stack: true }),
    timestamp({ format: "ISO" }),
    json()
  ),
  defaultMeta: { service: "inhealth-a2a-gateway" },
  transports: [
    new winston.transports.Console({
      format: isDevelopment
        ? combine(colorize(), simple())
        : combine(timestamp(), json()),
    }),
  ],
});

if (process.env.LOG_FILE) {
  logger.add(
    new winston.transports.File({
      filename: process.env.LOG_FILE,
      format: combine(timestamp(), json()),
    })
  );
}

export default logger;
