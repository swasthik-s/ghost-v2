-- Apply this file once to the PostgreSQL database connected to Vercel.
CREATE TABLE IF NOT EXISTS devices (
  id UUID PRIMARY KEY,
  device_name TEXT NOT NULL,
  token_hash CHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  agent_version TEXT,
  host_label TEXT,
  terminal_connected BOOLEAN NOT NULL DEFAULT FALSE,
  mt5_build INTEGER,
  latest_payload JSONB,
  latest_generated_at TIMESTAMPTZ,
  latest_received_at TIMESTAMPTZ
);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS latest_payload JSONB;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS latest_generated_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS latest_received_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS telemetry_snapshots (
  id BIGSERIAL PRIMARY KEY,
  device_id UUID NOT NULL REFERENCES devices(id),
  generated_at TIMESTAMPTZ NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB NOT NULL,
  UNIQUE(device_id, generated_at)
);
CREATE INDEX IF NOT EXISTS idx_telemetry_received ON telemetry_snapshots(received_at DESC);

CREATE TABLE IF NOT EXISTS equity_snapshots (
  id BIGSERIAL PRIMARY KEY,
  device_id UUID NOT NULL REFERENCES devices(id),
  captured_at TIMESTAMPTZ NOT NULL,
  balance NUMERIC(20, 8) NOT NULL,
  equity NUMERIC(20, 8) NOT NULL,
  floating_pnl NUMERIC(20, 8) NOT NULL,
  margin NUMERIC(20, 8) NOT NULL,
  free_margin NUMERIC(20, 8) NOT NULL,
  margin_level NUMERIC(20, 8) NOT NULL,
  currency VARCHAR(8) NOT NULL DEFAULT 'USD',
  UNIQUE(device_id, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_equity_device_time ON equity_snapshots(device_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS research_jobs (
  id UUID PRIMARY KEY,
  job_type TEXT NOT NULL CHECK (job_type IN ('PING','BACKTEST','SENSITIVITY','WALK_FORWARD','MONTE_CARLO')),
  params JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  assigned_device_id UUID REFERENCES devices(id),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  lease_until TIMESTAMPTZ,
  claimed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  result JSONB,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_research_queue ON research_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_research_device ON research_jobs(assigned_device_id, status);
