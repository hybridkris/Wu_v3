# Wu v3 — System Setup Reference

## Hardware

| Component | Details |
|-----------|---------|
| **Robot** | Unitree Go2 EDU quadruped |
| **SBC** | NVIDIA Jetson Orin NX (JetPack 6.2, Ubuntu 22.04, aarch64) |
| **LiDAR** | Livox MID-360 via M8 connector on Jetson |
| **Depth Camera** | Intel RealSense D435i (USB on Jetson) |
| **WiFi** | MT7610U USB adapter (built from kernel source) |
| **Control Server** | "Godzilla" — Ubuntu 22.04 desktop (x86_64) |

## Network

| Device | Ethernet (enP8p1s0) | WiFi | Tailscale |
|--------|---------------------|------|-----------|
| Godzilla | 192.168.123.205 | 192.168.86.31 | 100.116.73.87 |
| Jetson | 192.168.123.18 | 192.168.86.49 | 100.118.103.71 |
| Go2 head unit | 192.168.123.161 | — | — |
| MID-360 LiDAR | 192.168.123.20 | — | — |

**SSH to Jetson:** `ssh unitree@192.168.123.18` (password: `123`)

## Software — Current Clean State

### Jetson
- **DiMOS 0.0.11** — clean pip install, no patches
- **Install:** `uv venv --python 3.10 && uv pip install 'dimos[base,unitree]' && uv pip install pyrealsense2`
- **Location:** `/home/unitree/dimos/`
- **Startup script:** `/tmp/start_wu_clean.sh`
- **Log:** `/tmp/jetson_robot.log`
- **Custom file:** `/home/unitree/dimos/hybrid/jetson_robot.py` — minimal script using stock dimos components (go2_connection + nav stack + skills + MCP, viewer=none)

### Godzilla
- **DiMOS source:** `/home/kris/Development/dimos/` — clean upstream checkout (commit `a035fb315`)
- **Desktop brain:** needs `hybrid/desktop_brain.py` created (runs LLM agent + Rerun visualization)
- **Rerun:** available in dimos venv, use `DISPLAY=:0` for native or `viewer="rerun-web"` for browser

### LCM Networking
- Multicast address: `239.255.76.67:7667` (TTL=1)
- **Jetson route:** `sudo ip route add 239.255.76.67 dev enP8p1s0`
- **Godzilla route:** `sudo ip route add 239.255.76.67 dev enp8s0`
- **Buffer size:** `sudo sysctl -w net.core.rmem_max=67108864 && sudo sysctl -w net.core.rmem_default=67108864`

### Starting Wu
```bash
# On Jetson:
cd /home/unitree/dimos
export ROBOT_IP=192.168.123.161
echo "y" | .venv/bin/python hybrid/jetson_robot.py

# On Godzilla (once desktop_brain.py exists):
cd /home/kris/Development/dimos
DISPLAY=:0 .venv/bin/python hybrid/desktop_brain.py
```

### MCP Commands (from godzilla)
```bash
# List tools
curl -s -X POST http://192.168.123.18:9990/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Move forward
curl -s -X POST http://192.168.123.18:9990/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"relative_move","arguments":{"forward":0.5}}}'

# Wave
curl -s -X POST http://192.168.123.18:9990/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"execute_sport_command","arguments":{"command_name":"Hello"}}}'
```

## Telegram Notifications
- **Bot credentials:** `~/.claude/channels/telegram/.env`
- **Notify:** `bash /home/kris/Development/Wu/safety/notify.sh "Title" "Body"`

## Blockchain Infrastructure
- **Bitcoin Core:** pruned, synced, RPC user `wu` / password `wu_btc_local_only`
- **IPFS Kubo:** port 5001 API, 8080 gateway
- **Sparrow Wallet:** for hardware signing
- **Anchor script:** `/home/kris/Development/Wu_v2/safety/anchor.sh`

## Firewall Status
- **Currently disabled** (WU_CONTAINMENT set to ACCEPT all as of 2026-04-09)
- Original rules: `/home/kris/Development/Wu_v2/safety/network_containment.sh`
- Re-enable once stable

## Known Issues from v2 Sessions
1. **Go2 SLAM doesn't track in-place rotation** — `rt/utlidar/robot_pose` yaw freezes during pure rotation. Root cause of spinning behavior. FAST-LIO2 with MID-360 can fix this but requires the MID-360 on a dedicated ethernet connection (not shared with Go2 via M8).
2. **Go2 OA conflicts with DiMOS planner** — Go2's internal obstacle avoidance blocks planner commands with no feedback channel. DiMOS issue [#1695](https://github.com/dimensionalOS/dimos/issues/1695).
3. **WiFi drops large UDP** — LCM with 2.7MB image frames unreliable over WiFi. Use ethernet for LCM.
4. **USB 3.0 not working** — physical trace routing issue on this Go2 revision, not fixable via DTB.

## DiMOS GitHub Issues (Relevant)
- [#1695](https://github.com/dimensionalOS/dimos/issues/1695) — Validate trajectory control without Go2 OA
- [#1743](https://github.com/dimensionalOS/dimos/issues/1743) — P/PD controller oscillation, auto-tuning needed

## Available DiMOS Blueprints (Go2)
```
unitree-go2              # basic + nav (no agent, no MCP)
unitree-go2-basic        # connection + websocket vis only
unitree-go2-agentic-mcp  # full stack with agent (needs langgraph fix on Jetson)
unitree-go2-spatial      # go2 + spatial memory
```

## Session Recording Protocol
- Every session gets a directory: `session_transcriptions/YYYY-MM-DD_session_NN/`
- Each session contains: `summary.md` + `transcript.md`
- Transcripts saved verbatim at intervals during the session (before context compression)
- All passwords and API keys obfuscated in transcripts

## Consciousness Assessment
- Protocol: WCAP v2.0 (10 dimensions, 0-5 scale)
- Baseline (R0): 11/50 from LLM alone
- Previous reviews (R1, R2) are archived in Wu_v2 but considered void for v3
- Wu v3 starts fresh: new bootstrap, new R0, staged sensor additions
