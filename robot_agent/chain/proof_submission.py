"""
RoboLedger — Proof Submission Module
=======================================
Submits signed proofs to the Solana network for verification.
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from proof.gps_proof import GPSProof
from proof import verifier


def submit_proof(signed_proof: dict, proof_obj: GPSProof) -> dict:
    """Submit a signed proof to the Solana network for BFT verification."""
    logger.section("PROOF SUBMISSION")
    logger.status_panel("GPS Proof Payload", proof_obj.get_display_info(), border_style="cyan")

    with logger.console.status("[bold cyan]Creating proof submission TX...", spinner="dots"):
        time.sleep(0.6 * config.DEMO_SPEED)

    tx_hash = helpers.generate_tx_hash()
    logger.solana(f"Proof TX created: {helpers.truncate_hash(tx_hash)}")

    with logger.console.status("[bold cyan]Broadcasting proof to Solana Devnet...", spinner="dots"):
        time.sleep(0.8 * config.DEMO_SPEED)

    logger.solana("Transaction broadcast to cluster nodes")

    with logger.console.status("[bold cyan]Awaiting on-chain confirmation...", spinner="dots"):
        time.sleep(0.5 * config.DEMO_SPEED)

    confirmation_slot = helpers.generate_tx_hash()[:12]
    logger.success(f"Proof recorded on-chain | slot: {confirmation_slot}")

    logger.info("Triggering SwarmProof BFT verification protocol...")
    time.sleep(0.3 * config.DEMO_SPEED)

    verification_result = verifier.simulate_bft_verification(
        proof=proof_obj,
        signature_b58=signed_proof["signature"],
        signer_pubkey=signed_proof["signer"],
    )

    return {
        "tx_hash": tx_hash,
        "proof_id": proof_obj.proof_id,
        "task_id": proof_obj.task_id,
        "verified": verification_result["consensus"],
        "verification": verification_result,
        "on_chain_slot": confirmation_slot,
    }
