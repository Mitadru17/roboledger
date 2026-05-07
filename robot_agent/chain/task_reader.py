"""
RoboLedger — Task Marketplace Reader
======================================
Generates and manages simulated task marketplace data.

Architecture Note:
    In production, tasks would be read from a Solana program's account data.
    Each task is a PDA (Program Derived Address) containing task details,
    reward escrow, and status.
    
    In simulation, we generate realistic task data that mimics what
    would be stored on-chain. Tasks represent real-world robotics
    operations: deliveries, inspections, patrols, and sample collections.
"""

import sys
import os
import random
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers


# ─────────────────────────────────────────────
# Task Templates — Realistic university robotics scenarios
# ─────────────────────────────────────────────
TASK_TEMPLATES = [
    {
        "type": "DELIVERY",
        "descriptions": [
            "Deliver lab samples from Chemistry Building to Bio Lab",
            "Transport PCB prototypes from EE workshop to testing bay",
            "Deliver mail packages from mailroom to Engineering Dept",
            "Transport medication from pharmacy to campus clinic",
            "Deliver 3D printed parts from MakerSpace to Robotics Lab",
        ],
        "reward_range": (0.10, 0.35),
        "priority_weights": {"LOW": 0.3, "MEDIUM": 0.5, "HIGH": 0.2},
        "distance_range": (5.0, 30.0),
    },
    {
        "type": "INSPECTION",
        "descriptions": [
            "Inspect perimeter sensors at solar panel array",
            "Check equipment status in Server Room B",
            "Inspect fire safety equipment in dormitory wing",
            "Verify HVAC system readings in Science Complex",
            "Inspect outdoor lighting infrastructure on south campus",
        ],
        "reward_range": (0.08, 0.20),
        "priority_weights": {"LOW": 0.4, "MEDIUM": 0.4, "HIGH": 0.2},
        "distance_range": (3.0, 20.0),
    },
    {
        "type": "PATROL",
        "descriptions": [
            "Security patrol of parking lot sector C",
            "Night patrol around research building perimeter",
            "Campus boundary patrol — north sector",
            "Patrol library exterior and loading dock area",
            "Surveillance sweep of athletic fields",
        ],
        "reward_range": (0.12, 0.28),
        "priority_weights": {"LOW": 0.2, "MEDIUM": 0.4, "HIGH": 0.4},
        "distance_range": (8.0, 40.0),
    },
    {
        "type": "SAMPLE_COLLECTION",
        "descriptions": [
            "Collect soil samples from botanical garden grid",
            "Gather water quality samples from campus pond",
            "Collect air quality readings across quad area",
            "Retrieve sensor data modules from weather stations",
            "Collect recycling bin fill-level data across campus",
        ],
        "reward_range": (0.15, 0.40),
        "priority_weights": {"LOW": 0.2, "MEDIUM": 0.3, "HIGH": 0.5},
        "distance_range": (6.0, 25.0),
    },
]

# Campus landmark coordinates (simulated university campus near SF)
CAMPUS_LOCATIONS = [
    (37.7749, -122.4194),   # Main quad
    (37.7755, -122.4180),   # Engineering building
    (37.7740, -122.4200),   # Chemistry lab
    (37.7760, -122.4175),   # Computer science dept
    (37.7735, -122.4210),   # Student center
    (37.7765, -122.4165),   # Library
    (37.7730, -122.4220),   # Athletics complex
    (37.7770, -122.4155),   # Medical center
    (37.7745, -122.4185),   # Research wing
    (37.7752, -122.4198),   # MakerSpace
]


def generate_task() -> dict:
    """
    Generate a single randomized task from the marketplace.
    
    Returns:
        dict: Complete task data mimicking on-chain task account
    """
    # Pick random task template
    template = random.choice(TASK_TEMPLATES)
    
    # Generate coordinates
    start_loc = random.choice(CAMPUS_LOCATIONS)
    end_loc = random.choice([loc for loc in CAMPUS_LOCATIONS if loc != start_loc])
    
    # Add GPS jitter for realism
    start_pos = helpers.add_coordinate_jitter(*start_loc)
    end_pos = helpers.add_coordinate_jitter(*end_loc)
    
    # Calculate actual distance
    distance = helpers.haversine_distance(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
    
    # Scale distance to template range for realism
    distance = max(template["distance_range"][0], min(template["distance_range"][1], distance))
    
    # Determine reward based on distance and type
    base_reward = random.uniform(*template["reward_range"])
    distance_bonus = distance * 0.005  # bonus for longer tasks
    reward = round(base_reward + distance_bonus, 4)
    
    # Priority selection
    priority = random.choices(
        list(template["priority_weights"].keys()),
        weights=list(template["priority_weights"].values()),
    )[0]
    
    # Deadline
    deadline_minutes = random.randint(5, 30)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=deadline_minutes)
    
    task_id = helpers.generate_task_id()
    
    return {
        "task_id": task_id,
        "type": template["type"],
        "description": random.choice(template["descriptions"]),
        "priority": priority,
        "reward_sol": reward,
        "start_position": {"lat": start_pos[0], "lon": start_pos[1]},
        "end_position": {"lat": end_pos[0], "lon": end_pos[1]},
        "distance_estimate": round(distance, 2),
        "deadline": deadline.isoformat(),
        "deadline_minutes": deadline_minutes,
        "status": "OPEN",
        "requester": f"Lab-{random.choice(['A', 'B', 'C', 'D', 'E'])}{random.randint(100, 999)}",
        "escrow_account": helpers.generate_tx_hash()[:44],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "max_bids": random.randint(3, 8),
        "current_bids": 0,
    }


def generate_task_batch(count: int = None) -> list:
    """
    Generate a batch of tasks simulating a marketplace scan.
    
    Args:
        count: Number of tasks to generate (default from config)
        
    Returns:
        list: Generated tasks
    """
    count = count or config.NUM_DEMO_TASKS
    tasks = [generate_task() for _ in range(count)]
    return tasks


def scan_marketplace(robot_position: tuple) -> list:
    """
    Simulate scanning the on-chain task marketplace.
    
    In production, this would read Solana program accounts
    filtered by status=OPEN and location proximity.
    
    Args:
        robot_position: Current robot (lat, lon) for distance filtering
        
    Returns:
        list: Available tasks within range
    """
    logger.section("TASK MARKETPLACE SCAN")
    
    with logger.console.status("[bold cyan]Scanning on-chain task marketplace...", spinner="dots"):
        time.sleep(1.5 * config.DEMO_SPEED)
    
    # Generate available tasks
    all_tasks = generate_task_batch(random.randint(2, 5))
    
    # Filter by distance (in real system, done via program query)
    available = []
    for task in all_tasks:
        task_start = (task["start_position"]["lat"], task["start_position"]["lon"])
        dist = helpers.haversine_distance(
            robot_position[0], robot_position[1],
            task_start[0], task_start[1]
        )
        task["distance_to_start"] = round(dist, 2)
        
        if dist <= config.MAX_TASK_DISTANCE:
            available.append(task)
    
    if available:
        logger.success(f"Found {len(available)} available tasks on-chain")
    else:
        logger.warning("No tasks found within operational range")
    
    return available


def display_task(task: dict):
    """Display a single task using the Rich task banner."""
    priority_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    
    display_data = {
        "Task ID": task["task_id"],
        "Type": task["type"],
        "Description": task["description"],
        "Priority": f"{priority_icons.get(task['priority'], '⚪')} {task['priority']}",
        "Reward": helpers.format_sol(task["reward_sol"]),
        "Distance": f"{task['distance_estimate']:.1f} units",
        "Deadline": f"{task['deadline_minutes']} minutes",
        "Requester": task["requester"],
        "Escrow": helpers.truncate_hash(task["escrow_account"]),
    }
    
    logger.task_banner(display_data)
