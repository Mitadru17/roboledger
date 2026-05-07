"""
RoboLedger — Navigation Simulator
====================================
Simulates robot movement between coordinates with realistic progress tracking.

Uses linear interpolation with GPS jitter for believable movement simulation.
Tracks waypoints, distance traveled, and provides Rich progress visualization.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from simulator.battery import drain_for_distance


def simulate_navigation(
    robot,
    start_pos: tuple,
    end_pos: tuple,
    task_id: str,
) -> dict:
    """
    Simulate robot navigation from start to end position.
    
    Features:
        - Waypoint-based interpolation
        - Real-time progress bar with Rich
        - Battery drain during movement
        - GPS coordinate jitter for realism
        - Waypoint recording for proof generation
    
    Args:
        robot: Robot instance (state + battery updated in-place)
        start_pos: (lat, lon) starting coordinates
        end_pos: (lat, lon) destination coordinates
        task_id: Task being executed
        
    Returns:
        dict: Navigation result with waypoints and status
    """
    logger.section("NAVIGATION")
    
    distance = helpers.haversine_distance(
        start_pos[0], start_pos[1], end_pos[0], end_pos[1]
    )
    eta = helpers.calculate_eta(distance, config.ROBOT_SPEED)
    
    logger.nav(f"Route planned: {distance:.2f} units | ETA: {helpers.format_duration(eta)}")
    logger.nav(f"From: {helpers.format_coordinates(*start_pos)}")
    logger.nav(f"  To: {helpers.format_coordinates(*end_pos)}")
    
    # Check battery feasibility
    battery_needed = distance * config.BATTERY_DRAIN_RATE
    if battery_needed > robot.battery:
        logger.error(f"Insufficient battery: need {battery_needed:.1f}% have {robot.battery:.1f}%")
        return {"success": False, "reason": "BATTERY_INSUFFICIENT", "waypoints": []}
    
    # Simulate movement with progress bar
    waypoints = [start_pos]
    num_steps = max(10, int(distance * 2))
    step_time = (eta / num_steps) * config.DEMO_SPEED
    
    progress = logger.get_progress()
    with progress:
        nav_task = progress.add_task(
            f"[cyan]Navigating to {task_id}",
            total=num_steps,
        )
        
        for step in range(num_steps):
            t = (step + 1) / num_steps
            
            # Interpolate position with jitter
            current_pos = helpers.interpolate_position(start_pos, end_pos, t)
            current_pos = helpers.add_coordinate_jitter(*current_pos, jitter=config.NAV_WAYPOINT_JITTER)
            
            # Update robot state
            robot.update_position(*current_pos)
            step_distance = distance / num_steps
            drain_for_distance(robot, step_distance)
            
            # Record waypoint every few steps
            if step % max(1, num_steps // 8) == 0 or step == num_steps - 1:
                waypoints.append(current_pos)
            
            # Update progress
            progress.update(nav_task, advance=1)
            time.sleep(step_time)
            
            # Check for battery abort
            if robot.is_battery_low:
                logger.warning(f"Battery critical at {robot.battery:.1f}%! Aborting navigation.")
                return {
                    "success": False,
                    "reason": "BATTERY_CRITICAL",
                    "waypoints": waypoints,
                    "progress": t,
                }
    
    # Snap to exact destination
    robot.update_position(*end_pos)
    waypoints.append(end_pos)
    
    total_distance = sum(
        helpers.haversine_distance(
            waypoints[i][0], waypoints[i][1],
            waypoints[i+1][0], waypoints[i+1][1]
        )
        for i in range(len(waypoints) - 1)
    )
    
    logger.success(f"Navigation complete! Traveled {total_distance:.2f} units")
    logger.nav(f"Final position: {helpers.format_coordinates(*end_pos)}")
    logger.nav(f"Battery remaining: {robot.battery:.1f}%")
    
    return {
        "success": True,
        "waypoints": waypoints,
        "distance_traveled": total_distance,
        "final_position": end_pos,
        "battery_remaining": robot.battery,
    }
