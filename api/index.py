from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

app = FastAPI(
    title="GHOST v2 Cloud API",
    version="0.3.0",
    description="Authenticated telemetry ingestion and durable research queue. No broker execution endpoints.",
)

Strategy = Literal["PRECISION_SNIPER", "INTRADAY_MOMENTUM", "SUPERTREND_GRID", "ORIGIN_LADDER"]
JobType = Literal["PING", "BACKTEST", "SENSITIVITY", "WALK_FORWARD", "MONTE_CARLO"]
SESSION_COOKIE = "ghost_session"
SESSION_SECONDS = 12 * 60 * 60
STALE_AFTER_SECONDS = int(os.getenv("GHOST_STALE_AFTER_SECONDS", "10"))


def database_url() -> str:
    value = os.getenv("GHOST_DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if not value:
        raise HTTPException(status_code=503, detail="PostgreSQL is not configured. Add GHOST_DATABASE_URL or DATABASE_URL.")
    return value


def connect():
    try:
        return psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=8)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database connection failed ({type(exc).__name__}).") from exc


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HTTPException(status_code=503, detail=f"Server setting {name} is not configured.")
    return value


def session_signature(expiry: str) -> str:
    secret = require_env("GHOST_SESSION_SECRET").encode("utf-8")
    return hmac.new(secret, expiry.encode("ascii"), hashlib.sha256).hexdigest()


def make_session() -> str:
    expiry = str(int(time.time()) + SESSION_SECONDS)
    return expiry + "." + session_signature(expiry)


def valid_session(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expiry, signature = token.split(".", 1)
    if not expiry.isdigit() or int(expiry) < int(time.time()):
        return False
    try:
        expected = session_signature(expiry)
    except HTTPException:
        return False
    return hmac.compare_digest(signature, expected)


def require_dashboard(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)
    if not valid_session(token):
        raise HTTPException(status_code=401, detail="Login required.")
    return "admin"


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_device(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Device bearer token required.")
    raw_token = authorization[7:].strip()
    if len(raw_token) < 32:
        raise HTTPException(status_code=401, detail="Invalid device token.")
    with connect() as conn:
        row = conn.execute(
            "SELECT id, device_name FROM devices WHERE token_hash=%s AND revoked_at IS NULL",
            (token_digest(raw_token),),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Unknown or revoked device token.")
    return row


def parse_export_time(value: str | None) -> datetime:
    if value:
        try:
            return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                pass
    return datetime.now(timezone.utc)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class PairRequest(BaseModel):
    pairing_code: str = Field(min_length=16, max_length=256)
    device_name: str = Field(default="GHOST Windows Agent", min_length=1, max_length=80)


class HeartbeatRequest(BaseModel):
    agent_version: str = Field(default="0.1.0", max_length=32)
    host_label: str = Field(default="Windows", max_length=80)
    terminal_connected: bool = False
    mt5_build: int | None = None


class PositionModel(BaseModel):
    ticket: int
    symbol: str = Field(min_length=1, max_length=32)
    side: Literal["BUY", "SELL"]
    volume: float = Field(ge=0)
    price_open: float = Field(ge=0)
    price_current: float = Field(ge=0)
    profit: float
    swap: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    magic: int = 0
    comment: str = Field(default="", max_length=160)


class AccountModel(BaseModel):
    currency: str = Field(default="USD", min_length=1, max_length=8)
    balance: float
    equity: float
    floating_pnl: float
    margin: float
    free_margin: float
    margin_level: float


class TerminalModel(BaseModel):
    connected: bool
    company: str = Field(default="", max_length=120)
    server: str = Field(default="", max_length=120)
    build: int | None = None


class SnapshotRequest(BaseModel):
    schema_version: Literal[1]
    generated_at_utc: str | None = None
    terminal: TerminalModel
    account: AccountModel
    positions: list[PositionModel] = Field(max_length=500)


class JobCreateRequest(BaseModel):
    job_type: JobType
    params: dict[str, Any] = Field(default_factory=dict)


class JobResultRequest(BaseModel):
    result: dict[str, Any] = Field(default_factory=dict)


class JobFailureRequest(BaseModel):
    error: str = Field(min_length=1, max_length=2000)


@app.get("/api")
def root() -> dict[str, Any]:
    return {"service": "GHOST v2 Cloud API", "version": "0.3.0", "mode": "telemetry-and-research-queue", "execution_enabled": False}


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "database_configured": bool(os.getenv("GHOST_DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")), "execution_enabled": False}


@app.post("/api/v1/auth/login")
def login(body: LoginRequest, response: Response) -> dict[str, Any]:
    password = require_env("GHOST_DASHBOARD_PASSWORD")
    if not hmac.compare_digest(body.password, password):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    require_env("GHOST_SESSION_SECRET")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=make_session(),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.getenv("VERCEL") == "1",
        samesite="lax",
        path="/api/v1",
    )
    return {"authenticated": True, "expires_in": SESSION_SECONDS}


@app.get("/api/v1/auth/me")
def auth_me(_: str = Depends(require_dashboard)) -> dict[str, bool]:
    return {"authenticated": True}


@app.post("/api/v1/auth/logout")
def logout(response: Response, _: str = Depends(require_dashboard)) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE, path="/api/v1", httponly=True, secure=os.getenv("VERCEL") == "1", samesite="lax")
    return {"authenticated": False}


@app.post("/api/v1/devices/pair")
def pair_device(body: PairRequest) -> dict[str, Any]:
    expected = require_env("GHOST_PAIRING_SECRET")
    if not hmac.compare_digest(body.pairing_code, expected):
        raise HTTPException(status_code=401, detail="Invalid pairing code.")
    raw_token = secrets.token_urlsafe(48)
    device_id = uuid.uuid4()
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO devices (id, device_name, token_hash) VALUES (%s,%s,%s) RETURNING id, device_name, created_at",
            (device_id, body.device_name, token_digest(raw_token)),
        ).fetchone()
    return {"device_id": str(row["id"]), "device_name": row["device_name"], "device_token": raw_token, "created_at": row["created_at"].isoformat(), "warning": "Copy this token now. It is shown only once."}


@app.post("/api/v1/agent/heartbeat")
def heartbeat(body: HeartbeatRequest, device: dict[str, Any] = Depends(require_device)) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """UPDATE devices SET last_seen_at=now(), agent_version=%s, host_label=%s,
               terminal_connected=%s, mt5_build=%s WHERE id=%s""",
            (body.agent_version, body.host_label, body.terminal_connected, body.mt5_build, device["id"]),
        )
    return {"accepted": True, "server_time": datetime.now(timezone.utc).isoformat()}


@app.post("/api/v1/telemetry/snapshot")
def ingest_snapshot(body: SnapshotRequest, device: dict[str, Any] = Depends(require_device)) -> dict[str, Any]:
    generated_at = parse_export_time(body.generated_at_utc)
    payload = body.model_dump(mode="json")
    with connect() as conn:
        # Keep the latest state on the device row for real-time dashboards.
        conn.execute(
            """UPDATE devices SET latest_payload=%s, latest_generated_at=%s,
               latest_received_at=now(), last_seen_at=now(), terminal_connected=%s
               WHERE id=%s""",
            (Jsonb(payload), generated_at, body.terminal.connected, device["id"]),
        )
        # Keep a lower-frequency audit trail rather than one database row per upload.
        conn.execute(
            """INSERT INTO telemetry_snapshots (device_id, generated_at, payload)
               SELECT %s,%s,%s
               WHERE NOT EXISTS (
                 SELECT 1 FROM telemetry_snapshots
                 WHERE device_id=%s AND received_at > now() - interval '15 seconds'
               )
               ON CONFLICT (device_id, generated_at)
               DO UPDATE SET received_at=now(), payload=EXCLUDED.payload""",
            (device["id"], generated_at, Jsonb(payload), device["id"]),
        )
        account = body.account
        conn.execute(
            """INSERT INTO equity_snapshots
               (device_id,captured_at,balance,equity,floating_pnl,margin,free_margin,margin_level,currency)
               SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s
               WHERE NOT EXISTS (
                 SELECT 1 FROM equity_snapshots
                 WHERE device_id=%s AND captured_at > %s - interval '15 seconds'
               )
               ON CONFLICT (device_id,captured_at) DO NOTHING""",
            (device["id"], generated_at, account.balance, account.equity, account.floating_pnl,
             account.margin, account.free_margin, account.margin_level, account.currency,
             device["id"], generated_at),
        )
    return {"accepted": True, "generated_at": generated_at.isoformat(), "position_count": len(body.positions), "execution_enabled": False}


@app.get("/api/v1/dashboard/snapshot")
def dashboard_snapshot(_: str = Depends(require_dashboard)) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """SELECT latest_generated_at AS generated_at,latest_received_at AS received_at,
                      latest_payload AS payload,id AS device_id,device_name,last_seen_at,terminal_connected
               FROM devices
               WHERE revoked_at IS NULL AND latest_payload IS NOT NULL
               ORDER BY latest_received_at DESC LIMIT 1"""
        ).fetchone()
    if not row:
        return {"connected": False, "age_seconds": None, "account": None, "positions": [], "terminal": {}, "execution_enabled": False}
    age = max(0.0, (datetime.now(timezone.utc) - row["received_at"]).total_seconds())
    payload = row["payload"]
    terminal = payload.get("terminal", {})
    connected = age <= STALE_AFTER_SECONDS and bool(terminal.get("connected"))
    return {
        "connected": connected,
        "device_id": str(row["device_id"]),
        "device_name": row["device_name"],
        "age_seconds": round(age, 2),
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "last_update": row["generated_at"].isoformat(),
        "account": payload.get("account"),
        "positions": payload.get("positions", []),
        "terminal": terminal,
        "execution_enabled": False,
    }


@app.get("/api/v1/dashboard/equity")
def dashboard_equity(limit: int = 300, _: str = Depends(require_dashboard)) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 2000))
    with connect() as conn:
        device = conn.execute(
            "SELECT id AS device_id FROM devices WHERE latest_payload IS NOT NULL AND revoked_at IS NULL ORDER BY latest_received_at DESC LIMIT 1"
        ).fetchone()
        if not device:
            return {"count": 0, "items": []}
        rows = conn.execute(
            """SELECT captured_at,balance,equity,floating_pnl,margin,free_margin,margin_level,currency
               FROM equity_snapshots WHERE device_id=%s ORDER BY captured_at DESC LIMIT %s""",
            (device["device_id"], safe_limit),
        ).fetchall()
    items = [dict(row) for row in reversed(rows)]
    for item in items:
        item["captured_at"] = item["captured_at"].isoformat()
        for key, value in list(item.items()):
            if hasattr(value, "as_tuple"):
                item[key] = float(value)
    return {"count": len(items), "items": items}


@app.get("/api/v1/dashboard/devices")
def dashboard_devices(_: str = Depends(require_dashboard)) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id,device_name,created_at,last_seen_at,agent_version,host_label,
                      terminal_connected,mt5_build,latest_received_at,revoked_at
               FROM devices ORDER BY created_at DESC"""
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["id"] = str(item["id"])
        for key in ("created_at", "last_seen_at", "latest_received_at", "revoked_at"):
            item[key] = item[key].isoformat() if item[key] else None
        items.append(item)
    return {"items": items}


@app.post("/api/v1/research/jobs")
def create_research_job(body: JobCreateRequest, _: str = Depends(require_dashboard)) -> dict[str, Any]:
    params = body.params
    if body.job_type != "PING":
        if params.get("strategy") not in ("PRECISION_SNIPER", "INTRADAY_MOMENTUM", "SUPERTREND_GRID", "ORIGIN_LADDER"):
            raise HTTPException(status_code=422, detail="Research jobs require a valid strategy key.")
        if params.get("symbol", "XAUUSD") not in ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY"):
            raise HTTPException(status_code=422, detail="Unsupported symbol.")
        if body.job_type == "BACKTEST" and params.get("timeframe", "M5") not in ("M1", "M5", "M15", "H1", "H4"):
            raise HTTPException(status_code=422, detail="Unsupported timeframe.")
    job_id = uuid.uuid4()
    with connect() as conn:
        row = conn.execute(
            """INSERT INTO research_jobs (id,job_type,params,status)
               VALUES (%s,%s,%s,'queued')
               RETURNING id,job_type,params,status,created_at""",
            (job_id, body.job_type, Jsonb(params)),
        ).fetchone()
    return {"id": str(row["id"]), "job_type": row["job_type"], "params": row["params"], "status": row["status"], "created_at": row["created_at"].isoformat()}


@app.get("/api/v1/research/jobs")
def list_research_jobs(limit: int = 30, _: str = Depends(require_dashboard)) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    with connect() as conn:
        rows = conn.execute(
            """SELECT id,job_type,params,status,attempts,error,result,created_at,updated_at,finished_at
               FROM research_jobs ORDER BY created_at DESC LIMIT %s""",
            (safe_limit,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["id"] = str(item["id"])
        for key in ("created_at", "updated_at", "finished_at"):
            item[key] = item[key].isoformat() if item[key] else None
        items.append(item)
    return {"items": items}


@app.post("/api/v1/agent/jobs/claim")
def claim_job(device: dict[str, Any] = Depends(require_device)) -> dict[str, Any]:
    with connect() as conn:
        with conn.transaction():
            job = conn.execute(
                """SELECT id,job_type,params,attempts FROM research_jobs
                   WHERE attempts < 3 AND
                     (status='queued' OR (status='running' AND lease_until < now()))
                     AND (assigned_device_id IS NULL OR assigned_device_id=%s)
                   ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED""",
                (device["id"],),
            ).fetchone()
            if not job:
                return {"job": None}
            conn.execute(
                """UPDATE research_jobs SET status='running',assigned_device_id=%s,
                   claimed_at=now(),lease_until=now()+interval '120 seconds',
                   attempts=attempts+1,updated_at=now() WHERE id=%s""",
                (device["id"], job["id"]),
            )
    return {"job": {"id": str(job["id"]), "job_type": job["job_type"], "params": job["params"], "attempt": job["attempts"] + 1}}


@app.post("/api/v1/agent/jobs/{job_id}/complete")
def complete_job(job_id: uuid.UUID, body: JobResultRequest, device: dict[str, Any] = Depends(require_device)) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """UPDATE research_jobs SET status='succeeded',result=%s,error=NULL,
               finished_at=now(),updated_at=now(),lease_until=NULL
               WHERE id=%s AND status='running' AND assigned_device_id=%s
               RETURNING id""",
            (Jsonb(body.result), job_id, device["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Job is not leased to this device or is no longer running.")
    return {"accepted": True, "status": "succeeded"}


@app.post("/api/v1/agent/jobs/{job_id}/fail")
def fail_job(job_id: uuid.UUID, body: JobFailureRequest, device: dict[str, Any] = Depends(require_device)) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """UPDATE research_jobs SET status='failed',error=%s,finished_at=now(),
               updated_at=now(),lease_until=NULL
               WHERE id=%s AND status='running' AND assigned_device_id=%s
               RETURNING id""",
            (body.error, job_id, device["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=409, detail="Job is not leased to this device or is no longer running.")
    return {"accepted": True, "status": "failed"}


@app.get("/api/v1/research/jobs/{job_id}")
def get_research_job(job_id: uuid.UUID, _: str = Depends(require_dashboard)) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id,job_type,params,status,attempts,error,result,created_at,updated_at,finished_at FROM research_jobs WHERE id=%s",
            (job_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Research job not found.")
    item = dict(row)
    item["id"] = str(item["id"])
    for key in ("created_at", "updated_at", "finished_at"):
        item[key] = item[key].isoformat() if item[key] else None
    return item
