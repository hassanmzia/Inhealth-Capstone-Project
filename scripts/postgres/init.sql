-- PostgreSQL initialization script
-- Creates additional databases needed by services

-- Create grafana database if it doesn't exist
SELECT 'CREATE DATABASE grafana'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'grafana')\gexec

-- Create langfuse database if it doesn't exist
SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec

-- Grant privileges to the main user
GRANT ALL PRIVILEGES ON DATABASE grafana TO CURRENT_USER;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO CURRENT_USER;
