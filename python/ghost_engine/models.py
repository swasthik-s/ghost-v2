from enum import StrEnum
from pydantic import BaseModel, Field
class StrategyName(StrEnum):
    PRECISION_SNIPER="PRECISION_SNIPER"
    INTRADAY_MOMENTUM="INTRADAY_MOMENTUM"
    SUPERTREND_GRID="SUPERTREND_GRID"
    ORIGIN_LADDER="ORIGIN_LADDER"
class DecisionRequest(BaseModel):
    strategy: StrategyName
    symbol: str=Field(default="XAUUSD", min_length=1, max_length=32)
    snapshot_id: str|None=None
class DecisionResponse(BaseModel):
    strategy: StrategyName
    symbol: str
    decision: str="WAIT"
    reason: str
    execution_allowed: bool=False
