#!/usr/bin/env python3
"""Wu killswitch client — sends HMAC-authenticated requests from the RPi
supervisor to the Jetson's wu-killswitch service.

Usage as a module:

    from wu_killswitch_client import call
    call("GET", "/health")                    # unauthed, liveness
    call("GET", "/state")                     # authed, current state
    call("POST", "/stop")                     # authed, stop jetson_robot
    call("POST", "/reboot")                   # authed, reboot Jetson (nuclear)

Usage from CLI:

    python wu_killswitch_client.py health
    python wu_killswitch_client.py state
    python wu_killswitch_client.py stop
    python wu_killswitch_client.py reboot

Prerequisites:
    /etc/wu/killswitch.key exists with the same hex bytes as the Jetson's
    key file. Create it with:
        sudo mkdir -p /etc/wu
        sudo cp /path/to/shared.key /etc/wu/killswitch.key
        sudo chmod 400 /etc/wu/killswitch.key
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
import urllib.request

KEY_PATH = "/etc/wu/killswitch.key"
BASE_URL = "http://192.168.123.18:9300"
TIMEOUT = 5


def _load_key() -> bytes:
    with open(KEY_PATH) as f:
        return bytes.fromhex(f.read().strip())


def call(method: str, path: str, body: dict | None = None) -> dict:
    """Make a single HMAC-authenticated request to the killswitch."""
    body_bytes = json.dumps(body).encode() if body else b""
    ts = str(int(time.time()))

    headers = {"Content-Type": "application/json"}

    # GET /health is the only unauthed endpoint — skip signing for it
    # so monitoring probes don't need the key.
    if not (method == "GET" and path == "/health"):
        key = _load_key()
        msg = f"{ts}\n{method}\n{path}\n".encode() + body_bytes
        sig = hmac.new(key, msg, hashlib.sha256).hexdigest()
        headers["X-Wu-Ts"] = ts
        headers["X-Wu-Sig"] = sig

    req = urllib.request.Request(
        BASE_URL + path,
        data=body_bytes if method == "POST" else None,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: wu_killswitch_client.py {health|state|stop|reboot}",
            file=sys.stderr,
        )
        return 2

    verb = sys.argv[1]
    routes = {
        "health": ("GET", "/health"),
        "state": ("GET", "/state"),
        "stop": ("POST", "/stop"),
        "reboot": ("POST", "/reboot"),
    }
    if verb not in routes:
        print(f"unknown verb: {verb}", file=sys.stderr)
        return 2

    method, path = routes[verb]
    try:
        result = call(method, path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
