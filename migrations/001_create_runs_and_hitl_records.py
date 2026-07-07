"""Migration: add runs + hitl_records tables for Phase 17 persistence.

This is a standalone SQL migration (not alembic-managed yet).
Run manually: psql -f this_file  OR  python -m hanflow.persistence.migrate
"""
from __future__ import annotations

RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR,
    workflow_name VARCHAR,
    status VARCHAR,
    result JSONB,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    trigger_source VARCHAR,
    worker_id VARCHAR,
    token_total INTEGER,
    cost_usd NUMERIC(10, 4)
);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status);
"""

HITL_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS hitl_records (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES runs(run_id),
    node_id VARCHAR,
    workflow_name VARCHAR,
    action VARCHAR,
    decided_by VARCHAR,
    decided_at TIMESTAMP NOT NULL,
    duration_seconds FLOAT,
    edited_value JSONB,
    reroute_target VARCHAR,
    reason TEXT,
    form JSONB
);
CREATE INDEX IF NOT EXISTS idx_hitl_decided_at ON hitl_records (decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_hitl_run_id ON hitl_records (run_id);
"""

DROP_TABLES = """
DROP TABLE IF EXISTS hitl_records;
DROP TABLE IF EXISTS runs;
"""

MIGRATIONS = [
    ("001_create_runs_and_hitl_records", RUNS_TABLE + HITL_RECORDS_TABLE),
]
