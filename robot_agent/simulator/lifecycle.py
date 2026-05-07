"""
RoboLedger — Robot Lifecycle Orchestrator
============================================
Main orchestration loop that ties all modules together.

Lifecycle Flow:
    1. Listen for tasks on-chain marketplace
    2. Scan marketplace and detect available tasks
    3. Evaluate best task (battery, distance, reward scoring)
    4. Submit competitive bid
    5. On acceptance → execute simulated navigation
    6. Generate GPS proof of task completion
    7. Sign proof cryptographically with Ed25519
    8. Submit proof for SwarmProof BFT verification
    9. Process settlement (escrow release or slashing)
   10. Display completion banner → return to idle

Error Handling:
    - Bid rejection: automatically retries with next-best task
    - Navigation failure: generates FAILED proof, triggers slashing
    - BFT failure: slashing applied, robot continues to next cycle
    - Battery low: auto-charges before continuing
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from simulator.robot_state import Robot, RobotState
from simulator.navigation import simulate_navigation
from simulator.battery import check_battery_for_task, simulate_charging
from chain.task_reader import scan_marketplace, display_task
from chain.bid_submission import create_bid, submit_bid
from chain.settlement import process_settlement
from proof.gps_proof import generate_proof
from proof.signer import ProofSigner
from chain.proof_submission import submit_proof


def evaluate_task(robot: Robot, task: dict) -> dict:
    """
    Evaluate a task's suitability for this robot.

    Scoring System (0-100):
        - Battery feasibility: 30 points
        - Reward value: 25 points
        - Distance efficiency: 25 points
        - Priority bonus: 20 points

    Returns:
        dict with score, feasibility flag, and human-readable breakdown
    """
    score = 0
    breakdown = {}

    # ── Battery check (30 pts) ──
    battery_check = check_battery_for_task(robot, task["distance_estimate"])
    if battery_check["feasible"]:
        battery_score = min(30, 15 + battery_check["margin"])
        breakdown["Battery"] = f"[green]OK[/green] {battery_score:.0f}/30 (margin: {battery_check['margin']:.1f}%)"
    else:
        battery_score = 0
        breakdown["Battery"] = f"[red]FAIL[/red] 0/30 (insufficient)"
    score += battery_score

    # ── Reward value (25 pts) ──
    reward = task["reward_sol"]
    if reward >= 0.25:
        reward_score = 25
    elif reward >= 0.15:
        reward_score = 20
    elif reward >= config.MIN_REWARD_SOL:
        reward_score = 15
    else:
        reward_score = 5
    tag = "[green]OK[/green]" if reward_score > 15 else "[yellow]LOW[/yellow]"
    breakdown["Reward"] = f"{tag} {reward_score}/25 ({helpers.format_sol(reward)})"
    score += reward_score

    # ── Distance efficiency (25 pts) ──
    dist = task["distance_estimate"]
    reward_per_unit = reward / max(dist, 0.1)
    if reward_per_unit > 0.015:
        dist_score = 25
    elif reward_per_unit > 0.008:
        dist_score = 18
    else:
        dist_score = 10
    tag = "[green]OK[/green]" if dist_score > 18 else "[yellow]LOW[/yellow]"
    breakdown["Efficiency"] = f"{tag} {dist_score}/25 ({reward_per_unit:.4f} SOL/unit)"
    score += dist_score

    # ── Priority bonus (20 pts) ──
    priority_scores = {"HIGH": 20, "MEDIUM": 12, "LOW": 5}
    p_score = priority_scores.get(task["priority"], 5)
    tag = "[green]OK[/green]" if p_score > 12 else "[yellow]LOW[/yellow]"
    breakdown["Priority"] = f"{tag} {p_score}/20 ({task['priority']})"
    score += p_score

    # ── Total ──
    tag = "[green]PASS[/green]" if score >= 60 else "[red]FAIL[/red]"
    breakdown["TOTAL"] = f"{tag} {score}/100"

    return {
        "score": score,
        "feasible": battery_check["feasible"] and reward >= config.MIN_REWARD_SOL,
        "breakdown": breakdown,
    }


def _lifecycle_banner(stage: str, icon: str, detail: str = ""):
    """Print a compact lifecycle stage marker for cinematic flow."""
    msg = f"{icon}  {stage}"
    if detail:
        msg += f"  —  {detail}"
    logger.console.print(f"\n  [bold bright_cyan]{msg}[/bold bright_cyan]")


def run_task_cycle(robot: Robot, keypair, signer: ProofSigner, cycle_num: int) -> bool:
    """
    Execute a single task lifecycle cycle.

    Includes automatic retry on bid rejection (tries up to 2 remaining tasks).

    Returns:
        True if cycle completed (success or handled failure), False to stop
    """
    logger.banner(
        f"TASK CYCLE #{cycle_num}",
        f"Robot: {robot.name} | Battery: {robot.battery:.1f}% | Balance: {helpers.format_sol(robot.balance_sol)}"
    )

    # ══════════════════════════════════════════════
    # Step 1: Listen for tasks
    # ══════════════════════════════════════════════
    _lifecycle_banner("LISTENING FOR TASKS", "📡", "Scanning on-chain marketplace...")
    robot.transition(RobotState.SCANNING)
    tasks = scan_marketplace(robot.position)

    if not tasks:
        logger.warning("No tasks available. Waiting before next scan...")
        robot.transition(RobotState.IDLE)
        time.sleep(config.TASK_SCAN_INTERVAL * config.DEMO_SPEED)
        return True

    # ══════════════════════════════════════════════
    # Step 2: Evaluate all tasks & rank them
    # ══════════════════════════════════════════════
    _lifecycle_banner("EVALUATING TASKS", "🧠", f"Analyzing {len(tasks)} candidates...")
    robot.transition(RobotState.EVALUATING)
    logger.section("TASK EVALUATION")

    ranked = []
    for t in tasks:
        display_task(t)
        evaluation = evaluate_task(robot, t)

        logger.status_panel(
            f"Evaluation: {t['task_id']}",
            evaluation["breakdown"],
            border_style="yellow" if evaluation["feasible"] else "red",
        )

        if evaluation["feasible"]:
            ranked.append((evaluation["score"], t, evaluation))

    # Sort best-first
    ranked.sort(key=lambda x: x[0], reverse=True)

    if not ranked:
        logger.warning("No feasible tasks found. Returning to idle.")
        robot.transition(RobotState.IDLE)
        return True

    logger.success(f"Ranked {len(ranked)} feasible task(s) — best score: {ranked[0][0]}/100")

    # ══════════════════════════════════════════════
    # Step 3: Submit bid (with retry on rejection)
    # ══════════════════════════════════════════════
    accepted_task = None
    bid_result = None

    for score, candidate, evaluation in ranked:
        _lifecycle_banner("SUBMITTING BID", "💰", f"Task {candidate['task_id']} (score {score}/100)")
        robot.transition(RobotState.BIDDING)
        pubkey_str = str(keypair.pubkey())

        bid = create_bid(
            robot_id=robot.robot_id,
            robot_pubkey=pubkey_str,
            task=candidate,
            robot_position=robot.position,
            battery_level=robot.battery,
            reliability_score=robot.reliability_score,
        )

        bid_result = submit_bid(bid)

        if bid_result["accepted"]:
            accepted_task = candidate
            break
        else:
            logger.info("Trying next-best task...")
            # Transition back to evaluating to try next candidate
            robot.transition(RobotState.IDLE)
            robot.transition(RobotState.SCANNING)
            robot.transition(RobotState.EVALUATING)

    if not accepted_task:
        logger.warning("All bids rejected this cycle. Returning to idle.")
        robot.transition(RobotState.IDLE)
        return True

    robot.current_task = accepted_task

    # ══════════════════════════════════════════════
    # Step 4: Navigate to destination
    # ══════════════════════════════════════════════
    _lifecycle_banner("EXECUTING NAVIGATION", "🚀", f"Navigating to {accepted_task['task_id']}...")
    robot.transition(RobotState.NAVIGATING)

    start_pos = robot.position
    end_pos = (accepted_task["end_position"]["lat"], accepted_task["end_position"]["lon"])

    nav_result = simulate_navigation(robot, start_pos, end_pos, accepted_task["task_id"])

    # Simulate random failure (sensor malfunction, etc.)
    task_failed = random.random() < config.FAILURE_PROBABILITY
    task_success = nav_result["success"] and not task_failed

    if task_failed and nav_result["success"]:
        logger.error("TASK FAILURE SIMULATED — sensor malfunction detected!")
        time.sleep(0.5 * config.DEMO_SPEED)

    # ══════════════════════════════════════════════
    # Step 5: Generate GPS proof
    # ══════════════════════════════════════════════
    _lifecycle_banner("GENERATING GPS PROOF", "📍", "Creating proof payload...")
    robot.transition(RobotState.PROVING)
    logger.section("PROOF GENERATION")

    gps_proof = generate_proof(
        robot_id=robot.robot_id,
        task_id=accepted_task["task_id"],
        start_pos=start_pos,
        end_pos=end_pos,
        waypoints=nav_result.get("waypoints", []),
        success=task_success,
    )

    logger.proof(f"GPS proof generated: {gps_proof.proof_id}")

    # ══════════════════════════════════════════════
    # Step 6: Sign proof cryptographically
    # ══════════════════════════════════════════════
    _lifecycle_banner("SIGNING PROOF", "🔐", "Ed25519 cryptographic signature...")
    signed_proof = signer.sign_proof(gps_proof)
    logger.success(f"Proof signed with Ed25519 | sig: {helpers.truncate_hash(signed_proof['signature'], 6)}")

    # ══════════════════════════════════════════════
    # Step 7: Submit proof → SwarmProof BFT verification
    # ══════════════════════════════════════════════
    _lifecycle_banner("SWARMPROOF VERIFICATION", "🔒", "Submitting to BFT validators...")
    robot.transition(RobotState.VERIFYING)

    submission_result = submit_proof(signed_proof, gps_proof)

    # ══════════════════════════════════════════════
    # Step 8: Settlement (reward or slashing)
    # ══════════════════════════════════════════════
    _lifecycle_banner("PROCESSING SETTLEMENT", "💸", "Escrow + SOL transfer...")
    robot.transition(RobotState.SETTLING)

    settlement_result = process_settlement(
        task=accepted_task,
        proof_verified=submission_result["verified"] and task_success,
        robot_id=robot.robot_id,
        robot_balance=robot.balance_sol,
    )

    # ══════════════════════════════════════════════
    # Step 9: Update robot state & display completion
    # ══════════════════════════════════════════════
    if settlement_result["success"]:
        robot.add_earnings(settlement_result["net_reward"])
        robot.record_task_completion(accepted_task["task_id"], True, settlement_result["net_reward"])
        logger.banner(
            "TASK COMPLETED SUCCESSFULLY",
            f"{accepted_task['task_id']} | Earned {helpers.format_sol(settlement_result['net_reward'])} | Balance: {helpers.format_sol(robot.balance_sol)}"
        )
    else:
        robot.apply_slash(settlement_result.get("slash_amount", 0))
        robot.record_task_completion(accepted_task["task_id"], False, 0)
        logger.banner(
            "TASK FAILED — SLASHING APPLIED",
            f"{accepted_task['task_id']} | Penalty: {helpers.format_sol(settlement_result.get('slash_amount', 0))} | Balance: {helpers.format_sol(robot.balance_sol)}"
        )

    robot.current_task = None
    robot.transition(RobotState.IDLE)

    # Auto-charge if battery is low
    if robot.battery < 40:
        robot.transition(RobotState.CHARGING)
        simulate_charging(robot, target_level=80.0)
        robot.transition(RobotState.IDLE)

    return True


def run_lifecycle(robot: Robot, keypair, num_cycles: int = None):
    """
    Run the full robot lifecycle for N task cycles.

    Args:
        robot: Initialized Robot instance
        keypair: Solana keypair for signing
        num_cycles: Number of task cycles (default from config)

    Returns:
        int: Number of cycles completed
    """
    num_cycles = num_cycles or config.NUM_DEMO_TASKS
    signer = ProofSigner(keypair)

    robot.transition(RobotState.IDLE)

    logger.banner(
        "AUTONOMOUS MODE ACTIVATED",
        f"Running {num_cycles} task cycles | Robot: {robot.name}"
    )

    completed_cycles = 0
    for cycle in range(1, num_cycles + 1):
        try:
            result = run_task_cycle(robot, keypair, signer, cycle)
            completed_cycles += 1

            if cycle < num_cycles:
                logger.info(f"Cooldown before next cycle ({cycle}/{num_cycles})...")
                time.sleep(1.0 * config.DEMO_SPEED)

        except KeyboardInterrupt:
            logger.warning("Interrupt received — shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"Cycle {cycle} error: {e}")
            import traceback
            traceback.print_exc()
            # Recover to IDLE for next cycle
            if robot.state != RobotState.IDLE:
                robot.state = RobotState.ERROR
                robot.transition(RobotState.IDLE)
            completed_cycles += 1

    return completed_cycles
