"""
RoboLedger — Webots Simulation Bridge
=========================================
JSON file-based communication layer between RoboLedger and Webots.

Architecture:
    RoboLedger writes robot_target.json  → Webots controller reads it
    Webots writes robot_position.json    → RoboLedger reads it

Coordinate Conversion:
    GPS lat/lon ↔ Webots meters (20m × 20m arena)
    - Webots X axis  → longitude offset
    - Webots Z axis  → latitude offset

All file I/O uses atomic writes and retry-on-read for Windows safety.
"""

import sys
import os
import json
import time
import math
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from simulator.battery import drain_for_distance


# ─────────────────────────────────────────────
# File Paths
# ─────────────────────────────────────────────
def _target_path(robot_index: int = 0) -> str:
    """Get path to target JSON file for a robot."""
    if robot_index == 0:
        return os.path.join(config.WEBOTS_DATA_DIR, "robot_target.json")
    return os.path.join(config.WEBOTS_DATA_DIR, f"robot_{robot_index}_target.json")


def _position_path(robot_index: int = 0) -> str:
    """Get path to position JSON file for a robot."""
    if robot_index == 0:
        return os.path.join(config.WEBOTS_DATA_DIR, "robot_position.json")
    return os.path.join(config.WEBOTS_DATA_DIR, f"robot_{robot_index}_position.json")


# ─────────────────────────────────────────────
# Coordinate Conversion
# ─────────────────────────────────────────────
def gps_to_webots(lat: float, lon: float) -> tuple:
    """
    Convert GPS lat/lon to Webots arena coordinates (meters).

    Returns:
        (x, z) in Webots world coordinates
    """
    x = (lon - config.WEBOTS_GPS_LON_CENTER) / config.WEBOTS_GPS_LON_HALF_RANGE * config.WEBOTS_ARENA_HALF
    z = (lat - config.WEBOTS_GPS_LAT_CENTER) / config.WEBOTS_GPS_LAT_HALF_RANGE * config.WEBOTS_ARENA_HALF
    # Clamp to arena bounds
    x = max(-config.WEBOTS_ARENA_HALF, min(config.WEBOTS_ARENA_HALF, x))
    z = max(-config.WEBOTS_ARENA_HALF, min(config.WEBOTS_ARENA_HALF, z))
    return (round(x, 3), round(z, 3))


def webots_to_gps(x: float, z: float) -> tuple:
    """
    Convert Webots arena coordinates to GPS lat/lon.

    Returns:
        (lat, lon) GPS coordinates
    """
    lat = config.WEBOTS_GPS_LAT_CENTER + (z / config.WEBOTS_ARENA_HALF) * config.WEBOTS_GPS_LAT_HALF_RANGE
    lon = config.WEBOTS_GPS_LON_CENTER + (x / config.WEBOTS_ARENA_HALF) * config.WEBOTS_GPS_LON_HALF_RANGE
    return (round(lat, 7), round(lon, 7))


# ─────────────────────────────────────────────
# Atomic JSON File I/O (Windows-safe)
# ─────────────────────────────────────────────
def _atomic_write_json(path: str, data: dict):
    """Write JSON atomically using temp file + rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dir_name = os.path.dirname(path)
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=dir_name)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        # On Windows, os.rename fails if target exists, so remove first
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp_path, path)
    except Exception:
        # Fallback: direct write
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def _safe_read_json(path: str, retries: int = 3) -> dict:
    """Read JSON with retries for partial-write safety."""
    for attempt in range(retries):
        try:
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            if attempt < retries - 1:
                time.sleep(0.05)
    return None


# ─────────────────────────────────────────────
# Target Writing
# ─────────────────────────────────────────────
def write_target(task_id: str, target_x: float, target_z: float,
                 status: str = "assigned", robot_index: int = 0):
    """
    Write target coordinates for Webots controller to consume.

    Args:
        task_id: Task being assigned
        target_x: Webots X coordinate (meters)
        target_z: Webots Z coordinate (meters)
        status: assigned | navigating | completed | cancelled
        robot_index: Robot index for multi-robot support
    """
    data = {
        "task_id": task_id,
        "target_x": target_x,
        "target_z": target_z,
        "status": status,
        "timestamp": int(time.time()),
    }
    _atomic_write_json(_target_path(robot_index), data)
    logger.info(f"[WEBOTS] Target written: ({target_x:.2f}, {target_z:.2f}) for {task_id}")


def clear_target(robot_index: int = 0):
    """Clear the target file (robot should stop)."""
    data = {
        "task_id": "",
        "target_x": 0.0,
        "target_z": 0.0,
        "status": "idle",
        "timestamp": int(time.time()),
    }
    _atomic_write_json(_target_path(robot_index), data)


# ─────────────────────────────────────────────
# Position Reading
# ─────────────────────────────────────────────
def read_position(robot_index: int = 0) -> dict:
    """
    Read current robot position from Webots controller.

    Returns:
        dict with x, z, battery, status, timestamp — or None if unavailable
    """
    return _safe_read_json(_position_path(robot_index))


def wait_for_webots(timeout: float = 10.0) -> bool:
    """Wait for Webots to start writing position data."""
    start = time.time()
    while time.time() - start < timeout:
        pos = read_position()
        if pos and "x" in pos:
            return True
        time.sleep(0.5)
    return False


# ─────────────────────────────────────────────
# Navigation via Webots (replaces simulate_navigation)
# ─────────────────────────────────────────────
def webots_navigate(robot, start_pos: tuple, end_pos: tuple, task_id: str) -> dict:
    """
    Navigate using real Webots simulation instead of interpolation.

    Drop-in replacement for simulate_navigation().
    Writes target → polls position → collects waypoints → returns result dict.

    Args:
        robot: Robot instance (state + battery updated in-place)
        start_pos: (lat, lon) starting GPS coordinates
        end_pos: (lat, lon) destination GPS coordinates
        task_id: Task being executed

    Returns:
        dict: Same format as simulate_navigation() result
    """
    logger.section("WEBOTS NAVIGATION")

    # Convert GPS to Webots coordinates
    target_x, target_z = gps_to_webots(end_pos[0], end_pos[1])
    start_x, start_z = gps_to_webots(start_pos[0], start_pos[1])

    total_distance = math.sqrt((target_x - start_x) ** 2 + (target_z - start_z) ** 2)
    logger.nav(f"[WEBOTS] Target: ({target_x:.2f}, {target_z:.2f}) | Distance: {total_distance:.2f}m")
    logger.nav(f"[WEBOTS] GPS: {helpers.format_coordinates(*end_pos)}")

    # Check battery feasibility
    gps_distance = helpers.haversine_distance(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
    battery_needed = gps_distance * config.BATTERY_DRAIN_RATE
    if battery_needed > robot.battery:
        logger.error(f"Insufficient battery: need {battery_needed:.1f}% have {robot.battery:.1f}%")
        return {"success": False, "reason": "BATTERY_INSUFFICIENT", "waypoints": []}

    # Check Webots is running
    logger.info("[WEBOTS] Waiting for simulation connection...")
    if not wait_for_webots(timeout=15.0):
        logger.warning("[WEBOTS] Simulation not detected — falling back to internal navigation")
        from simulator.navigation import _internal_navigate
        return _internal_navigate(robot, start_pos, end_pos, task_id)

    # Write target for Webots controller
    write_target(task_id, target_x, target_z, status="navigating")

    # Poll position and track progress
    waypoints = [start_pos]
    start_time = time.time()
    last_log_time = 0
    arrived = False

    progress = logger.get_progress()
    with progress:
        nav_task = progress.add_task(
            f"[cyan]🤖 WEBOTS → {task_id}",
            total=100,
        )

        while time.time() - start_time < config.WEBOTS_NAV_TIMEOUT:
            pos = read_position()
            if not pos or "x" not in pos:
                time.sleep(config.WEBOTS_POLL_INTERVAL)
                continue

            # Current position in Webots coords
            cur_x = pos["x"]
            cur_z = pos["z"]
            cur_gps = webots_to_gps(cur_x, cur_z)

            # Update robot state with real position
            robot.update_position(*cur_gps)

            # Distance remaining
            dx = target_x - cur_x
            dz = target_z - cur_z
            dist_remaining = math.sqrt(dx * dx + dz * dz)

            # Progress percentage
            pct = max(0, min(100, (1.0 - dist_remaining / max(total_distance, 0.01)) * 100))
            progress.update(nav_task, completed=int(pct))

            # Drain battery proportionally
            step_drain = (gps_distance * config.BATTERY_DRAIN_RATE) / max(total_distance / 0.2, 1)
            drain_for_distance(robot, gps_distance * 0.005)

            # Log position periodically
            now = time.time()
            if now - last_log_time > 1.5:
                logger.nav(
                    f"[WEBOTS] Position: ({cur_x:.2f}, {cur_z:.2f}) | "
                    f"Remaining: {dist_remaining:.2f}m | Battery: {robot.battery:.1f}%"
                )
                last_log_time = now

            # Record waypoints
            if len(waypoints) == 0 or waypoints[-1] != cur_gps:
                waypoints.append(cur_gps)

            # Check arrival
            if pos.get("status") == "arrived" or dist_remaining < config.WEBOTS_ARRIVAL_THRESHOLD:
                arrived = True
                progress.update(nav_task, completed=100)
                break

            # Battery abort
            if robot.is_battery_low:
                logger.warning(f"Battery critical at {robot.battery:.1f}%! Aborting navigation.")
                clear_target()
                return {
                    "success": False,
                    "reason": "BATTERY_CRITICAL",
                    "waypoints": waypoints,
                    "progress": pct / 100,
                }

            time.sleep(config.WEBOTS_POLL_INTERVAL)

    if not arrived:
        logger.error("[WEBOTS] Navigation timeout — robot did not reach destination")
        clear_target()
        return {"success": False, "reason": "TIMEOUT", "waypoints": waypoints}

    # Snap to destination
    robot.update_position(*end_pos)
    waypoints.append(end_pos)
    clear_target()

    total_traveled = sum(
        helpers.haversine_distance(
            waypoints[i][0], waypoints[i][1],
            waypoints[i + 1][0], waypoints[i + 1][1],
        )
        for i in range(len(waypoints) - 1)
    )

    logger.success(f"[WEBOTS] Navigation complete! Traveled {total_traveled:.2f} units")
    logger.nav(f"[WEBOTS] Final GPS: {helpers.format_coordinates(*end_pos)}")
    logger.nav(f"[WEBOTS] Battery remaining: {robot.battery:.1f}%")

    return {
        "success": True,
        "waypoints": waypoints,
        "distance_traveled": total_traveled,
        "final_position": end_pos,
        "battery_remaining": robot.battery,
    }


def initialize_webots_bridge():
    """Create the webots_data directory and initial files."""
    os.makedirs(config.WEBOTS_DATA_DIR, exist_ok=True)
    logger.success(f"[WEBOTS] Data directory: {config.WEBOTS_DATA_DIR}")

    # Write initial idle target
    clear_target()

    # Check if Webots is already running
    pos = read_position()
    if pos:
        logger.success("[WEBOTS] Simulation detected — position data available")
        return True
    else:
        logger.info("[WEBOTS] Waiting for Webots simulation to start...")
        logger.info("[WEBOTS] Open webots/worlds/roboledger_arena.wbt and press Play")
        return False
