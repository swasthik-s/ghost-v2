# GHOST v2

A local-first trading, risk and research terminal for MT5. The initial UI release is a dashboard prototype with clearly labelled sample data. It does **not** connect to a broker or place trades.

## Stack

- Next.js 15 App Router + React + TypeScript
- Recharts for dashboard visualisation
- Monaco Editor for Python and MQL5 workspace tabs
- Python research/bridge services (to be added in the next milestone)
- MT5 Expert Advisor on the Windows execution machine

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Current pages

- Trading overview: equity, P&L, win rate, positions, execution log, risk limits
- Risk overview, exposure and risk alerts
- Strategy selector for Precision Sniper, Intraday Momentum, SuperTrend Grid and Origin Ladder
- Backtest runner UI, validation lab scaffolds (sensitivity, walk-forward, Monte Carlo)
- Market data catalogue
- MT5 bridge onboarding and status
- Monaco code workspace with Python and MQL5 starter files
- Settings draft UI

## Important boundaries

1. All figures currently shown are illustrative demo values and must not be treated as broker records or strategy validation.
2. The browser editor currently edits in-memory source only. Saving does not write to the local filesystem yet.
3. Python execution must be implemented through the local Python service/worker, not a browser `eval` mechanism.
4. MQL5 compilation must run through MetaEditor on the Windows MT5 host.
5. The EA risk governor remains the final authority. Dashboard or Python strategy signals must never bypass broker-side/EA-side hard limits.
6. The MT5 terminal should not be exposed directly to the public internet. A local agent should initiate an authenticated outbound connection to the dashboard/API.

## Planned architecture

```text
Next.js dashboard (Vercel or local)
        | HTTPS / authenticated WebSocket
        v
Python API + research worker (local first; cloud worker later)
        ^
        | authenticated outbound connection
Windows local agent <----> MT5 terminal + GHOST EA
        |
        +---- SQLite research store / exported trade and equity records
```

Strategy Tester mode should use file-based configuration and export files. Live/demo mode may use a local bridge with a versioned JSON protocol, heartbeat, timeouts and fail-closed behaviour (`WAIT` when the bridge is disconnected or stale).

## Next milestones

1. Implement Python FastAPI service, SQLite schema and typed API contracts.
2. Implement Windows local agent and MT5 EA telemetry/export protocol.
3. Connect dashboard to live/demo account, position, equity and execution events.
4. Add research worker for bar-level backtests, sensitivity, walk-forward and Monte Carlo.
5. Add filesystem-backed editor save, MetaEditor compile command and controlled Python job execution.
6. Add auth, roles, audit log, secrets handling and deployment hardening before any live account integration.
