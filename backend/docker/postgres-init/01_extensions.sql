-- Runs automatically when the PostgreSQL container is first created.
-- Enables extensions required by the application.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
