from fastapi import FastAPI
from ghost_engine.models import DecisionRequest, DecisionResponse
app=FastAPI(title="GHOST v2 API",version="0.1.0")
@app.get("/health")
def health(): return {"status":"ok","mode":"research-only"}
@app.post("/v1/decision",response_model=DecisionResponse)
def decision(request:DecisionRequest):
    return DecisionResponse(strategy=request.strategy,symbol=request.symbol,decision="WAIT",reason="No validated signal adapter or trusted market snapshot is connected.",execution_allowed=False)
