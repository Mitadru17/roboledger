"""
RoboLedger — Wallet Keypair Loader
====================================
Manages Ed25519 keypair generation, loading, and persistence.
Uses solders for Solana-compatible keypair operations.

Architecture Note:
    The wallet is the robot's on-chain identity. Each robot agent has
    a unique Solana keypair used for signing proofs and receiving payments.
    On first run, a new keypair is auto-generated and saved to disk.
"""

import os
import sys
import json

# Solders for Solana keypair management
from solders.keypair import Keypair

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger


def _get_wallet_path() -> str:
    """Get absolute path to the keypair file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, config.WALLET_PATH)


def generate_keypair() -> Keypair:
    """
    Generate a fresh Ed25519 keypair and save to disk.
    
    Returns:
        Keypair: New Solana-compatible keypair
    """
    kp = Keypair()
    wallet_path = _get_wallet_path()
    
    # Ensure wallet directory exists
    os.makedirs(os.path.dirname(wallet_path), exist_ok=True)
    
    # Save as JSON array of secret key bytes (Solana CLI compatible format)
    secret_bytes = list(bytes(kp))
    with open(wallet_path, "w") as f:
        json.dump(secret_bytes, f)
    
    logger.success(f"New wallet generated and saved to {config.WALLET_PATH}")
    return kp


def load_keypair() -> Keypair:
    """
    Load existing keypair from disk, or generate new one if not found.
    
    Returns:
        Keypair: The robot's Solana keypair
    """
    wallet_path = _get_wallet_path()
    
    if os.path.exists(wallet_path):
        try:
            with open(wallet_path, "r") as f:
                secret_bytes = json.load(f)
            
            # Reconstruct keypair from secret key bytes
            kp = Keypair.from_bytes(bytes(secret_bytes))
            logger.success(f"Wallet loaded from {config.WALLET_PATH}")
            return kp
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Corrupt wallet file, generating new keypair: {e}")
            return generate_keypair()
    else:
        logger.info("No wallet found — generating new keypair...")
        return generate_keypair()


def get_public_key_str(keypair: Keypair) -> str:
    """Get the base58-encoded public key string."""
    return str(keypair.pubkey())


def get_keypair_info(keypair: Keypair) -> dict:
    """Get displayable wallet information."""
    pubkey = str(keypair.pubkey())
    return {
        "Public Key": pubkey,
        "Short Address": f"{pubkey[:8]}...{pubkey[-8:]}",
        "Wallet File": config.WALLET_PATH,
    }
