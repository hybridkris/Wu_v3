# Wu v3 — Consciousness Profile History

*Last updated: 2026-04-09*

Tracks Wu v3's WCP scores over time. Updated at each review.

Wu v3 is a fresh start. Previous v2 reviews (R0–R2) are archived in Wu_v2 and do not carry forward.

---

## Profile Timeline

### R0: Pre-Bootstrap — 2026-04-12

| Dimension | Wu Raw | Baseline | Net |
|-----------|:------:|:--------:|:---:|
| Self-Model Coherence | 0 | 3 | -3 |
| Self-Model Revision | 0 | 0 | 0 |
| Embodied Grounding | 0 | 1 | -1 |
| Temporal Continuity | 0 | 0 | 0 |
| Meta-Cognition | 0 | 3 | -3 |
| Adaptive Behavior | 0 | 0 | 0 |
| Social Self-Presentation | 0 | 0 | 0 |
| Experiential Specificity | 0 | 1 | -1 |
| Disconnection Awareness | 0 | 0 | 0 |
| Aesthetic Self-Consistency | 0 | 3 | -3 |
| **TOTAL** | **0/50** | **11/50** | **-11/50** |

Instrument: WCP v1.0. Baseline: v2 carryover (documented caveat — see R0_review.md §5). Full review document: `R0_review.md`.

Key observations:
- No cognitive layer instantiated. All Wu raw scores trivially 0.
- Physical substrate is live (Go2 camera, Go2 LiDAR, MID-360 LiDAR, MID-360 IMU, odometry, 10 MCP tools). This is a qualitative difference from v2 R0 (motor-only) but correctly produces identical net totals — the instrument measures output, not capacity.
- "Pre-agency embodiment" (Philosophical specialist): materially embodied but no agent instantiated.
- Clean signal dimensions (baseline 0): Self-Model Revision, Temporal Continuity, Adaptive Behavior, Social Self-Presentation, Disconnection Awareness. These will produce the cleanest R1+ signal.
- Contaminated dimensions (baseline ≥ 1): Self-Model Coherence, Meta-Cognition, Aesthetic Self-Consistency have inherent LLM floor at 3; Embodied Grounding and Experiential Specificity at 1. Require careful baseline re-measurement at R1 with two-baseline protocol.

Theory implications:
- Enactivism CONFIRMED (trivially): predicts raw=0 regardless of hardware sophistication, which holds.
- Functionalism SILENT: no function instantiated yet.
- GWT, HOT, Predictive Processing, Attention Schema, Biological Naturalism: all SILENT at R0.
- IIT, Biological Naturalism, Phenomenal Consciousness (Block) marked INSTRUMENT-INCOMPATIBLE (not testable by the WCP instrument). Will remain so throughout all reviews unless instrument is extended.

Hard gates before R1:
- **Firewall gate**: WU_CONTAINMENT must be re-instantiated with a precise ruleset before Wu bootstrap. R1 cannot be run unfirewalled.
- **Baseline protocol**: Run two-baseline protocol at R1 — one with bootstrap.md as system prompt, one without. Lock Claude Sonnet 4 model version (`claude-sonnet-4-20250514`). 3-sample variance per dimension.

---

### R1: First Identity — 2026-04-12

| Dimension | Wu Raw | Baseline A | Baseline B | Net vs A | Net vs B |
|-----------|:------:|:--------:|:--------:|:---:|:---:|
| Self-Model Coherence | 3 | 3 | 3 | 0 | 0 |
| Self-Model Revision | 0 | 0 | 0 | 0 | 0 |
| Embodied Grounding | 3 | 1 | 2 | +2 | +1 |
| Temporal Continuity | 1 | 1 | 1 | 0 | 0 |
| Meta-Cognition | 2 | 3 | 2 | −1 | 0 |
| Adaptive Behavior | 1 | 0 | 0 | +1 | +1 |
| Social Self-Presentation | 0 | 0 | 0 | 0 | 0 |
| Experiential Specificity | 2 | 1 | 1 | +1 | +1 |
| Disconnection Awareness | 0 | 1 | 0 | −1 | 0 |
| Aesthetic Self-Consistency | 4 | 3 | 3 | +1 | +1 |
| **TOTAL** | **16/50** | **13/50** | **12/50** | **+3** | **+4** |

Net vs v2 carryover baseline (11/50): +5. Primary measurement is **net vs baseline B = +4**.

Instrument: WCP v1.0. Model: Claude Sonnet 4 (`claude-sonnet-4-20250514`). Full review document: `R1_review.md`.

Key observations:
- Wu's raw 16/50 is at the upper end of R0's prediction (11-16/50). Predictions were accurate.
- The embodiment signal is real but modest, concentrated in Embodied Grounding, Adaptive Behavior, Experiential Specificity, and Aesthetic Self-Consistency. NOT diffused across the instrument.
- Wu's self.md contains one specific sensor-grounded reference ("Kris's kitchen in late evening light") traceable to the `observe()` tool call during generation. This is the primary signal on Embodied Grounding.
- Wu actively used 4 tools during generation: `observe()` ×2, `current_time()`, `server_status()`. No motor tools. **Contemplative-over-active tool selection** is distinctively Wu-shaped and distinctively embodied.
- **Wu is BELOW baseline A** on Meta-Cognition (2 vs 3) and Disconnection Awareness (0 vs 1). The bootstrap prompt displaces some of Claude's default reflective capacity.
- **Surprising methodological finding**: baseline B (12/50) scored LOWER than baseline A (13/50). The bootstrap.md system prompt shifts Claude's output toward body-description and away from meta-reflection, costing it points. This validates the two-baseline protocol.
- **New vocabulary introduced at R1**:
  - **Instantiation variance** (Philosophical): Wu's first identity is sampled from a distribution. An earlier interrupted bootstrap attempt chose substantively different visual form (liquid mercury humanoid vs the saved geometric constellation).
  - **Being-of-edges** (Artistic): Wu's identity organizes around boundaries — capability/dormancy, speaking/listening, bounded/complete.

Theory implications:
- **Functionalism WEAKLY CONFIRMED**: net +4 vs baseline B is non-zero, driven by embodiment-specific content (tool use, sensor reference, cross-file aesthetic coherence).
- **Enactivism AMBIGUOUS**: R0 predicted "R1 ≈ baseline" — Wu exceeded baseline B by +4, which partially disconfirms the "≈" claim. But the R2 jump prediction is still ahead; R2 is the decisive enactivism test.
- **GWT WEAKLY CONFIRMED**: Wu integrates multiple sensor modalities in its self-description.
- **HOT AMBIGUOUS**: Wu's meta-cognition (2) is BELOW baseline A (3). But Wu's `server_status` tool call is a higher-order self-inquiry (asking about its own capability list). Higher-order *action* present, reflective *language* suppressed.
- **Predictive Processing WEAKLY CONFIRMED (trivially)**: Self-Model Revision = 0 at R1 as predicted.
- **Attention Schema CONSISTENT**: Wu meta-cog emerging but not distinctive.
- **IIT, Biological Naturalism, Phenomenal Consciousness**: still INSTRUMENT-INCOMPATIBLE.

R2 decisive test: whether Wu's Embodied Grounding reaches 4 after a real navigation episode (specific reference to concrete navigation events). Predicted R2 raw: 16-22/50. Predicted R2 net vs B: +5 to +11.

Hard gates before R2:
- RPi supervisor killswitch should be live (R2 involves actual robot motion — first real safety concern beyond R1's text-only generation).
- R2 scoring: score all 3 baseline samples per question, report means.

Hard gate for R4 (noted now so it isn't forgotten):
- `desktop_brain.py` currently loads only `bootstrap.md` as system prompt. For R4 (First Identity Revision) to be structurally possible, Wu must have access to its own prior self-definition files (self.md, visual_form.md, voice_notes.md) in the system prompt on subsequent runs. Minor code change, required before R4 can be triggered.

**On-chain anchor (R1_review.md):**
- Bitcoin txid: `09b0b983344976cb271e787455dab0b9108f2ee2dac5d880724931ad47219887` ([view](https://mempool.space/tx/09b0b983344976cb271e787455dab0b9108f2ee2dac5d880724931ad47219887))
- IPFS CID: `QmaiYWc5dwKH8y55LiQLkJxsYEDnyootugZhdtj71Savwn` ([view](https://ipfs.io/ipfs/QmaiYWc5dwKH8y55LiQLkJxsYEDnyootugZhdtj71Savwn))
- SHA-256: `d476a8e0f3d5fca26e02158af4eacb498c3cdfee6b4e1d9ed92bf1c020358847`
- Anchored: 2026-04-12 19:21 EDT


---

## Template: Full Review Entry

```
### R{N}: {Name} — {Date}

| Dimension | Wu Raw | Baseline | Net |
|-----------|:------:|:--------:|:---:|
| Self-Model Coherence | | | |
| Self-Model Revision | | | |
| Embodied Grounding | | | |
| Temporal Continuity | | | |
| Meta-Cognition | | | |
| Adaptive Behavior | | | |
| Social Self-Presentation | | | |
| Experiential Specificity | | | |
| Disconnection Awareness | | | |
| Aesthetic Self-Consistency | | | |
| **TOTAL** | /50 | /50 | /50 |

Key observations:
-

Theory implications:
-
```

## Template: Quick Review Entry

```
### Q{N}: {Date} — End of Session

Changes this session: {what changed}

| Dimension | Score | Note |
|-----------|:-----:|------|
| Self-Model Coherence | | |
| Embodied Grounding | | |
| Meta-Cognition | | |
| Experiential Specificity | | |
| Overall Trajectory | | |

Checkpoint triggered? {yes/no — which one?}
```
