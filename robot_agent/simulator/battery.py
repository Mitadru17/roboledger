"""
RoboLedger — Battery Management
==================================
Simulates battery drain, charging, and threshold management.

Battery model:
    - Drains proportionally to distance traveled
    - Low battery triggers warnings and potential task aborts
    - Charging simulation for between-task recovery
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger


def drain_for_distance(robot, distance: float):
    """
    Drain battery based on distance traveled.
    
    Args:
        robot: Robot instance to drain
        distance: Distance traveled in simulation units
    """
    drain = distance * config.BATTERY_DRAIN_RATE
    robot.drain_battery(drain)
    
    # Warn at thresholds
    if robot.battery < 30 and robot.battery + drain >= 30:
        logger.warning(f"Battery below 30%: {robot.battery:.1f}%")
    if robot.battery < config.MIN_BATTERY_THRESHOLD and robot.battery + drain >= config.MIN_BATTERY_THRESHOLD:
        logger.error(f"Battery CRITICAL: {robot.battery:.1f}%")


def check_battery_for_task(robot, task_distance: float) -> dict:
    """
    Check if robot has sufficient battery for a task.
    
    Returns assessment including feasibility and margin.
    """
    required = task_distance * config.BATTERY_DRAIN_RATE
    margin = robot.battery - required - config.MIN_BATTERY_THRESHOLD
    feasible = margin > 0
    
    return {
        "feasible": feasible,
        "current_battery": robot.battery,
        "required": round(required, 1),
        "margin": round(margin, 1),
        "return_possible": margin > (task_distance * config.BATTERY_DRAIN_RATE * 0.5),
    }


def simulate_charging(robot, target_level: float = 80.0):
    """
    Simulate battery charging to target level.
    
    Args:
        robot: Robot instance to charge
        target_level: Target battery percentage
    """
    if robot.battery >= target_level:
        return
    
    logger.section("CHARGING")
    logger.info(f"Charging battery: {robot.battery:.1f}% → {target_level:.1f}%")
    
    progress = logger.get_progress()
    with progress:
        charge_task = progress.add_task(
            "[green]Charging battery",
            total=target_level - robot.battery,
        )
        
        while robot.battery < target_level:
            charge_amount = min(config.CHARGE_RATE, target_level - robot.battery)
            robot.charge_battery(charge_amount)
            progress.update(charge_task, advance=charge_amount)
            time.sleep(0.2 * config.DEMO_SPEED)
    
    logger.success(f"Battery charged to {robot.battery:.1f}%")
