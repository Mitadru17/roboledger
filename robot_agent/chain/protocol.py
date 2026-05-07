"""
RoboLedger — Protocol Simulation Layer
=========================================
Advanced blockchain realism for hackathon showcase.

Provides:
    - Mock transaction confirmation lifecycle (PENDING → CONFIRMED → FINALIZED)
    - Incrementing slot counter
    - Validator mock identities with Ed25519 pubkeys
    - Program Derived Addresses (PDAs) for escrow accounts
    - Protocol event stream with timestamped entries
    - Task history persistence across cycles
"""

import sys
import os
import time
import random
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers

from rich.table import Table
from rich.panel import Panel
from rich import box


# ─────────────────────────────────────────────
# Slot Counter — simulates advancing Solana slots
# ─────────────────────────────────────────────
class SlotCounter:
    """Simulates an incrementing Solana slot counter."""

    def __init__(self, start_slot: int = None):
        self.slot = start_slot or random.randint(280_000_000, 300_000_000)

    def advance(self, steps: int = None) -> int:
        """Advance slot by a realistic number of steps."""
        steps = steps or random.randint(1, 4)
        self.slot += steps
        return self.slot

    @property
    def formatted(self) -> str:
        return f"#{self.slot:,}"


# Global slot counter for the showcase session
_slot_counter = SlotCounter()


def get_slot() -> int:
    """Get current slot number."""
    return _slot_counter.slot


def advance_slot(steps: int = None) -> int:
    """Advance and return new slot."""
    return _slot_counter.advance(steps)


# ─────────────────────────────────────────────
# Validator Identities
# ─────────────────────────────────────────────
VALIDATOR_NAMES = [
    "SwarmNode-Alpha",
    "SwarmNode-Beta",
    "SwarmNode-Gamma",
    "SwarmNode-Delta",
    "SwarmNode-Epsilon",
]


def generate_validator_identities(count: int = 5) -> list:
    """Generate mock validator identities with pubkeys."""
    validators = []
    for i in range(min(count, len(VALIDATOR_NAMES))):
        # Generate deterministic-looking mock pubkey for each validator
        seed = f"validator-{i}-{VALIDATOR_NAMES[i]}"
        mock_pubkey = hashlib.sha256(seed.encode()).hexdigest()[:44]
        validators.append({
            "name": VALIDATOR_NAMES[i],
            "pubkey": mock_pubkey,
            "stake": round(random.uniform(50_000, 200_000), 2),
            "version": "1.18.15",
        })
    return validators


# ─────────────────────────────────────────────
# Transaction Confirmation Lifecycle
# ─────────────────────────────────────────────
def confirm_transaction(tx_hash: str, tx_type: str = "Transfer") -> dict:
    """
    Simulate realistic Solana transaction confirmation lifecycle.

    Stages: PENDING → CONFIRMED → FINALIZED
    """
    speed = config.DEMO_SPEED
    slot = advance_slot()

    # Stage 1: PENDING
    logger.console.print(
        f"    [dim]TX[/dim] [yellow]PENDING[/yellow]  "
        f"[dim]{helpers.truncate_hash(tx_hash)}[/dim]  "
        f"[dim]slot {_slot_counter.formatted}[/dim]"
    )
    time.sleep(0.25 * speed)

    # Stage 2: CONFIRMED
    slot = advance_slot()
    logger.console.print(
        f"    [dim]TX[/dim] [cyan]CONFIRMED[/cyan] "
        f"[dim]{helpers.truncate_hash(tx_hash)}[/dim]  "
        f"[dim]slot {_slot_counter.formatted}[/dim]"
    )
    time.sleep(0.2 * speed)

    # Stage 3: FINALIZED
    slot = advance_slot()
    logger.console.print(
        f"    [dim]TX[/dim] [green]FINALIZED[/green] "
        f"[dim]{helpers.truncate_hash(tx_hash)}[/dim]  "
        f"[dim]slot {_slot_counter.formatted}[/dim]"
    )

    return {
        "tx_hash": tx_hash,
        "status": "FINALIZED",
        "slot": slot,
        "type": tx_type,
    }


# ─────────────────────────────────────────────
# Escrow PDA Generation
# ─────────────────────────────────────────────
def generate_escrow_pda(task_id: str) -> str:
    """Generate a mock Program Derived Address for an escrow account."""
    seed = f"escrow-{task_id}-{int(time.time())}"
    return hashlib.sha256(seed.encode()).hexdigest()[:44]


# ─────────────────────────────────────────────
# Protocol Event Stream
# ─────────────────────────────────────────────
class ProtocolEventStream:
    """
    Timestamped protocol event log.
    Maintains a scrolling buffer of recent protocol events for dashboard display.
    """

    def __init__(self, max_events: int = 50):
        self.events = []
        self.max_events = max_events

    def emit(self, event_type: str, detail: str, slot: int = None):
        """Record a protocol event."""
        slot = slot or get_slot()
        event = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "slot": slot,
            "type": event_type,
            "detail": detail,
        }
        self.events.append(event)

        # Trim buffer
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        # Print event in protocol stream format
        logger.console.print(
            f"    [dim]{event['timestamp']}[/dim]  "
            f"[dim cyan]SLOT {slot:,}[/dim cyan]  "
            f"[bold]{event_type}[/bold]  "
            f"[dim]{detail}[/dim]"
        )

    def get_recent(self, count: int = 15) -> list:
        """Get the most recent events for dashboard display."""
        return self.events[-count:]

    def display_stream(self, count: int = 10):
        """Display recent events in a Rich panel."""
        recent = self.get_recent(count)
        if not recent:
            return

        table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Time", style="dim", width=10)
        table.add_column("Slot", style="cyan", width=14)
        table.add_column("Event", style="bold", width=22)
        table.add_column("Detail", style="dim", width=30)

        for e in recent:
            table.add_row(
                e["timestamp"],
                f"#{e['slot']:,}",
                e["type"],
                e["detail"]
            )

        panel = Panel(
            table,
            title="[bold cyan]📡 PROTOCOL EVENT STREAM[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
        logger.console.print(panel)


# Global event stream instance
event_stream = ProtocolEventStream()


# ─────────────────────────────────────────────
# Task History Log
# ─────────────────────────────────────────────
class TaskHistoryLog:
    """Persistent log of all tasks across the session."""

    def __init__(self):
        self.entries = []

    def record(self, task_id: str, robot_id: str, result: str,
               reward: float = 0.0, penalty: float = 0.0, tx_hash: str = ""):
        """Record a task result."""
        self.entries.append({
            "task_id": task_id,
            "robot_id": robot_id,
            "result": result,
            "reward": reward,
            "penalty": penalty,
            "tx_hash": tx_hash,
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

    def display(self):
        """Display full task history as a Rich table."""
        if not self.entries:
            return

        table = Table(
            title="📜 TASK HISTORY LOG",
            box=box.DOUBLE_EDGE,
            border_style="bright_magenta",
            title_style="bold bright_magenta",
        )
        table.add_column("Time", style="dim", width=10)
        table.add_column("Task", style="bold yellow", width=14)
        table.add_column("Robot", style="cyan", width=14)
        table.add_column("Result", justify="center", width=12)
        table.add_column("Reward", justify="right", width=14)
        table.add_column("Penalty", justify="right", width=14)

        for e in self.entries:
            result_style = "green" if e["result"] == "SUCCESS" else "red"
            table.add_row(
                e["timestamp"],
                e["task_id"],
                e["robot_id"],
                f"[{result_style}]{e['result']}[/{result_style}]",
                helpers.format_sol(e["reward"]) if e["reward"] > 0 else "—",
                helpers.format_sol(e["penalty"]) if e["penalty"] > 0 else "—",
            )

        logger.console.print()
        logger.console.print(table)
        logger.console.print()


# Global task history instance
task_history = TaskHistoryLog()
