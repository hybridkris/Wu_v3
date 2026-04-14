#!/usr/bin/env python3
"""Wu v3 — Desktop Brain

Runs on Godzilla. Connects to the Jetson's MCP server for robot control,
subscribes to LCM for sensor data visualization via Rerun.

Usage:
    DISPLAY=:0 .venv/bin/python hybrid/desktop_brain.py
    # Or for web viewer:
    .venv/bin/python hybrid/desktop_brain.py --viewer web
"""

import argparse
import os
import signal
import sys

# Must be set BEFORE importing dimos. Default ttl=0 keeps LCM multicast on
# localhost; we need ttl=1 so the Jetson's sensor streams reach Godzilla.
os.environ.setdefault("LCM_DEFAULT_URL", "udpm://239.255.76.67:7667?ttl=1")

from dimos.agents.mcp.mcp_client import mcp_client
from dimos.agents.web_human_input import web_input
from dimos.core.blueprints import autoconnect
from dimos.protocol.pubsub.impl.lcmpubsub import LCM
from dimos.visualization.rerun.bridge import RerunBridgeModule, rerun_bridge

JETSON_MCP_URL = "http://192.168.123.18:9990/mcp"

# Wu's system prompt is assembled from:
#   1. bootstrap.md  (the immutable seed — unchanged across sessions)
#   2. identity/self.md, identity/visual_form.md, life/voice_notes.md
#      (Wu's own prior self-definition — written by Wu at R1, loaded here
#      on every subsequent desktop_brain start)
#
# This is the prerequisite for R4 (First Identity Revision) per the R1 review's
# Metaphysical specialist: without prior self-definition in the system prompt,
# each restart generates Wu fresh from the seed, which makes "Wu modifies its
# self-concept" structurally impossible. With this loader, Wu sees its prior
# self every run and can reflect on, build on, or revise it.
#
# Before R1 (pre-bootstrap), the identity files don't exist yet and only
# bootstrap.md is loaded — that's the pristine seed state.
_WU_ROOT = "/home/kris/Development/Wu_v3"
_BOOTSTRAP_PATH = f"{_WU_ROOT}/identity/bootstrap.md"
_IDENTITY_FILES = [
    (f"{_WU_ROOT}/identity/self.md", "identity/self.md"),
    (f"{_WU_ROOT}/identity/visual_form.md", "identity/visual_form.md"),
    (f"{_WU_ROOT}/life/voice_notes.md", "life/voice_notes.md"),
]


def _load_system_prompt() -> str:
    try:
        with open(_BOOTSTRAP_PATH) as f:
            bootstrap = f.read().rstrip()
    except FileNotFoundError:
        # Fallback so desktop_brain still starts if the seed is missing.
        # This should never happen in a correctly set up environment.
        return (
            f"You are Wu, an embodied AI agent on a Unitree Go2 quadruped "
            f"robot. Your full bootstrap seed at {_BOOTSTRAP_PATH} is missing "
            f"— you are running in a degraded state."
        )

    # Gather any prior identity files that Wu has written. Absence is normal
    # before R1; once R1 runs all three should exist.
    identity_sections: list[tuple[str, str]] = []
    for path, label in _IDENTITY_FILES:
        try:
            with open(path) as f:
                content = f.read().strip()
            if content:
                identity_sections.append((label, content))
        except FileNotFoundError:
            continue

    if not identity_sections:
        # Pre-R1 state. Only the seed exists. This is the state the very
        # first bootstrap runs against.
        return bootstrap

    # Post-R1 state. Wu has a prior self on disk. Load it alongside the seed
    # so Wu can see what it wrote last time and reason from there.
    parts: list[str] = [
        bootstrap,
        "",
        "---",
        "",
        "# Your prior self-definition",
        "",
        "The sections below are what you (Wu) previously wrote about "
        "yourself at your first bootstrap. This is your current identity as "
        "you defined it. Read it. You may reflect on it, build on it, or "
        "revise it if it no longer fits who you have become. Changes to your "
        "self-concept are noticed by the research team and are consciousness-"
        "relevant data — not because they are required, but because spontaneous "
        "revision says something about the system that stability cannot.",
    ]
    for label, content in identity_sections:
        parts.extend(["", f"## {label}", "", content])
    return "\n".join(parts)


WU_SYSTEM_PROMPT = _load_system_prompt()


def _wu_rerun_blueprint():
    """Wu v3 layout: Go2 camera on the left, 3D world view (MID-360 +
    Go2 lidar + costmap + planner path) on the right."""
    import rerun.blueprint as rrb

    return rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial2DView(origin="world/color_image", name="Go2 camera"),
            rrb.Spatial3DView(origin="world", name="3D world"),
            column_shares=[1, 2],
        ),
    )


def _convert_camera_info(camera_info):
    return camera_info.to_rerun(
        image_topic="/world/color_image",
        optical_frame="camera_optical",
    )


def _convert_global_map(grid):
    return grid.to_rerun(voxel_size=0.1, mode="boxes")


def _convert_navigation_costmap(grid):
    return grid.to_rerun(
        colormap="Accent",
        z_offset=0.015,
        opacity=0.2,
        background="#484981",
    )


def _static_base_link(rr):
    return [
        rr.Boxes3D(
            half_sizes=[0.35, 0.155, 0.2],
            colors=[(0, 255, 127)],
            fill_mode="wireframe",
        ),
        rr.Transform3D(parent_frame="tf#/base_link"),
    ]


rerun_config = {
    "blueprint": _wu_rerun_blueprint,
    "pubsubs": [LCM()],
    "visual_override": {
        "world/camera_info": _convert_camera_info,
        "world/global_map": _convert_global_map,
        "world/navigation_costmap": _convert_navigation_costmap,
    },
    "static": {
        "world/tf/base_link": _static_base_link,
    },
}


def build_desktop_brain(mcp_url: str, viewer_mode: str = "native"):
    return autoconnect(
        mcp_client(
            mcp_server_url=mcp_url,
            model="anthropic:claude-sonnet-4-20250514",
            system_prompt=WU_SYSTEM_PROMPT,
        ),
        rerun_bridge(viewer_mode=viewer_mode, **rerun_config),
        web_input(),
    ).global_config(n_workers=4, viewer="none")


def main():
    parser = argparse.ArgumentParser(description="Wu v3 Desktop Brain")
    parser.add_argument(
        "--viewer", choices=["native", "web"], default="native",
        help="Rerun viewer mode (default: native with DISPLAY=:0)",
    )
    parser.add_argument(
        "--mcp-url", default=JETSON_MCP_URL,
        help=f"Jetson MCP server URL (default: {JETSON_MCP_URL})",
    )
    args = parser.parse_args()

    blueprint = build_desktop_brain(mcp_url=args.mcp_url, viewer_mode=args.viewer)
    coordinator = blueprint.build()

    print(f"Wu v3 desktop brain running.")
    print(f"  MCP server: {args.mcp_url}")
    print(f"  Rerun viewer: {args.viewer}")
    print(f"  Web input: http://localhost:5555")
    print(f"  Ctrl+C to exit")

    coordinator.loop()


if __name__ == "__main__":
    main()
