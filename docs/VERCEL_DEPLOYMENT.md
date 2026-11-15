# GHOST v2 — Vercel Cloud Deployment

The hosted application is a single Next.js + FastAPI project. The Next.js frontend and the FastAPI application in `api/index.py` are deployed from this repository. The local MT5 agent remains on your Windows machine.

## 1. Connect PostgreSQL

1. Open your Vercel project.
2. Open **Storage / Marketplace** and add a PostgreSQL provider such as Neon or Supabase.
3. Make sure the integration exposes one of `GHOST_DATABASE_URL`, `POSTGRES_URL` or `DATABASE_URL` to the Production environment.
4. Open the provider's SQL editor and execute the complete contents of `api/schema.sql`.

Vercel's legacy Vercel Postgres product is no longer offered for new projects; new Postgres databases are connected through Marketplace providers. See the [Vercel Postgres guidance](https://vercel.com/docs/postgres) and [Marketplace Storage](https://vercel.com/docs/marketplace-storage).

## 2. Set Vercel environment variables

In **Project → Settings → Environment Variables**, add the following to Production (and Preview too if you want preview deployments to use a separate test DB and secrets):

| Variable | Purpose |
|---|---|
| `GHOST_DATABASE_URL` | Optional if the Marketplace provider injects `POSTGRES_URL` or `DATABASE_URL` |
| `GHOST_DASHBOARD_PASSWORD` | Password for the private GHOST dashboard |
| `GHOST_SESSION_SECRET` | Long random key for signing the 12-hour session cookie |
| `GHOST_PAIRING_SECRET` | Long random code used only when pairing a Windows agent |
| `GHOST_STALE_AFTER_SECONDS` | Optional; defaults to `10` |

Generate two different secrets locally with:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use one for `GHOST_SESSION_SECRET` and another for `GHOST_PAIRING_SECRET`. Set a separate strong password for `GHOST_DASHBOARD_PASSWORD`. Never commit these values or put them in `NEXT_PUBLIC_*` variables.

**Do not set `NEXT_PUBLIC_GHOST_LOCAL_API_URL` in Vercel.** That variable is only for local browser development against the Windows machine. The deployed dashboard uses the same-origin `/api/v1` endpoints and the private login screen.

After connecting the database, applying the SQL schema and adding the variables, redeploy the project.

## 3. Smoke-test the cloud API

Open:

- `https://YOUR-VERCEL-DOMAIN/api/v1/health`

Expected response includes `"status":"ok"`, `"database_configured":true`, `"database_connected":true` and `"execution_enabled":false`. If `database_connected` is false, check the Marketplace database integration and the `GHOST_DATABASE_URL` / `POSTGRES_URL` / `DATABASE_URL` environment variable before pairing an agent. The login screen should appear on the website root.

Sign in using `GHOST_DASHBOARD_PASSWORD`.

## 4. Pair the Windows GHOST Agent

Download the repository ZIP or clone the repository. On the Windows machine with MT5, open PowerShell in `local_agent`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py pair.py --api-url https://YOUR-VERCEL-DOMAIN --device-name GHOST-MT5-PC
```

Enter the pairing code when prompted. The agent receives a random device token and stores it in:

```text
%APPDATA%\GHOST\agent.json
```

That file is a credential. Keep it private; do not commit it or share it. If it is exposed, revoke the device record in PostgreSQL and pair again.

## 5. Start MT5 telemetry and the agent

1. Copy `mt5/GHOST_Bridge_Exporter.mq5` to MT5's `MQL5/Experts/GHOST` folder.
2. Compile it in MetaEditor and attach it to a chart.
3. Start the local agent from `local_agent`:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8765
```

The agent reads the exporter file from MT5 Common Files, stores a local SQLite history, sends snapshots and heartbeats to Vercel, and polls the cloud research queue. The local API binds to loopback only. Do not open port 8765 on your router or expose the MT5 terminal.

### Optional: install as an always-running Windows app

After pairing and verifying the Python agent manually, build and install the executable:

\`\`\`powershell
.\build_windows.ps1
.\install_startup.ps1
\`\`\`

The installer copies the complete PyInstaller bundle into \`%LOCALAPPDATA%\Programs\GHOST-Agent\`, registers a Task Scheduler task named \`GHOST Agent\`, and starts it. It starts automatically at the next Windows logon and is configured to restart if the process exits.

To remove the app and startup task, run \`.\uninstall_startup.ps1\`. This preserves the pairing credential in \`%APPDATA%\GHOST\agent.json\`; revoke the device in the dashboard and delete that credential file separately if you are retiring the PC.

When the cloud snapshot is fresh, the Vercel dashboard should change from sample/demo metrics to read-only MT5 account and position data.

## 6. Job queue status in Agent 0.2.0

The cloud queue supports `PING`, `BACKTEST`, `SENSITIVITY`, `WALK_FORWARD` and `MONTE_CARLO` job records.

In this release, the Windows agent executes only `PING`. Other job types are accepted and queued but are returned as failed with an explicit “research executor not included” message. The backtest engine and validation runners are not implemented in this milestone. Do not interpret a queued job as a completed test.

## Architecture and safety

- Vercel Functions handle authenticated API requests; they are not a permanent MT5 process.
- The Windows agent initiates outbound HTTPS requests. No inbound tunnel is required.
- The agent credential is stored hashed in PostgreSQL; the raw token is stored only in the Windows agent config after pairing. The Devices page can revoke a lost or replaced PC token. Revocation takes effect on the next request.
- Dashboard sessions are signed, HTTP-only cookies with a 12-hour lifetime and a random per-login nonce.
- Telemetry and job APIs are separate from broker execution.
- No cloud endpoint places, modifies or closes trades. Live order execution remains out of scope.
