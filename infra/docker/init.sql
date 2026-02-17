-- PostgreSQL initialization for ClassMate
-- Enables pgvector extension and creates base tables

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Example table for pgvector testing
CREATE TABLE IF NOT EXISTS demo_embeddings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content text NOT NULL,
    embedding vector(1536)
);
