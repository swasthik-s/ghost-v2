# Local MT5 Bridge (read-only milestone)

This bridge reads telemetry exported by an MT5 Expert Advisor through the terminal's Common\Files sandbox. It does not send, modify, or close orders.

## 1. Install the exporter EA

Copy `mt5/GHOST_Bridge_Exporter.mq5` into your MT5 data folder under `MQL5/Experts/GHOST/`, open it in MetaEditor, compile it, then attach it to any chart. Enable Algo Trading only if your terminal requires it for timer events, but this EA contains no trade functions and sends no orders. Keep the terminal running.

The exporter writes:
`%APPDATA%\MetaQuotes\Terminal\Common\Files\GHOST\telemetry.json`

It exports account balance/equity/margin and open positions once per second. It is read-only and does not include credentials.

## 2. Start the local Python API on Windows

Open PowerShell in the repository's `local_agent` directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MT5_COMMON_FILES_DIR = "$env:APPDATA\MetaQuotes\Terminal\Common\Files"
uvicorn main:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/docs` to inspect the read-only API.

Useful endpoints:
- `GET /health`
- `GET /api/v1/snapshot`
- `GET /api/v1/equity?limit=300`
- `GET /api/v1/config`

SQLite history is stored in `local_agent/data/ghost_local.db`. Override it using `GHOST_DB_PATH`.

## 3. Dashboard

For local Next.js development, set `NEXT_PUBLIC_GHOST_API_URL=http://127.0.0.1:8765` in `.env.local`, restart Next.js and open the dashboard from `http://localhost:3000`.

The deployed Vercel site cannot automatically reach your Windows localhost. Do not expose port 8765 to the public internet. To connect a hosted dashboard, deploy a properly authenticated cloud ingestion/API layer with durable storage and a secure outbound agent channel. That cloud relay is a separate next step.

## Safety and limitations

- All endpoints are read-only. There is no order endpoint.
- The dashboard should mark telemetry stale after 10 seconds without a fresh file.
- A terminal disconnect should show disconnected status even if the last snapshot remains in the database.
- This exporter is a separate EA; it does not modify the user's strategy EA.
- Compile with MetaEditor and verify the Common Files path on the target terminal. This source has not been compiled in this development environment.
