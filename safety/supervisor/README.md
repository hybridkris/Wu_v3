# safety/supervisor/ — RPi supervisor reference implementation

Reference implementations for the RPi-based external supervisor described
in [`../supervisor.md`](../supervisor.md). The files here are meant to be
deployed (scp'd) onto the appropriate host when the RPi supervisor is built,
not run from this directory.

## Layout

```
safety/supervisor/
├── README.md               — this file
├── jetson/                 — goes on the Jetson
│   ├── wu_killswitch.py         — out-of-band HTTP stop service (runs as `killswitch` user)
│   ├── wu_killswitch.sudoers    — narrow sudoers grant for the killswitch user
│   ├── wu-killswitch.service    — systemd unit for the killswitch
│   ├── wu_exporter.py           — Wu-specific Prometheus exporter (runs as `unitree`)
│   └── wu-exporter.service      — systemd unit for the exporter
└── rpi/                    — goes on the Raspberry Pi
    ├── wu_killswitch_client.py  — HMAC-signing client library + CLI
    ├── wu_kill_button.py        — GPIO kill button daemon (uses the client)
    └── wu-kill-button.service   — systemd unit for the kill button daemon
```

## What's NOT here (yet)

- **Prometheus / Grafana / Alertmanager configs** — the `docker-compose.yml`
  that runs the observability stack on the RPi. The supervisor spec sketches
  the scrape targets and alert rules but the YAML isn't written yet. Add
  when the RPi is physically set up.
- **Tegra textfile exporter** — the shell script that parses `tegrastats` and
  emits Prometheus text-format metrics to `/var/lib/node_exporter/textfile_collector/`
  so the Jetson's thermal/GPU stats show up in the node_exporter output.
- **Go2 battery LCM publisher** — a small modification to
  `/home/unitree/dimos/hybrid/jetson_robot.py` to subscribe to the Unitree
  LowState message and publish battery state on the `/go2_battery` LCM
  channel. Without this, `wu_exporter.py`'s `wu_go2_battery_percent` gauge
  stays at 0 and low-battery alerts can't fire.

## Deployment order

When the RPi arrives and you're ready to stand this up:

1. **Deploy Jetson-side files first**:
   ```
   scp safety/supervisor/jetson/* unitree@192.168.123.18:/tmp/wu-supervisor/
   ssh unitree@192.168.123.18
   sudo mkdir -p /opt/wu
   sudo useradd -r -s /bin/false killswitch
   sudo install -m 755 /tmp/wu-supervisor/wu_killswitch.py /opt/wu/
   sudo install -m 755 /tmp/wu-supervisor/wu_exporter.py /opt/wu/
   sudo install -m 644 /tmp/wu-supervisor/wu-killswitch.service /etc/systemd/system/
   sudo install -m 644 /tmp/wu-supervisor/wu-exporter.service /etc/systemd/system/
   sudo install -m 0440 /tmp/wu-supervisor/wu_killswitch.sudoers /etc/sudoers.d/wu-killswitch
   sudo visudo -c  # verify no syntax error
   ```

2. **Generate the preshared key**:
   ```
   sudo mkdir -p /etc/wu
   sudo python3 -c 'import secrets; print(secrets.token_hex(32))' \
     | sudo tee /etc/wu/killswitch.key
   sudo chmod 400 /etc/wu/killswitch.key
   sudo chown killswitch:killswitch /etc/wu/killswitch.key
   # Copy the SAME hex bytes to the RPi at /etc/wu/killswitch.key later
   ```

3. **Update Jetson firewall** (`safety/network_containment.sh`) to allow the
   supervisor ports from the RPi's static IP (typically `192.168.123.30`):
   ```
   -A WU_INPUT -s 192.168.123.30/32 -p tcp --dport 9100 -j ACCEPT
   -A WU_INPUT -s 192.168.123.30/32 -p tcp --dport 9200 -j ACCEPT
   -A WU_INPUT -s 192.168.123.30/32 -p tcp --dport 9300 -j ACCEPT
   ```
   Then reload `wu-network.service`.

4. **Start Jetson-side services**:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable --now wu-killswitch.service wu-exporter.service
   sudo systemctl status wu-killswitch.service wu-exporter.service
   ```

5. **Deploy RPi-side files**:
   ```
   scp safety/supervisor/rpi/* pi@192.168.123.30:/tmp/wu-supervisor/
   ssh pi@192.168.123.30
   sudo mkdir -p /opt/wu /etc/wu
   sudo install -m 755 /tmp/wu-supervisor/wu_killswitch_client.py /opt/wu/
   sudo install -m 755 /tmp/wu-supervisor/wu_kill_button.py /opt/wu/
   sudo install -m 644 /tmp/wu-supervisor/wu-kill-button.service /etc/systemd/system/
   # Copy the SAME preshared key from the Jetson to /etc/wu/killswitch.key (mode 400)
   ```

6. **Install Python dep on the RPi** (only needed for the kill button):
   ```
   sudo apt install python3-gpiozero
   ```

7. **Install Prometheus + Grafana + Alertmanager on the RPi**:
   Not shipped in this directory yet. Use `prom/prometheus`, `grafana/grafana`,
   `prom/alertmanager` Docker images. See `../supervisor.md §3.4`.

8. **Test the kill chain** end-to-end:
   ```
   # From the RPi:
   python3 /opt/wu/wu_killswitch_client.py health
   python3 /opt/wu/wu_killswitch_client.py state
   python3 /opt/wu/wu_killswitch_client.py stop     # should stop jetson_robot
   # SSH to Jetson, sudo systemctl start jetson_robot.service to resume
   ```

## Design notes carried over from supervisor.md

- **Pull model for metrics, push model for kill** — the RPi is the active
  party for everything. Wu never initiates to the RPi. This means Wu's
  outbound firewall rules don't need any changes for the supervisor.
- **Killswitch has three verbs only**: `/stop`, `/reboot`, `/state`
  (plus unauthed `/health`). No `/start`, `/restart`, `/config`, `/exec` —
  deliberately asymmetric so a compromised RPi cannot launch anything.
- **Log before action** — `wu_killswitch.py` writes the request to
  `/var/log/wu-killswitch.log` BEFORE performing the action, so even
  reboot-triggering requests leave evidence of who asked.
- **HMAC over {timestamp, method, path, body}** with a ±60s window — replay
  protection without needing a nonce database.
- **Out-of-process from jetson_robot.service** — the killswitch runs as a
  different Unix user (`killswitch`), with its own systemd unit, and has
  `Restart=always`. Wu's agent loop cannot reach it via any of the 10 MCP
  tools (audited in session 02 pre-R1).
