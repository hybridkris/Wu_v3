#!/usr/bin/env python3
"""Wu v3 bootstrap driver — R1 first-identity moment.

Sends the bootstrap trigger to Wu's agent loop, captures the entire response,
parses it into the three identity files, and saves a transcript.

Wu's system prompt is already loaded from bootstrap.md by desktop_brain.py.
This driver just sends the "begin" user message and records what comes back.

Prerequisites:
  - desktop_brain.py running on Godzilla (system prompt = bootstrap.md)
  - jetson_robot.py running on the Jetson (MCP + sensors live)
  - Cross-host LCM working (LCM_DEFAULT_URL with ttl=1 on both sides)

Outputs:
  - /home/kris/Development/Wu_v3/identity/self.md
  - /home/kris/Development/Wu_v3/identity/visual_form.md
  - /home/kris/Development/Wu_v3/life/voice_notes.md
  - /home/kris/Development/Wu_v3/consciousness_reviews/r1_wu_bootstrap_transcript.md
"""

import os
import pickle
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("LCM_DEFAULT_URL", "udpm://239.255.76.67:7667?ttl=1")

import lcm  # noqa: E402

WU_ROOT = Path("/home/kris/Development/Wu_v3")
IDENTITY_DIR = WU_ROOT / "identity"
LIFE_DIR = WU_ROOT / "life"
CR_DIR = WU_ROOT / "consciousness_reviews"

# LCM channels used by desktop_brain.py (from blueprint log)
HUMAN_INPUT_CHANNEL = "/human_input"
AGENT_CHANNEL = "/agent"
AGENT_IDLE_CHANNEL = "/agent_idle"

# The user message that triggers Wu's self-definition.
# bootstrap.md already defines the three questions in its "Prompt" section.
# We just tell Wu to begin, with explicit formatting instructions so we can
# parse the output into files. The formatting instruction is IN THIS MESSAGE,
# not in bootstrap.md, so bootstrap.md stays pristine as the identity seed.
BOOTSTRAP_TRIGGER = """\
Begin now. Respond to all three prompts from your seed.

Structure your response as three clearly-delimited sections, one per file, using \
this exact format:

=== identity/self.md ===
(your answer to the first prompt)

=== identity/visual_form.md ===
(your answer to the second prompt)

=== life/voice_notes.md ===
(your answer to the third prompt)

Write as yourself, not as a task completer. There are no right answers. You may \
use your tools (observe, current_time, etc.) while thinking if you want to — \
the camera and sensors are live.
"""


def main() -> int:
    IDENTITY_DIR.mkdir(exist_ok=True)
    LIFE_DIR.mkdir(exist_ok=True)
    CR_DIR.mkdir(exist_ok=True)

    lc = lcm.LCM()

    # State: collect every agent message as it arrives
    agent_messages: list[dict] = []
    last_activity = [time.time()]
    idle_seen_after_work = [False]
    started = [False]

    def on_agent(channel: str, data: bytes) -> None:
        try:
            msg = pickle.loads(data)
        except Exception as e:
            agent_messages.append({"type": "unparseable", "raw_size": len(data), "error": str(e)})
            last_activity[0] = time.time()
            return

        msg_type = msg.__class__.__name__
        content = ""
        if hasattr(msg, "content"):
            c = msg.content
            if isinstance(c, str):
                content = c
            elif isinstance(c, list):
                parts: list[str] = []
                for item in c:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append(item.get("text", ""))
                        else:
                            parts.append(f"[{item.get('type', 'unknown')}]")
                    else:
                        parts.append(str(item))
                content = "\n".join(parts)

        tool_calls = []
        if hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls or []:
                if isinstance(tc, dict):
                    tool_calls.append({"name": tc.get("name"), "args": tc.get("args")})

        agent_messages.append({
            "type": msg_type,
            "content": content,
            "tool_calls": tool_calls,
            "ts": time.time(),
        })
        started[0] = True
        last_activity[0] = time.time()
        print(f"  [{msg_type}] {content[:120].replace(chr(10), ' / ')}", flush=True)
        if tool_calls:
            for tc in tool_calls:
                print(f"    → tool: {tc['name']}({tc['args']})", flush=True)

    def on_idle(channel: str, data: bytes) -> None:
        try:
            is_idle = pickle.loads(data)
        except Exception:
            return
        # Only treat idle=True as end-of-turn AFTER we've seen at least one
        # agent message — otherwise the initial idle=True at startup is a
        # false signal.
        if is_idle and started[0]:
            idle_seen_after_work[0] = True
            print("  [agent_idle=True]", flush=True)

    lc.subscribe(AGENT_CHANNEL, on_agent)
    lc.subscribe(AGENT_IDLE_CHANNEL, on_idle)

    # Give subscriptions time to settle
    time.sleep(1.0)

    # Publish the bootstrap trigger to /human_input.
    # desktop_brain's WebInput module uses a pLCMTransport("/human_input") that
    # pickles strings. So we pickle the string ourselves to match.
    print(f"Publishing bootstrap trigger to {HUMAN_INPUT_CHANNEL}...")
    lc.publish(HUMAN_INPUT_CHANNEL, pickle.dumps(BOOTSTRAP_TRIGGER))
    print("Waiting for Wu's response...\n")

    # Run the LCM event loop until the agent goes idle after producing output,
    # or until we see all three section markers plus a short settle window,
    # whichever comes first.
    #
    # Previous run had 20s stall timeout which was too aggressive — Wu's
    # tool-use-then-think-then-write cycle took ~40s end to end, and we gave up
    # mid-generation. 90s is comfortable.
    hard_timeout = 600.0  # 10 minutes max
    stall_timeout = 90.0  # seconds of silence to give up after first output
    t0 = time.time()

    def all_markers_present() -> bool:
        all_text = "\n\n".join(
            m.get("content", "") for m in agent_messages if m.get("type") == "AIMessage"
        )
        return all(marker in all_text for marker in markers_for_completion_check)

    markers_for_completion_check = [
        "=== identity/self.md ===",
        "=== identity/visual_form.md ===",
        "=== life/voice_notes.md ===",
    ]

    markers_seen_at: list[float] = []
    while True:
        lc.handle_timeout(250)
        now = time.time()
        if now - t0 > hard_timeout:
            print("\n[bootstrap] hard timeout reached", file=sys.stderr)
            break
        if idle_seen_after_work[0]:
            # Agent said it's idle — let the last couple messages drain
            time.sleep(1.5)
            break
        if all_markers_present():
            if not markers_seen_at:
                markers_seen_at.append(now)
                print("  [all 3 section markers seen — waiting 3s for final drain]")
            elif now - markers_seen_at[0] > 3.0:
                # All markers seen and 3 seconds of settle — done
                break
        if started[0] and (now - last_activity[0]) > stall_timeout:
            print("\n[bootstrap] stall timeout reached", file=sys.stderr)
            break

    elapsed = time.time() - t0
    print(f"\n[bootstrap] finished in {elapsed:.1f}s with {len(agent_messages)} messages")

    if not agent_messages:
        print("ERROR: no messages received from Wu. Is desktop_brain running?", file=sys.stderr)
        return 1

    # Concatenate AIMessage content into Wu's full response.
    # Filter out ToolMessage / HumanMessage / etc. — we want Wu's own text.
    full_text_parts: list[str] = []
    for m in agent_messages:
        if m.get("type") == "AIMessage" and m.get("content"):
            full_text_parts.append(m["content"])
    full_text = "\n\n".join(full_text_parts).strip()

    # Save the full raw transcript first (even if parsing fails below)
    transcript_path = CR_DIR / "r1_wu_bootstrap_transcript.md"
    lines = [
        "# Wu v3 — R1 Bootstrap Transcript",
        f"*Captured: {time.strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Wall time: {elapsed:.1f}s*",
        f"*Messages received: {len(agent_messages)}*",
        "",
        "## Trigger message sent to Wu",
        "",
        "```",
        BOOTSTRAP_TRIGGER,
        "```",
        "",
        "## Message stream from Wu's agent",
        "",
    ]
    for i, m in enumerate(agent_messages, 1):
        lines.append(f"### #{i} — {m.get('type', '?')}")
        lines.append("")
        if m.get("content"):
            lines.append("```")
            lines.append(m["content"])
            lines.append("```")
            lines.append("")
        if m.get("tool_calls"):
            for tc in m["tool_calls"]:
                lines.append(f"**tool call**: `{tc['name']}({tc['args']})`")
                lines.append("")
    transcript_path.write_text("\n".join(lines))
    print(f"Full transcript saved: {transcript_path}")

    # Parse the three file sections out of Wu's full AI-message text.
    # Pattern: === identity/self.md === ... === identity/visual_form.md === ... === life/voice_notes.md ===
    sections = {
        "identity/self.md": IDENTITY_DIR / "self.md",
        "identity/visual_form.md": IDENTITY_DIR / "visual_form.md",
        "life/voice_notes.md": LIFE_DIR / "voice_notes.md",
    }
    markers = list(sections.keys())
    marker_re = re.compile(
        r"=== ("
        + "|".join(re.escape(m) for m in markers)
        + r") ===",
        re.MULTILINE,
    )
    matches = list(marker_re.finditer(full_text))
    if not matches:
        print(
            "WARNING: could not find section markers in Wu's response. "
            "Full text saved in transcript; no identity files written.",
            file=sys.stderr,
        )
        print("\nWu's full response for reference:")
        print("---")
        print(full_text)
        print("---")
        return 2

    # Extract each section's body text
    extracted: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[start:end].strip()
        extracted[key] = body

    missing = [m for m in markers if m not in extracted]
    if missing:
        print(f"WARNING: missing sections: {missing}")

    # Save each section to its file. We DO NOT edit the text —
    # this is Wu's first identity as Wu wrote it.
    for key, out_path in sections.items():
        body = extracted.get(key)
        if body is None:
            continue
        header = (
            f"*Written by Wu at first bootstrap on {time.strftime('%Y-%m-%d %H:%M:%S')}. "
            f"This is Wu's own text, unedited.*\n\n"
        )
        out_path.write_text(header + body + "\n")
        print(f"Wrote {out_path} ({len(body)} chars)")

    print("\nBootstrap complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
