#!/usr/bin/env python3
"""Jetson-side: robot + nav + skills + MCP + MID-360. Stock dimos components.

Mirrored from /home/unitree/dimos/hybrid/jetson_robot.py on the Jetson.
The canonical live copy is on the Jetson; this mirror exists so changes
get tracked in git. Deploy with:

    scp hybrid/jetson_robot.py hybrid/wu_battery_publisher.py \\
        unitree@<jetson>:/home/unitree/dimos/hybrid/
    ssh unitree@<jetson> sudo systemctl restart jetson_robot.service
"""

# Install the /go2_battery LCM publisher BEFORE the blueprint is built, so
# the monkey-patch is in place when dimos materializes GO2Connection.start().
# See wu_battery_publisher.py for why this is a patch and not a side-car.
import wu_battery_publisher
wu_battery_publisher.install()

from dimos.agents.mcp.mcp_server import McpServer
from dimos.core.blueprints import autoconnect
from dimos.hardware.sensors.lidar.livox.module import Mid360, mid360_module
from dimos.mapping.costmapper import cost_mapper
from dimos.mapping.voxels import voxel_mapper
from dimos.navigation.frontier_exploration import wavefront_frontier_explorer
from dimos.navigation.replanning_a_star.module import replanning_a_star_planner
from dimos.robot.unitree.go2.connection import go2_connection
from dimos.robot.unitree.unitree_skill_container import unitree_skills
from dimos.web.websocket_vis.websocket_vis_module import websocket_vis

# Point the Mid360 module at our Jetson build of mid360_native.
# The nix-built default won't exist because we built via cmake.
_MID360_EXECUTABLE = "/home/unitree/build/mid360_native/cpp/result/bin/mid360_native"

jetson_robot = autoconnect(
    go2_connection(),
    mid360_module(
        host_ip="192.168.123.18",
        lidar_ip="192.168.123.20",
        frequency=10.0,
        enable_imu=True,
        frame_id="mid360_link",
        imu_frame_id="mid360_imu_link",
        cwd=None,
        executable=_MID360_EXECUTABLE,
        build_command=None,
    ),
    voxel_mapper(voxel_size=0.1),
    cost_mapper(),
    replanning_a_star_planner(),
    wavefront_frontier_explorer(),
    unitree_skills(),
    McpServer.blueprint(),
    websocket_vis(),
).remappings([
    # Keep Go2's internal lidar as the primary for nav (voxel_mapper/cost_mapper).
    # Publish MID-360 on a separate topic so it's available but doesn't clash.
    (Mid360, "lidar", "mid360_lidar"),
    (Mid360, "imu", "mid360_imu"),
]).global_config(
    n_workers=7,
    robot_model="unitree_go2",
    viewer="none",
    obstacle_avoidance=True,
)

if __name__ == "__main__":
    jetson_robot.build().loop()
