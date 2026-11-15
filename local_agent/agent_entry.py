from __future__ import annotations

import os
import sys

import uvicorn

if "--pair" in sys.argv[1:]:
    from pair import main as pair_main

    sys.argv = [sys.argv[0]] + [arg for arg in sys.argv[1:] if arg != "--pair"]
    raise SystemExit(pair_main())

from main import app


if __name__ == "__main__":
    host = os.getenv("GHOST_AGENT_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("GHOST_AGENT_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, reload=False, access_log=False)
