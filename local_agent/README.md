# GHOST Windows Local Agent

The Windows agent connects MT5 locally and synchronizes read-only telemetry with the GHOST Vercel API. It also polls the cloud research queue. It does not send, modify or close trades.

## Requirements

- Windows 10/11
- Python 3.12
- MT5 terminal installed and logged into the intended demo account
- GHOST Cloud API deployed and configured

## 1. Install the telemetry exporter

Copy `mt5/GHOST_Bridge_Exporter.mq5` into the MT5 data folder under `MQL5/Experts/GHOST/`, open it in MetaEditor, compile it, then attach it to a chart. The EA uses timer events and contains no trade functions.

The exporter writes UTF-8 JSON to:
`%APPDATA%\MetaQuotes\Terminal\Common\Files\GHOST\telemetry.json`

It includes balance, equity, floating P&L, margin, terminal details and open positions. It does not export account login numbers or credentials.

## 2. Install and pair the Windows agent

From PowerShell in this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py pair.py --api-url https://YOUR-VERCEL-DOMAIN --device-name GHOST-MT5-PC
```

Enter the pairing code configured in Vercel as `GHOST_PAIRING_SECRET`. Pairing writes a device token to `%APPDATA%\GHOST\agent.json`. Protect that file like a password.

## 3. Run the always-on agent

```powershell
uvicorn main:app --host 127.0.0.1 --port 8765
```

Keep this process running while MT5 is running. The local FastAPI service reads the Common Files export and maintains SQLite history. Its cloud sync task sends telemetry and heartbeats through outbound HTTPS and claims research jobs.

Local diagnostics:
- `http://127.0.0.1:8765/health`
- `http://127.0.0.1:8765/api/v1/snapshot`
- `http://127.0.0.1:8765/api/v1/config`

## 4. Local dashboard development

For local Next.js development only, set in the root `.env.local`:

```env
NEXT_PUBLIC_GHOST_LOCAL_API_URL=http://127.0.0.1:8765
```

Do not add this variable to Vercel. The hosted dashboard talks to the same-origin cloud API.

## 4. Build the Windows executable

On the Windows build machine, from this directory:

```powershell
.\build_windows.ps1
```

The script creates an onedir package at:

```text
dist\GHOST-Agent\GHOST-Agent.exe
```

Keep the entire `dist\GHOST-Agent` folder together when moving it to the trading PC. The executable stores its SQLite data and pairing config under `%APPDATA%\GHOST`. Python does not need to be installed on the destination PC if you copy the complete onedir package, but MT5 must be installed and running.

Run `GHOST-Agent.exe` manually once and confirm the local health endpoint responds at `http://127.0.0.1:8765/health`.

## 5. Job worker availability

Agent 0.2.0 handles the `PING` diagnostic job. Backtest, sensitivity, walk-forward and Monte Carlo job types can be recorded in the cloud queue, but are not run by this agent release. They are failed with a clear unsupported-handler message until the research runner module is delivered.

## Windows automatic startup

After manual validation, create a Windows Task Scheduler task:
- Trigger: At log on
- Program: the Python executable inside `.venv\Scripts\python.exe`
- Arguments: `-m uvicorn main:app --host 127.0.0.1 --port 8765`
- Start in: this `local_agent` folder
- Enable restart on failure

Keep MT5 itself configured to start with Windows and remain logged in. Do not run the local API on `0.0.0.0`; it should stay bound to `127.0.0.1`.

## Safety

- Read-only telemetry and cloud sync only.
- No trade execution API or remote shell-command facility.
- No router port forwarding.
- Revoke the device token if `agent.json` is lost or exposed.
