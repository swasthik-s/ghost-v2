# GHOST v2 Architecture

## Runtime boundaries

| Component | Responsibility | Must not do |
|---|---|---|
| Next.js on Vercel | Private dashboard, charts, settings drafts, job submission | Direct broker execution |
| FastAPI on Vercel | Session auth, device pairing, telemetry ingest, job queue | Run a permanent MT5 session or bypass EA risk |
| PostgreSQL | Device records, telemetry/equity history, research job state | Store raw device bearer tokens |
| Windows GHOST Agent | Read MT5 exporter, local SQLite buffer, outbound cloud sync, job polling | Expose an inbound public listener or place trades |
| Local Python research engine | Backtests, sensitivity, walk-forward and Monte Carlo | Bypass data-quality controls or the EA execution governor |
| MT5 EA | Broker execution, final risk limits, order audit | Trust stale/untrusted external commands |

## Cloud data flow

```text
MT5 terminal
  └─ read-only MQL5 exporter
       └─ MT5 Common Files / GHOST/telemetry.json
            └─ Windows GHOST Agent.exe
                 ├─ local SQLite buffer
                 ├─ outbound HTTPS telemetry + heartbeat
                 └─ polls PostgreSQL-backed research job queue
                       └─ Vercel FastAPI + PostgreSQL
                            ├─ Next.js dashboard
                            └─ authenticated research job API
```

The browser and API share the Vercel origin. The local agent initiates all network connections; no router port forwarding is required.

## API security

- Dashboard: password login, HMAC-signed HTTP-only 12-hour cookie.
- Pairing: one-time display of a randomly generated device token, stored as SHA-256 digest in PostgreSQL.
- Agent: bearer token required for heartbeat, telemetry and queue claim/complete/fail endpoints.
- Pairing code, session secret, dashboard password and database URL are server-side environment variables only.
- Telemetry payload does not include account login credentials.
- No order placement, modification or close endpoints exist.

## Research queue

PostgreSQL stores a typed allowlist of job kinds. Workers claim jobs using row locks and leases. A job is not a result: the local agent must run a registered handler and submit a completion payload. In Agent 0.2.0, only the PING diagnostic handler is implemented; research jobs remain unimplemented and return a clear failure rather than fabricated output.

## Required trading controls before any execution integration

- Max risk per trade, daily equity loss, peak-to-current drawdown, lots, concurrent positions and symbol exposure.
- Stale signal expiry, duplicate request idempotency, heartbeat timeout and disconnected-state no-entry policy.
- Append-only audit log for configuration changes, strategy decisions, risk approvals/rejections and orders.
- Separate demo/live credentials; live mode locked by default.
- EA risk governor retains final authority.

## Validation sequence

1. Confirm MT5 exporter compiles and writes valid telemetry.
2. Confirm Windows pairing, heartbeat and cloud telemetry arrive.
3. Confirm stale/disconnected state is detected.
4. Confirm PING job completes through the durable queue.
5. Implement the Python research job handlers using real historical data.
6. Add sensitivity analysis, walk-forward and Monte Carlo.
7. Cross-check against MT5 Strategy Tester and demo forward test.


## Cloud device lifecycle

- Device pairing uses a high-entropy pairing secret from server-side environment variables.
- The Windows agent receives a high-entropy bearer token once; PostgreSQL stores only its SHA-256 digest.
- The dashboard can list paired devices and revoke a device token. Revocation blocks subsequent agent requests.
- Dashboard sessions are HMAC-signed, HTTP-only cookies with expiry and a random nonce; session secrets must be at least 32 characters.
