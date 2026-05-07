"""
RoboLedger — Solana RPC Client
================================
Manages connection to Solana Devnet for blockchain operations.

Architecture Note:
    This module wraps the solana-py Client to provide:
    - Connection health checking with retries
    - Balance queries
    - Airdrop requests for testing
    - Status display using Rich
    
    In production, this would connect to a Solana program (smart contract).
    In simulation, we use real Devnet RPC for connection/balance operations
    and mock the program-specific interactions.
"""

import sys
import os
import time

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger


class SolanaClient:
    """
    Wrapper around solana-py Client for RoboLedger operations.
    Provides connection management, balance checks, and airdrop requests.
    """
    
    def __init__(self):
        """Initialize the Solana RPC client."""
        self.rpc_url = config.SOLANA_RPC_URL
        self.client = None
        self.connected = False
        self.slot = 0
    
    def connect(self) -> bool:
        """
        Establish connection to Solana Devnet with retry logic.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.section("SOLANA NETWORK CONNECTION")
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.solana(f"Connecting to {config.NETWORK}... (attempt {attempt}/{max_retries})")
                
                self.client = Client(self.rpc_url)
                
                # Health check — get current slot
                # Using a simple getSlot call to verify connectivity
                try:
                    response = self.client.get_slot(commitment=Confirmed)
                    self.slot = response.value
                    self.connected = True
                    
                    logger.success(f"Connected to Solana {config.NETWORK}")
                    logger.status_panel("Solana Connection", {
                        "Network": config.NETWORK.upper(),
                        "RPC Endpoint": self.rpc_url,
                        "Current Slot": f"#{self.slot:,}",
                        "Status": "🟢 CONNECTED",
                    }, border_style="blue")
                    
                    return True
                except Exception:
                    # If RPC call fails (e.g., rate limited), still consider connected
                    # The client object is valid, we just couldn't verify slot
                    self.connected = True
                    logger.warning("Connected to RPC (slot verification skipped)")
                    logger.status_panel("Solana Connection", {
                        "Network": config.NETWORK.upper(),
                        "RPC Endpoint": self.rpc_url,
                        "Status": "🟡 CONNECTED (unverified)",
                    }, border_style="yellow")
                    return True
                    
            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    wait_time = attempt * 2
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        
        logger.error("Failed to connect to Solana Devnet after all retries")
        logger.info("Continuing in offline simulation mode...")
        self.connected = False
        return False
    
    def get_balance(self, pubkey_str: str) -> float:
        """
        Get SOL balance for a public key.
        
        Args:
            pubkey_str: Base58-encoded public key
            
        Returns:
            Balance in SOL (0.0 if offline)
        """
        if not self.connected or not self.client:
            return 0.0
        
        try:
            pubkey = Pubkey.from_string(pubkey_str)
            response = self.client.get_balance(pubkey, commitment=Confirmed)
            # Balance is in lamports (1 SOL = 1e9 lamports)
            lamports = response.value
            return lamports / 1e9
        except Exception as e:
            logger.warning(f"Balance check failed: {e}")
            return 0.0
    
    def request_airdrop(self, pubkey_str: str, amount_sol: float = 1.0) -> bool:
        """
        Request SOL airdrop from Devnet faucet.
        
        Args:
            pubkey_str: Recipient public key
            amount_sol: Amount of SOL to request (max 2 on devnet)
            
        Returns:
            True if airdrop confirmed, False otherwise
        """
        if not self.connected or not self.client:
            logger.warning("Cannot airdrop — not connected to Solana")
            return False
        
        try:
            pubkey = Pubkey.from_string(pubkey_str)
            lamports = int(amount_sol * 1e9)
            
            logger.solana(f"Requesting airdrop of {amount_sol} SOL...")
            response = self.client.request_airdrop(pubkey, lamports, commitment=Confirmed)
            
            if response.value:
                logger.success(f"Airdrop confirmed: {amount_sol} SOL received")
                return True
            else:
                logger.warning("Airdrop request sent but not confirmed")
                return False
                
        except Exception as e:
            logger.warning(f"Airdrop failed (devnet rate limit likely): {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get current connection status information."""
        return {
            "connected": self.connected,
            "rpc_url": self.rpc_url,
            "network": config.NETWORK,
            "slot": self.slot,
        }
