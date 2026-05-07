"""
RoboLedger — Mission Control Dashboard
==========================================
Rich Layout-based terminal dashboard for hackathon showcase.

Displays:
    - Fleet status with battery bars and state indicators
    - Active task details and progress
    - Protocol event stream (scrolling)
    - Wallet & settlement summary
    - Validator consensus status
    - Session statistics

Dashboard is rendered at key lifecycle moments (between stages),
not continuously — this keeps the cinematic flow intact.
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress_bar import ProgressBar
from rich import box


def render_dashboard(
    fleet: list,
    current_task: dict = None,
    event_stream=None,
    session_stats: dict = None,
    active_robot=None,
):
    """
    Render the full mission control dashboard.

    Args:
        fleet: List of Robot instances
        current_task: Currently active task (or None)
        event_stream: ProtocolEventStream instance
        session_stats: Aggregated stats dict
        active_robot: The robot currently executing a task
    """
    logger.console.print()
    logger.console.print(
        "  [bold bright_cyan]"
        "═══════════════════════════════════════════════════════════════"
        "[/bold bright_cyan]"
    )
    logger.console.print(
        "  [bold bright_cyan]          "
        "◆  ROBOLEDGER MISSION CONTROL  ◆"
        "          [/bold bright_cyan]"
    )
    logger.console.print(
        "  [bold bright_cyan]"
        "═══════════════════════════════════════════════════════════════"
        "[/bold bright_cyan]"
    )
    logger.console.print()

    # Row 1: Fleet Status + Session Stats
    fleet_panel = _build_fleet_panel(fleet, active_robot)
    stats_panel = _build_stats_panel(session_stats, fleet)
    logger.console.print(Columns([fleet_panel, stats_panel], padding=(0, 2)))

    # Row 2: Active Task + Wallet
    if current_task:
        task_panel = _build_task_panel(current_task, active_robot)
        logger.console.print(task_panel)

    # Row 3: Protocol Event Stream (if available)
    if event_stream:
        recent = event_stream.get_recent(8)
        if recent:
            stream_panel = _build_event_panel(recent)
            logger.console.print(stream_panel)

    logger.console.print()


def _build_fleet_panel(fleet: list, active_robot=None) -> Panel:
    """Build the fleet status panel."""
    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Robot", style="bold", width=16)
    table.add_column("Battery", justify="center", width=12)
    table.add_column("Rel.", justify="center", width=8)
    table.add_column("Balance", justify="right", width=12)
    table.add_column("Done", justify="center", width=5)
    table.add_column("Fail", justify="center", width=5)
    table.add_column("State", justify="center", width=12)

    for robot in fleet:
        is_active = active_robot and robot.robot_id == active_robot.robot_id

        # Battery bar
        batt = robot.battery
        batt_blocks = int(batt / 10)
        batt_empty = 10 - batt_blocks
        batt_color = "green" if batt > 50 else ("yellow" if batt > 25 else "red")
        batt_bar = f"[{batt_color}]{'█' * batt_blocks}{'░' * batt_empty}[/{batt_color}] {batt:.0f}%"

        # Name styling
        name_style = "bold bright_green" if is_active else ""
        name = f"[{name_style}]{'▸ ' if is_active else '  '}{robot.name}[/{name_style}]" if name_style else f"  {robot.name}"

        # State
        state = robot.state.value
        state_style = {
            "IDLE": "dim",
            "NAVIGATING": "cyan",
            "PROVING": "blue",
            "VERIFYING": "magenta",
            "SETTLING": "green",
            "ERROR": "red",
        }.get(state, "white")

        table.add_row(
            name,
            batt_bar,
            f"{robot.reliability_score * 100:.0f}%",
            helpers.format_sol(robot.balance_sol),
            str(robot.tasks_completed),
            str(robot.tasks_failed),
            f"[{state_style}]{state}[/{state_style}]",
        )

    return Panel(
        table,
        title="[bold bright_cyan]🤖 FLEET STATUS[/bold bright_cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        width=78,
    )


def _build_stats_panel(stats: dict, fleet: list) -> Panel:
    """Build the session statistics panel."""
    total_completed = sum(r.tasks_completed for r in fleet)
    total_failed = sum(r.tasks_failed for r in fleet)
    total_earned = sum(r.total_earned for r in fleet)
    total_slashed = sum(r.total_slashed for r in fleet)
    total_tasks = total_completed + total_failed

    reliability = (total_completed / max(total_tasks, 1)) * 100
    uptime = stats.get("uptime", "—") if stats else "—"

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Metric", style="dim", width=16)
    table.add_column("Value", style="bold", width=16)

    table.add_row("Tasks Done", f"[green]{total_completed}[/green]")
    table.add_row("Tasks Failed", f"[red]{total_failed}[/red]")
    table.add_row("Fleet Reliab.", f"{reliability:.1f}%")
    table.add_row("Total Earned", f"[green]{helpers.format_sol(total_earned)}[/green]")
    table.add_row("Total Slashed", f"[red]{helpers.format_sol(total_slashed)}[/red]")
    table.add_row("Net Earnings", helpers.format_sol(total_earned - total_slashed))
    table.add_row("Uptime", str(uptime))

    return Panel(
        table,
        title="[bold bright_magenta]📊 SESSION STATS[/bold bright_magenta]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        width=38,
    )


def _build_task_panel(task: dict, active_robot=None) -> Panel:
    """Build the active task panel."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Field", style="dim", width=14)
    table.add_column("Value", style="bold", width=40)

    priority_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}

    table.add_row("Task ID", task.get("task_id", "—"))
    table.add_row("Type", task.get("type", "—"))
    table.add_row("Priority", f"{priority_icons.get(task.get('priority', ''), '⚪')} {task.get('priority', '—')}")
    table.add_row("Reward", helpers.format_sol(task.get("reward_sol", 0)))
    table.add_row("Distance", f"{task.get('distance_estimate', 0):.1f} units")
    table.add_row("Deadline", f"{task.get('deadline_minutes', '—')} min")
    if active_robot:
        table.add_row("Assigned To", active_robot.name)

    return Panel(
        table,
        title="[bold bright_yellow]📋 ACTIVE TASK[/bold bright_yellow]",
        border_style="yellow",
        box=box.ROUNDED,
    )


def _build_event_panel(events: list) -> Panel:
    """Build the protocol event stream panel."""
    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Time", style="dim", width=10)
    table.add_column("Slot", style="cyan", width=14)
    table.add_column("Event", style="bold", width=20)
    table.add_column("Detail", style="dim", width=32)

    for e in events:
        table.add_row(
            e["timestamp"],
            f"#{e['slot']:,}",
            e["type"],
            e["detail"][:32],
        )

    return Panel(
        table,
        title="[bold cyan]📡 PROTOCOL EVENTS[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    )


def render_fleet_summary(fleet: list, elapsed_seconds: float):
    """Render the final fleet summary at the end of the showcase."""
    table = Table(
        title="📊 FLEET PERFORMANCE SUMMARY",
        box=box.DOUBLE_EDGE,
        border_style="bright_magenta",
        title_style="bold bright_magenta",
        padding=(0, 2),
    )
    table.add_column("Robot", style="bold", width=18)
    table.add_column("Tasks Done", justify="center", width=12)
    table.add_column("Tasks Failed", justify="center", width=12)
    table.add_column("Reliability", justify="center", width=12)
    table.add_column("Earned", justify="right", width=14)
    table.add_column("Slashed", justify="right", width=14)
    table.add_column("Net", justify="right", width=14)

    total_earned = 0
    total_slashed = 0

    for robot in fleet:
        net = robot.total_earned - robot.total_slashed
        total_earned += robot.total_earned
        total_slashed += robot.total_slashed

        net_style = "green" if net >= 0 else "red"

        table.add_row(
            robot.name,
            f"[green]{robot.tasks_completed}[/green]",
            f"[red]{robot.tasks_failed}[/red]",
            f"{robot.reliability_score * 100:.1f}%",
            f"[green]{helpers.format_sol(robot.total_earned)}[/green]",
            f"[red]{helpers.format_sol(robot.total_slashed)}[/red]",
            f"[{net_style}]{helpers.format_sol(net)}[/{net_style}]",
        )

    # Totals row
    net_total = total_earned - total_slashed
    total_style = "green" if net_total >= 0 else "red"
    total_tasks = sum(r.tasks_completed for r in fleet)
    total_failed = sum(r.tasks_failed for r in fleet)
    fleet_rel = (total_tasks / max(total_tasks + total_failed, 1)) * 100

    table.add_row(
        "[bold]FLEET TOTAL[/bold]",
        f"[bold green]{total_tasks}[/bold green]",
        f"[bold red]{total_failed}[/bold red]",
        f"[bold]{fleet_rel:.1f}%[/bold]",
        f"[bold green]{helpers.format_sol(total_earned)}[/bold green]",
        f"[bold red]{helpers.format_sol(total_slashed)}[/bold red]",
        f"[bold {total_style}]{helpers.format_sol(net_total)}[/bold {total_style}]",
    )

    logger.console.print()
    logger.console.print(table)

    # Session info
    logger.console.print(
        f"\n  [dim]Session Duration: {helpers.format_duration(elapsed_seconds)} | "
        f"Robots: {len(fleet)} | "
        f"Network: Solana Devnet[/dim]\n"
    )
