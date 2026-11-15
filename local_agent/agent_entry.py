from __future__ import annotations

import os

import uvicorn

from main import app


if __name__ == "__main__":
    host = os.getenv("GHOST_AGENT_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("GHOST_AGENT_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, reload=False, access_log=False)
