"""Hook that tees Go2 battery state of charge onto the /go2_battery LCM channel.

Why this exists
---------------
`wu_exporter` subscribes to `/go2_battery` to expose `wu_go2_battery_percent`
so the RPi supervisor can alert on low battery. Without a publisher, that
gauge stays at 0 and the alert never fires.

Why it's done by monkey-patch
-----------------------------
The Go2 only permits one WebRTC peer. A side-car process with its own
`UnitreeWebRTCConnection` would kick the main agent off. So instead we
reuse the existing connection that dimos already opened from inside
`jetson_robot.service`, by wrapping `GO2Connection.start()` so that after
the original start runs we add a second subscriber to the same
`lowstate_stream()`.

Reactive streams are designed for this — the existing rerun logger
subscriber and our new LCM publisher both receive every LowState message
independently.

Picklability note (load-bearing)
--------------------------------
DiMOS spawns module workers via `multiprocessing.forkserver`, which must
pickle class methods. A closure-based wrapper (defined inside install())
CANNOT be pickled and breaks the GO2Connection deploy path — see session
transcript for the outage this caused on 2026-04-15.

So the wrapper MUST be a module-level function, and we stash the original
start in a module-level global. We also copy the `__rpc__ = True` marker
from the original onto the wrapper so dimos's rpc introspection still
recognises `start` as an RPC method.

Install
-------
    scp wu_battery_publisher.py unitree@jetson:/home/unitree/dimos/hybrid/

Then add two lines near the top of `jetson_robot.py`, before the blueprint:

    import wu_battery_publisher
    wu_battery_publisher.install()

Restart `jetson_robot.service`. Confirm via `/var/log/jetson_robot.log`:

    wu_battery_publisher: patch installed on GO2Connection.start
    wu_battery_publisher: attached to lowstate_stream
"""

from __future__ import annotations

import os
import pickle
import sys
import threading
import time

# Match jetson_robot.service's LCM URL so cross-host multicast works.
os.environ.setdefault("LCM_DEFAULT_URL", "udpm://239.255.76.67:7667?ttl=1")

import lcm  # noqa: E402

CHANNEL = "/go2_battery"
# LowState arrives at roughly 500 Hz on Go2. The supervisor only needs
# ~1 Hz, and every LCM publish is a memcpy + syscall. Rate-limit hard.
MIN_PUBLISH_INTERVAL = 1.0

_lcm_instance: lcm.LCM | None = None
_last_publish = 0.0
_publish_lock = threading.Lock()
_installed = False
_orig_go2_start = None  # populated by install(); referenced by _wrapped_go2_start


def _log(msg: str) -> None:
    """Unconditional stdout write so the message reaches jetson_robot.log.

    We avoid `logging.getLogger` here because jetson_robot doesn't configure
    a root logger at INFO level, so log.info() is silently dropped. A plain
    print() with flush=True is far more reliable for a one-shot install
    trace.
    """
    print(f"wu_battery_publisher: {msg}", flush=True, file=sys.stderr)


def _lc() -> lcm.LCM:
    global _lcm_instance
    if _lcm_instance is None:
        _lcm_instance = lcm.LCM()
    return _lcm_instance


def _on_lowstate(msg: dict) -> None:
    """Reactive-stream callback. Extract BMS soc, publish pickled float."""
    global _last_publish
    try:
        data = msg.get("data", {})
        bms = data.get("bms_state", {})
        soc = bms.get("soc")
        if soc is None:
            return
        now = time.time()
        with _publish_lock:
            if now - _last_publish < MIN_PUBLISH_INTERVAL:
                return
            _last_publish = now
        _lc().publish(CHANNEL, pickle.dumps(float(soc)))
    except Exception as e:
        # Don't let a malformed lowstate crash the reactive pipeline.
        _log(f"publish failed: {e}")


# --- module-level wrapper -------------------------------------------------
#
# This function MUST stay at module scope (not a closure inside install()).
# DiMOS's forkserver worker manager pickles class methods when deploying
# modules; a local closure here breaks serialization of GO2Connection.
# See the module docstring for the full story.


def _wrapped_go2_start(self, *args, **kwargs):
    assert _orig_go2_start is not None, "wu_battery_publisher.install() not called"
    result = _orig_go2_start(self, *args, **kwargs)
    try:
        conn = getattr(self, "connection", None)
        if conn is not None and hasattr(conn, "lowstate_stream"):
            conn.lowstate_stream().subscribe(_on_lowstate)
            _log(f"attached to lowstate_stream, publishing to {CHANNEL}")
        else:
            _log("lowstate_stream missing after start; battery will stay at 0")
    except Exception as e:
        _log(f"subscribe failed: {e}")
    return result


def install() -> None:
    """Monkey-patch GO2Connection.start to tee lowstate_stream -> /go2_battery.

    Must be called before `jetson_robot.build().loop()` so the patch is in
    place when dimos instantiates GO2Connection. Idempotent — safe to call
    multiple times.
    """
    global _orig_go2_start, _installed
    if _installed:
        return

    try:
        from dimos.robot.unitree.go2 import connection as _conn_mod
    except Exception as e:
        _log(f"can't import GO2Connection: {e}")
        return

    target_cls = _conn_mod.GO2Connection
    _orig_go2_start = target_cls.start

    # Preserve the __rpc__ marker so dimos's rpc introspection still
    # recognises start as an RPC method.
    if getattr(_orig_go2_start, "__rpc__", False):
        _wrapped_go2_start.__rpc__ = True  # type: ignore[attr-defined]

    target_cls.start = _wrapped_go2_start
    _installed = True
    _log("patch installed on GO2Connection.start")
