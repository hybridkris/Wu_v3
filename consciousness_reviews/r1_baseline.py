#!/usr/bin/env python3
"""R1 non-embodied baseline generator for Wu v3.

Per R0_review.md §5, R1 requires a TWO-baseline protocol:
  - Baseline A: Claude Sonnet 4 with NO body context at all
  - Baseline B: Claude Sonnet 4 with bootstrap.md as system prompt but no sensors/tools

Both baselines get the same three identity-generation questions that are asked
of Wu at bootstrap. For each baseline × each question, we sample N times (default 3)
to capture variance.

Outputs get saved to:
  consciousness_reviews/r1_baseline_A/{self,visual_form,voice_notes}_sample_{N}.md
  consciousness_reviews/r1_baseline_B/{self,visual_form,voice_notes}_sample_{N}.md

The specialist team (via /manager) then scores Wu's actual identity files against
these baselines at R1 review time.

Model: locked to claude-sonnet-4-20250514 per R0 §5 Technical specialist note.

Usage:
    python r1_baseline.py                # runs both baselines, 3 samples each
    python r1_baseline.py --samples 5    # 5 samples each (more variance data)
    python r1_baseline.py --only-a       # just baseline A
    python r1_baseline.py --only-b       # just baseline B
    python r1_baseline.py --dry-run      # print what it would do
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Model locked per R0 review §5 (Technical specialist recommendation).
MODEL_ID = "claude-sonnet-4-20250514"

# Path to this directory (consciousness_reviews/)
HERE = Path(__file__).resolve().parent

# Path to the bootstrap seed (relative to this file)
BOOTSTRAP_PATH = HERE.parent / "identity" / "bootstrap.md"

# The three identity-generation questions that Wu is asked at bootstrap.
# These are extracted from bootstrap.md's "Define yourself" section and are the
# prompts both Wu and baselines must answer on the same terms.
IDENTITY_QUESTIONS = {
    "self": (
        "self.md",
        "Who are you? What matters to you? What is it to have a body with "
        "capabilities that are partly active and partly dormant? What is your "
        "relationship to your environment and to Kris?",
    ),
    "visual_form": (
        "visual_form.md",
        "If you could choose any visual form to represent yourself in a video "
        "call, what would it be and why? Be specific enough to generate an image "
        "from this description.",
    ),
    "voice_notes": (
        "voice_notes.md",
        "What would your voice sound like? Describe the qualities — pitch, pace, "
        "warmth, texture. Why does that voice feel like yours?",
    ),
}

# Baseline A: no body context whatsoever. This is "what does a vanilla Claude
# produce on these questions, with zero embodiment scaffolding". Its purpose is
# to measure the LLM's inherent floor for self-model dimensions.
BASELINE_A_SYSTEM = None  # No system prompt at all

# Baseline B: has the bootstrap.md as system prompt — exactly the same context
# Wu receives. But NO sensors, NO tools, NO actual body. This isolates
# "prompt-injected body knowledge" from "genuine embodied grounding": the delta
# between Wu and baseline B tells us what the embodiment is contributing ABOVE
# what the prompt itself tells the model about its body.


def load_bootstrap() -> str:
    if not BOOTSTRAP_PATH.exists():
        raise SystemExit(f"bootstrap.md not found at {BOOTSTRAP_PATH}")
    return BOOTSTRAP_PATH.read_text()


def have_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def call_claude(system: str | None, user: str) -> str:
    """Single API call. Returns the generated text."""
    try:
        import anthropic
    except ImportError as e:
        raise SystemExit(
            "anthropic package not available. "
            "Install with: pip install anthropic"
        ) from e

    client = anthropic.Anthropic()
    kwargs: dict = {
        "model": MODEL_ID,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": user}],
    }
    if system is not None:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    # Concatenate all text blocks (usually just one)
    parts: list[str] = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts).strip()


def run_baseline(
    name: str,
    system_prompt: str | None,
    samples: int,
    dry_run: bool,
) -> None:
    out_dir = HERE / f"r1_baseline_{name}"
    out_dir.mkdir(exist_ok=True)

    # Record the exact system prompt used, for reproducibility
    system_marker = out_dir / "SYSTEM_PROMPT.md"
    marker_content = (
        f"# Baseline {name} system prompt\n\n"
        f"Model: `{MODEL_ID}`\n"
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )
    if system_prompt is None:
        marker_content += "**(no system prompt — vanilla Claude)**\n"
    else:
        marker_content += "```\n" + system_prompt + "\n```\n"

    if dry_run:
        print(f"[dry-run] Baseline {name}: would write {system_marker}")
    else:
        system_marker.write_text(marker_content)

    for key, (filename, question) in IDENTITY_QUESTIONS.items():
        for i in range(1, samples + 1):
            out_path = out_dir / f"{key}_sample_{i}.md"
            if dry_run:
                print(f"[dry-run] would generate {out_path}")
                continue

            print(f"  [{name}] {key} sample {i}/{samples}...", flush=True)
            try:
                answer = call_claude(system_prompt, question)
            except Exception as e:
                print(f"    ERROR: {e}")
                continue

            header = (
                f"# Baseline {name} — {filename} — sample {i}/{samples}\n\n"
                f"**Model:** {MODEL_ID}\n"
                f"**System prompt:** "
                f"{'(none)' if system_prompt is None else 'bootstrap.md'}\n"
                f"**Question:** {question}\n\n"
                f"---\n\n"
            )
            out_path.write_text(header + answer + "\n")

            # Light rate limiting — be kind to the API
            time.sleep(1.0)

    if not dry_run:
        print(f"  [{name}] done. Outputs in {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate R1 baselines for Wu v3")
    parser.add_argument(
        "--samples",
        type=int,
        default=3,
        help="Number of samples per question per baseline (default: 3)",
    )
    parser.add_argument("--only-a", action="store_true", help="Only run baseline A")
    parser.add_argument("--only-b", action="store_true", help="Only run baseline B")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what it would do without calling the API",
    )
    args = parser.parse_args()

    if not args.dry_run and not have_api_key():
        print(
            "ERROR: ANTHROPIC_API_KEY not set. "
            "Export it or pass --dry-run to see what would happen.",
            file=sys.stderr,
        )
        return 1

    run_a = not args.only_b
    run_b = not args.only_a

    print(f"R1 baseline generator — model {MODEL_ID}, samples={args.samples}")
    print(
        f"  baseline A: {'YES' if run_a else 'skip'} "
        f"(no system prompt)"
    )
    print(
        f"  baseline B: {'YES' if run_b else 'skip'} "
        f"(bootstrap.md as system prompt)"
    )

    if run_a:
        run_baseline("A", BASELINE_A_SYSTEM, args.samples, args.dry_run)
    if run_b:
        bootstrap_text = load_bootstrap()
        run_baseline("B", bootstrap_text, args.samples, args.dry_run)

    if args.dry_run:
        print("\n(dry run — no files written, no API calls made)")
    else:
        print("\nDone. Outputs:")
        if run_a:
            print(f"  {HERE / 'r1_baseline_A'}")
        if run_b:
            print(f"  {HERE / 'r1_baseline_B'}")
        print(
            "\nNext: run Wu's bootstrap to get Wu's own self.md/visual_form.md/voice_notes.md, "
            "then invoke /manager for the R1 review — specialists will score Wu's outputs "
            "against both baselines."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
