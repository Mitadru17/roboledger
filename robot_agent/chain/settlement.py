"""
RoboLedger — Settlement Module
=================================
Handles escrow release, reward payment, and slashing logic.

Architecture Note:
    Settlement is the final stage of the task lifecycle. After BFT
    verification approves a proof, the escrow holding the task reward
    is released to the robot. On failure, a portion of the robot's
    stake is slashed as penalty.
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers


def process_settlement(
    task: dict,
    proof_verified: bool,
    robot_id: str,
    robot_balance: float,
) -> dict:
    """
    Process payment settlement after proof verification.
    
    Args:
        task: The completed task data
        proof_verified: Whether BFT verification passed
        robot_id: Robot identifier
        robot_balance: Current robot SOL balance
        
    Returns:
        dict: Settlement result with payment details
    """
    logger.section("SETTLEMENT")
    
    if proof_verified:
        return _process_reward(task, robot_id, robot_balance)
    else:
        return _process_slashing(task, robot_id, robot_balance)


def _process_reward(task: dict, robot_id: str, robot_balance: float) -> dict:
    """Process successful task reward payment."""
    
    reward = task["reward_sol"]
    platform_fee = round(reward * config.PLATFORM_FEE_RATE, 4)
    net_reward = round(reward - platform_fee, 4)
    new_balance = round(robot_balance + net_reward, 4)
    
    # Simulate escrow release
    with logger.console.status("[bold green]Releasing escrow funds...", spinner="dots"):
        time.sleep(config.ESCROW_HOLD_TIME * config.DEMO_SPEED)
    
    logger.settlement("Escrow released successfully")
    
    # Simulate SOL transfer
    tx_hash = helpers.generate_tx_hash()
    with logger.console.status("[bold green]Processing SOL transfer...", spinner="dots"):
        time.sleep(0.5 * config.DEMO_SPEED)
    
    logger.settlement(f"Transfer confirmed: {helpers.truncate_hash(tx_hash)}")
    
    # Display settlement panel
    logger.settlement_panel({
        "Task": task["task_id"],
        "Robot": robot_id,
        "Gross Reward": helpers.format_sol(reward),
        "Platform Fee": f"- {helpers.format_sol(platform_fee)} ({config.PLATFORM_FEE_RATE*100:.0f}%)",
        "Net Payment": helpers.format_sol(net_reward),
        "New Balance": helpers.format_sol(new_balance),
        "TX Hash": helpers.truncate_hash(tx_hash),
        "Status": "SETTLED",
    })
    
    return {
        "type": "REWARD",
        "task_id": task["task_id"],
        "gross_reward": reward,
        "platform_fee": platform_fee,
        "net_reward": net_reward,
        "new_balance": new_balance,
        "tx_hash": tx_hash,
        "success": True,
    }


def _process_slashing(task: dict, robot_id: str, robot_balance: float) -> dict:
    """Process slashing penalty for failed task."""
    
    reward = task["reward_sol"]
    slash_amount = round(reward * config.SLASHING_RATE, 4)
    new_balance = round(max(0, robot_balance - slash_amount), 4)
    
    # Simulate slashing
    with logger.console.status("[bold red]Processing slashing penalty...", spinner="dots"):
        time.sleep(config.ESCROW_HOLD_TIME * config.DEMO_SPEED)
    
    tx_hash = helpers.generate_tx_hash()
    
    logger.error(f"⚠️  SLASHING APPLIED: {helpers.format_sol(slash_amount)}")
    logger.status_panel("⛔ SLASHING PENALTY", {
        "Task": task["task_id"],
        "Robot": robot_id,
        "Slash Rate": f"{config.SLASHING_RATE * 100:.0f}%",
        "Penalty": f"- {helpers.format_sol(slash_amount)}",
        "New Balance": helpers.format_sol(new_balance),
        "TX Hash": helpers.truncate_hash(tx_hash),
        "Status": "SLASHED",
    }, border_style="red")
    
    return {
        "type": "SLASH",
        "task_id": task["task_id"],
        "slash_amount": slash_amount,
        "new_balance": new_balance,
        "tx_hash": tx_hash,
        "success": False,
    }
