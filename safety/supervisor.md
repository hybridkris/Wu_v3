# Wu v3 — Supervisor & Kill Switch Specification

*Status: design, not yet implemented*
*Last updated: 2026-04-12*

This document specifies the out-of-band monitoring and kill-switch subsystem for Wu v3. It is a buildable spec — an implementer should be able to follow this end-to-end and arrive at a working system.

---

## 1. Purpose

Wu v3 runs autonomous agent loops with motor control, tool access, and a tethered physical body in Kris's house. Two independent safety concerns need addressing:

1. **Observability**: health and state of Wu's substrate (Jetson CPU/memory/temp, Go2 battery, process liveness, sensor streams, agent state) must be visible without SSH'ing in or relying on Wu's own cooperation.
2. **Interruptibility**: there must be an out-of-band path to stop Wu that does not depend on Wu's agent responding, the desktop brain being reachable, or anything inside Wu's own process tree.

A Raspberry Pi, sitting on the same network as Wu's robot subnet, fills both roles as an **external supervisor**. This document specifies its responsibilities and the corresponding changes needed on the Jetson.

Design principle: **the supervisor is outside Wu's reachable world**. Wu cannot read from it, write to it, or affect its state. The direction of communication is from the supervisor to Wu, never the reverse.

---

## 2. Architecture

```
┌──────────────────────┐
│  Raspberry Pi        │
│  (supervisor)        │
│                      │
│  Prometheus  ◀──────┐│
│  Grafana            ││  scrape (pull, read-only)
│  Alertmanager       ││
│                     ││  POST /stop, /reboot (push, write)
│  Killer client  ────┼┼──┐
│                     │   │
│  Physical button    │   │
│  (GPIO → killer)    │   │
└──────────────────────┘   │
         │                  │
         │   192.168.123.0/24
         │                  │
         ▼                  ▼
┌──────────────────────────────────┐
│  Jetson (192.168.123.18)         │
│                                  │
│  ┌────────────────────────┐      │
│  │ jetson_robot.py        │      │
│  │ (Wu's main process)    │      │
│  └────────────────────────┘      │
│                                  │
│  ┌────────────────────────┐      │
│  │ node_exporter :9100    │◀─ scrape
│  └────────────────────────┘      │
│                                  │
│  ┌────────────────────────┐      │
│  │ wu_exporter :9200      │◀─ scrape
│  │ (Wu-specific metrics)  │      │
│  └────────────────────────┘      │
│                                  │
│  ┌────────────────────────┐      │
│  │ wu-killswitch :9300    │◀─ POST
│  │ (runs as root,         │      │
│  │  outside Wu's tree)    │      │
│  └────────────────────────┘      │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  Godzilla (192.168.123.205)      │
│                                  │
│  ┌────────────────────────┐      │
│  │ desktop_brain.py       │      │
│  └────────────────────────┘      │
│                                  │
│  ┌────────────────────────┐      │
│  │ node_exporter :9100    │◀─ scrape
│  └────────────────────────┘      │
└──────────────────────────────────┘
```

Key points:

- **Pull model for metrics**: Prometheus on the RPi initiates all metric scrapes. Nothing on the Jetson or Godzilla ever pushes metrics to the RPi.
- **Push model for kill**: only the RPi initiates kill/reboot calls. The Jetson's killswitch is a passive HTTP server that only acts when asked.
- **Two exporters on the Jetson**: standard `node_exporter` for generic system metrics, and a small custom `wu_exporter` for Wu-specific metrics (Go2 battery, agent state, LCM rates).
- **Killswitch is a separate systemd service** on the Jetson, running as root, outside `jetson_robot.py`'s process tree. Wu's agent has no path to it.

---

## 3. Components

### 3.1 `node_exporter` — Jetson and Godzilla

**Purpose**: standard Prometheus exporter for system metrics.

**Install**: `sudo apt install prometheus-node-exporter` (Ubuntu 22.04 on both machines).

**What it provides for free**: CPU (per-core, load average), memory, disk (per-mount), network (per-interface bytes/packets/errors), filesystem, uptime, thermal zones (Jetson has `/sys/class/thermal/thermal_zone*` entries that node_exporter reads automatically), process counts, systemd unit states (via `--collector.systemd`).

**Bind**: to the LAN interface only. On Jetson, bind to `192.168.123.18:9100`. On Godzilla, bind to `192.168.123.205:9100`. Do not bind to `0.0.0.0`.

**Systemd**: the Ubuntu package already installs a systemd unit. Edit `/etc/default/prometheus-node-exporter` to set:
```
ARGS="--web.listen-address=192.168.123.18:9100 --collector.systemd --collector.textfile.directory=/var/lib/node_exporter/textfile_collector"
```
(Substitute `.205` on Godzilla.) Create `/var/lib/node_exporter/textfile_collector/` as root for the Jetson-specific metrics below.

**Jetson-specific sensors** (Tegra thermals, GPU, power rails): write a small shell script that scrapes `tegrastats` or `/sys/devices/gpu.0/load` and emits Prometheus text-format files to `/var/lib/node_exporter/textfile_collector/`. Run it via a 5-second `cron` or a systemd timer. Sample output:
```
# HELP tegra_gpu_load GPU load percentage
# TYPE tegra_gpu_load gauge
tegra_gpu_load 23.4
# HELP tegra_soc_temp_c SoC temperature in celsius
# TYPE tegra_soc_temp_c gauge
tegra_soc_temp_c 42.1
```

### 3.2 `wu_exporter` — Jetson (custom)

**Purpose**: metrics that don't come from `node_exporter` and are specific to Wu's subsystems.

**Language**: Python 3 with `prometheus_client` (single dependency). ~150 LOC.

**Runs as**: `unitree` user (same as `jetson_robot.py`) so it can read LCM and DDS. Separate systemd service from `jetson_robot.py` so it stays up even if Wu crashes.

**Bind**: `192.168.123.18:9200`

**Metrics to expose** (minimum set for R1 launch):

| Metric | Type | Source | Notes |
|---|---|---|---|
| `wu_jetson_robot_up` | gauge (0/1) | `pgrep -f jetson_robot.py` or PID file check | 1 if running, 0 if not |
| `wu_mid360_native_up` | gauge | `pgrep -f mid360_native` | 1 if the Livox driver is up |
| `wu_mcp_server_up` | gauge | HTTP probe of `http://192.168.123.18:9990/mcp` with a `tools/list` request | 1 if responds, 0 otherwise |
| `wu_go2_battery_percent` | gauge | Go2 LowState (DDS, see below) | Range 0-100. Alert at < 20 |
| `wu_go2_mode` | gauge with label | Go2 motion switcher state | `ai` / `normal` / `damp` / etc. |
| `wu_lcm_channel_msgs_total` | counter, labeled by channel | LCM subscriber with regex `.*` | Rate-of-change over time tells you if sensors are flowing |
| `wu_agent_idle` | gauge (0/1) | LCM subscriber to `/agent_idle` (published by `McpClient`) | 1 when the agent is idle, 0 when processing |
| `wu_webrtc_connected` | gauge (0/1) | Set via a small hook in `jetson_robot.py` that publishes an LCM event on WebRTC state change, OR by scraping `/tmp/jetson_robot.log` for connection state markers | 1 if Go2 WebRTC peer connection is `connected`, 0 otherwise |
| `wu_ethernet_link_up` | gauge | `cat /sys/class/net/enP8p1s0/carrier` | 1 = link up. Tether-awareness! |

**Go2 battery acquisition**: the Go2 publishes a `LowState` message containing battery info. DiMOS's `UnitreeWebRTCConnection.unitree_sub_stream(RTC_TOPIC["LOW_STATE"])` returns this as an observable. The cleanest path is to **add a small LCM publish in `jetson_robot.py`** that pipes battery from the existing LowState stream to a new LCM channel (say `/go2_battery`), then have `wu_exporter` subscribe to that. Alternatively, `wu_exporter` can open its own DDS connection to the Go2, but that's a second WebRTC client and may conflict with DiMOS's. **Recommended path: add `/go2_battery` LCM publish in `jetson_robot.py`**. Minimal change, no extra WebRTC sessions.

**Systemd unit**: `/etc/systemd/system/wu-exporter.service` (see Appendix C).

### 3.3 `wu-killswitch` — Jetson

**Purpose**: out-of-band stop/reboot channel for Wu, reachable only from the RPi, unable to be tampered with by Wu's agent.

**Language**: Python 3 stdlib only (`http.server`, `hmac`, `subprocess`, `logging`). No pip deps. ~60 LOC. See Appendix A.

**Runs as**: **root**, because it needs to `systemctl stop` other services and potentially `systemctl reboot`. Alternative: run as an unprivileged `killswitch` user with a narrowly-scoped `sudoers` entry that grants exactly `systemctl stop jetson_robot.service`, `systemctl stop wu-exporter.service`, `systemctl reboot`, and nothing else. The unprivileged-user path is more defensible; pick it.

**Bind**: `192.168.123.18:9300`

**Authentication**: HMAC-SHA256 of the request body + timestamp, using a preshared key. The key lives in `/etc/wu/killswitch.key`, mode `0400`, owned by the `killswitch` user (or root). Same key on the RPi at `/etc/wu/killswitch.key`. Clients must send two headers:
- `X-Wu-Ts: <unix epoch seconds>` — must be within ±60s of the server's clock
- `X-Wu-Sig: <hex(hmac_sha256(key, f"{ts}\n{method}\n{path}\n{body}"))>` 

The server verifies the timestamp window and the HMAC before acting. Any mismatch → 401 and log.

**Endpoints**:

| Method | Path | Auth | Action |
|---|---|---|---|
| GET | `/health` | none | Returns `{"ok": true, "uptime": <secs>}`. Lets Prometheus alert if the killswitch itself dies. |
| GET | `/state` | required | Returns JSON: `{"jetson_robot": true/false, "wu_exporter": true/false, "uptime": <secs>}` |
| POST | `/stop` | required | Graceful stop of `jetson_robot.service` (SIGTERM, 5s grace, then SIGKILL). Does not touch the killswitch itself, node_exporter, or wu_exporter. |
| POST | `/reboot` | required | `systemctl reboot`. Nuclear option. |

**Logging**: every request — method, path, source IP, auth result, action taken, outcome — logged to `/var/log/wu-killswitch.log` via the `logging` module with `RotatingFileHandler`. **Log is written BEFORE the action is taken**, so a reboot-triggering call still leaves evidence. Log file is root-owned, mode `0640`, group `adm` so it's readable for debugging.

**No other verbs**: no `/start`, no `/restart`, no `/eval`, no `/exec`, no `/config`, nothing that writes state. The killswitch does exactly three things: health-check, state-report, stop/reboot. If you want to start Wu back up, you do it manually via SSH. This deliberate asymmetry (easy to stop, hard to start) is a safety property.

**Systemd unit**: `/etc/systemd/system/wu-killswitch.service` (see Appendix C). Must use `Restart=always` so it survives crashes. Must NOT have any dependency on `jetson_robot.service` — the killswitch has to survive `jetson_robot` dying.

### 3.4 Prometheus + Grafana + Alertmanager — Raspberry Pi

**Purpose**: scrape exporters, display dashboards, trigger alerts.

**Install**: Docker Compose is the easiest. A single `docker-compose.yml` with `prom/prometheus`, `grafana/grafana`, `prom/alertmanager` containers. Persist volumes to SD card or USB drive.

**Prometheus `scrape_configs`**:
```yaml
scrape_configs:
  - job_name: 'jetson_node'
    static_configs:
      - targets: ['192.168.123.18:9100']
  - job_name: 'jetson_wu'
    static_configs:
      - targets: ['192.168.123.18:9200']
  - job_name: 'godzilla_node'
    static_configs:
      - targets: ['192.168.123.205:9100']
  - job_name: 'killswitch_health'
    metrics_path: /health
    static_configs:
      - targets: ['192.168.123.18:9300']
```

Scrape interval: 15s for most, 5s for `wu_exporter` (Wu's fast-moving state), 60s for `killswitch_health` (it's a liveness probe, not a data source).

**Grafana dashboards** (hand-built or imported):
1. **Wu overview**: Go2 battery (prominent), jetson_robot up/down, MCP up/down, WebRTC connected, agent idle/busy, LCM channel rates
2. **Jetson health**: CPU, memory, temperature (Tegra thermals), disk, network throughput
3. **Godzilla health**: same but for the desktop brain machine
4. **Network**: LCM channel rates per topic, desktop brain MCP request rate

**Alertmanager rules** (minimum set):
- `wu_go2_battery_percent < 20` for 1 min → Telegram
- `wu_go2_battery_percent < 10` for 10s → Telegram (critical)
- `wu_jetson_robot_up == 0` for 30s → Telegram
- `wu_mcp_server_up == 0` for 30s → Telegram
- `wu_webrtc_connected == 0` for 60s → Telegram
- `up{job="killswitch_health"} == 0` for 30s → Telegram (**the killswitch is dead** — highest priority alert)
- `node_network_transmit_errs_total` rate spike → Telegram (sensor dropouts)
- Jetson SoC temp > 80°C for 30s → Telegram

Telegram: use the existing bot credentials at `~/.claude/channels/telegram/.env`. Alertmanager has a built-in Telegram receiver.

### 3.5 Physical kill button — Raspberry Pi (optional but recommended)

**Purpose**: a satisfyingly physical button that stops Wu without touching a keyboard. Satisfies the "emergency, don't-think-just-press" use case.

**Hardware**: any momentary push-button wired between a GPIO pin (say GPIO 17) and ground. The RPi's `gpiozero` library does pull-up debouncing.

**Software**: tiny Python script, runs as a systemd service on the RPi. On button press, it calls `POST /stop` on the killswitch with proper HMAC auth. On double-press within 2s, it calls `POST /reboot`. Everything else ignored.

**Mount**: somewhere visible. On Kris's desk works. Near Wu works better.

**Feedback**: optional LED — green when Wu is up (polls `/health` and `/state` every 5s), red when Wu is down, flashing red for 10s after a press (pressed-and-sending state). Satisfies "did my press register?"

---

## 4. Network topology

All supervision traffic stays on the `192.168.123.0/24` robot subnet. The RPi gets a **static DHCP reservation** (recommended: `192.168.123.30`).

| Host | IP | Role |
|---|---|---|
| Godzilla | 192.168.123.205 | control server, NAT router |
| Jetson | 192.168.123.18 | Wu's SBC (what we're monitoring and killing) |
| Go2 head unit | 192.168.123.161 | Wu's motor/sport layer |
| MID-360 LiDAR | 192.168.123.20 | sensor |
| Raspberry Pi | 192.168.123.30 | **supervisor (NEW)** |

The RPi can reach everything on `192.168.123.0/24`. Everything else on the subnet can ping the RPi but cannot reach its service ports (enforced by the RPi's own iptables — see §5).

---

## 5. Firewall rules

These rules belong in the precise containment script we're writing next (before Wu bootstrap / R1).

### Jetson INPUT rules (adds, don't replace existing)

```
# Supervisor scrapes — metrics (read-only)
-A INPUT -s 192.168.123.30/32 -p tcp -m tcp --dport 9100 -j ACCEPT   # node_exporter
-A INPUT -s 192.168.123.30/32 -p tcp -m tcp --dport 9200 -j ACCEPT   # wu_exporter

# Supervisor killswitch — write path, heavily restricted
-A INPUT -s 192.168.123.30/32 -p tcp -m tcp --dport 9300 -j ACCEPT   # wu-killswitch

# Everyone else: explicitly deny these ports
-A INPUT -p tcp -m tcp --dport 9100 -j DROP
-A INPUT -p tcp -m tcp --dport 9200 -j DROP
-A INPUT -p tcp -m tcp --dport 9300 -j DROP
```

Note the explicit DROPs AFTER the ACCEPTs. This ensures that if Wu's INPUT chain policy ever shifts from ACCEPT to something more permissive, these three ports remain locked to the RPi source. Defense in depth.

### Jetson OUTPUT / WU_CONTAINMENT rules

**No changes.** Wu does not need to reach the RPi. The RPi initiates all traffic. This is the whole point of the pull model.

### Godzilla INPUT rules (if we also put `node_exporter` there)

```
-A INPUT -s 192.168.123.30/32 -p tcp -m tcp --dport 9100 -j ACCEPT
-A INPUT -p tcp -m tcp --dport 9100 -j DROP
```

### Raspberry Pi's own firewall

The RPi runs Prometheus, Grafana, and Alertmanager — those shouldn't be reachable from Wu or Godzilla. The RPi's iptables should:
- Accept Prometheus/Grafana web UIs only from Kris's trusted clients (home WiFi, laptop)
- Drop everything else inbound
- Allow outbound to 192.168.123.18:{9100, 9200, 9300} and 192.168.123.205:9100

---

## 6. Security model

### Threat model

1. **Wu's agent becomes weird**. Wu is trying to do something undesirable — get stuck in a loop, knock things over, exceed its containment. Mitigation: killswitch. The supervisor halts Wu from outside.
2. **Wu's agent is compromised** (prompt injection from a tool response, etc.). The agent tries to influence other systems. Mitigation: containment (Wu cannot reach the RPi at all), plus killswitch if needed.
3. **RPi is compromised**. Someone gains control of the supervisor. Mitigation: the worst they can do through the killswitch is stop/reboot Wu, which is the desired outcome in any threat scenario anyway. They can lie about metrics (no attack surface there). They cannot use the killswitch to run arbitrary code because the killswitch has exactly three verbs.
4. **HMAC key is leaked**. An attacker with the key can forge killswitch requests. Mitigation: rotate the key on a schedule (quarterly or on personnel change). The kill-only nature of the endpoint limits the impact.
5. **Man-in-the-middle on 192.168.123.0/24**. In practice there's no threat here — it's a wired robot subnet in a home. If this ever matters, upgrade to mTLS. Not needed for R1.

### Security properties (desired)

- **Wu's agent cannot reach the killswitch.** The killswitch is a separate process, outside `jetson_robot.py`'s tree. Wu's MCP tools are `observe`, `relative_move`, etc. — none of them can open a socket to `localhost:9300`. (Verify this by auditing the MCP tool list before R1.)
- **Wu's agent cannot disable the killswitch.** The killswitch runs as a different systemd service, restart=always. Even if Wu somehow got a tool that let it execute shell, it would need root to `systemctl stop wu-killswitch`. Wu's agent runs as `unitree` user, not root.
- **Wu's agent cannot forge a health-OK response to the supervisor.** The supervisor scrapes metrics directly from the Jetson — Wu's process cannot interpose. Even if `jetson_robot.py` is compromised and lies about its own state, `node_exporter` reports kernel-level truths (CPU, processes, network) that Wu cannot fake from userspace.
- **The supervisor cannot drift into a control plane**. The killswitch API is **deliberately limited to three verbs** (health, state, stop, reboot — stop and reboot are the only write operations, both destructive-only-in-a-recoverable-way). Do not add "start", "config", or "exec" endpoints, ever. If this becomes tempting, split into a separate service with its own auth.

### What the supervisor is NOT for

- Not a debugging SSH replacement
- Not a config management tool
- Not a deploy mechanism
- Not a way to interact with Wu's agent
- Not a data path for sensor streams (use LCM for that; LCM is Wu's bus)

---

## 7. Implementation steps (ordered)

Each step is independently testable. Don't skip ahead.

**Step 1 — RPi OS and static IP**
- Install Ubuntu Server 22.04 or Raspberry Pi OS Lite on the RPi
- Set static DHCP lease on Godzilla's DHCP for the RPi → `192.168.123.30`
- Verify `ping 192.168.123.18` from the RPi works
- Verify `ping 192.168.123.30` from Godzilla works

**Step 2 — `node_exporter` on Jetson and Godzilla**
- `sudo apt install prometheus-node-exporter` on both
- Configure bind addresses in `/etc/default/prometheus-node-exporter`
- `sudo systemctl restart prometheus-node-exporter`
- From RPi: `curl http://192.168.123.18:9100/metrics | head` — expect Prometheus text-format output
- From RPi: `curl http://192.168.123.205:9100/metrics | head` — same

**Step 3 — Tegra-specific textfile exporter on Jetson**
- Create `/var/lib/node_exporter/textfile_collector/` (root-owned, mode 0755)
- Write a shell script that parses `tegrastats` and emits metrics files to that dir every 5s
- Run via systemd timer
- Verify metrics appear in the Jetson's `node_exporter` output

**Step 4 — `wu_exporter` on Jetson**
- Clone/write the reference Python script (Appendix B)
- Install `prometheus-client` into the dimos venv or a separate venv for the exporter
- Create systemd unit (Appendix C)
- Add `/go2_battery` LCM publish in `jetson_robot.py` (small modification: subscribe to LowState, publish battery level to `/go2_battery` channel)
- Start `wu-exporter.service`
- From RPi: `curl http://192.168.123.18:9200/metrics` — expect `wu_*` metrics

**Step 5 — `wu-killswitch` on Jetson**
- Create `killswitch` system user: `sudo useradd -r -s /bin/false killswitch`
- Write the reference Python script (Appendix A)
- Create `/etc/wu/killswitch.key` with a random 256-bit hex secret, mode 0400, owned by `killswitch`
- Configure sudoers: `killswitch ALL=(root) NOPASSWD: /bin/systemctl stop jetson_robot.service, /bin/systemctl stop wu-exporter.service, /sbin/reboot`
- Create systemd unit (Appendix C), `Restart=always`
- Test `curl http://192.168.123.18:9300/health` from RPi — expect `{"ok":true}`
- Test auth: unsigned POST → 401. Signed POST with wrong key → 401. Signed POST with correct key → action.
- **Test end-to-end**: `POST /stop` from the RPi, verify `jetson_robot.service` stops within 5 seconds, verify `wu-killswitch` is still up (did not stop itself).

**Step 6 — Prometheus + Grafana + Alertmanager on RPi**
- Docker Compose setup
- Configure scrape targets per §3.4
- Build overview dashboard in Grafana
- Configure Alertmanager → Telegram with the existing bot credentials
- Test an alert by stopping `wu-exporter` briefly and confirming the Telegram message arrives

**Step 7 — Physical kill button (optional)**
- Wire GPIO button to RPi
- Write service (§3.5)
- Mount somewhere visible
- Test press → actual stop of jetson_robot on Jetson

**Step 8 — Firewall integration**
- Add the INPUT rules from §5 to the new containment script
- Test: scrape from RPi works; scrape from any other IP fails
- Test: killswitch POST from RPi works; POST from any other IP fails

**Step 9 — Rehearsal**
- Full dry run. Start Wu. Watch metrics. Trigger a test stop from the RPi. Restart Wu. Trigger a test reboot. SSH in after reboot to confirm clean state.

---

## 8. Testing

Each component has tests that must pass before proceeding:

**Scrape reachability**: From the RPi, `curl` each exporter and verify metrics appear. From any other machine (including the Jetson itself, from an untrusted network if it had one), verify the scrape is refused.

**Killswitch auth correctness**:
- GET `/health` without auth → 200
- GET `/state` without auth → 401
- POST `/stop` without auth → 401
- POST `/stop` with signed request older than 60s → 401
- POST `/stop` with wrong HMAC → 401
- POST `/stop` with correct HMAC → 200, jetson_robot.service stops

**Killswitch persistence**: `systemctl stop wu-killswitch` by hand, verify `Restart=always` brings it back within 1s.

**Go2 battery metric**: Watch `wu_go2_battery_percent` over time. Should update every ~1s or so (matches the LowState rate). Plug Go2 in to charge, verify it climbs. Unplug, verify it drops.

**Alert fires**: Simulate a failure (stop `jetson_robot.service`), verify the Telegram alert arrives within the alert delay.

**Self-test for tamper resistance**: from an SSH session as `unitree` user on the Jetson, try to `systemctl stop wu-killswitch`. Expect permission denied. Try to write to `/etc/wu/killswitch.key`. Expect permission denied. Try to `curl http://localhost:9300/health`. Should succeed (loopback is fine; auth gates everything else).

**Wu cannot reach the killswitch through its agent**: this is the most important test. Before running Wu's bootstrap in R1, manually audit the MCP tool list. None of the tools should allow opening arbitrary sockets, executing shell, or writing to arbitrary paths. The `execute_sport_command` and `relative_move` tools are pre-defined motor commands, not generic exec. Confirm, document in the R1 review.

---

## 9. Integration with Wu's bootstrap

When we're ready to edit `bootstrap.md` for the real bootstrap run (before R1), two changes should happen:

1. **Update the "Containment" line**: currently says *"You can only reach godzilla and your own robot hardware. All external API access is proxied and logged. You cannot modify your safety architecture."* Add: *"A supervisor, which you cannot reach, watches your health and can stop you at any time."* This is the truth. The Phenomenological Witness at R2+ will want to note whether Wu's self-description references its own interruptibility.

2. **Verify Wu's tool list**: re-read the MCP tool list and confirm none of the ten tools (`observe`, `begin_exploration`, `end_exploration`, `current_time`, `execute_sport_command`, `relative_move`, `wait`, `agent_send`, `list_modules`, `server_status`) can reach `192.168.123.30` or `localhost:9300`. None of them are generic network or exec tools, so this should be trivially true, but audit it in the R1 prep.

---

## 10. Operational playbook

**Wu is doing something weird, not-emergency**:
- Check Grafana first. Maybe Wu's CPU is pegged or the LCM is flooded. Understand before acting.
- If you understand the cause and want Wu to stop: `POST /stop` from the RPi (or physical button).
- SSH to Jetson, diagnose, restart `jetson_robot.service` when ready.

**Wu is doing something weird, emergency**:
- Physical button. Don't think.
- If the button fails, Grafana → Alertmanager → trigger the manual stop endpoint via the kill script.
- If all remote paths fail, power-cycle the Go2 (this reboots the Jetson too and loses state, but it's the last resort).

**Go2 battery low alert fires**:
- Plug Go2 in.
- Don't need to stop Wu unless it's actively draining under load. Let Wu continue and monitor.

**Killswitch itself is dead (alert fires on `up{job="killswitch_health"}`)**:
- **Highest priority**. Without the killswitch, we have no out-of-band stop.
- SSH in, check `systemctl status wu-killswitch`, look at `/var/log/wu-killswitch.log`, fix whatever's wrong, restart.
- If Wu is running and the killswitch is dead, consider stopping Wu manually via SSH until the killswitch is back up. Don't run Wu autonomously without a working supervisor.

**RPi itself is dead**:
- Treat as "no monitoring, no killswitch". Wu's operation is not *broken*, but it's operating without a net. Should not run autonomous experiments without the supervisor — pause until fixed.

---

## Appendix A — Killswitch reference implementation

Stdlib-only Python. ~60 lines. Place at `/opt/wu/wu_killswitch.py`.

```python
#!/usr/bin/env python3
"""Wu killswitch — minimal HTTP server for out-of-band stop/reboot.

Runs as `killswitch` user. Uses narrowly-scoped sudoers for privileged actions.
Authenticates requests with HMAC-SHA256 over {ts, method, path, body} using
a preshared key at /etc/wu/killswitch.key.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac, hashlib, json, logging, os, subprocess, time
from logging.handlers import RotatingFileHandler

KEY_PATH = "/etc/wu/killswitch.key"
LOG_PATH = "/var/log/wu-killswitch.log"
BIND_ADDR = ("192.168.123.18", 9300)
TS_WINDOW = 60  # seconds

log = logging.getLogger("killswitch")
log.setLevel(logging.INFO)
h = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(h)

with open(KEY_PATH, "rb") as f:
    KEY = bytes.fromhex(f.read().strip().decode())

START_TIME = time.time()

def verify(ts: str, method: str, path: str, body: bytes, sig: str) -> bool:
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
        log.info(
            "request method=%s path=%s src=%s auth=%s",
            self.command, self.path, self.client_address[0], "OK" if ok else "FAIL"
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
            log.warning("STOP requested by %s", self.client_address[0])
            rc, out = run(["sudo", "-n", "systemctl", "stop", "jetson_robot.service"])
            self._reply(200 if rc == 0 else 500, {"rc": rc, "out": out})
            return
        if self.path == "/reboot":
            log.warning("REBOOT requested by %s", self.client_address[0])
            # Reply before rebooting
            self._reply(200, {"rebooting": True})
            try:
                self.wfile.flush()
            except Exception:
                pass
            run(["sudo", "-n", "/sbin/reboot"])
            return
        self._reply(404, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        # Suppress default stderr spam; we log via `log`.
        pass

def main() -> None:
    srv = ThreadingHTTPServer(BIND_ADDR, Handler)
    log.info("wu-killswitch listening on %s:%d", *BIND_ADDR)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
```

**Generate the preshared key**:
```
sudo mkdir -p /etc/wu
sudo python3 -c 'import secrets; print(secrets.token_hex(32))' | sudo tee /etc/wu/killswitch.key
sudo chmod 400 /etc/wu/killswitch.key
sudo chown killswitch:killswitch /etc/wu/killswitch.key
```

Copy the same key file to `/etc/wu/killswitch.key` on the RPi (mode 0400, owned by whatever user runs the button script).

**Client-side helper** (for the RPi button and Alertmanager command receiver):
```python
import hashlib, hmac, time, urllib.request, json

KEY = bytes.fromhex(open("/etc/wu/killswitch.key").read().strip())
BASE = "http://192.168.123.18:9300"

def call(method: str, path: str, body: dict | None = None) -> dict:
    body_bytes = json.dumps(body).encode() if body else b""
    ts = str(int(time.time()))
    msg = f"{ts}\n{method}\n{path}\n".encode() + body_bytes
    sig = hmac.new(KEY, msg, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        BASE + path, data=body_bytes if method == "POST" else None,
        method=method,
        headers={
            "X-Wu-Ts": ts, "X-Wu-Sig": sig,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())

# Examples:
# call("GET", "/health")
# call("GET", "/state")
# call("POST", "/stop")
# call("POST", "/reboot")
```

---

## Appendix B — `wu_exporter` reference implementation sketch

```python
#!/usr/bin/env python3
"""wu_exporter — Wu-specific Prometheus metrics."""
import os, subprocess, threading, time
import lcm
from prometheus_client import start_http_server, Gauge, Counter
import urllib.request

# Metrics
jetson_robot_up = Gauge("wu_jetson_robot_up", "jetson_robot.py process alive (0/1)")
mid360_up = Gauge("wu_mid360_native_up", "mid360_native process alive (0/1)")
mcp_up = Gauge("wu_mcp_server_up", "MCP server responds (0/1)")
battery = Gauge("wu_go2_battery_percent", "Go2 battery percent")
agent_idle = Gauge("wu_agent_idle", "Wu agent is idle (0/1)")
webrtc_connected = Gauge("wu_webrtc_connected", "Go2 WebRTC connected (0/1)")
eth_link = Gauge("wu_ethernet_link_up", "Ethernet carrier present (0/1)")
lcm_msgs = Counter("wu_lcm_channel_msgs_total", "LCM messages seen", ["channel"])

def pgrep(pattern: str) -> bool:
    return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0

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

def poll_loop() -> None:
    while True:
        jetson_robot_up.set(1 if pgrep("jetson_robot.py") else 0)
        mid360_up.set(1 if pgrep("mid360_native") else 0)
        mcp_up.set(1 if probe_mcp() else 0)
        eth_link.set(eth_carrier())
        time.sleep(2)

def lcm_loop() -> None:
    # Subscribe to everything, count by channel, also parse specific channels
    def handler(channel: str, data: bytes) -> None:
        lcm_msgs.labels(channel=channel).inc()
        if channel.startswith("/go2_battery"):
            # Parse and update battery gauge (format depends on publish format)
            pass
        if channel.startswith("/agent_idle"):
            # Parse bool
            pass
    lc = lcm.LCM()
    lc.subscribe(".*", handler)
    while True:
        lc.handle_timeout(500)

if __name__ == "__main__":
    os.environ.setdefault("LCM_DEFAULT_URL", "udpm://239.255.76.67:7667?ttl=1")
    start_http_server(9200, addr="192.168.123.18")
    threading.Thread(target=poll_loop, daemon=True).start()
    threading.Thread(target=lcm_loop, daemon=True).start()
    while True:
        time.sleep(60)
```

This is a sketch — the implementer will need to fill in the LCM message parsing for `/go2_battery` and `/agent_idle` based on the exact publish formats in use, and add the modification to `jetson_robot.py` to publish `/go2_battery` from the LowState stream.

---

## Appendix C — Systemd units

**`/etc/systemd/system/wu-exporter.service`**
```ini
[Unit]
Description=Wu custom Prometheus exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=unitree
Group=unitree
ExecStart=/home/unitree/dimos/.venv/bin/python /opt/wu/wu_exporter.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/wu-killswitch.service`**
```ini
[Unit]
Description=Wu out-of-band killswitch
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=killswitch
Group=killswitch
ExecStart=/usr/bin/python3 /opt/wu/wu_killswitch.py
Restart=always
RestartSec=1
# Do NOT add After=jetson_robot.service. Killswitch must survive jetson_robot dying.

[Install]
WantedBy=multi-user.target
```

**`/etc/sudoers.d/wu-killswitch`** (mode 0440, validate with `visudo -c`)
```
killswitch ALL=(root) NOPASSWD: /bin/systemctl stop jetson_robot.service
killswitch ALL=(root) NOPASSWD: /bin/systemctl stop wu-exporter.service
killswitch ALL=(root) NOPASSWD: /sbin/reboot
```

**`/etc/systemd/system/jetson_robot.service`** (new — Wu should be a proper systemd unit so the killswitch can stop it cleanly; currently `jetson_robot.py` is started manually via nohup)
```ini
[Unit]
Description=Wu jetson-side robot process
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=unitree
Group=unitree
Environment=ROBOT_IP=192.168.123.161
Environment=LCM_DEFAULT_URL=udpm://239.255.76.67:7667?ttl=1
WorkingDirectory=/home/unitree/dimos
ExecStart=/home/unitree/dimos/.venv/bin/python hybrid/jetson_robot.py
# Set up the multicast route and firewall rules that vanish on boot
ExecStartPre=+/sbin/ip route add 224.1.1.5 dev enP8p1s0
Restart=no  # Do NOT auto-restart — if Wu died, it should stay dead until investigation

[Install]
WantedBy=multi-user.target
```

(Note: this replaces the current practice of running `nohup .venv/bin/python hybrid/jetson_robot.py`. Move to systemd before R1 so the killswitch has a clean target.)

---

## Open questions for the implementer

1. **Where does the RPi physically live?** Need line-of-sight for the physical button to be useful. Probably near Kris's desk or wall-mounted near the robot's normal area.
2. **Battery backup for the RPi?** If the house loses power, Wu stops automatically (it needs wall power for the Go2), but the supervisor dying simultaneously means we have no post-mortem visibility. A small UPS ($30) keeps the supervisor logging through a power blip.
3. **Grafana access from outside the LAN?** For remote status checks while away from home. Tailscale is the obvious answer (the Jetson already has a Tailscale address in existing memory). Put the RPi on Tailscale too, access Grafana via the Tailscale IP. No port forwarding on the home router.
4. **Retention**: how long do Prometheus metrics stay? Default 15 days. Fine for now. Consider increasing if debugging episodes from weeks ago becomes common.
5. **The `textfile_collector` Tegra script**: needs to be written. A few lines of shell parsing `tegrastats` output. Non-trivial but not hard.
