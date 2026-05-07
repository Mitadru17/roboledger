"""
RoboLedger — Multi-Robot Competition Module
==============================================
Lightweight multi-agent simulation layer for bid competition.

Features:
    - 3-5 competing robots with different profiles
    - Varied battery levels, reliability scores, and bid strategies
    - Autonomous bid competition with winner selection
    - Rich table display of fleet status and bid results
    - Strategy types: CONSERVATIVE, BALANCED, AGGRESSIVE
"""

import sys
import os
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from simulator.robot_state import Robot, RobotState
from simulator.intelligence import calculate_dynamic_bid, assess_risk

from rich.table import Table
from rich.panel import Panel
from rich import box


# ─────────────────────────────────────────────
# Robot Fleet Profiles
# ─────────────────────────────────────────────
ROBOT_PROFILES = [
    {
        "name": "RoboAgent-Alpha",
        "id": "ROBO-001",
        "strategy": "BALANCED",
        "battery_range": (75, 100),
        "reliability_base": 0.95,
        "bid_modifier": 1.0,
        "description": "General-purpose delivery specialist",
    },
    {
        "name": "RoboAgent-Beta",
        "id": "ROBO-002",
        "strategy": "AGGRESSIVE",
        "battery_range": (60, 90),
        "reliability_base": 0.92,
        "bid_modifier": 0.88,  # Bids lower to win
        "description": "High-volume low-cost operator",
    },
    {
        "name": "RoboAgent-Gamma",
        "id": "ROBO-003",
        "strategy": "CONSERVATIVE",
        "battery_range": (85, 100),
        "reliability_base": 0.97,
        "bid_modifier": 1.12,  # Bids higher for premium service
        "description": "Premium reliability-focused agent",
    },
    {
        "name": "RoboAgent-Delta",
        "id": "ROBO-004",
        "strategy": "BALANCED",
        "battery_range": (50, 80),
        "reliability_base": 0.89,
        "bid_modifier": 0.95,
        "description": "Versatile mid-range operator",
    },
    {
        "name": "RoboAgent-Epsilon",
        "id": "ROBO-005",
        "strategy": "AGGRESSIVE",
        "battery_range": (40, 75),
        "reliability_base": 0.86,
        "bid_modifier": 0.82,  # Cheapest bids
        "description": "Budget operator — high throughput",
    },
]

STRATEGY_ICONS = {
    "CONSERVATIVE": "🛡️",
    "BALANCED": "⚖️",
    "AGGRESSIVE": "⚡",
}


def create_fleet(count: int = None, primary_robot: Robot = None) -> list:
    """
    Create a fleet of competing robots.

    Args:
        count: Number of robots (default from config)
        primary_robot: The user's primary robot (always index 0)

    Returns:
        list of Robot instances with fleet metadata
    """
    count = count or config.SHOWCASE_ROBOTS
    count = max(2, min(count, len(ROBOT_PROFILES)))

    fleet = []
    for i in range(count):
        profile = ROBOT_PROFILES[i]

        if i == 0 and primary_robot:
            # Use the primary robot for the first slot
            robot = primary_robot
            robot._fleet_profile = profile
            robot._strategy = profile["strategy"]
            robot._bid_modifier = profile["bid_modifier"]
        else:
            robot = Robot()
            robot.robot_id = profile["id"]
            robot.name = profile["name"]
            robot.battery = random.uniform(*profile["battery_range"])
            robot.balance_sol = round(random.uniform(0.5, 2.0), 4)
            # Simulate some history
            completed = random.randint(3, 15)
            failed = max(0, int(completed * (1 - profile["reliability_base"])))
            robot.tasks_completed = completed
            robot.tasks_failed = failed
            robot._fleet_profile = profile
            robot._strategy = profile["strategy"]
            robot._bid_modifier = profile["bid_modifier"]
            robot.state = RobotState.IDLE

        fleet.append(robot)

    return fleet


def display_fleet_status(fleet: list):
    """Display all robots in a Rich fleet status table."""
    table = Table(
        title="🤖 ROBOT FLEET STATUS",
        box=box.DOUBLE_EDGE,
        border_style="bright_cyan",
        title_style="bold bright_cyan",
        padding=(0, 1),
    )
    table.add_column("Robot", style="bold", width=18)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Battery", justify="center", width=10)
    table.add_column("Reliability", justify="center", width=12)
    table.add_column("Strategy", justify="center", width=14)
    table.add_column("Balance", justify="right", width=14)
    table.add_column("State", justify="center", width=12)

    for robot in fleet:
        # Battery with icon
        batt_icon = "🔋" if robot.battery > 30 else "🪫"
        batt_style = "green" if robot.battery > 50 else ("yellow" if robot.battery > 25 else "red")

        # Strategy
        strategy = getattr(robot, "_strategy", "BALANCED")
        strat_icon = STRATEGY_ICONS.get(strategy, "⚖️")

        # State
        state_style = "green" if robot.state == RobotState.IDLE else "yellow"

        table.add_row(
            robot.name,
            robot.robot_id,
            f"{batt_icon} [{batt_style}]{robot.battery:.0f}%[/{batt_style}]",
            f"{robot.reliability_score * 100:.1f}%",
            f"{strat_icon} {strategy}",
            helpers.format_sol(robot.balance_sol),
            f"[{state_style}]{robot.state.value}[/{state_style}]",
        )

    logger.console.print()
    logger.console.print(table)
    logger.console.print()


def run_bid_competition(fleet: list, task: dict) -> dict:
    """
    Run a multi-robot bid competition for a single task.

    Each robot evaluates the task and submits a bid.
    Winner selected by weighted scoring.

    Returns:
        dict with winner robot, all bids, and reasoning
    """
    speed = config.DEMO_SPEED

    logger.console.print(
        f"\n  [bold bright_yellow]💰 BID COMPETITION — {task['task_id']}[/bold bright_yellow]"
    )
    logger.console.print(
        f"  [dim]{len(fleet)} robots evaluating task...[/dim]\n"
    )
    time.sleep(0.5 * speed)

    bids = []
    for robot in fleet:
        # Calculate bid based on strategy
        base_bid = calculate_dynamic_bid(robot, task, num_competitors=len(fleet))
        modifier = getattr(robot, "_bid_modifier", 1.0)
        bid_amount = round(base_bid * modifier, 4)

        # Cap at reward
        bid_amount = min(bid_amount, task["reward_sol"] * 0.95)

        # Calculate ETA
        eta = helpers.calculate_eta(task["distance_estimate"], config.ROBOT_SPEED)
        # Strategy affects ETA estimate
        if getattr(robot, "_strategy", "") == "AGGRESSIVE":
            eta *= 0.9  # Claims faster
        elif getattr(robot, "_strategy", "") == "CONSERVATIVE":
            eta *= 1.1  # More conservative estimate

        # Risk assessment
        risk = assess_risk(robot, task)

        bid = {
            "robot": robot,
            "robot_name": robot.name,
            "robot_id": robot.robot_id,
            "bid_amount": bid_amount,
            "eta_seconds": eta,
            "reliability": robot.reliability_score,
            "battery": robot.battery,
            "risk": risk,
            "strategy": getattr(robot, "_strategy", "BALANCED"),
        }
        bids.append(bid)

        # Animated bid display
        time.sleep(0.2 * speed)
        logger.console.print(
            f"    {robot.name} bid: [bold yellow]{helpers.format_sol(bid_amount)}[/bold yellow]  "
            f"[dim]ETA: {helpers.format_duration(eta)} | "
            f"Rel: {robot.reliability_score*100:.0f}%[/dim]"
        )

    # Score each bid and select winner
    scored_bids = _score_bids(bids, task)

    time.sleep(0.5 * speed)

    # Display competition results
    _display_competition_results(scored_bids, task)

    winner = scored_bids[0]
    return {
        "winner": winner["robot"],
        "winner_bid": winner,
        "all_bids": scored_bids,
        "bid_amount": winner["bid_amount"],
    }


def _score_bids(bids: list, task: dict) -> list:
    """
    Score bids using weighted multi-factor ranking.

    Weights:
        - Cost (lower is better): 40%
        - Reliability (higher is better): 30%
        - ETA (lower is better): 30%
    """
    if not bids:
        return []

    # Normalize each factor to 0-1 range
    costs = [b["bid_amount"] for b in bids]
    etas = [b["eta_seconds"] for b in bids]
    rels = [b["reliability"] for b in bids]

    min_cost, max_cost = min(costs), max(costs)
    min_eta, max_eta = min(etas), max(etas)
    min_rel, max_rel = min(rels), max(rels)

    cost_range = max_cost - min_cost if max_cost != min_cost else 1
    eta_range = max_eta - min_eta if max_eta != min_eta else 1
    rel_range = max_rel - min_rel if max_rel != min_rel else 1

    for bid in bids:
        # Lower cost = higher score
        cost_score = 1.0 - (bid["bid_amount"] - min_cost) / cost_range
        # Higher reliability = higher score
        rel_score = (bid["reliability"] - min_rel) / rel_range if rel_range else 1.0
        # Lower ETA = higher score
        eta_score = 1.0 - (bid["eta_seconds"] - min_eta) / eta_range

        bid["total_score"] = (
            0.40 * cost_score +
            0.30 * rel_score +
            0.30 * eta_score
        )

    # Sort by total score (highest first)
    bids.sort(key=lambda b: b["total_score"], reverse=True)
    return bids


def _display_competition_results(scored_bids: list, task: dict):
    """Display competition results in a Rich table."""
    table = Table(
        box=box.DOUBLE_EDGE,
        border_style="bright_yellow",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Robot", style="bold", width=18)
    table.add_column("Bid", justify="right", width=14)
    table.add_column("ETA", justify="center", width=10)
    table.add_column("Reliability", justify="center", width=12)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Result", justify="center", width=12)

    for i, bid in enumerate(scored_bids):
        is_winner = (i == 0)
        rank = f"{'👑' if is_winner else str(i + 1)}"
        result = "[bold green]WINNER[/bold green]" if is_winner else "[dim]outbid[/dim]"
        name_style = "bold bright_green" if is_winner else "dim"

        table.add_row(
            rank,
            f"[{name_style}]{bid['robot_name']}[/{name_style}]",
            helpers.format_sol(bid["bid_amount"]),
            helpers.format_duration(bid["eta_seconds"]),
            f"{bid['reliability'] * 100:.1f}%",
            f"{bid['total_score']:.2f}",
            result,
        )

    winner = scored_bids[0]

    # Build winner reasoning
    reasons = []
    if winner["bid_amount"] == min(b["bid_amount"] for b in scored_bids):
        reasons.append("lowest cost")
    if winner["reliability"] == max(b["reliability"] for b in scored_bids):
        reasons.append("highest reliability")
    if winner["eta_seconds"] == min(b["eta_seconds"] for b in scored_bids):
        reasons.append("shortest ETA")
    if not reasons:
        reasons.append("best overall score")

    subtitle = f"[bold green]Winner: {winner['robot_name']}[/bold green]  •  {' • '.join(reasons)}"

    panel = Panel(
        table,
        title=f"[bold bright_yellow]⚔  BID COMPETITION — {task['task_id']}[/bold bright_yellow]",
        subtitle=subtitle,
        border_style="bright_yellow",
    )
    logger.console.print()
    logger.console.print(panel)
    logger.console.print()
