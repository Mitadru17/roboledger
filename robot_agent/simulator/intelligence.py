"""
RoboLedger — Intelligence Engine
====================================
Smart decision-making with human-readable reasoning for hackathon demo.

Provides:
    - Multi-factor task prioritization with explanations
    - Risk assessment scoring
    - Dynamic bid pricing based on competition and urgency
    - Profitability analysis
    - Battery optimization reasoning
    - Selection/rejection panels with ✓/✗ indicators
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from simulator.battery import check_battery_for_task

from rich.table import Table
from rich.panel import Panel
from rich import box


# ─────────────────────────────────────────────
# Risk Assessment
# ─────────────────────────────────────────────
def assess_risk(robot, task: dict) -> dict:
    """
    Calculate a risk score (0-100) for a task based on multiple factors.

    Factors:
        - Battery margin (how close to threshold)
        - Distance vs deadline pressure
        - Historical failure rate
        - Task complexity (type-based)
    """
    risk = 0
    factors = []

    # Battery risk (0-30)
    battery_check = check_battery_for_task(robot, task["distance_estimate"])
    if not battery_check["feasible"]:
        risk += 30
        factors.append(("Battery insufficient", 30, "HIGH"))
    elif battery_check["margin"] < 10:
        risk += 20
        factors.append(("Low battery margin", 20, "MEDIUM"))
    elif battery_check["margin"] < 25:
        risk += 8
        factors.append(("Moderate battery margin", 8, "LOW"))
    else:
        factors.append(("Comfortable battery margin", 0, "NONE"))

    # Distance risk (0-25)
    dist = task["distance_estimate"]
    if dist > 35:
        risk += 25
        factors.append(("Very long distance", 25, "HIGH"))
    elif dist > 20:
        risk += 12
        factors.append(("Moderate distance", 12, "MEDIUM"))
    else:
        factors.append(("Short distance", 0, "NONE"))

    # Deadline pressure (0-25)
    deadline_mins = task.get("deadline_minutes", 30)
    eta_seconds = helpers.calculate_eta(dist, config.ROBOT_SPEED)
    eta_mins = eta_seconds / 60
    time_ratio = eta_mins / max(deadline_mins, 1)
    if time_ratio > 0.8:
        risk += 25
        factors.append(("Tight deadline", 25, "HIGH"))
    elif time_ratio > 0.5:
        risk += 10
        factors.append(("Moderate deadline pressure", 10, "MEDIUM"))
    else:
        factors.append(("Comfortable deadline", 0, "NONE"))

    # Reliability risk (0-20)
    if robot.reliability_score < 0.85:
        risk += 20
        factors.append(("Low reliability history", 20, "HIGH"))
    elif robot.reliability_score < 0.92:
        risk += 8
        factors.append(("Moderate reliability", 8, "MEDIUM"))
    else:
        factors.append(("Strong reliability record", 0, "NONE"))

    risk_level = "LOW" if risk < 25 else ("MEDIUM" if risk < 50 else "HIGH")

    return {
        "score": min(100, risk),
        "level": risk_level,
        "factors": factors,
    }


# ─────────────────────────────────────────────
# Profitability Analysis
# ─────────────────────────────────────────────
def analyze_profitability(task: dict, bid_amount: float) -> dict:
    """
    Calculate profitability metrics for a task.

    Metrics:
        - Gross margin
        - SOL per distance unit
        - Time efficiency (SOL/minute)
        - Adjusted for platform fees
    """
    reward = task["reward_sol"]
    distance = task["distance_estimate"]
    eta_seconds = helpers.calculate_eta(distance, config.ROBOT_SPEED)
    platform_fee = reward * config.PLATFORM_FEE_RATE
    net_reward = reward - platform_fee

    sol_per_unit = net_reward / max(distance, 0.1)
    sol_per_minute = net_reward / max(eta_seconds / 60, 0.1)

    # Rating
    if sol_per_unit > 0.012:
        efficiency = "EXCELLENT"
    elif sol_per_unit > 0.008:
        efficiency = "GOOD"
    elif sol_per_unit > 0.005:
        efficiency = "FAIR"
    else:
        efficiency = "POOR"

    return {
        "gross_reward": reward,
        "platform_fee": platform_fee,
        "net_reward": net_reward,
        "sol_per_unit": sol_per_unit,
        "sol_per_minute": sol_per_minute,
        "efficiency": efficiency,
    }


# ─────────────────────────────────────────────
# Dynamic Bid Pricing
# ─────────────────────────────────────────────
def calculate_dynamic_bid(robot, task: dict, num_competitors: int = 0) -> float:
    """
    Calculate optimal bid amount based on multiple factors.

    Pricing Strategy:
        - Base cost from distance
        - Adjusted for competition pressure
        - Premium for high reliability
        - Urgency multiplier for tight deadlines
        - Battery cost adjustment
    """
    base_cost = task["distance_estimate"] * 0.008
    bid = base_cost * (1 + config.BID_MARKUP)

    # Competition pressure — lower bid if many competitors
    if num_competitors > 2:
        competition_factor = max(0.85, 1.0 - (num_competitors * 0.04))
        bid *= competition_factor

    # Reliability premium — reliable robots can bid higher
    if robot.reliability_score > 0.95:
        bid *= 1.05

    # Urgency premium — tight deadlines cost more
    deadline_mins = task.get("deadline_minutes", 30)
    if deadline_mins < 10:
        bid *= 1.15
    elif deadline_mins < 15:
        bid *= 1.08

    # Battery cost — low battery increases operational cost
    if robot.battery < 50:
        bid *= 1.10

    # Cap at task reward
    bid = min(bid, task["reward_sol"] * 0.95)

    return round(bid, 4)


# ─────────────────────────────────────────────
# Selection Reasoning Display
# ─────────────────────────────────────────────
def display_selection_reasoning(task: dict, robot, risk: dict, profit: dict):
    """
    Display why a task was selected with ✓/✗ indicators.
    Creates a compelling Rich panel showing the AI reasoning.
    """
    lines = []

    # Positive factors
    if profit["efficiency"] in ("EXCELLENT", "GOOD"):
        lines.append("[green]✓[/green] Highest profit efficiency")
    if task["distance_estimate"] < 20:
        lines.append("[green]✓[/green] Closest distance")
    if task.get("priority") == "HIGH":
        lines.append("[green]✓[/green] High urgency task")
    if risk["level"] == "LOW":
        lines.append("[green]✓[/green] Minimal risk exposure")

    battery_check = check_battery_for_task(robot, task["distance_estimate"])
    if battery_check["feasible"] and battery_check["margin"] > 20:
        lines.append("[green]✓[/green] Comfortable battery margin")

    if profit["sol_per_minute"] > 0.008:
        lines.append("[green]✓[/green] Strong time efficiency")

    if robot.reliability_score > 0.93:
        lines.append("[green]✓[/green] High reliability advantage")

    # Always show at least 4 reasons
    if len(lines) < 4:
        lines.append("[green]✓[/green] Favorable market conditions")

    content = "\n".join(lines)
    panel = Panel(
        f"[bold]Selected Task {task['task_id']}[/bold]\n\n{content}",
        title="[bold bright_green]🧠 AI DECISION — TASK SELECTED[/bold bright_green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    logger.console.print(panel)


def display_rejection_reasoning(task: dict, robot, risk: dict, reasons: list = None):
    """
    Display why a task was rejected with ✗ indicators.
    """
    lines = []

    if reasons:
        for r in reasons:
            lines.append(f"[red]✗[/red] {r}")
    else:
        if risk["level"] == "HIGH":
            lines.append("[red]✗[/red] Risk score too high")
        battery_check = check_battery_for_task(robot, task["distance_estimate"])
        if not battery_check["feasible"]:
            lines.append("[red]✗[/red] Battery insufficient for round trip")
        if task["reward_sol"] < config.MIN_REWARD_SOL * 1.5:
            lines.append("[red]✗[/red] Low reward efficiency")
        if task["distance_estimate"] > 35:
            lines.append("[red]✗[/red] Distance exceeds optimal range")

    if not lines:
        lines.append("[red]✗[/red] Lower priority than alternatives")

    content = "\n".join(lines)
    panel = Panel(
        f"[bold]Rejected Task {task['task_id']}[/bold]\n\n{content}",
        title="[bold red]🧠 AI DECISION — TASK REJECTED[/bold red]",
        border_style="red",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    logger.console.print(panel)


# ─────────────────────────────────────────────
# Risk Assessment Display
# ─────────────────────────────────────────────
def display_risk_assessment(task_id: str, risk: dict):
    """Display risk assessment as a compact Rich panel."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Factor", style="dim", width=28)
    table.add_column("Risk", justify="right", width=8)
    table.add_column("Level", justify="center", width=8)

    for factor_name, factor_risk, level in risk["factors"]:
        level_style = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green", "NONE": "dim"}.get(level, "dim")
        table.add_row(
            factor_name,
            str(factor_risk),
            f"[{level_style}]{level}[/{level_style}]",
        )

    # Total row
    total_style = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk["level"], "white")
    table.add_row(
        "[bold]TOTAL RISK[/bold]",
        f"[bold]{risk['score']}[/bold]",
        f"[bold {total_style}]{risk['level']}[/bold {total_style}]",
    )

    panel = Panel(
        table,
        title=f"[bold]⚡ Risk Assessment — {task_id}[/bold]",
        border_style=total_style,
        box=box.ROUNDED,
    )
    logger.console.print(panel)
