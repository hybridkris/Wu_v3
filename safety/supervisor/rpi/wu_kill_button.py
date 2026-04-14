#!/usr/bin/env python3
"""Physical kill button on the RPi — optional hardware stop for Wu.

Wire a momentary push-button between GPIO 17 and ground. The RPi's internal
pull-up handles debouncing via gpiozero.

Behavior:
    single press → POST /stop on the Jetson killswitch (graceful stop of
                   jetson_robot.service)
    double press within 2s → POST /reboot (nuclear, reboots the Jetson)

Optional LED on GPIO 27 shows killswitch liveness:
    solid green  → killswitch /health is up (polled every 5s)
    solid red    → killswitch /health is not responding
    flashing red → button was pressed, request in flight

Dependencies:
    pip install gpiozero

Install:
    sudo install -m 755 wu_kill_button.py /opt/wu/wu_kill_button.py
    sudo install -m 644 wu-kill-button.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now wu-kill-button.service
"""

from __future__ import annotations

import logging
import time
from threading import Thread

from gpiozero import Button, LED  # type: ignore[import-not-found]

from wu_killswitch_client import call

BUTTON_PIN = 17
LED_PIN = 27
DOUBLE_PRESS_WINDOW = 2.0  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("wu_kill_button")


# --- state ------------------------------------------------------------------

_last_press_ts = 0.0


def _health_watcher(led: LED) -> None:
    """Poll /health every 5s, update LED accordingly."""
    while True:
        try:
            result = call("GET", "/health")
            if result.get("ok"):
                led.on()
            else:
                led.off()
        except Exception:
            led.off()
        time.sleep(5.0)


def _flash(led: LED, duration: float = 10.0, interval: float = 0.2) -> None:
    """Flash the LED for `duration` seconds (blocking — run in thread)."""
    end = time.time() + duration
    while time.time() < end:
        led.toggle()
        time.sleep(interval)
    led.on()  # return to solid


def _on_press(led: LED) -> None:
    """Button callback — handles single vs double press semantics."""
    global _last_press_ts
    now = time.time()

    if (now - _last_press_ts) < DOUBLE_PRESS_WINDOW:
        # Double press → reboot
        log.warning("DOUBLE PRESS — sending /reboot")
        Thread(target=_flash, args=(led, 15.0, 0.1), daemon=True).start()
        try:
            result = call("POST", "/reboot")
            log.info("reboot response: %s", result)
        except Exception as e:
            log.error("reboot failed: %s", e)
        _last_press_ts = 0.0  # reset so we don't triple-trigger
        return

    # Single press → stop
    log.warning("SINGLE PRESS — sending /stop")
    Thread(target=_flash, args=(led, 10.0, 0.2), daemon=True).start()
    try:
        result = call("POST", "/stop")
        log.info("stop response: %s", result)
    except Exception as e:
        log.error("stop failed: %s", e)
    _last_press_ts = now


def main() -> None:
    button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
    led = LED(LED_PIN)
    led.on()  # assume killswitch is reachable at startup

    button.when_pressed = lambda: _on_press(led)

    Thread(target=_health_watcher, args=(led,), daemon=True).start()

    log.info("wu-kill-button ready on GPIO %d, LED on GPIO %d", BUTTON_PIN, LED_PIN)
    try:
        while True:
            time.sleep(60.0)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
