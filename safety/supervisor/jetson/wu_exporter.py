#!/usr/bin/env python3
"""wu_exporter — Wu-specific Prometheus metrics.

Runs on the Jetson as a separate systemd service from jetson_robot.service.
Binds to 192.168.123.18:9200. The RPi supervisor scrapes it via Prometheus.

Metrics exposed:
    wu_jetson_robot_up           gauge  (pgrep jetson_robot.py)
    wu_mid360_native_up          gauge  (pgrep mid360_native)
    wu_mcp_server_up             gauge  (http probe of :9990/mcp tools/list)
    wu_go2_battery_percent       gauge  (parsed from /go2_battery LCM channel)
    wu_agent_idle                gauge  (parsed from /agent_idle LCM channel)
    wu_webrtc_connected          gauge  (inferred from LCM traffic liveness)
    wu_ethernet_link_up          gauge  (from /sys/class/net/enP8p1s0/carrier)
    wu_lcm_channel_msgs_total    counter per channel name

Requires a small modification to jetson_robot.py to publish Go2 battery
level on the `/go2_battery` LCM channel (parsed from the Unitree LowState
message that DiMOS's UnitreeWebRTCConnection already subscribes to). Until
that publish exists, wu_go2_battery_percent stays at 0 and the supervisor
can't alert on low battery. This is the single most important feature gap
of this exporter as-shipped.

Install:
    sudo install -m 755 wu_exporter.py /opt/wu/wu_exporter.py
    # Uses the dimos venv for its dependencies (prometheus_client, lcm)
    sudo install -m 644 wu-exporter.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now wu-exporter.service
"""

from __future__ import annotations

import os
import pickle
import subprocess
import threading
import time
import urllib.request

os.environ.setdefault("LCM_DEFAULT_URL", "udpm://239.255.76.67:7667?ttl=1")

import lcm  # noqa: E402
from prometheus_client import Counter, Gauge, start_http_server  # noqa: E402

# --- metrics ----------------------------------------------------------------

jetson_robot_up = Gauge(
    "wu_jetson_robot_up",
    "jetson_robot.py process is alive (0/1)",
)
mid360_up = Gauge(
    "wu_mid360_native_up",
    "mid360_native process is alive (0/1)",
)
mcp_up = Gauge(
    "wu_mcp_server_up",
    "MCP server responds to tools/list on port 9990 (0/1)",
)
battery = Gauge(
    "wu_go2_battery_percent",
    "Go2 battery state of charge, 0-100",
)
agent_idle = Gauge(
    "wu_agent_idle",
    "Wu agent loop is idle and waiting for input (0/1)",
)
webrtc_connected = Gauge(
    "wu_webrtc_connected",
    "Go2 WebRTC peer connection is active (0/1), inferred from recent LCM odom traffic",
)
eth_link = Gauge(
    "wu_ethernet_link_up",
    "Jetson enP8p1s0 carrier present (0/1)",
)
lcm_msgs = Counter(
    "wu_lcm_channel_msgs_total",
    "LCM messages seen by the exporter, labeled by channel",
    ["channel"],
)

# --- internal state ---------------------------------------------------------

# Track the timestamp of the most recent /odom publication. If we haven't
# seen one in the last N seconds, Go2 WebRTC is probably not flowing.
_last_odom_ts = 0.0
_odom_lock = threading.Lock()


def _set_odom_seen() -> None:
    global _last_odom_ts
    with _odom_lock:
        _last_odom_ts = time.time()


def _odom_recent(window_sec: float = 5.0) -> bool:
    with _odom_lock:
        return (time.time() - _last_odom_ts) < window_sec


# --- probes -----------------------------------------------------------------

def pgrep(pattern: str) -> bool:
    return subprocess.run(
        ["pgrep", "-f", pattern],
        capture_output=True,
    ).returncode == 0


def probe_mcp() -> bool:
    try:
        req = urllib.request.Request(
            "http://192.168.123.18:9990/mcp",
            data=b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}',
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def eth_carrier() -> int:
    try:
        return int(open("/sys/class/net/enP8p1s0/carrier").read().strip())
    except Exception:
        return 0


# --- poll loops -------------------------------------------------------------

def poll_loop() -> None:
    while True:
        jetson_robot_up.set(1 if pgrep("jetson_robot.py") else 0)
        mid360_up.set(1 if pgrep("mid360_native") else 0)
        mcp_up.set(1 if probe_mcp() else 0)
        eth_link.set(eth_carrier())
        webrtc_connected.set(1 if _odom_recent() else 0)
        time.sleep(2.0)


def lcm_loop() -> None:
    """Subscribe to everything, count by channel, pull specific signals."""
    def handler(channel: str, data: bytes) -> None:
        lcm_msgs.labels(channel=channel).inc()

        # Track odom liveness as a WebRTC health proxy.
        if channel.startswith("/odom"):
            _set_odom_seen()

        # Battery (requires jetson_robot.py to publish /go2_battery).
        # Format: we expect a pickled float/int percent. Adapt to whatever
        # jetson_robot.py ends up publishing — this is the integration point.
        if channel.startswith("/go2_battery"):
            try:
                value = pickle.loads(data)
                if isinstance(value, (int, float)):
                    battery.set(float(value))
            except Exception:
                pass  # don't let malformed messages crash the exporter

        # Agent idle flag from desktop_brain's McpClient.
        if channel.startswith("/agent_idle"):
            try:
                value = pickle.loads(data)
                if isinstance(value, bool):
                    agent_idle.set(1 if value else 0)
            except Exception:
                pass

    lc = lcm.LCM()
    lc.subscribe(".*", handler)
    while True:
        lc.handle_timeout(500)


# --- main -------------------------------------------------------------------

def main() -> None:
    start_http_server(9200, addr="192.168.123.18")
    threading.Thread(target=poll_loop, daemon=True).start()
    threading.Thread(target=lcm_loop, daemon=True).start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
