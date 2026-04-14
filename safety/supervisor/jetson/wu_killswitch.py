#!/usr/bin/env python3
"""Wu killswitch — minimal HTTP server for out-of-band stop/reboot.

Lives on the Jetson, reachable only from the RPi supervisor (enforced by
iptables). Runs as a dedicated `killswitch` user with a narrow sudoers entry
that grants exactly three privileged commands:

    /bin/systemctl stop jetson_robot.service
    /bin/systemctl stop wu-exporter.service
    /sbin/reboot

The killswitch has four endpoints — GET /health (unauthed, liveness check
for the supervisor's up{} alert), GET /state (authed), POST /stop (authed),
POST /reboot (authed). No /start, /restart, /config, /exec — deliberately
asymmetric so a compromised killswitch cannot *launch* anything, only stop
things that are already running.

Authentication is HMAC-SHA256 over {timestamp, method, path, body} using a
preshared key in /etc/wu/killswitch.key. Timestamps outside a ±60s window
are rejected (replay protection).

Every request is logged to /var/log/wu-killswitch.log BEFORE the action is
taken, so reboot-triggering requests still leave evidence of who asked.

Install:
    # 1. create the killswitch user
    sudo useradd -r -s /bin/false killswitch

    # 2. deploy script
    sudo install -m 755 wu_killswitch.py /opt/wu/wu_killswitch.py

    # 3. create preshared key
    sudo mkdir -p /etc/wu
    sudo python3 -c 'import secrets; print(secrets.token_hex(32))' \
        | sudo tee /etc/wu/killswitch.key
    sudo chmod 400 /etc/wu/killswitch.key
    sudo chown killswitch:killswitch /etc/wu/killswitch.key

    # 4. sudoers entry (use visudo)
    # Install the file at:
    sudo install -m 0440 wu-killswitch.sudoers /etc/sudoers.d/wu-killswitch

    # 5. systemd unit
    sudo install -m 644 wu-killswitch.service /etc/systemd/system/wu-killswitch.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now wu-killswitch.service

    # 6. copy /etc/wu/killswitch.key (same hex bytes) to the RPi supervisor
    #    so it can sign requests
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler

KEY_PATH = "/etc/wu/killswitch.key"
LOG_PATH = "/var/log/wu-killswitch.log"
BIND_ADDR = ("192.168.123.18", 9300)
TS_WINDOW = 60  # seconds — HMAC timestamp drift tolerance

logger = logging.getLogger("killswitch")
logger.setLevel(logging.INFO)
_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_handler)

try:
    with open(KEY_PATH, "rb") as f:
        KEY = bytes.fromhex(f.read().strip().decode())
except FileNotFoundError:
    print(f"ERROR: preshared key not found at {KEY_PATH}", file=sys.stderr)
    sys.exit(1)

START_TIME = time.time()


def verify(ts: str, method: str, path: str, body: bytes, sig: str) -> bool:
    """HMAC-SHA256 verification with ±60s timestamp window."""
    try:
        ts_int = int(ts)
    except (ValueError, TypeError):
        return False
    if abs(time.time() - ts_int) > TS_WINDOW:
        return False
    msg = f"{ts}\n{method}\n{path}\n".encode() + body
    expected = hmac.new(KEY, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig or "")


def run(argv: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def service_up(name: str) -> bool:
    rc, _ = run(["systemctl", "is-active", "--quiet", name])
    return rc == 0


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _authed(self) -> bool:
        body = b""
        if self.command == "POST":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length > 0 else b""
            self._body = body
        ts = self.headers.get("X-Wu-Ts", "")
        sig = self.headers.get("X-Wu-Sig", "")
        ok = verify(ts, self.command, self.path, body, sig)
        logger.info(
            "request method=%s path=%s src=%s auth=%s",
            self.command, self.path, self.client_address[0],
            "OK" if ok else "FAIL",
        )
        return ok

    def do_GET(self) -> None:
        if self.path == "/health":
            self._reply(200, {"ok": True, "uptime": int(time.time() - START_TIME)})
            return
        if self.path == "/state":
            if not self._authed():
                self._reply(401, {"error": "auth"})
                return
            self._reply(200, {
                "jetson_robot": service_up("jetson_robot.service"),
                "wu_exporter": service_up("wu-exporter.service"),
                "uptime": int(time.time() - START_TIME),
            })
            return
        self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._authed():
            self._reply(401, {"error": "auth"})
            return
        if self.path == "/stop":
            logger.warning("STOP requested by %s", self.client_address[0])
            rc, out = run(["sudo", "-n", "systemctl", "stop", "jetson_robot.service"])
            self._reply(200 if rc == 0 else 500, {"rc": rc, "out": out})
            return
        if self.path == "/reboot":
            logger.warning("REBOOT requested by %s", self.client_address[0])
            # Reply before rebooting so the caller gets an ack.
            self._reply(200, {"rebooting": True})
            try:
                self.wfile.flush()
            except Exception:
                pass
            run(["sudo", "-n", "/sbin/reboot"])
            return
        self._reply(404, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        # Suppress default stderr access log; we log via `logger`.
        pass


def main() -> None:
    srv = ThreadingHTTPServer(BIND_ADDR, Handler)
    logger.info("wu-killswitch listening on %s:%d", *BIND_ADDR)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
