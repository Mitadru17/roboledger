"""
RoboLedger — Proof Verifier
==============================
Verifies Ed25519 signatures and simulates BFT multi-validator consensus.

Architecture Note:
    In the RoboLedger protocol, submitted proofs must pass two checks:
    
    1. Cryptographic Verification — Ed25519 signature matches the proof data
       and the signer's public key. This is deterministic and trustless.
       
    2. BFT Consensus — Multiple validator nodes independently verify the proof
       and vote on acceptance. A minimum of 3/5 validators must approve for
       the proof to be accepted (Byzantine Fault Tolerance).
    
    In production, validators would be separate network nodes running
    verification logic. In simulation, we mock this with realistic timing.
"""

import sys
import os
import time
import random
import base58

from solders.pubkey import Pubkey
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger, helpers
from proof.gps_proof import GPSProof


def verify_signature(proof: GPSProof, signature_b58: str, signer_pubkey: str) -> bool:
    """
    Verify an Ed25519 signature against proof data and public key.
    
    This is the real cryptographic verification — not simulated.
    
    Args:
        proof: The GPS proof that was signed
        signature_b58: Base58-encoded signature
        signer_pubkey: Base58-encoded public key of signer
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Decode the signature from base58
        signature_bytes = base58.b58decode(signature_b58)
        
        # Get the public key bytes from the Solana public key
        pubkey = Pubkey.from_string(signer_pubkey)
        pubkey_bytes = bytes(pubkey)
        
        # Create a VerifyKey from the public key
        verify_key = VerifyKey(pubkey_bytes)
        
        # Get the proof bytes that were signed
        proof_bytes = proof.to_bytes()
        
        # Verify the signature
        verify_key.verify(proof_bytes, signature_bytes)
        
        logger.success("Cryptographic signature verified ✓")
        return True
        
    except BadSignatureError:
        logger.error("Signature verification FAILED — invalid signature")
        return False
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def simulate_bft_verification(
    proof: GPSProof,
    signature_b58: str,
    signer_pubkey: str,
) -> dict:
    """
    Simulate BFT (Byzantine Fault Tolerance) multi-validator consensus.
    
    Process:
        1. Spawn N validator nodes (simulated)
        2. Each validator independently verifies the proof
        3. Validators vote approve/reject with simulated latency
        4. Check if minimum consensus threshold is met
    
    Args:
        proof: GPS proof to verify
        signature_b58: The signature to check
        signer_pubkey: Public key of the signer
        
    Returns:
        dict with validation results and consensus status
    """
    logger.section("BFT CONSENSUS VERIFICATION")
    
    # First, do the real cryptographic verification
    sig_valid = verify_signature(proof, signature_b58, signer_pubkey)
    
    if not sig_valid:
        return {
            "consensus": False,
            "validators": [],
            "reason": "Cryptographic signature invalid",
        }
    
    # Simulate multiple validator nodes processing
    validators = []
    num_validators = config.NUM_VALIDATORS
    min_consensus = config.MIN_CONSENSUS
    
    for i in range(num_validators):
        # Simulate validator processing time
        process_time = random.uniform(0.2, config.VALIDATOR_RESPONSE_TIME) * config.DEMO_SPEED
        time.sleep(process_time)
        
        # Each validator has a high probability of approving valid proofs
        # In BFT, up to (n-1)/3 can be faulty — we simulate ~90% approval rate
        approved = random.random() < 0.92
        
        validator = {
            "name": f"Validator-{chr(65 + i)}{random.randint(10, 99):02d}",
            "approved": approved,
            "time_ms": int(process_time * 1000),
        }
        validators.append(validator)
        
        status = "[green]APPROVED[/green]" if approved else "[red]REJECTED[/red]"
        logger.console.print(f"    🔒 {validator['name']}: {status} ({validator['time_ms']}ms)")
    
    # Check consensus
    approvals = sum(1 for v in validators if v["approved"])
    consensus = approvals >= min_consensus
    
    # Display verification panel
    logger.verification_panel(validators, consensus)
    
    if consensus:
        logger.success(f"BFT Consensus reached: {approvals}/{num_validators} validators approved")
    else:
        logger.error(f"BFT Consensus FAILED: only {approvals}/{num_validators} approved (need {min_consensus})")
    
    return {
        "consensus": consensus,
        "approvals": approvals,
        "total_validators": num_validators,
        "min_required": min_consensus,
        "validators": validators,
    }
