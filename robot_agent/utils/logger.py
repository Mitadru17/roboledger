"""
RoboLedger — Rich Logger
=========================
Cinematic terminal logging using Python Rich library.
Provides themed panels, colored output, timestamps, and file logging.

Architecture Note:
    All modules use this logger for consistent, beautiful terminal output.
    The logger creates both terminal output (Rich) and file logs (plain text).
"""

import os
import sys
import logging
from datetime import datetime

# Force UTF-8 output on Windows to support emoji and box-drawing characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ─────────────────────────────────────────────
# Custom Theme for RoboLedger
# ─────────────────────────────────────────────
ROBO_THEME = Theme({
    "info":       "cyan",
    "warning":    "yellow",
    "error":      "bold red",
    "success":    "bold green",
    "robot":      "bold magenta",
    "solana":     "bold blue",
    "proof":      "bold cyan",
    "settlement": "bold green",
    "task":       "bold yellow",
    "nav":        "bold white",
    "battery":    "bold green",
    "battery_low":"bold red",
    "banner":     "bold bright_magenta",
    "dim":        "dim white",
})

# Global Rich console instance — force_terminal enables ANSI on Windows
console = Console(theme=ROBO_THEME, record=True, force_terminal=True)

# ─────────────────────────────────────────────
# File Logger Setup
# ─────────────────────────────────────────────
def _setup_file_logger():
    """Set up plain text file logging to logs/ directory."""
    if not config.LOG_TO_FILE:
        return None
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config.LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"roboledger_{timestamp}.log")
    
    file_logger = logging.getLogger("roboledger")
    file_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    file_logger.addHandler(handler)
    
    return file_logger

_file_logger = _setup_file_logger()


# ─────────────────────────────────────────────
# Logging Functions
# ─────────────────────────────────────────────
def _log_to_file(level: str, message: str):
    """Write to file log if enabled."""
    if _file_logger:
        getattr(_file_logger, level.lower(), _file_logger.info)(message)


def info(message: str, icon: str = "ℹ️"):
    """Log an informational message."""
    console.print(f"  {icon}  [info]{message}[/info]")
    _log_to_file("info", message)


def success(message: str, icon: str = "✅"):
    """Log a success message."""
    console.print(f"  {icon}  [success]{message}[/success]")
    _log_to_file("info", f"SUCCESS: {message}")


def warning(message: str, icon: str = "⚠️"):
    """Log a warning message."""
    console.print(f"  {icon}  [warning]{message}[/warning]")
    _log_to_file("warning", message)


def error(message: str, icon: str = "❌"):
    """Log an error message."""
    console.print(f"  {icon}  [error]{message}[/error]")
    _log_to_file("error", message)


def robot(message: str, icon: str = "🤖"):
    """Log a robot-specific message."""
    console.print(f"  {icon}  [robot]{message}[/robot]")
    _log_to_file("info", f"ROBOT: {message}")


def solana(message: str, icon: str = "🔗"):
    """Log a Solana-related message."""
    console.print(f"  {icon}  [solana]{message}[/solana]")
    _log_to_file("info", f"SOLANA: {message}")


def task(message: str, icon: str = "📋"):
    """Log a task-related message."""
    console.print(f"  {icon}  [task]{message}[/task]")
    _log_to_file("info", f"TASK: {message}")


def nav(message: str, icon: str = "🧭"):
    """Log a navigation message."""
    console.print(f"  {icon}  [nav]{message}[/nav]")
    _log_to_file("info", f"NAV: {message}")


def proof(message: str, icon: str = "🔐"):
    """Log a proof-related message."""
    console.print(f"  {icon}  [proof]{message}[/proof]")
    _log_to_file("info", f"PROOF: {message}")


def settlement(message: str, icon: str = "💸"):
    """Log a settlement message."""
    console.print(f"  {icon}  [settlement]{message}[/settlement]")
    _log_to_file("info", f"SETTLEMENT: {message}")


# ─────────────────────────────────────────────
# Rich Panels & Banners
# ─────────────────────────────────────────────
def banner(title: str, subtitle: str = "", style: str = "bold bright_magenta"):
    """Display a large themed banner panel."""
    content = Text(title, justify="center", style=style)
    if subtitle:
        content.append(f"\n{subtitle}", style="dim white")
    panel = Panel(
        content,
        box=box.DOUBLE_EDGE,
        border_style="bright_magenta",
        padding=(1, 4),
    )
    console.print(panel)
    _log_to_file("info", f"=== {title} === {subtitle}")


def section(title: str, style: str = "bold cyan"):
    """Display a section divider."""
    console.print()
    console.rule(f"[{style}] {title} ", style=style)
    console.print()
    _log_to_file("info", f"--- {title} ---")


def status_panel(title: str, items: dict, border_style: str = "cyan"):
    """Display a status panel with key-value pairs."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Key", style="dim", width=20)
    table.add_column("Value", style="bold")
    
    for key, value in items.items():
        table.add_row(str(key), str(value))
    
    panel = Panel(table, title=f"[bold]{title}[/bold]", border_style=border_style, box=box.ROUNDED)
    console.print(panel)
    _log_to_file("info", f"{title}: {items}")


def task_banner(task_data: dict):
    """Display a prominent task information banner."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Field", style="bold yellow", width=16)
    table.add_column("Value", style="white")
    
    for key, value in task_data.items():
        table.add_row(str(key), str(value))
    
    panel = Panel(
        table,
        title="[bold yellow]📋 TASK DETECTED[/bold yellow]",
        border_style="yellow",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    )
    console.print(panel)
    _log_to_file("info", f"TASK DETECTED: {task_data}")


def verification_panel(validators: list, consensus: bool):
    """Display BFT verification results panel."""
    table = Table(show_header=True, box=box.SIMPLE_HEAVY, padding=(0, 2))
    table.add_column("Validator", style="cyan", width=16)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Response", justify="right", width=10)
    
    for v in validators:
        status_icon = "✅ APPROVED" if v["approved"] else "❌ REJECTED"
        status_style = "green" if v["approved"] else "red"
        table.add_row(
            v["name"],
            f"[{status_style}]{status_icon}[/{status_style}]",
            f"{v['time_ms']}ms"
        )
    
    consensus_text = "[bold green]✅ CONSENSUS REACHED[/bold green]" if consensus else "[bold red]❌ CONSENSUS FAILED[/bold red]"
    
    panel = Panel(
        table,
        title="[bold cyan]🔒 BFT VERIFICATION[/bold cyan]",
        subtitle=consensus_text,
        border_style="cyan" if consensus else "red",
        box=box.DOUBLE_EDGE,
    )
    console.print(panel)


def settlement_panel(details: dict):
    """Display settlement confirmation panel."""
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("", style="bold", width=20)
    table.add_column("", style="bold green")
    
    for key, value in details.items():
        table.add_row(str(key), str(value))
    
    panel = Panel(
        table,
        title="[bold green]💰 SETTLEMENT CONFIRMED[/bold green]",
        border_style="green",
        box=box.DOUBLE_EDGE,
        padding=(0, 1),
    )
    console.print(panel)


def get_progress():
    """Return a Rich progress bar instance for navigation simulation."""
    return Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TextColumn("[bold]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def print_summary(stats: dict):
    """Display final session summary."""
    table = Table(
        title="📊 SESSION SUMMARY",
        box=box.DOUBLE_EDGE,
        border_style="bright_magenta",
        padding=(0, 2),
        title_style="bold bright_magenta",
    )
    table.add_column("Metric", style="bold cyan", width=24)
    table.add_column("Value", style="bold white", justify="right", width=20)
    
    for key, value in stats.items():
        table.add_row(str(key), str(value))
    
    console.print()
    console.print(table)
    console.print()
