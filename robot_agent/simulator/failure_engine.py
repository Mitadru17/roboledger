"""
RoboLedger — Failure Injection Engine
========================================
Probabilistic failure scenarios for realistic hackathon demo.

Failure Types:
    - BATTERY_LOW: Robot rejects task due to insufficient battery
    - PROOF_REJECTED: BFT validators reject proof
    - TIMEOUT: Task exceeds deadline during execution
    - NAV_INTERRUPT: Navigation interrupted by obstacle/sensor failure
    - VALIDATOR_DISAGREE: Validators cannot reach consensus

Each failure triggers:
    - Dramatic Rich terminal output
    - Reputation decrease
    - Escrow slashing (where applicable)
    - Protocol event stream entry
"""

import sys
import os
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from utils.cinematic import failure_banner, reputation_change


class FailureEngine:
    """
    Probabilistic failure injection for showcase mode.

    Tracks failure history per robot and adjusts probabilities
    to ensure a good mix of successes and failures in the demo.
    """

    def __init__(self):
        self.failure_log = []
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        # Ensure demo shows at least one of each scenario type
        self._guaranteed_failures = ["PROOF_REJECTED", "NAV_INTERRUPT"]
        self._cycle_count = 0

    def check_battery_failure(self, robot, task_distance: float) -> dict:
        """
        Check if robot should fail due to low battery.
        Uses config probability + actual battery level influence.

        Returns:
            dict with 'failed' bool and details
        """
        # Actual low battery always triggers
        battery_needed = task_distance * config.BATTERY_DRAIN_RATE
        if robot.battery < config.MIN_BATTERY_THRESHOLD:
            return self._create_failure(
                "BATTERY_CRITICAL",
                f"Battery at {robot.battery:.1f}% — below minimum threshold {config.MIN_BATTERY_THRESHOLD}%",
            )

        # Probabilistic failure — higher chance when battery is lower
        battery_factor = max(0, 1.0 - (robot.battery / 100.0))  # 0.0-1.0
        effective_prob = config.BATTERY_FAILURE_PROB * (1 + battery_factor)

        if random.random() < effective_prob:
            # Simulate sudden battery drop
            drain = random.uniform(15, 30)
            robot.drain_battery(drain)
            return self._create_failure(
                "BATTERY_FAILURE",
                f"Unexpected battery drain detected! "
                f"Battery dropped to {robot.battery:.1f}%",
                {"drain_amount": drain},
            )

        return {"failed": False}

    def check_nav_interruption(self) -> dict:
        """Check if navigation should be interrupted."""
        self._cycle_count += 1

        # Guarantee a nav interrupt in early cycles for demo
        if "NAV_INTERRUPT" in self._guaranteed_failures and self._cycle_count >= 3:
            self._guaranteed_failures.remove("NAV_INTERRUPT")
            return self._create_failure(
                "NAV_INTERRUPT",
                random.choice([
                    "Obstacle detected — emergency stop activated",
                    "Sensor malfunction — LiDAR module unresponsive",
                    "GPS signal lost — position uncertainty too high",
                    "Path blocked — rerouting failed",
                ]),
            )

        if random.random() < config.NAV_INTERRUPT_PROB:
            return self._create_failure(
                "NAV_INTERRUPT",
                random.choice([
                    "Obstacle detected — emergency stop activated",
                    "Sensor malfunction — LiDAR module unresponsive",
                    "GPS signal lost — position uncertainty too high",
                    "Path blocked — rerouting failed",
                    "Motor controller fault — safety shutdown",
                ]),
            )

        return {"failed": False}

    def check_timeout(self, task: dict, elapsed_seconds: float) -> dict:
        """Check if task has timed out."""
        if random.random() < config.TIMEOUT_FAILURE_PROB:
            return self._create_failure(
                "TIMEOUT",
                f"Task {task['task_id']} exceeded deadline "
                f"({task.get('deadline_minutes', 15)} min)",
            )
        return {"failed": False}

    def check_proof_rejection(self) -> dict:
        """Check if proof should be rejected by validators."""
        # Guarantee a proof rejection in early cycles for demo
        if "PROOF_REJECTED" in self._guaranteed_failures and self._cycle_count >= 2:
            self._guaranteed_failures.remove("PROOF_REJECTED")
            return self._create_failure(
                "PROOF_REJECTED",
                random.choice([
                    "GPS coordinates deviate from expected path",
                    "Timestamp inconsistency detected in proof payload",
                    "Path hash verification failed — data integrity issue",
                ]),
            )

        if random.random() < config.PROOF_REJECTION_PROB:
            return self._create_failure(
                "PROOF_REJECTED",
                random.choice([
                    "GPS coordinates deviate from expected path",
                    "Timestamp inconsistency detected in proof payload",
                    "Path hash verification failed — data integrity issue",
                    "Proof submitted after verification window closed",
                ]),
            )
        return {"failed": False}

    def check_validator_disagreement(self) -> dict:
        """Check if validators should disagree (Byzantine failure)."""
        if random.random() < config.VALIDATOR_DISAGREE_PROB:
            return self._create_failure(
                "VALIDATOR_DISAGREE",
                "Byzantine fault detected — validators cannot reach consensus",
            )
        return {"failed": False}

    def apply_failure(self, robot, task: dict, failure: dict) -> dict:
        """
        Apply a failure result: display dramatics, slash escrow, decrease reputation.

        Returns:
            dict with slashing details
        """
        speed = config.DEMO_SPEED
        failure_type = failure["type"]
        detail = failure["detail"]

        # Track old reliability for display
        old_reliability = robot.reliability_score

        # Calculate slashing penalty
        reward = task.get("reward_sol", 0.1)
        slash_amount = round(reward * config.SLASHING_RATE, 4)

        # Display dramatic failure banner
        time.sleep(0.3 * speed)
        failure_banner(
            failure_type=self._format_failure_type(failure_type),
            detail=detail,
            penalty_sol=slash_amount,
        )
        time.sleep(0.3 * speed)

        # Apply slashing
        robot.apply_slash(slash_amount)
        robot.record_task_completion(task.get("task_id", "UNKNOWN"), False, 0)

        # Display reputation change
        new_reliability = robot.reliability_score
        reputation_change(robot.name, old_reliability, new_reliability)

        # Log the failure
        self.failure_log.append({
            "type": failure_type,
            "task_id": task.get("task_id"),
            "robot_id": robot.robot_id,
            "slash_amount": slash_amount,
            "detail": detail,
        })

        self.consecutive_failures += 1
        self.consecutive_successes = 0

        return {
            "success": False,
            "failure_type": failure_type,
            "slash_amount": slash_amount,
            "new_balance": robot.balance_sol,
        }

    def record_success(self):
        """Record a successful cycle (adjusts failure probabilities)."""
        self.consecutive_successes += 1
        self.consecutive_failures = 0

    def should_inject_failure(self) -> bool:
        """
        Meta-check: should we inject any failure this cycle?
        Ensures a good demo balance — not too many failures in a row,
        but guarantees at least some for showcase purposes.
        """
        # Never more than 2 failures in a row (boring for demo)
        if self.consecutive_failures >= 2:
            return False
        # After 3 consecutive successes, increase failure chance
        if self.consecutive_successes >= 3:
            return True
        return True  # Allow normal probability checks

    def _create_failure(self, failure_type: str, detail: str, extra: dict = None) -> dict:
        """Create a failure result dict."""
        result = {
            "failed": True,
            "type": failure_type,
            "detail": detail,
        }
        if extra:
            result.update(extra)
        return result

    def _format_failure_type(self, failure_type: str) -> str:
        """Format failure type for display."""
        formats = {
            "BATTERY_CRITICAL": "⚡ BATTERY CRITICAL",
            "BATTERY_FAILURE": "🪫 BATTERY FAILURE",
            "NAV_INTERRUPT": "🚫 NAVIGATION ABORTED",
            "TIMEOUT": "⏰ TASK TIMEOUT",
            "PROOF_REJECTED": "❌ PROOF REJECTED BY SWARMPROOF",
            "VALIDATOR_DISAGREE": "🔒 VALIDATOR CONSENSUS FAILED",
        }
        return formats.get(failure_type, f"⚠ {failure_type}")
