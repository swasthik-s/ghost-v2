from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="GHOST v2 API",
    version="0.1.0",
    description="Research-only API scaffold. It does not connect to MT5 or place trades.",
)

Strategy = Literal[
    "PRECISION_SNIPER",
    "INTRADAY_MOMENTUM",
    "SUPERTREND_GRID",
    "ORIGIN_LADDER",
]

class DecisionRequest(BaseModel):
    strategy: Strategy
    symbol: str = Field(default="XAUUSD", min_length=1, max_length=32)

@app.get("/")
def root():
    return {"service": "GHOST v2 API", "status": "online", "mode": "research-only"}

@app.get("/health")
def health():
    return {"status": "ok", "mt5_connected": False, "execution_enabled": False}

@app.post("/decision")
def decision(request: DecisionRequest):
    return {
        "strategy": request.strategy,
        "symbol": request.symbol,
        "decision": "WAIT",
        "execution_allowed": False,
        "reason": "No validated signal adapter or trusted market snapshot is connected.",
    }
