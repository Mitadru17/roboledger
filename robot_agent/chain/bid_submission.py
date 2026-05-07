"""
RoboLedger — Bid Submission Module
=====================================
Handles task bid creation, submission, and acceptance logic.

Architecture Note:
    In the RoboLedger protocol, robots compete for tasks by submitting bids.
    A bid includes the robot's proposed price, estimated completion time,
    and reliability score. The task requester (or smart contract) selects
    the optimal bid based on these factors.
    
    In production, bids would be Solana transactions calling a bid_on_task
    instruction on the RoboLedger program. In simulation, we create
    realistic bid payloads and simulate the acceptance process.
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers


def create_bid(
    robot_id: str,
    robot_pubkey: str,
    task: dict,
    robot_position: tuple,
    battery_level: float,
    reliability_score: float = 0.95,
) -> dict:
    """
    Create a bid payload for a task.
    
    The bid includes the robot's offer, estimated completion time,
    and capability assessment. In production, this would be serialized
    as instruction data for a Solana transaction.
    
    Args:
        robot_id: Robot identifier
        robot_pubkey: Robot's Solana public key
        task: Task to bid on
        robot_position: Current robot position
        battery_level: Current battery percentage
        reliability_score: Robot's historical reliability (0-1)
        
    Returns:
        dict: Complete bid payload
    """
    # Calculate bid amount (competitive pricing based on distance + markup)
    base_cost = task["distance_estimate"] * 0.008  # cost per distance unit
    bid_amount = round(base_cost * (1 + config.BID_MARKUP), 4)
    
    # Ensure bid doesn't exceed task reward
    bid_amount = min(bid_amount, task["reward_sol"] * 0.95)
    
    # Calculate ETA
    distance = task["distance_estimate"]
    eta_seconds = helpers.calculate_eta(distance, config.ROBOT_SPEED)
    
    bid = {
        "bid_id": f"BID-{helpers.generate_task_id().split('-')[1]}",
        "task_id": task["task_id"],
        "robot_id": robot_id,
        "robot_pubkey": robot_pubkey,
        "bid_amount_sol": bid_amount,
        "eta_seconds": round(eta_seconds, 1),
        "battery_level": round(battery_level, 1),
        "reliability_score": round(reliability_score, 3),
        "timestamp": helpers.format_timestamp(),
        "distance_to_start": task.get("distance_to_start", 0),
        "status": "PENDING",
    }
    
    logger.info(f"Bid created: {bid['bid_id']} for {task['task_id']}")
    logger.status_panel("📝 Bid Details", {
        "Bid ID": bid["bid_id"],
        "Task": bid["task_id"],
        "Bid Amount": helpers.format_sol(bid["bid_amount_sol"]),
        "ETA": helpers.format_duration(bid["eta_seconds"]),
        "Battery": f"{bid['battery_level']}%",
        "Reliability": f"{bid['reliability_score'] * 100:.1f}%",
    }, border_style="yellow")
    
    return bid


def submit_bid(bid: dict) -> dict:
    """
    Submit a bid to the task marketplace.
    
    In production, this would:
    1. Serialize bid as instruction data
    2. Create a Solana transaction
    3. Sign with robot's keypair
    4. Submit to the network
    5. Wait for confirmation
    
    In simulation, we mock the submission with realistic timing
    and weighted random acceptance.
    
    Args:
        bid: Bid payload to submit
        
    Returns:
        dict: Submission result with acceptance status
    """
    logger.section("BID SUBMISSION")
    
    # Simulate transaction creation and signing
    with logger.console.status("[bold yellow]Creating bid transaction...", spinner="dots"):
        time.sleep(0.8 * config.DEMO_SPEED)
    
    tx_hash = helpers.generate_tx_hash()
    logger.solana(f"Transaction created: {helpers.truncate_hash(tx_hash)}")
    
    # Simulate submission to network
    with logger.console.status("[bold yellow]Submitting bid to Solana Devnet...", spinner="dots"):
        time.sleep(config.BID_RESPONSE_TIME * config.DEMO_SPEED)
    
    logger.solana(f"Transaction submitted | slot pending")
    
    # Simulate acceptance decision
    # Higher reliability and lower bid amounts have better acceptance chances
    acceptance_modifier = bid["reliability_score"] * 0.1
    accepted = random.random() < (config.BID_ACCEPTANCE_RATE + acceptance_modifier)
    
    # Simulate confirmation wait
    with logger.console.status("[bold yellow]Waiting for on-chain confirmation...", spinner="dots"):
        time.sleep(0.5 * config.DEMO_SPEED)
    
    result = {
        "bid_id": bid["bid_id"],
        "task_id": bid["task_id"],
        "tx_hash": tx_hash,
        "accepted": accepted,
        "status": "ACCEPTED" if accepted else "REJECTED",
        "confirmation_slot": random.randint(200000000, 300000000),
    }
    
    if accepted:
        logger.success(f"🎯 Bid ACCEPTED! Task {bid['task_id']} assigned to robot")
        logger.status_panel("✅ Bid Accepted", {
            "Bid ID": bid["bid_id"],
            "Task": bid["task_id"],
            "Reward": helpers.format_sol(bid["bid_amount_sol"]),
            "TX Hash": helpers.truncate_hash(tx_hash),
            "Slot": f"#{result['confirmation_slot']:,}",
        }, border_style="green")
    else:
        logger.warning(f"Bid REJECTED for {bid['task_id']} — another robot won")
        result["reason"] = random.choice([
            "Lower bid received from competing robot",
            "Task already assigned",
            "Insufficient reliability score",
        ])
        logger.info(f"Reason: {result['reason']}")
    
    return result
