-- Database Initialization Script for AI Lead Response System
-- This script runs automatically when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create the database if it doesn't exist (handled by Docker env vars)
-- Create schema
CREATE SCHEMA IF NOT EXISTS public;

-- Grant permissions
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Note: Tables are created automatically by SQLAlchemy models
-- This script just ensures extensions are enabled

-- Create indexes for vector similarity search (will be added after tables exist)
-- These can be run after initial table creation:
-- CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
