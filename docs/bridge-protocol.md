# GHOST Telemetry Protocol v1

The first integration uses an MT5 Common Files export. It is intentionally one-way and read-only.

## File

GHOST/telemetry.json under the terminal's FILE_COMMON sandbox. The exporter writes UTF-8 JSON every second.

## Payload shape

- schema_version: integer, currently 1
- generated_at_utc: exporter timestamp in UTC
- terminal: connected flag, broker company, server and terminal build
- account: currency, balance, equity, floating P&L, used margin, free margin and margin level
- positions: ticket, symbol, side, volume, open/current price, profit, swap, stop-loss, take-profit, magic and comment

Account login numbers and credentials are not exported.

## Python service endpoints

- GET /health
- GET /api/v1/health
- GET /api/v1/snapshot
- GET /api/v1/equity?limit=300
- GET /api/v1/config

The service reads the file once per second, considers data stale after 10 seconds by default, and saves chart history to SQLite every 15 seconds by default.

## Security invariants

- API binds to loopback only in the documented run command.
- CORS is restricted to local Next.js origins unless a single explicit dashboard origin is configured.
- No write, trade, order, modify or close endpoints exist.
- Every snapshot response includes execution_enabled: false.
- This is not the cloud agent relay. The Vercel page cannot reach a Windows localhost service by magic; a separate authenticated remote transport is required.
