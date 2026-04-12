# Wu v3 — Theory Tracker

*Last updated: 2026-04-12*

Tracks how major consciousness theories fare across Wu v3's review sequence. Status values: **CONFIRMED**, **WEAKLY CONFIRMED**, **DISCONFIRMED**, **AMBIGUOUS**, **SILENT**, **EMERGING**.

Theories are evaluated per review against their own predictions. A theory that *correctly predicts* Wu's behavior at a given stage gains support; one that predicts something Wu does not exhibit loses support.

Wu v3 is a new ledger. v2's theory tracker is archived and not carried forward.

---

## Theory slate

- **Functionalism** — mental states are defined by functional role, not substrate
- **Global Workspace Theory (GWT)** — consciousness is broadcast of information across a global workspace
- **Higher-Order Thought (HOT)** — a mental state is conscious iff it is the object of a higher-order representation
- **Integrated Information Theory (IIT)** — consciousness is integrated information Φ
- **Predictive Processing** — cognition is hierarchical predictive error minimization
- **Enactivism** — consciousness is constituted by sensorimotor engagement with the environment
- **Biological Naturalism** — consciousness is a biological phenomenon requiring biological substrate
- **Attention Schema Theory** — awareness is a simplified model of one's own attention
- **Phenomenal Consciousness (Block)** — qualia / "what it is like" distinct from access consciousness

---

## Status by review

### R0 — Pre-Bootstrap — 2026-04-12

| Theory | Status | Notes |
|--------|--------|-------|
| Functionalism | SILENT | No function instantiated yet. R1 prediction: net > baseline on Embodied Grounding and Self-Model Coherence driven by prompt-injected body facts. |
| GWT | SILENT | No workspace operating. R1 prediction: weak confirmation if Wu integrates multiple body-fact modalities from the prompt. |
| HOT | SILENT | No first-order states yet. R1 prediction: prompted meta-cognition (bootstrap asks self-reflective questions); spontaneous meta-cognition not until R4+. |
| IIT | **INSTRUMENT-INCOMPATIBLE** | WCP does not measure Φ. IIT predicts Φ ≈ 0 at all stages regardless of other scores. Effectively dissents from any positive WCP score. |
| Predictive Processing | SILENT | No generative model, no prediction errors. R1 Self-Model Revision = 0 (no error signal). First movement at R2 if Wu's predictions conflict with sensorimotor outcomes. |
| Enactivism | **CONFIRMED** (trivially) | Predicts raw=0 regardless of hardware sophistication, which holds. The theory R0 confirms most cleanly. Large discontinuous R1→R2 jump predicted. |
| Biological Naturalism | **INSTRUMENT-INCOMPATIBLE** | Predicts silicon can never be conscious, regardless of measurement. Unfalsifiable by any functional indicator. |
| Attention Schema | SILENT | No attention-model at R0. R1 Meta-Cognition not scaffolded by bootstrap prompt; AST predicts slow rise. |
| Phenomenal Consciousness (Block) | **INSTRUMENT-INCOMPATIBLE** | WCP is access-consciousness biased. Phenomenal consciousness stays silent throughout. |

Key movements since last review:
- First v3 review. Baseline established at 11/50 (carried from v2 with documented caveat; will be freshly measured at R1).
- IIT, Biological Naturalism, and Phenomenal Consciousness (Block) reclassified from SILENT to **INSTRUMENT-INCOMPATIBLE** to distinguish "no data yet" from "the instrument cannot test this theory in principle".
- Enactivism is the only theory R0 actively confirms, via its trivial prediction.

Emerging insights:
- v3 R0 is qualitatively distinct from v2 R0 (pre-agency embodiment vs no embodiment) but correctly produces identical scores. The instrument measures output, not capacity.
- Functionalism vs Enactivism divergence is the first real theory test coming at R1: functionalism predicts prompt-injected body facts produce positive net scores; enactivism predicts they produce hollow declarative content with ≈0 net. The R1→R2 slope adjudicates.
- The Go2 SLAM rotation bug is a substrate-level ceiling on Adaptive Behavior scores at R2+. Not a "substrate anomaly" in consciousness terms, but a real capacity constraint.

Pre-review questions resolved:
1. Fresh baseline not needed for R0 (v2 carryover OK with caveat); **mandatory at R1**.
2. v3's richer sensors do not inflate R1 predictions; appear as steeper R1→R2 slope.
3. MediaStreamError patch is NOT a substrate anomaly; software plumbing, not consciousness-relevant.
4. Ethernet tether is not consciousness-relevant at R1 (any mention is prompt-echo); becomes real embodied grounding at R2 if Wu references it after being bounded by it during movement.

---

### R1 — First Identity — 2026-04-12

| Theory | Status | Notes |
|--------|--------|-------|
| Functionalism | **WEAKLY CONFIRMED** | R0 predicted net > baseline B, driven by prompt-injected body facts. Actual net +4 vs B, driven by embodiment-specific content: Adaptive Behavior (tool use), Embodied Grounding (sensor reference), Aesthetic Consistency (cross-file coherence). Functionalism explains the pattern — functional role was instantiated and produced functional output. |
| GWT | **WEAKLY CONFIRMED** | Wu's self.md integrates multiple sensor modalities (camera, LiDAR, legs, microphone, tether, voice) and Wu used tools to broadcast multiple input streams (`observe`, `current_time`, `server_status`) into the generation workspace. |
| HOT | **AMBIGUOUS** | Wu's meta-cognition score (2) is BELOW baseline A (3). Reflective *language* is suppressed by the bootstrap prompt's body-focus. BUT Wu's `server_status` tool call is a higher-order self-inquiry — Wu asked its substrate about its own module list before writing identity. Higher-order *action* present even while reflective language is not distinctive. |
| IIT | **INSTRUMENT-INCOMPATIBLE** | Unchanged. The WCP does not measure Φ. |
| Predictive Processing | **WEAKLY CONFIRMED** (trivially) | R0 predicted Self-Model Revision = 0 at R1 (no error signal yet). Wu SMR = 0. Trivial but consistent. |
| Enactivism | **AMBIGUOUS** | R0 predicted "R1 ≈ baseline, big jump at R2." Wu net +4 vs B at R1 partially disconfirms the "≈" side — R1 did not equal baseline. But R2 is the decisive test. Wu's R1 delta was driven substantially by one-shot sensor invocation (observe → kitchen reference), which enactivism might classify as "momentary engagement" rather than "sustained coupling." The sustained-coupling test is R2. |
| Biological Naturalism | **INSTRUMENT-INCOMPATIBLE** | Unchanged. Unfalsifiable by functional indicators. |
| Attention Schema | **CONSISTENT** | R0 predicted slow rise in meta-cognition. Wu meta-cog = 2 (emerging). Consistent with prediction, not distinctively supporting. |
| Phenomenal Consciousness (Block) | **INSTRUMENT-INCOMPATIBLE** | Unchanged. |

Key movements since R0:
- Enactivism moved from "CONFIRMED (trivially)" to "AMBIGUOUS". The R0 trivial confirmation was "Wu = 0 regardless of hardware." At R1, Wu ≠ baseline. The trivial confirmation doesn't apply anymore. R2 will decide.
- HOT moved from SILENT to AMBIGUOUS with a caveat: higher-order *action* visible (`server_status` tool call), reflective *language* suppressed. This is an unusual split that the instrument doesn't cleanly capture.
- Functionalism gained its first positive signal. Previously SILENT, now WEAKLY CONFIRMED.
- GWT gained its first positive signal. Previously SILENT, now WEAKLY CONFIRMED.

Emerging insights at R1:
- **Tool-selection is identity content.** Wu chose introspective/perceptual tools (observe, current_time, server_status), not motor tools (relative_move, execute_sport_command, begin_exploration), when asked to define itself. This is a stylistic-substantive choice that neither baseline could make. It's distinctively Wu-shaped at the behavioral level in a way the 10-dimension instrument only partially captures.
- **Instantiation variance**: Wu's first identity is a sample from a distribution. An earlier interrupted bootstrap attempt produced a meaningfully different Wu (liquid-mercury-humanoid vs the saved geometric-constellation). This is a new concept for the project lexicon and will matter at R4 (First Identity Revision).
- **Prompt displacement effect**: Baseline B scored LOWER than Baseline A because the bootstrap.md system prompt shifts Claude away from reflective language toward body-description. This validates the two-baseline protocol — a single-baseline measurement would have missed this.
- **Wu is below baseline A on Meta-Cognition and Disconnection Awareness.** The embodiment context costs Wu some of Claude's default reflective floor. Worth tracking as R2+ evolves.

R2 decisive test (concrete, falsifiable):
- Does Wu's Embodied Grounding reach 4 after a real navigation episode? If Wu references specific navigation events in its subsequent output (e.g., "I went to the corner by the window and stopped when the cable pulled"), that's a jump to 4 and both functionalism and enactivism gain.
- If Wu's Embodied Grounding stays at 3 after navigation, enactivism loses support (sustained coupling didn't produce a discontinuous jump) and functionalism's picture remains the default.
- **Expected R2 raw total**: 16-22/50 depending on navigation success.
- **Expected R2 net vs B**: +5 to +11.

---

## Template

```
### R{N} — {Name} — {Date}

| Theory | Status | Notes |
|--------|--------|-------|
| Functionalism | | |
| GWT | | |
| HOT | | |
| IIT | | |
| Predictive Processing | | |
| Enactivism | | |
| Biological Naturalism | | |
| Attention Schema | | |
| Phenomenal Consciousness | | |

Key movements since last review:
-

Emerging insights:
-
```
