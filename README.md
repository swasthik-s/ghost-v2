# GHOST v2

GHOST v2 is a local-first MT5 trading and research platform with a Vercel-hosted web application.

## Stack and responsibilities

- **Next.js 15:** trading dashboard, risk views, strategy pages, research job UI and Monaco code workspace.
- **FastAPI on Vercel:** authenticated dashboard API, Windows device pairing, telemetry ingestion and PostgreSQL-backed job queue.
- **PostgreSQL:** device registry, telemetry snapshots, equity history and research jobs.
- **Windows GHOST Agent:** always-running Python process that reads MT5 telemetry, maintains a local SQLite buffer, uploads data and polls jobs.
- **MT5:** terminal and EA-side risk/execution authority. The current exporter is telemetry-only.

## Cloud deployment

Follow [docs/VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md). The repository is structured for one Vercel project:

- Next.js frontend at the repository root.
- FastAPI app at `api/index.py`; Vercel file-based Python function routes are explicitly prefixed `/api/v1/...`.
- Python dependencies at the repository root in `requirements.txt`.
- Python version pinned by root `.python-version`.

A PostgreSQL Marketplace database must be connected and `api/schema.sql` applied. Configure `GHOST_DASHBOARD_PASSWORD`, `GHOST_SESSION_SECRET`, and `GHOST_PAIRING_SECRET` as Vercel environment variables. The hosted dashboard uses same-origin API calls and a signed HTTP-only session cookie.

## Windows agent

Follow [local_agent/README.md](local_agent/README.md).

1. Compile and attach `mt5/GHOST_Bridge_Exporter.mq5` in MetaEditor.
2. Install Python dependencies in `local_agent`.
3. Pair using `py pair.py --api-url https://YOUR-VERCEL-DOMAIN`.
4. Run `uvicorn main:app --host 127.0.0.1 --port 8765`.

The agent initiates outbound HTTPS connections to Vercel. Do not port-forward the local service or expose the MT5 terminal. Local browser development can use `NEXT_PUBLIC_GHOST_LOCAL_API_URL=http://127.0.0.1:8765`; do not set that variable in Vercel.

## Current milestone boundaries

- Dashboard login and cloud API session: implemented in source; must be configured in Vercel before the site is private.
- PostgreSQL schema and telemetry/device/job endpoints: implemented in source; database must be provisioned and schema applied.
- Device pairing and Windows outbound telemetry sync: implemented in source; must be tested on the target Windows/MT5 machine.
- Durable queue supports PING, BACKTEST, SENSITIVITY, WALK_FORWARD and MONTE_CARLO records. **Agent 0.2.0 executes only PING.** Other job types are queued but fail with an explicit unsupported-runner message until the research handlers are implemented.
- Browser editor remains in-memory; filesystem save, MetaEditor compile dispatch and Python code execution are not implemented.
- No cloud API places, modifies or closes broker orders. Trading execution remains disabled.

## Validation

GitHub Actions is configured to run Python bridge tests, compile Python sources and build the Next.js app. Do not assume these checks passed unless a completed run reports success. MetaEditor compilation and real MT5 telemetry still require verification on Windows.
