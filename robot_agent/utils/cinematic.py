"""
RoboLedger — Cinematic Effects Module
=======================================
Animated terminal effects for hackathon showcase presentation.

Provides:
    - Character-by-character boot sequence
    - Animated stage transitions
    - Transaction propagation visuals
    - Validator vote animations
    - Protocol narration
    - Dramatic shutdown sequence
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box


# ─────────────────────────────────────────────
# Boot Sequence
# ─────────────────────────────────────────────
BOOT_CHECKS = [
    ("Initializing RoboLedger Protocol Engine", "v0.2.0"),
    ("Loading Ed25519 Cryptographic Module", "READY"),
    ("Connecting to Solana Devnet Cluster", "CONNECTED"),
    ("Bootstrapping BFT Validator Network", "5 NODES"),
    ("Initializing GPS Proof Subsystem", "ACTIVE"),
    ("Loading SwarmProof Consensus Module", "ONLINE"),
    ("Activating Escrow Settlement Engine", "ARMED"),
    ("Scanning Task Marketplace Registry", "SYNCED"),
    ("Deploying Autonomous Navigation Stack", "LOADED"),
    ("Starting Protocol Event Stream", "STREAMING"),
]

SHOWCASE_BANNER = r"""
 ╔══════════════════════════════════════════════════════════════════════╗
 ║                                                                      ║
 ║   ██████╗  ██████╗ ██████╗  ██████╗ ██╗     ███████╗██████╗  ██████╗ ║
 ║   ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║     ██╔════╝██╔══██╗██╔════╝ ║
 ║   ██████╔╝██║   ██║██████╔╝██║   ██║██║     █████╗  ██║  ██║██║  ███╗║
 ║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██║     ██╔══╝  ██║  ██║██║   ██║║
 ║   ██║  ██║╚██████╔╝██████╔╝╚██████╔╝███████╗███████╗██████╔╝╚██████╔╝║
 ║   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═════╝  ╚═════╝ ║
 ║                                                                      ║
 ║          ✦  DECENTRALIZED ROBOT ECONOMY — LIVE SHOWCASE  ✦          ║
 ║                                                                      ║
 ║    Autonomous Agents  •  Cryptographic Proofs  •  BFT Consensus     ║
 ║         Trustless Settlement  •  Solana Blockchain  •  DePIN         ║
 ║                                                                      ║
 ╚══════════════════════════════════════════════════════════════════════╝
"""


def animated_boot():
    """Display the cinematic boot sequence with system check animations."""
    speed = config.DEMO_SPEED

    # Flash the showcase banner
    logger.console.print(SHOWCASE_BANNER, style="bold bright_cyan")
    time.sleep(0.8 * speed)

    logger.console.print(
        "    [dim]v0.2.0  |  Hackathon Showcase Mode  |  Solana Devnet[/dim]\n"
    )
    time.sleep(0.4 * speed)

    # Boot sequence with animated checks
    logger.console.print("  [bold bright_white]◆ PROTOCOL BOOT SEQUENCE[/bold bright_white]\n")

    for check_name, status in BOOT_CHECKS:
        # Print the check name with dots animation
        logger.console.print(f"    [dim]▸[/dim] {check_name}", end="")

        # Animated dots
        for _ in range(random.randint(2, 4)):
            time.sleep(0.08 * speed)
            logger.console.print(".", end="")

        # Status
        time.sleep(0.05 * speed)
        logger.console.print(f" [bold green]✓ {status}[/bold green]")

    logger.console.print()
    logger.console.print(
        "  [bold bright_green]◆ ALL SYSTEMS OPERATIONAL[/bold bright_green]"
    )
    logger.console.print(
        "  [dim]Protocol ready for autonomous task execution[/dim]\n"
    )
    time.sleep(0.5 * speed)


# ─────────────────────────────────────────────
# Stage Transitions
# ─────────────────────────────────────────────
STAGE_NARRATIONS = {
    "SCANNING": "Querying on-chain task marketplace for open work orders...",
    "EVALUATING": "Running multi-factor AI analysis on candidate tasks...",
    "COMPETING": "Autonomous robots submitting competitive bids on-chain...",
    "NAVIGATING": "Executing autonomous navigation to task destination...",
    "PROVING": "Generating cryptographic GPS proof of task completion...",
    "VERIFYING": "SwarmProof BFT validators reaching distributed consensus...",
    "SETTLING": "Escrow smart contract releasing locked funds on-chain...",
    "FAILURE": "Anomaly detected — activating protocol failure handler...",
    "SLASHING": "Penalty protocol triggered — executing stake slashing...",
}


def stage_transition(stage: str, icon: str, detail: str = ""):
    """Display an animated stage transition with protocol narration."""
    speed = config.DEMO_SPEED

    # Divider with animated dots
    logger.console.print()
    dots = "─" * 50
    logger.console.print(f"  [dim bright_cyan]{dots}[/dim bright_cyan]")

    # Stage header
    msg = f"{icon}  {stage}"
    if detail:
        msg += f"  —  {detail}"
    logger.console.print(f"  [bold bright_cyan]{msg}[/bold bright_cyan]")

    # Narration
    narration = STAGE_NARRATIONS.get(stage.split(" ")[0].upper().rstrip("..."), "")
    if narration:
        logger.console.print(f"  [dim italic]{narration}[/dim italic]")

    logger.console.print()
    time.sleep(0.3 * speed)


# ─────────────────────────────────────────────
# Transaction Propagation Visual
# ─────────────────────────────────────────────
def tx_propagation(tx_hash: str, tx_type: str = "Settlement"):
    """Display animated transaction propagation across network nodes."""
    speed = config.DEMO_SPEED
    from utils.helpers import truncate_hash

    logger.console.print()
    logger.console.print(
        f"  [bold blue]⚡ TRANSACTION PROPAGATION — {tx_type.upper()}[/bold blue]"
    )

    # Simulate propagation across nodes
    nodes = ["Leader", "Validator-A", "Validator-B", "Validator-C", "Cluster"]
    for i, node in enumerate(nodes):
        time.sleep(0.15 * speed)
        progress = "━" * (i + 1) + "╸" + "╌" * (len(nodes) - i - 1)
        logger.console.print(
            f"    [cyan]{progress}[/cyan] [dim]{node}[/dim] [green]✓[/green]"
        )

    time.sleep(0.2 * speed)
    logger.console.print(
        f"  [bold green]✓ TX Finalized[/bold green]  [dim]{truncate_hash(tx_hash)}[/dim]"
    )
    logger.console.print()


# ─────────────────────────────────────────────
# Validator Vote Animation
# ─────────────────────────────────────────────
def animated_validator_vote(validator_name: str, approved: bool, time_ms: int):
    """Display a single validator vote with animation."""
    speed = config.DEMO_SPEED
    time.sleep(0.12 * speed)

    if approved:
        status = "[bold green]APPROVED[/bold green]"
        icon = "✅"
    else:
        status = "[bold red]REJECTED[/bold red]"
        icon = "❌"

    logger.console.print(
        f"    🔒 {validator_name}: {icon} {status}  [dim]({time_ms}ms)[/dim]"
    )


# ─────────────────────────────────────────────
# Failure Dramatics
# ─────────────────────────────────────────────
def failure_banner(failure_type: str, detail: str, penalty_sol: float = 0.0):
    """Display a dramatic failure banner with Rich styling."""
    from utils.helpers import format_sol

    lines = [f"[bold red]{failure_type}[/bold red]"]
    lines.append(f"[white]{detail}[/white]")
    if penalty_sol > 0:
        lines.append(f"\n[bold red]Penalty: {format_sol(penalty_sol)}[/bold red]")

    content = Text.from_markup("\n".join(lines), justify="center")

    panel = Panel(
        content,
        title="[bold red]⚠  PROTOCOL ALERT  ⚠[/bold red]",
        border_style="bright_red",
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
    )
    logger.console.print(panel)


def reputation_change(robot_name: str, old_score: float, new_score: float):
    """Display reputation change with dramatic formatting."""
    old_pct = f"{old_score * 100:.1f}%"
    new_pct = f"{new_score * 100:.1f}%"

    if new_score < old_score:
        logger.console.print(
            f"\n  [bold red]⬇ REPUTATION DECREASED[/bold red]"
        )
        logger.console.print(
            f"    {robot_name}: [yellow]{old_pct}[/yellow] → [red]{new_pct}[/red]\n"
        )
    else:
        logger.console.print(
            f"\n  [bold green]⬆ REPUTATION INCREASED[/bold green]"
        )
        logger.console.print(
            f"    {robot_name}: [yellow]{old_pct}[/yellow] → [green]{new_pct}[/green]\n"
        )


# ─────────────────────────────────────────────
# Shutdown Sequence
# ─────────────────────────────────────────────
SHUTDOWN_STEPS = [
    "Flushing protocol event stream",
    "Persisting reputation scores",
    "Closing escrow channels",
    "Disconnecting from Solana cluster",
    "Archiving task history logs",
    "Shutting down navigation stack",
    "Protocol shutdown complete",
]


def animated_shutdown():
    """Display dramatic protocol shutdown sequence."""
    speed = config.DEMO_SPEED

    logger.console.print()
    logger.console.print(
        "  [bold bright_magenta]◆ PROTOCOL SHUTDOWN SEQUENCE[/bold bright_magenta]\n"
    )

    for step in SHUTDOWN_STEPS:
        time.sleep(0.12 * speed)
        logger.console.print(f"    [dim]▸[/dim] {step}... [dim green]done[/dim green]")

    time.sleep(0.3 * speed)
    logger.console.print()
    logger.console.print(
        "  [dim]Thank you for using RoboLedger[/dim]  "
        "[bold bright_magenta]◆[/bold bright_magenta]\n",
        justify="center",
    )
