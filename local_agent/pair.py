from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import httpx


def config_path() -> Path:
    appdata = Path(os.getenv("APPDATA", str(Path.home())))
    return Path(os.getenv("GHOST_AGENT_CONFIG", str(appdata / "GHOST" / "agent.json")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Pair this Windows GHOST Agent with your GHOST Vercel deployment.")
    parser.add_argument("--api-url", default=os.getenv("GHOST_CLOUD_API_URL", ""), help="Base URL, e.g. https://ghost-v2.vercel.app")
    parser.add_argument("--device-name", default=platform.node(), help="Friendly name shown in GHOST")
    args = parser.parse_args()

    if not args.api_url:
        parser.error("Provide --api-url or set GHOST_CLOUD_API_URL.")
    base = args.api_url.rstrip("/")
    pairing_code = getpass.getpass("GHOST pairing code: ").strip()
    if not pairing_code:
        parser.error("Pairing code cannot be empty.")

    try:
        response = httpx.post(
            f"{base}/api/v1/devices/pair",
            json={"pairing_code": pairing_code, "device_name": args.device_name},
            timeout=15.0,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        print(f"Pairing failed: {exc}")
        if getattr(exc, "response", None) is not None:
            print(exc.response.text[:500])
        return 1

    settings = {
        "cloud_api_url": base,
        "device_id": payload["device_id"],
        "device_name": payload["device_name"],
        "device_token": payload["device_token"],
        "paired_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    destination = config_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass

    print(f"Paired device: {settings['device_name']} ({settings['device_id']})")
    print(f"Credential file: {destination}")
    print("The device token is stored locally and will not be printed. Keep this file private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
