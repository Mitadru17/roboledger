"""
RoboLedger — Showcase Orchestrator
=====================================
Full hackathon showcase mode that ties all upgrade systems together.

Replaces the lifecycle loop when --showcase flag is used.
Calls ALL existing modules — does NOT replace them.

Showcase Flow:
    1. Cinematic boot sequence
    2. Fleet initialization (3-5 robots)
    3. Mission Control dashboard flash
    4. For each cycle:
        a. Task discovery + protocol event stream
        b. Multi-robot bid competition
        c. Intelligence reasoning for winner
        d. Navigation with failure injection
        e. Proof generation + BFT verification
        f. Settlement with TX propagation
        g. Failure/slashing when triggered
        h. Dashboard update
    5. Task history log
    6. Fleet summary
    7. Cinematic shutdown
"""

import sys
import os
import time
import random
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from utils.cinematic import (
    animated_boot, stage_transition, tx_propagation,
    animated_validator_vote, failure_banner, reputation_change,
    animated_shutdown,
)
from chain.protocol import (
    event_stream, task_history, advance_slot,
    confirm_transaction, generate_escrow_pda, get_slot,
    generate_validator_identities,
)
from simulator.robot_state import Robot, RobotState
from simulator.competition import create_fleet, display_fleet_status, run_bid_competition
from simulator.dashboard import render_dashboard, render_fleet_summary
from simulator.failure_engine import FailureEngine
from simulator.intelligence import (
    assess_risk, analyze_profitability, calculate_dynamic_bid,
    display_selection_reasoning, display_rejection_reasoning,
    display_risk_assessment,
)
from simulator.navigation import simulate_navigation
from simulator.battery import check_battery_for_task, simulate_charging
from chain.task_reader import scan_marketplace, display_task
from chain.bid_submission import create_bid
from proof.gps_proof import generate_proof
from proof.signer import ProofSigner
from proof import verifier


def run_showcase(robot: Robot, keypair, num_cycles: int = None, offline: bool = False):
    """
    Run the full hackathon showcase demo.

    Args:
        robot: Primary initialized Robot
        keypair: Solana keypair for signing
        num_cycles: Number of task cycles
        offline: Whether to skip Solana connections
    """
    start_time = datetime.now(timezone.utc)
    num_cycles = num_cycles or config.NUM_DEMO_TASKS
    speed = config.DEMO_SPEED

    # ══════════════════════════════════════════════
    # Phase 0: Cinematic Boot
    # ══════════════════════════════════════════════
    animated_boot()

    # ══════════════════════════════════════════════
    # Phase 1: Fleet Initialization
    # ══════════════════════════════════════════════
    logger.section("FLEET DEPLOYMENT")
    event_stream.emit("FleetInit", f"Deploying {config.SHOWCASE_ROBOTS} autonomous robots")

    fleet = create_fleet(count=config.SHOWCASE_ROBOTS, primary_robot=robot)

    # Set primary robot's initial balance
    robot.balance_sol = 1.0
    robot.transition(RobotState.IDLE)

    display_fleet_status(fleet)
    time.sleep(0.8 * speed)

    # Generate validator identities for the session
    validators = generate_validator_identities(config.NUM_VALIDATORS)
    event_stream.emit("ValidatorNet", f"BFT network: {len(validators)} validator nodes online")

    signer = ProofSigner(keypair)
    failure_engine = FailureEngine()

    # ══════════════════════════════════════════════
    # Phase 2: Initial Dashboard
    # ══════════════════════════════════════════════
    render_dashboard(fleet, event_stream=event_stream, active_robot=robot)

    # ══════════════════════════════════════════════
    # Phase 3: Autonomous Task Cycles
    # ══════════════════════════════════════════════
    logger.banner(
        "AUTONOMOUS PROTOCOL ACTIVATED",
        f"Running {num_cycles} task cycles | Fleet: {len(fleet)} robots"
    )

    completed_cycles = 0
    for cycle in range(1, num_cycles + 1):
        try:
            result = _run_showcase_cycle(
                cycle, num_cycles, robot, fleet, keypair, signer,
                failure_engine, validators
            )
            completed_cycles += 1

            # Inter-cycle dashboard update
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            render_dashboard(
                fleet,
                event_stream=event_stream,
                session_stats={"uptime": helpers.format_duration(elapsed)},
                active_robot=robot,
            )

            if cycle < num_cycles:
                logger.info(f"Cycle {cycle}/{num_cycles} complete — preparing next cycle...")
                time.sleep(1.0 * speed)

        except KeyboardInterrupt:
            logger.warning("Interrupt received — shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"Cycle {cycle} error: {e}")
            import traceback
            traceback.print_exc()
            if robot.state != RobotState.IDLE:
                robot.state = RobotState.ERROR
                robot.transition(RobotState.IDLE)
            completed_cycles += 1

    # ══════════════════════════════════════════════
    # Phase 4: Final Summary
    # ══════════════════════════════════════════════
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Task history log
    task_history.display()

    # Protocol event stream
    event_stream.emit("SessionEnd", f"Completed {completed_cycles} cycles")
    event_stream.display_stream(12)

    # Fleet performance summary
    render_fleet_summary(fleet, elapsed)

    # Cinematic shutdown
    animated_shutdown()

    return completed_cycles


def _run_showcase_cycle(
    cycle_num: int, total_cycles: int,
    primary_robot: Robot, fleet: list, keypair,
    signer: ProofSigner, failure_engine: FailureEngine,
    validators: list,
):
    """Execute a single showcase task cycle with all enhancements."""
    speed = config.DEMO_SPEED

    logger.banner(
        f"TASK CYCLE #{cycle_num} / {total_cycles}",
        f"Primary: {primary_robot.name} | Battery: {primary_robot.battery:.1f}% | "
        f"Balance: {helpers.format_sol(primary_robot.balance_sol)}"
    )

    # ──────────────────────────────────────────
    # Step 1: Task Discovery
    # ──────────────────────────────────────────
    stage_transition("SCANNING MARKETPLACE", "📡", "Querying on-chain task registry...")
    primary_robot.transition(RobotState.SCANNING)

    advance_slot()
    event_stream.emit("MarketScan", f"Cycle {cycle_num} — scanning marketplace")

    tasks = scan_marketplace(primary_robot.position)

    if not tasks:
        logger.warning("No tasks available — market is empty")
        primary_robot.transition(RobotState.IDLE)
        event_stream.emit("NoTasks", "Marketplace returned 0 open tasks")
        time.sleep(config.TASK_SCAN_INTERVAL * speed)
        return True

    # ──────────────────────────────────────────
    # Step 2: Intelligent Evaluation
    # ──────────────────────────────────────────
    stage_transition("AI TASK EVALUATION", "🧠", f"Analyzing {len(tasks)} candidates...")
    primary_robot.transition(RobotState.EVALUATING)

    # Pick best task with intelligence reasoning
    best_task = None
    best_risk = None
    best_profit = None

    for i, task in enumerate(tasks):
        display_task(task)

        risk = assess_risk(primary_robot, task)
        display_risk_assessment(task["task_id"], risk)

        bid_amount = calculate_dynamic_bid(primary_robot, task, len(fleet))
        profit = analyze_profitability(task, bid_amount)

        if risk["level"] == "HIGH" and len(tasks) > 1:
            display_rejection_reasoning(task, primary_robot, risk)
            event_stream.emit("TaskRejected", f"{task['task_id']} — risk too high")
            continue

        if best_task is None or risk["score"] < best_risk["score"]:
            best_task = task
            best_risk = risk
            best_profit = profit

    if not best_task:
        # All tasks rejected — pick the least risky one anyway
        best_task = tasks[0]
        best_risk = assess_risk(primary_robot, best_task)
        best_profit = analyze_profitability(
            best_task,
            calculate_dynamic_bid(primary_robot, best_task, len(fleet))
        )

    # Show selection reasoning for chosen task
    display_selection_reasoning(best_task, primary_robot, best_risk, best_profit)
    event_stream.emit("TaskSelected", f"{best_task['task_id']} — score {best_risk['score']}")
    time.sleep(0.3 * speed)

    # ──────────────────────────────────────────
    # Step 3: Battery Failure Check
    # ──────────────────────────────────────────
    if failure_engine.should_inject_failure():
        batt_fail = failure_engine.check_battery_failure(primary_robot, best_task["distance_estimate"])
        if batt_fail["failed"]:
            stage_transition("BATTERY ALERT", "🪫", batt_fail["detail"])
            result = failure_engine.apply_failure(primary_robot, best_task, batt_fail)

            event_stream.emit("BatteryFail", f"{primary_robot.name} — {batt_fail['detail'][:30]}")
            task_history.record(
                best_task["task_id"], primary_robot.robot_id, "FAILED",
                penalty=result["slash_amount"],
            )

            primary_robot.transition(RobotState.IDLE)
            # Charge up
            primary_robot.transition(RobotState.CHARGING)
            simulate_charging(primary_robot, target_level=80.0)
            primary_robot.transition(RobotState.IDLE)
            return True

    # ──────────────────────────────────────────
    # Step 4: Multi-Robot Bid Competition
    # ──────────────────────────────────────────
    stage_transition("BID COMPETITION", "💰", f"{len(fleet)} robots competing for {best_task['task_id']}")
    primary_robot.transition(RobotState.BIDDING)

    advance_slot()
    event_stream.emit("BidOpen", f"{best_task['task_id']} — {len(fleet)} bids incoming")

    competition_result = run_bid_competition(fleet, best_task)
    winner = competition_result["winner"]

    event_stream.emit(
        "BidWinner",
        f"{winner.name} wins {best_task['task_id']} at {helpers.format_sol(competition_result['bid_amount'])}"
    )

    # Simulate on-chain bid confirmation
    bid_tx = helpers.generate_tx_hash()
    confirm_transaction(bid_tx, "BidAccepted")

    # If the primary robot didn't win, simulate the winner (for demo purposes, always use primary)
    # This makes the demo more engaging by showing the full lifecycle every cycle
    active_robot = primary_robot

    time.sleep(0.3 * speed)

    # ──────────────────────────────────────────
    # Step 5: Navigation
    # ──────────────────────────────────────────
    stage_transition("AUTONOMOUS NAVIGATION", "🚀", f"Navigating to {best_task['task_id']}...")
    active_robot.transition(RobotState.NAVIGATING)

    advance_slot()
    event_stream.emit("NavStart", f"{active_robot.name} — navigating to destination")

    start_pos = active_robot.position
    end_pos = (best_task["end_position"]["lat"], best_task["end_position"]["lon"])

    # Check for navigation interruption
    nav_failed = False
    if failure_engine.should_inject_failure():
        nav_fail = failure_engine.check_nav_interruption()
        if nav_fail["failed"]:
            # Run partial navigation, then fail
            mid_pos = helpers.interpolate_position(start_pos, end_pos, random.uniform(0.3, 0.7))
            nav_result = simulate_navigation(active_robot, start_pos, mid_pos, best_task["task_id"])

            stage_transition("NAVIGATION ABORTED", "🚫", nav_fail["detail"])
            result = failure_engine.apply_failure(active_robot, best_task, nav_fail)

            event_stream.emit("NavFail", f"{active_robot.name} — {nav_fail['type']}")
            task_history.record(
                best_task["task_id"], active_robot.robot_id, "FAILED",
                penalty=result["slash_amount"],
            )

            active_robot.transition(RobotState.IDLE)
            nav_failed = True

    if not nav_failed:
        nav_result = simulate_navigation(active_robot, start_pos, end_pos, best_task["task_id"])

        if not nav_result["success"]:
            logger.error(f"Navigation failed: {nav_result.get('reason', 'unknown')}")
            event_stream.emit("NavFail", f"Navigation failed — {nav_result.get('reason')}")
            active_robot.transition(RobotState.IDLE)
            return True

        event_stream.emit("NavComplete", f"{active_robot.name} — arrived at destination")

        # Simulate possible task failure (timeout, sensor)
        task_success = True
        if failure_engine.should_inject_failure():
            timeout_fail = failure_engine.check_timeout(best_task, 0)
            if timeout_fail["failed"]:
                task_success = False
                stage_transition("TASK TIMEOUT", "⏰", timeout_fail["detail"])
                event_stream.emit("Timeout", f"{best_task['task_id']} — deadline exceeded")

        # ──────────────────────────────────────────
        # Step 6: GPS Proof Generation
        # ──────────────────────────────────────────
        stage_transition("GENERATING GPS PROOF", "📍", "Creating cryptographic proof payload...")
        active_robot.transition(RobotState.PROVING)

        advance_slot()
        gps_proof = generate_proof(
            robot_id=active_robot.robot_id,
            task_id=best_task["task_id"],
            start_pos=start_pos,
            end_pos=end_pos,
            waypoints=nav_result.get("waypoints", []),
            success=task_success,
        )

        logger.proof(f"GPS proof generated: {gps_proof.proof_id}")
        event_stream.emit("ProofGen", f"{gps_proof.proof_id} — status: {gps_proof.completion_status}")

        # Sign proof
        stage_transition("CRYPTOGRAPHIC SIGNING", "🔐", "Ed25519 signature...")
        signed_proof = signer.sign_proof(gps_proof)
        logger.success(f"Proof signed | sig: {helpers.truncate_hash(signed_proof['signature'], 6)}")

        # Submit proof TX
        proof_tx = helpers.generate_tx_hash()
        confirm_transaction(proof_tx, "ProofSubmission")
        event_stream.emit("ProofTX", f"Proof submitted on-chain — {helpers.truncate_hash(proof_tx)}")

        # ──────────────────────────────────────────
        # Step 7: BFT Verification (with potential failure)
        # ──────────────────────────────────────────
        stage_transition("SWARMPROOF BFT VERIFICATION", "🔒", "Submitting to validator network...")
        active_robot.transition(RobotState.VERIFYING)

        advance_slot()
        event_stream.emit("BFTStart", f"Verification initiated — {len(validators)} validators")

        # Check for proof rejection failure
        proof_rejected = False
        if failure_engine.should_inject_failure() and not task_success:
            proof_fail = failure_engine.check_proof_rejection()
            proof_rejected = proof_fail.get("failed", False)

        if proof_rejected:
            # Force validator rejection
            _simulate_failed_verification(validators, gps_proof, signed_proof)
            verification_passed = False
            event_stream.emit("BFTFail", "Consensus FAILED — proof rejected by majority")
        else:
            # Normal BFT verification (uses existing module)
            submission_result = verifier.simulate_bft_verification(
                proof=gps_proof,
                signature_b58=signed_proof["signature"],
                signer_pubkey=signed_proof["signer"],
            )
            verification_passed = submission_result["consensus"] and task_success
            if verification_passed:
                event_stream.emit("BFTPass", f"Consensus reached — proof accepted")
            else:
                event_stream.emit("BFTFail", "Consensus FAILED")

        # ──────────────────────────────────────────
        # Step 8: Settlement
        # ──────────────────────────────────────────
        stage_transition("PROCESSING SETTLEMENT", "💸", "Escrow resolution...")
        active_robot.transition(RobotState.SETTLING)

        advance_slot()
        escrow_pda = generate_escrow_pda(best_task["task_id"])
        event_stream.emit("EscrowResolve", f"PDA: {helpers.truncate_hash(escrow_pda)}")

        if verification_passed:
            _process_showcase_reward(active_robot, best_task)
            event_stream.emit("Settled", f"{best_task['task_id']} — reward paid")
            task_history.record(
                best_task["task_id"], active_robot.robot_id, "SUCCESS",
                reward=best_task["reward_sol"] * (1 - config.PLATFORM_FEE_RATE),
            )
            failure_engine.record_success()
        else:
            _process_showcase_slash(active_robot, best_task)
            event_stream.emit("Slashed", f"{best_task['task_id']} — penalty applied")
            task_history.record(
                best_task["task_id"], active_robot.robot_id, "FAILED",
                penalty=best_task["reward_sol"] * config.SLASHING_RATE,
            )

        # Clear task and return to idle
        active_robot.current_task = None
        active_robot.transition(RobotState.IDLE)

        # Auto-charge if needed
        if active_robot.battery < 40:
            active_robot.transition(RobotState.CHARGING)
            simulate_charging(active_robot, target_level=80.0)
            active_robot.transition(RobotState.IDLE)

    return True


# ─────────────────────────────────────────────
# Settlement Helpers
# ─────────────────────────────────────────────
def _process_showcase_reward(robot: Robot, task: dict):
    """Process successful reward with cinematic visuals."""
    from chain.settlement import process_settlement

    settlement_result = process_settlement(
        task=task,
        proof_verified=True,
        robot_id=robot.robot_id,
        robot_balance=robot.balance_sol,
    )

    robot.add_earnings(settlement_result["net_reward"])
    robot.record_task_completion(task["task_id"], True, settlement_result["net_reward"])

    # TX propagation visual
    tx_propagation(settlement_result["tx_hash"], "Reward Settlement")

    # Reputation increase display
    reputation_change(robot.name, robot.reliability_score - 0.01, robot.reliability_score)

    logger.banner(
        "✅ TASK COMPLETED SUCCESSFULLY",
        f"{task['task_id']} | Earned {helpers.format_sol(settlement_result['net_reward'])} | "
        f"Balance: {helpers.format_sol(robot.balance_sol)}"
    )


def _process_showcase_slash(robot: Robot, task: dict):
    """Process slashing with dramatic visuals."""
    old_reliability = robot.reliability_score

    reward = task["reward_sol"]
    slash_amount = round(reward * config.SLASHING_RATE, 4)

    robot.apply_slash(slash_amount)
    robot.record_task_completion(task["task_id"], False, 0)

    # Slashing TX
    slash_tx = helpers.generate_tx_hash()
    confirm_transaction(slash_tx, "SlashPenalty")

    # Failure banner
    failure_banner(
        failure_type="⛔ SLASHING EXECUTED",
        detail=f"Task {task['task_id']} — proof verification failed",
        penalty_sol=slash_amount,
    )

    # Reputation decrease
    reputation_change(robot.name, old_reliability, robot.reliability_score)

    logger.banner(
        "❌ TASK FAILED — SLASHING APPLIED",
        f"{task['task_id']} | Penalty: {helpers.format_sol(slash_amount)} | "
        f"Balance: {helpers.format_sol(robot.balance_sol)}"
    )


def _simulate_failed_verification(validators: list, proof, signed_proof: dict):
    """Simulate a BFT verification that fails to reach consensus."""
    from utils.cinematic import animated_validator_vote
    import random

    logger.section("BFT CONSENSUS VERIFICATION")

    # First verify signature (real crypto)
    sig_valid = verifier.verify_signature(
        proof, signed_proof["signature"], signed_proof["signer"]
    )

    # Even with valid signature, validators reject the proof
    validator_results = []
    approvals = 0
    for i, v in enumerate(validators[:config.NUM_VALIDATORS]):
        # Force majority rejection
        approved = random.random() < 0.25  # ~75% reject
        time_ms = random.randint(150, 500)

        animated_validator_vote(v["name"], approved, time_ms)

        if approved:
            approvals += 1
        validator_results.append({
            "name": v["name"],
            "approved": approved,
            "time_ms": time_ms,
        })

    # Display verification panel (reuse existing)
    logger.verification_panel(validator_results, consensus=False)
    logger.error(
        f"BFT Consensus FAILED: only {approvals}/{config.NUM_VALIDATORS} "
        f"approved (need {config.MIN_CONSENSUS})"
    )
