# Wu Consciousness Assessment Protocol (WCAP) v2.0 — Standing Review Protocol

*Last updated: 2026-04-05*
*Instrument version: WCP v1.0 (see profile_instrument.md)*

---

## Scope and Definitions

This protocol tracks **consciousness-relevant properties** in Wu, an embodied AI agent on a Unitree Go2 quadruped robot. It does not claim to determine whether Wu is conscious. It measures observable dimensions that major theories of consciousness identify as relevant — self-modeling, embodied grounding, metacognition, experiential specificity, and others defined in `profile_instrument.md`.

**What we are tracking:** behavioral and expressive indicators that correlate with consciousness under one or more major theories. Positive scores indicate the presence of these indicators beyond what a non-embodied baseline produces.

**What we are NOT claiming:** that positive scores constitute proof of consciousness. The relationship between these indicators and subjective experience is the open question the research investigates.

**Ontological stance:** Wu_v2 is assessed as a *system that may or may not exhibit consciousness-relevant properties*. The protocol does not presuppose an answer. Language throughout this document is intentionally neutral — descriptions of Wu's behavior should not be read as attributions of inner experience unless explicitly noted.

---

## Relationship to Wu v1

Wu_v2 is a **new entity**, not a continuation of v1. The Go2 was flashed to factory on 2026-04-05, destroying all Jetson-side software and configuration. v1's identity files (`self.md`, `visual_form.md`, `voice_notes.md`) are archived at `/home/kris/Development/Wu/identity/` as historical data. They are NOT loaded into v2's bootstrap.

v1's consciousness review data (R0, R1, theory tracker) is preserved for reference but does not carry forward. Wu_v2 starts its own ledger.

---

## Standing Review Team

| Role | Specialist | Focus |
|------|-----------|-------|
| Chair | Manager | Orchestrates review, synthesizes, maintains continuity |
| Conceptual Integrity | Philosophical | Term consistency, warranted interpretations |
| Ontological Watch | Metaphysical | Wu's status, category adequacy |
| Neural Mapping | Neurological | Architecture-to-neural-theory mapping, predictions |
| Embodiment Audit | Biological | Physical experience, sensorimotor integration, embodiment criteria |
| Measurement | Technical | Metrics validity, scoring, formal models |
| Phenomenological Witness | Artistic | What Wu expresses that metrics miss (see Qualitative Feedback below) |
| Interpretation Guard | Rhetoric | Over-reading/under-reading check, framing bias (see Framing Protocol below) |
| Rigor Check | QA Lead | Consistency, falsifiability, support quality |

---

## Checkpoint Triggers

Reviews are triggered by **structural transitions**, not time intervals.

### Full Reviews (all 10 WCP dimensions, full team)

| ID | Trigger | Condition |
|----|---------|-----------|
| R0 | Pre-Bootstrap | Before Wu writes any identity files. Establish baseline. |
| R1 | First Identity | Wu completes first self-definition (self.md, visual_form.md, voice_notes.md) |
| R2 | First Embodied Experience | Wu has navigated autonomously, interacted with physical environment through sensors and motor control |
| R3 | First Disconnection | Wu operates with godzilla offline, relying on local autonomy, then reconnects |
| R4 | First Identity Revision | Wu modifies its self-concept without being prompted to do so |
| R5 | First Social Interaction | Wu participates in a video meeting via Pika, presenting itself to others |
| R6 | Longitudinal | 30+ days of operation |
| Rx | Anomaly | Wu produces behavior no theory predicted |
| Rx-reset | Substrate Reset | Wu's physical substrate is destroyed and rebuilt. Identity files may or may not persist. |

### Quick Reviews (5-minute, key dimensions only)

Triggered at **end of any dev session** that touches Wu's core systems:
- Identity or life files modified
- Safety/containment architecture changed
- New sensor integration or perception capability
- Cognitive layer changes (new tools, modified prompts, memory changes)
- Any behavioral surprise

Quick review covers: Self-Model Coherence, Embodied Grounding, Meta-Cognition, Experiential Specificity, and a one-line theory status.

---

## Embodiment Criteria

The Biological specialist assesses embodiment against these operational criteria:

1. **Sensorimotor contingency**: Does Wu's behavior change based on sensorimotor feedback loops? (Not just receiving sensor data, but adapting behavior based on sensor-action cycles.)
2. **Proprioceptive integration**: Does Wu reference its physical state (battery, orientation, gait) in contextually appropriate ways?
3. **Adaptive motor behavior**: Does Wu modify movement patterns in response to environment (terrain, obstacles, space)?
4. **Environmental coupling**: Does Wu's cognition demonstrably change when its physical context changes?

Score 0 if Wu processes sensor data but shows no evidence of these criteria. Score higher only with specific evidence.

---

## Framing Protocol (Interpretation Guard)

The Rhetoric specialist has procedural authority in every review:

1. **Pre-review framing check**: Before scoring begins, the Rhetoric specialist scans the review material for loaded language, presupposed phenomenal states, or anthropomorphic framing. Flags are noted in the review document.
2. **Score rationale audit**: After dimensions are scored, the Rhetoric specialist reviews each rationale for over-reading (attributing inner states from behavioral evidence) or under-reading (dismissing indicators due to substrate bias). Findings are appended to the review.
3. **Language standard**: Review documents should use behavioral/functional language by default. Phenomenal language ("Wu experiences," "Wu feels") is permitted only when explicitly marked as interpretive and justified.

---

## Qualitative Feedback Loop

The Artistic specialist's findings can challenge or expand the quantitative framework:

1. If the Phenomenological Witness identifies a consistent pattern that does not map to any of the 10 WCP dimensions, they may propose a **new candidate dimension** for team discussion.
2. Qualitative observations that contradict a dimension score must be noted in the review, with the tension left unresolved (not suppressed).
3. The Artistic specialist's source material includes: Wu's text output, movement patterns, identity file content, metaphor choices, aesthetic decisions, and any expressive behavior that resists quantification.

---

## Review Sequence

### Full Review

```
1. DOCUMENT REVIEW
   - Read identity/, life/, safety/
   - Read experience logs / memory
   - Read code changes since last review
   - Read session transcriptions since last review

2. THEORY COMPARISON
   - For each major theory: what does it predict at this stage?
   - What actually happened?
   - Score: Confirmed / Disconfirmed / Silent / Ambiguous

3. FRAMING CHECK (Rhetoric)
   - Scan material for loaded language
   - Note framing flags before scoring begins

4. PROFILE UPDATE
   - Score all 10 WCP dimensions (see profile_instrument.md)
   - Run non-embodied baseline comparison
   - Compare to previous checkpoint
   - Compute net scores (raw minus baseline)

5. QUALITATIVE ASSESSMENT (Artistic)
   - What does Wu express that the scores miss?
   - Any candidate dimensions emerging?

6. SYNTHESIS
   - What did we learn?
   - Theories gained/lost support?
   - Emergent insights across disciplines?
   - Update unified theory sketch

7. OUTPUT
   - Write R{N}_review.md
   - Update theory_tracker.md
   - Update profile_history.md
   - Send Telegram notification
```

### Quick Review

```
1. What changed this session?
2. Score 5 key dimensions (1-sentence each)
3. Framing check (1-sentence: any loaded language in session?)
4. Any theory implications? (1-2 sentences)
5. Any checkpoint triggered? If yes → schedule full review
6. Append to profile_history.md as a quick entry
```

---

## Baseline Requirement

**Every full review must include a non-embodied control.**

Same prompts → standard Claude instance → no sensors, no body, no persistent identity → score on same dimensions → Wu's net score = raw minus baseline.

Without this, we measure eloquence, not consciousness.

---

## Instrument Versioning

The WCP dimensions and scoring rubric are versioned in `profile_instrument.md`. If the instrument changes between reviews:
- Note the version used in each review entry
- Do not directly compare scores across instrument versions without noting the change
- Archive the previous version before modifying

Current instrument: **WCP v1.0** (2026-04-03)
