from __future__ import annotations

import asyncio
import json
import os
import platform
import sqlite3
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

STALE_AFTER_SECONDS = float(os.getenv("GHOST_STALE_AFTER_SECONDS", "10"))
EQUITY_SAMPLE_SECONDS = float(os.getenv("GHOST_EQUITY_SAMPLE_SECONDS", "15"))
CLOUD_UPLOAD_SECONDS = float(os.getenv("GHOST_CLOUD_UPLOAD_SECONDS", "5"))
CLOUD_HEARTBEAT_SECONDS = float(os.getenv("GHOST_CLOUD_HEARTBEAT_SECONDS", "30"))
CLOUD_JOB_POLL_SECONDS = float(os.getenv("GHOST_CLOUD_JOB_POLL_SECONDS", "15"))
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DEFAULT_APP_DATA = Path(os.getenv("APPDATA", str(Path.home()))) / "GHOST"
DB_PATH = Path(os.getenv("GHOST_DB_PATH", str(DEFAULT_APP_DATA / "data" / "ghost_local.db")))
DEFAULT_COMMON = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "MetaQuotes" / "Terminal" / "Common" / "Files"
COMMON_FILES_DIR = Path(os.getenv("MT5_COMMON_FILES_DIR", str(DEFAULT_COMMON)))
SNAPSHOT_PATH = COMMON_FILES_DIR / "GHOST" / "telemetry.json"
CONFIG_PATH = Path(os.getenv("GHOST_AGENT_CONFIG", str(Path(os.getenv("APPDATA", str(Path.home())) ) / "GHOST" / "agent.json")))

cache: dict[str, Any] = {"payload": None, "mtime": None, "read_error": None, "last_sampled_at": None}


def db_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at REAL NOT NULL,
                file_mtime REAL NOT NULL UNIQUE,
                balance REAL NOT NULL,
                equity REAL NOT NULL,
                floating_pnl REAL NOT NULL,
                margin REAL NOT NULL,
                free_margin REAL NOT NULL,
                margin_level REAL NOT NULL,
                currency TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_equity_time ON equity_snapshots(captured_at)")


def load_agent_settings() -> dict[str, Any]:
    settings: dict[str, Any] = {}
    try:
        if CONFIG_PATH.exists():
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                settings.update(loaded)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"GHOST Agent: could not read config: {exc}")
    settings["cloud_api_url"] = os.getenv("GHOST_CLOUD_API_URL", settings.get("cloud_api_url", "")).rstrip("/")
    settings["device_token"] = os.getenv("GHOST_DEVICE_TOKEN", settings.get("device_token", ""))
    settings["device_name"] = os.getenv("GHOST_DEVICE_NAME", settings.get("device_name", platform.node()))
    return settings


def read_export() -> tuple[dict[str, Any] | None, float | None, str | None]:
    try:
        stat = SNAPSHOT_PATH.stat()
        raw = SNAPSHOT_PATH.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("Unsupported telemetry schema; expected schema_version=1")
        account = payload.get("account")
        positions = payload.get("positions")
        if not isinstance(account, dict) or not isinstance(positions, list):
            raise ValueError("Telemetry is missing account or positions data")
        required = ("balance", "equity", "floating_pnl", "margin", "free_margin", "margin_level")
        for key in required:
            if not isinstance(account.get(key), (int, float)):
                raise ValueError(f"Invalid account field: {key}")
        return payload, stat.st_mtime, None
    except FileNotFoundError:
        return None, None, "Waiting for MT5 exporter file"
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return None, None, str(exc)


def save_equity(payload: dict[str, Any], mtime: float) -> None:
    account = payload["account"]
    with db_connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO equity_snapshots
            (captured_at,file_mtime,balance,equity,floating_pnl,margin,free_margin,margin_level,currency)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            mtime, mtime, float(account["balance"]), float(account["equity"]),
            float(account["floating_pnl"]), float(account["margin"]),
            float(account["free_margin"]), float(account["margin_level"]),
            str(account.get("currency", "USD"))[:8],
        ))


async def telemetry_worker() -> None:
    while True:
        try:
            payload, mtime, error = await asyncio.to_thread(read_export)
            if payload is not None and mtime is not None:
                old_mtime = cache.get("mtime")
                cache.update(payload=payload, mtime=mtime, read_error=None)
                last_sampled = cache.get("last_sampled_at")
                if (
                    (old_mtime is None or mtime > float(old_mtime))
                    and (last_sampled is None or time.time() - float(last_sampled) >= EQUITY_SAMPLE_SECONDS)
                ):
                    await asyncio.to_thread(save_equity, payload, mtime)
                    cache["last_sampled_at"] = time.time()
            elif error:
                cache["read_error"] = error
        except Exception as exc:
            cache["read_error"] = f"Telemetry worker error: {exc}"
        await asyncio.sleep(1)


async def cloud_sync_worker() -> None:
    """Outbound-only sync loop. It never exposes an inbound listener for cloud traffic."""
    last_heartbeat = 0.0
    last_upload = 0.0
    last_uploaded_mtime: float | None = None
    last_job_poll = 0.0
    async with httpx.AsyncClient(timeout=8.0) as client:
        while True:
            try:
                settings = load_agent_settings()
                base = settings.get("cloud_api_url", "")
                token = settings.get("device_token", "")
                if not base or not token:
                    await asyncio.sleep(3)
                    continue

                client.headers["Authorization"] = f"Bearer {token}"
                now = time.time()
                if now - last_heartbeat >= CLOUD_HEARTBEAT_SECONDS:
                    payload = cache.get("payload") or {}
                    terminal = payload.get("terminal", {})
                    try:
                        response = await client.post(
                            f"{base}/api/v1/agent/heartbeat",
                            json={
                                "agent_version": "0.2.0",
                                "host_label": platform.node()[:80],
                                "terminal_connected": bool(terminal.get("connected", False)),
                                "mt5_build": terminal.get("build"),
                            },
                        )
                        response.raise_for_status()
                        last_heartbeat = now
                    except httpx.HTTPError as exc:
                        print(f"GHOST Agent heartbeat failed: {exc}")

                payload, mtime, read_error = await asyncio.to_thread(read_export)
                if (
                    payload is not None and mtime is not None
                    and mtime != last_uploaded_mtime
                    and now - last_upload >= CLOUD_UPLOAD_SECONDS
                ):
                    try:
                        response = await client.post(f"{base}/api/v1/telemetry/snapshot", json=payload)
                        response.raise_for_status()
                        last_uploaded_mtime = mtime
                        last_upload = now
                    except httpx.HTTPError as exc:
                        print(f"GHOST Agent telemetry upload failed: {exc}")
                elif read_error:
                    cache["read_error"] = read_error

                if now - last_job_poll >= CLOUD_JOB_POLL_SECONDS:
                    last_job_poll = now
                    try:
                        response = await client.post(f"{base}/api/v1/agent/jobs/claim")
                        response.raise_for_status()
                        job = response.json().get("job")
                        if job:
                            job_id = job["id"]
                            if job["job_type"] == "PING":
                                result = await client.post(
                                    f"{base}/api/v1/agent/jobs/{job_id}/complete",
                                    json={"result": {
                                        "agent_version": "0.2.0",
                                        "host": platform.node(),
                                        "mt5_connected": bool((cache.get("payload") or {}).get("terminal", {}).get("connected", False)),
                                    }},
                                )
                            else:
                                result = await client.post(
                                    f"{base}/api/v1/agent/jobs/{job_id}/fail",
                                    json={"error": "This job type is queued but its research executor is not included in GHOST Agent 0.2.0 yet."},
                                )
                            result.raise_for_status()
                    except httpx.HTTPError as exc:
                        print(f"GHOST Agent job poll failed: {exc}")
            except Exception as exc:
                print(f"GHOST Agent cloud worker error: {type(exc).__name__}: {exc}")
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    tasks = [asyncio.create_task(telemetry_worker()), asyncio.create_task(cloud_sync_worker())]
    print(f"GHOST Agent local telemetry file: {SNAPSHOT_PATH}")
    print(f"GHOST Agent config file: {CONFIG_PATH}")
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    title="GHOST Local Agent",
    version="0.2.0",
    description="Local MT5 telemetry collector and outbound-only cloud sync agent. No order execution endpoints.",
    lifespan=lifespan,
)

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
extra_origin = os.getenv("GHOST_DASHBOARD_ORIGIN")
if extra_origin:
    origins.append(extra_origin.rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


def snapshot_response() -> dict[str, Any]:
    payload = cache.get("payload")
    mtime = cache.get("mtime")
    age = max(0.0, time.time() - float(mtime)) if mtime is not None else None
    fresh = age is not None and age <= STALE_AFTER_SECONDS
    terminal = (payload or {}).get("terminal", {})
    settings = load_agent_settings()
    return {
        "connected": bool(fresh and terminal.get("connected", False)),
        "data_source": "MT5_COMMON_FILES" if payload else "NONE",
        "age_seconds": round(age, 2) if age is not None else None,
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "last_update": (payload or {}).get("generated_at_utc"),
        "account": (payload or {}).get("account"),
        "positions": (payload or {}).get("positions", []),
        "terminal": terminal,
        "cloud_configured": bool(settings.get("cloud_api_url") and settings.get("device_token")),
        "execution_enabled": False,
        "read_error": cache.get("read_error"),
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {"service": "GHOST Local Agent", "version": "0.2.0", "mode": "read-only-and-cloud-sync"}


@app.get("/health")
@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    result = snapshot_response()
    return {
        "status": "ok",
        "mt5_connected": result["connected"],
        "cloud_configured": result["cloud_configured"],
        "age_seconds": result["age_seconds"],
        "execution_enabled": False,
    }


@app.get("/api/v1/snapshot")
def get_snapshot() -> dict[str, Any]:
    return snapshot_response()


@app.get("/api/v1/equity")
def get_equity(limit: int = 300) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 2000))
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT captured_at,balance,equity,floating_pnl,currency "
            "FROM equity_snapshots ORDER BY captured_at DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    records = [dict(row) for row in reversed(rows)]
    return {"count": len(records), "items": records}


@app.get("/api/v1/config")
def get_config() -> dict[str, Any]:
    settings = load_agent_settings()
    return {
        "mode": "read-only",
        "cloud_configured": bool(settings.get("cloud_api_url") and settings.get("device_token")),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "snapshot_file": str(SNAPSHOT_PATH),
        "database_file": str(DB_PATH),
        "config_file": str(CONFIG_PATH),
        "execution_enabled": False,
    }
