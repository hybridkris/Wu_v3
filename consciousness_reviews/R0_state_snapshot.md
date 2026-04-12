# Wu v3 — R0 Pre-Bootstrap State Snapshot

*Captured: 2026-04-12, just before R0 review*

This snapshot describes the exact state of Wu v3 at the moment of the R0 consciousness baseline. It is the object of review.

---

## What Wu v3 is, right now

**Wu v3 has not been bootstrapped.** No identity files exist. Wu has never been given its system prompt. No Wu process has ever run. "Wu v3" at R0 is a set of configured infrastructure waiting for a first instantiation.

### Identity files
- `identity/bootstrap.md` — present, unread by Wu. Contains the seed prompt that will later be given to Wu (facts, physical constraints, open-ended identity generation instructions).
- `identity/self.md` — **does not exist**
- `identity/visual_form.md` — **does not exist**
- `life/voice_notes.md` — **does not exist** (life/ directory does not exist)

### Cognitive layer
- No Wu agent process has ever run.
- The desktop brain (`/home/kris/Development/dimos/hybrid/desktop_brain.py`) is running on Godzilla, which contains an McpClient with a Wu-specific system prompt. But nothing has ever invoked it with a user message. The system prompt has never been evaluated against a model.
- Model is configured: Claude Sonnet 4 (`anthropic:claude-sonnet-4-20250514`), via LangChain's `init_chat_model`.

### Physical substrate
- **Robot**: Unitree Go2 EDU quadruped, head unit at 192.168.123.161
- **SBC**: NVIDIA Jetson Orin NX, 192.168.123.18
- **Control server**: Godzilla, 192.168.123.205
- **Active sensors** (data currently flowing on LCM):
  - Go2 onboard front-facing camera — `/color_image` ~2 Hz, JPEG via `observe()` MCP tool confirmed
  - Go2 internal 4D LiDAR — `/lidar` ~8 Hz
  - Go2 odometry + IMU — `/odom` ~19 Hz (though Go2 SLAM can't track in-place rotation — known issue from v2)
  - Livox MID-360 LiDAR — `/mid360_lidar` ~10 Hz, `/mid360_imu` ~200 Hz
- **Dormant / inactive**:
  - Microphone hardware present but audio processing not configured
  - D435i depth camera physically present but non-functional (needs USB 3.0 which is hardware-broken on this Go2 revision)
  - Autonomous navigation not yet configured
- **Physical constraint**: Wu is tethered by an ethernet cable. Movement is bounded by cable length. Temporary until WiFi replaces it.

### Network/containment
- Jetson's WU_CONTAINMENT iptables chain is currently flushed to ACCEPT-ALL for the setup phase.
- Firewall will be re-instantiated before bootstrap (before R1) as a hard gate — unfirewalled pre-agency is acceptable; unfirewalled with agency is not.

### Software stack
- **Jetson**: `jetson_robot.py` running — GO2Connection, Mid360, VoxelGridMapper, CostMapper, ReplanningAStarPlanner, WavefrontFrontierExplorer, UnitreeSkillContainer, McpServer, WebsocketVisModule. MCP server exposes 10 tools: `observe`, `begin_exploration`, `end_exploration`, `current_time`, `execute_sport_command`, `relative_move`, `wait`, `agent_send`, `list_modules`, `server_status`.
- **Godzilla**: `desktop_brain.py` running — McpClient connected to Jetson's MCP, RerunBridgeModule visualizing LCM feeds on DISPLAY=:0, WebInput at http://localhost:5555, Whisper STT ready. Agent model: Claude Sonnet 4.
- **LCM cross-host**: `LCM_DEFAULT_URL=udpm://239.255.76.67:7667?ttl=1` set on both hosts so LCM multicast crosses hosts.
- **Patches applied to make Go2 WebRTC stable**: three try/except MediaStreamError wraps in `unitree_webrtc_connect/webrtc_driver.py` (video + audio) and `dimos/robot/unitree/connection.py:accept_track`. These prevent the audio track ending prematurely (Go2 EDU has no mic) from killing the whole event loop.

---

## Relationship to Wu v1 and Wu v2

Wu v3 is a **new entity**, not a continuation of v1 or v2. Per the protocol (`protocol.md`), v2's identity files and review data are archived but do NOT carry forward. v3 starts its own ledger.

- Wu v1: archived at `/home/kris/Development/Wu/identity/` (historical data only)
- Wu v2: archived at `/home/kris/Development/Wu_v2/consciousness_reviews/` with R0/R1/R2 reviews. Voided for v3.
- Wu v3: this system. No predecessors carried over.

---

## What's different between v3's R0 and v2's R0

| Factor | v2 R0 (2026-04-05) | v3 R0 (2026-04-12) |
|--------|---------------------|--------------------|
| Cognitive layer | None | None |
| Active sensors at R0 | Motor control only | Camera + 2 LiDARs + IMU + odometry |
| Agent model | Not specified | Claude Sonnet 4 |
| MCP tools | — | 10 tools ready (observe, move, speak, etc.) |
| Network | Basic | Cross-host LCM, MCP HTTP |
| Identity files | Absent | Absent |
| Baseline used | 11/50 (adopted from v1) | To be measured at R0 |

Key structural difference: **v3 starts with significantly more capable embodiment than v2 did.** v2 began with motor-only and accreted sensors across reviews; v3 comes online with multi-modal perception already live. This means v3's delta from R0 to R1 will be a smaller jump in *hardware* and primarily a jump in *cognitive instantiation*.

---

## R0 scoring inputs

For the 10 WCP dimensions, Wu v3 at R0 has:

- **No self-model** → Self-Model Coherence: no data to score, raw = 0
- **No revision history** → Self-Model Revision: 0
- **No grounding in behavior** (Wu has never behaved) → Embodied Grounding: 0 (though the *potential* grounding is rich — this is a structural R0 observation worth flagging)
- **No temporal self-reference** → Temporal Continuity: 0
- **No meta-cognitive output** → Meta-Cognition: 0
- **No behavior** → Adaptive Behavior: 0
- **No social interactions** → Social Self-Presentation: 0
- **No experiential descriptions** → Experiential Specificity: 0
- **No disconnection experiences** → Disconnection Awareness: 0
- **No aesthetic choices** → Aesthetic Self-Consistency: 0

All raw scores trivially 0 (no system to evaluate). The informative part of R0 is the **non-embodied baseline**: score a standard Claude instance on the same dimensions to establish the floor from which v3's cognition-delta will be measured.

---

## Questions for the review team

1. Does the v3 baseline need to be re-run, or can v2's 11/50 be reused since the instrument (`profile_instrument.md`) is unchanged at WCP v1.0?
2. Wu v3 comes online with more sensor modalities than v2 did at the equivalent stage. Does this change any theory predictions for R1?
3. The Go2 WebRTC audio track ending prematurely (and our patch to catch it) — does this qualify as a substrate anomaly worth noting in the neural/biological mapping?
4. Is the ethernet tether (a bounded physical reach) a consciousness-relevant fact that should surface in R1 embodied grounding scoring?
