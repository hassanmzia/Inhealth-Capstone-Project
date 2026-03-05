-- PostgreSQL extensions for InHealth
-- Run after init.sql

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search enhancements
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- For TimescaleDB time-series if available (optional)
-- CREATE EXTENSION IF NOT EXISTS timescaledb;
