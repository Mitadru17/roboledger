"""
RoboLedger — Cryptographic Proof Signer
=========================================
Signs proof payloads using Ed25519 keypair for on-chain verification.

Architecture Note:
    Every GPS proof must be cryptographically signed before submission.
    The signature binds the proof data to the robot's identity (public key),
    preventing tampering and enabling trustless on-chain verification.
    
    Uses Ed25519 signatures via the solders library, which is the same
    signature scheme used by Solana for transaction signing.
"""

import sys
import os
import base58

from solders.keypair import Keypair

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import logger, helpers
from proof.gps_proof import GPSProof


class ProofSigner:
    """
    Signs GPS proof payloads using the robot's Ed25519 keypair.
    
    The signed proof can be verified by any party with access to
    the robot's public key, enabling decentralized trust.
    """
    
    def __init__(self, keypair: Keypair):
        """
        Initialize the signer with the robot's keypair.
        
        Args:
            keypair: Solana-compatible Ed25519 keypair
        """
        self.keypair = keypair
        self.public_key = str(keypair.pubkey())
    
    def sign_proof(self, proof: GPSProof) -> dict:
        """
        Sign a GPS proof payload.
        
        Process:
            1. Serialize proof to deterministic JSON bytes
            2. Sign bytes with Ed25519 private key
            3. Encode signature as base58 string
            4. Return signed proof package
        
        Args:
            proof: GPS proof to sign
            
        Returns:
            dict with signed proof data including signature
        """
        # Step 1: Get deterministic bytes representation
        proof_bytes = proof.to_bytes()
        
        # Step 2: Sign using Ed25519 via solders
        signature = self.keypair.sign_message(proof_bytes)
        
        # Step 3: Encode signature as base58 (Solana convention)
        sig_b58 = base58.b58encode(bytes(signature)).decode("utf-8")
        
        logger.proof(f"Proof signed | sig={helpers.truncate_hash(sig_b58, 6)}")
        
        # Step 4: Return complete signed proof package
        return {
            "proof": proof.to_dict(),
            "signature": sig_b58,
            "signer": self.public_key,
            "algorithm": "Ed25519",
            "encoding": "base58",
        }
    
    def sign_bytes(self, data: bytes) -> str:
        """
        Sign arbitrary bytes and return base58-encoded signature.
        Useful for signing transaction memos and other data.
        """
        signature = self.keypair.sign_message(data)
        return base58.b58encode(bytes(signature)).decode("utf-8")
