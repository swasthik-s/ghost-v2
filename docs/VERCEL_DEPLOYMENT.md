# Deploy GHOST v2 to Vercel

## Import from GitHub

1. Open https://vercel.com/new and choose **Import Git Repository**.
2. Select `swasthik-s/ghost-v2`.
3. Keep the Root Directory as `./`.
4. Framework Preset should be **Next.js**.
5. Use the default build command `npm run build` and deploy.

The frontend is a Next.js app. The small FastAPI scaffold is exposed separately as a Python Function from `api/index.py`; dependencies are declared in the repository-root `requirements.txt`. After deployment, check the Vercel runtime logs for the Python function.

## Environment variables

The UI is currently configured to display demo/sample information. No secrets are required for the first deployment. Do not add broker passwords, MT5 credentials, API keys or account tokens to `NEXT_PUBLIC_*` variables.

## Important system boundary

Vercel hosts the web UI and small request/response API endpoints. It is not the MT5 terminal host. Keep the MT5 terminal, local execution agent and final risk governor on the Windows machine. The dashboard and Python API are not authorized to bypass the EA risk governor.

Heavy historical backtests, parameter sweeps, walk-forward analysis and Monte Carlo workloads should run in a dedicated research worker and be benchmarked against the chosen compute/runtime limits. The API currently returns `WAIT` and never authorizes an order.

## Current implementation status

- Next.js dashboard: scaffolded; figures are sample values only.
- Browser code editor: Monaco-based, in-memory edits only; no filesystem persistence yet.
- Python FastAPI: health and decision contract stubs only.
- MT5 bridge: not implemented; no account connection or order execution.
- MT5 source: safe placeholder only; compile and validate it with MetaEditor before any use.


## Connecting the Vercel UI to the local MT5 data

The local bridge in `local_agent/` binds to `127.0.0.1` and is intentionally not exposed. The browser app can poll a configured API URL, but a Vercel deployment does not make the Windows PC reachable. Do not set the public Vercel variable to `http://127.0.0.1:8765` expecting it to reach the PC, and do not open the local port on the router.

For now, use local Next.js development to verify MT5 telemetry. A later remote deployment milestone must add a secure authenticated outbound agent channel and durable cloud storage before the Vercel app can receive account data.
