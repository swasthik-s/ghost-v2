# GHOST v2 Architecture Notes

## Runtime responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Next.js UI | Visualisation, configuration drafts, code editing, job submission | Direct broker execution or risk override |
| Python API | Auth, account snapshot API, job orchestration, research metadata | Bypass EA governor |
| Python research worker | Historical simulations, parameter sweeps, WFA, Monte Carlo | Place live orders |
| Windows local agent | Authenticated bridge, file exchange, process supervision | Expose terminal port publicly |
| MT5 EA | Signal evaluation, execution, hard risk governor, telemetry | Trust stale/unauthenticated Python commands |

## Strategy registry

- PRECISION_SNIPER: selective liquidity sweep/reclaim/confirmation hypothesis.
- INTRADAY_MOMENTUM: EMA alignment, breakout and volatility filter hypothesis.
- SUPERTREND_GRID: favourable-direction pyramiding with hard leg/lot limits.
- ORIGIN_LADDER: experimental hypothesis; not represented as a reverse-engineered clone.

The router may return WAIT. Risk approval precedes every order. The risk governor may reject any requested order.

## Required controls

- Max risk per trade, daily equity loss, peak-to-current drawdown, lots, concurrent positions and symbol exposure.
- Stale signal expiry, duplicate request idempotency, heartbeat timeout and disconnected-state no-entry policy.
- Append-only audit log for configuration changes, strategy decisions, risk approvals/rejections and orders.
- Separate demo/live credentials; live mode locked by default.

## Validation sequence

1. Data quality checks (missing bars/ticks, spread, session boundaries, timezone).
2. Baseline backtest using conservative fill ordering and explicit costs.
3. Sensitivity analysis for robust parameter plateaus.
4. Walk-forward train/test with strict temporal separation.
5. Monte Carlo on trade outcomes and cost perturbations.
6. MT5 Strategy Tester cross-check and demo forward test.
