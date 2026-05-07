"""
RoboLedger — Main Entry Point
================================
Autonomous Robot Agent for Decentralized Task Execution & Settlement

This is the cinematic demo entry point.  It initializes the robot,
connects to Solana Devnet, and runs the full autonomous lifecycle loop.

Usage:
    python main.py                    # Run with defaults (3 task cycles)
    python main.py --cycles 5         # Run 5 task cycles
    python main.py --name "Bot-Beta"  # Custom robot name
    python main.py --fast             # Fast demo mode (0.5x speed)
    python main.py --offline          # Skip Solana Devnet connection
    python main.py --robots 3         # Multi-robot swarm simulation

Multi-Robot Mode:
    When --robots N is specified (N > 1), the system spawns N independent
    robot agents that each run a full lifecycle sequentially.  This
    demonstrates the decentralized coordination model.
"""

import sys
import os
import time
import argparse
from datetime import datetime, timezone

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils import logger, helpers
from wallet.keypair_loader import load_keypair, get_keypair_info
from chain.rpc_client import SolanaClient
from simulator.robot_state import Robot, RobotState
from simulator.lifecycle import run_lifecycle


# ─────────────────────────────────────────────
# Startup Banner
# ─────────────────────────────────────────────
LOGO = r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   ██████╗  ██████╗ ██████╗  ██████╗ ██╗     ███████╗██████╗  ║
    ║   ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██║     ██╔════╝██╔══██╗ ║
    ║   ██████╔╝██║   ██║██████╔╝██║   ██║██║     █████╗  ██║  ██║ ║
    ║   ██╔══██╗██║   ██║██╔══██╗██║   ██║██║     ██╔══╝  ██║  ██║ ║
    ║   ██║  ██║╚██████╔╝██████╔╝╚██████╔╝███████╗███████╗██████╔╝ ║
    ║   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═════╝  ║
    ║                                                              ║
    ║       Decentralized Robot Coordination & Settlement          ║
    ║                    Protocol on Solana                        ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
"""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RoboLedger — Autonomous Robot Agent Simulator"
    )
    parser.add_argument("--cycles", type=int, default=None,
                        help="Number of task cycles per robot (default: 3)")
    parser.add_argument("--name", type=str, default=None,
                        help="Robot name override")
    parser.add_argument("--fast", action="store_true",
                        help="Fast demo mode (0.5x timing)")
    parser.add_argument("--slow", action="store_true",
                        help="Slow demo mode (2x timing)")
    parser.add_argument("--offline", action="store_true",
                        help="Skip Solana Devnet connection")
    parser.add_argument("--robots", type=int, default=1,
                        help="Number of robots for swarm simulation (default: 1)")
    parser.add_argument("--showcase", action="store_true",
                        help="Full hackathon showcase mode with all enhancements")
    return parser.parse_args()


def display_startup():
    """Display the cinematic startup sequence."""
    logger.console.print(LOGO, style="bold bright_magenta")
    time.sleep(0.5)

    logger.console.print(
        f"    v{config.APP_VERSION} | {config.APP_TAGLINE}\n",
        style="dim",
    )
    time.sleep(0.3)


def initialize_robot(name: str = None, robot_index: int = 0) -> Robot:
    """
    Initialize a robot agent with configuration.

    Args:
        name: Optional name override
        robot_index: Index for multi-robot mode (0-based)
    """
    logger.section("ROBOT INITIALIZATION")

    robot = Robot()

    # Apply per-robot identity in multi-robot mode
    if robot_index > 0:
        robot.robot_id = f"ROBO-{robot_index + 1:03d}"
        robot.name = f"RoboAgent-{chr(65 + robot_index)}"  # Alpha, Beta, Gamma...

    if name:
        robot.name = name
        config.ROBOT_NAME = name

    logger.status_panel("Robot Configuration", robot.get_status(), border_style="magenta")

    return robot


def initialize_wallet():
    """Load or generate the robot's Solana wallet."""
    logger.section("WALLET INITIALIZATION")

    try:
        keypair = load_keypair()
        wallet_info = get_keypair_info(keypair)
        logger.status_panel("Wallet Details", wallet_info, border_style="blue")
        return keypair
    except Exception as e:
        logger.error(f"Wallet initialization failed: {e}")
        logger.info("Generating emergency keypair...")
        from solders.keypair import Keypair
        keypair = Keypair()
        logger.warning("Using ephemeral keypair (not persisted)")
        return keypair


def initialize_solana(keypair, offline: bool = False) -> SolanaClient:
    """Connect to Solana Devnet and check balance."""
    client = SolanaClient()

    if offline:
        logger.warning("Offline mode — skipping Solana connection")
        return client

    try:
        connected = client.connect()

        if connected:
            pubkey = str(keypair.pubkey())
            balance = client.get_balance(pubkey)

            if balance > 0:
                logger.solana(f"Wallet balance: {helpers.format_sol(balance)}")
            else:
                logger.info("Wallet balance: 0 SOL (simulation uses mock balances)")
    except Exception as e:
        logger.warning(f"Solana connection issue: {e}")
        logger.info("Continuing in offline simulation mode...")

    return client


def display_shutdown(robot: Robot, start_time: datetime, cycles_completed: int):
    """Display the shutdown summary with final statistics."""
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    logger.banner(
        "ROBOT AGENT SHUTDOWN",
        f"Session completed at {datetime.now().strftime('%H:%M:%S')}"
    )

    logger.print_summary({
        "Robot": robot.name,
        "Session Duration": helpers.format_duration(elapsed),
        "Task Cycles": str(cycles_completed),
        "Tasks Completed": str(robot.tasks_completed),
        "Tasks Failed": str(robot.tasks_failed),
        "Reliability": f"{robot.reliability_score * 100:.1f}%",
        "Total Earned": helpers.format_sol(robot.total_earned),
        "Total Slashed": helpers.format_sol(robot.total_slashed),
        "Net Earnings": helpers.format_sol(robot.total_earned - robot.total_slashed),
        "Final Battery": f"{robot.battery:.1f}%",
        "State Transitions": str(len(robot.state_history)),
    })

    logger.console.print(
        "\n    [dim]Thank you for using RoboLedger[/dim]  [bold bright_magenta]<>[/bold bright_magenta]\n",
        justify="center"
    )


def run_single_robot(args):
    """Run the standard single-robot lifecycle."""
    start_time = datetime.now(timezone.utc)
    robot = None

    try:
        # ── Startup ──
        display_startup()

        # ── Initialize Robot ──
        robot = initialize_robot(name=args.name)

        # ── Initialize Wallet ──
        keypair = initialize_wallet()

        # ── Connect to Solana ──
        client = initialize_solana(keypair, offline=args.offline)

        # Set initial mock balance for simulation
        robot.balance_sol = 1.0

        # ── Run Lifecycle ──
        num_cycles = args.cycles or config.NUM_DEMO_TASKS
        cycles_completed = run_lifecycle(robot, keypair, num_cycles)

        # ── Shutdown ──
        display_shutdown(robot, start_time, cycles_completed)

    except KeyboardInterrupt:
        logger.console.print("\n")
        logger.warning("Interrupted by user")
        if robot:
            display_shutdown(robot, start_time, robot.tasks_completed)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        if robot:
            display_shutdown(robot, start_time, robot.tasks_completed)
        sys.exit(1)


def run_multi_robot(args):
    """
    Run multi-robot swarm simulation.

    Each robot runs its lifecycle sequentially, demonstrating
    the decentralized coordination model.
    """
    start_time = datetime.now(timezone.utc)
    num_robots = args.robots
    num_cycles = args.cycles or max(1, config.NUM_DEMO_TASKS // num_robots)

    display_startup()

    logger.banner(
        f"SWARM MODE — {num_robots} ROBOTS",
        f"Each robot will execute {num_cycles} task cycle(s)"
    )

    # Shared wallet (in production each robot has its own)
    keypair = initialize_wallet()
    client = initialize_solana(keypair, offline=args.offline)

    robots = []
    total_earned = 0.0

    for i in range(num_robots):
        logger.banner(
            f"ROBOT {i + 1}/{num_robots}",
            f"Initializing agent {chr(65 + i)}..."
        )

        robot = initialize_robot(robot_index=i)
        robot.balance_sol = 1.0
        robots.append(robot)

        cycles = run_lifecycle(robot, keypair, num_cycles)
        total_earned += robot.total_earned

        if i < num_robots - 1:
            logger.info("Handing off to next robot in swarm...")
            time.sleep(1.0 * config.DEMO_SPEED)

    # ── Swarm Summary ──
    logger.banner("SWARM SIMULATION COMPLETE", f"{num_robots} robots finished")

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    total_tasks = sum(r.tasks_completed for r in robots)
    total_failed = sum(r.tasks_failed for r in robots)
    total_slashed = sum(r.total_slashed for r in robots)

    logger.print_summary({
        "Robots Deployed": str(num_robots),
        "Session Duration": helpers.format_duration(elapsed),
        "Total Tasks Completed": str(total_tasks),
        "Total Tasks Failed": str(total_failed),
        "Fleet Reliability": f"{(total_tasks / max(1, total_tasks + total_failed)) * 100:.1f}%",
        "Total Earned": helpers.format_sol(total_earned),
        "Total Slashed": helpers.format_sol(total_slashed),
        "Net Fleet Earnings": helpers.format_sol(total_earned - total_slashed),
    })

    logger.console.print(
        "\n    [dim]Thank you for using RoboLedger[/dim]  [bold bright_magenta]<>[/bold bright_magenta]\n",
        justify="center"
    )


def run_showcase_mode(args):
    """
    Run the full hackathon showcase with all enhancements.

    Activates: multi-robot competition, failure injection,
    intelligent reasoning, cinematic effects, live dashboard,
    and advanced protocol simulation.
    """
    start_time = datetime.now(timezone.utc)
    robot = None

    try:
        # Import showcase module (only when needed)
        from simulator.showcase import run_showcase

        # Initialize primary robot
        robot = initialize_robot(name=args.name)

        # Initialize wallet
        keypair = initialize_wallet()

        # Connect to Solana (optional)
        client = initialize_solana(keypair, offline=args.offline)

        # Run showcase
        num_cycles = args.cycles or config.NUM_DEMO_TASKS
        run_showcase(
            robot=robot,
            keypair=keypair,
            num_cycles=num_cycles,
            offline=args.offline,
        )

    except KeyboardInterrupt:
        logger.console.print("\n")
        logger.warning("Interrupted by user")
        if robot:
            display_shutdown(robot, start_time, robot.tasks_completed)
    except Exception as e:
        logger.error(f"Showcase error: {e}")
        import traceback
        traceback.print_exc()
        if robot:
            display_shutdown(robot, start_time, robot.tasks_completed)
        sys.exit(1)


def main():
    """Main entry point — run the autonomous robot agent(s)."""
    args = parse_args()

    # Apply speed settings
    if args.fast:
        config.DEMO_SPEED = 0.5
    elif args.slow:
        config.DEMO_SPEED = 2.0

    if args.showcase:
        run_showcase_mode(args)
    elif args.robots > 1:
        run_multi_robot(args)
    else:
        run_single_robot(args)


if __name__ == "__main__":
    main()
