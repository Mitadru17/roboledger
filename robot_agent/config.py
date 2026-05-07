"""
RoboLedger — Configuration Module
==================================
Central configuration for the entire robot agent system.
Loads settings from environment variables with sensible defaults.

Architecture Note:
    All modules import from config.py to avoid hardcoded values.
    This makes the system easy to reconfigure for different demo scenarios.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# ─────────────────────────────────────────────
# Solana Network Configuration
# ─────────────────────────────────────────────
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.devnet.solana.com/")
NETWORK = os.getenv("NETWORK", "devnet")

# ─────────────────────────────────────────────
# Robot Identity & Defaults
# ─────────────────────────────────────────────
ROBOT_NAME = os.getenv("ROBOT_NAME", "RoboAgent-Alpha")
ROBOT_ID = os.getenv("ROBOT_ID", "ROBO-001")
ROBOT_MODEL = os.getenv("ROBOT_MODEL", "RoboLedger-X1")
ROBOT_VERSION = "1.0.0"

# ─────────────────────────────────────────────
# Wallet Configuration
# ─────────────────────────────────────────────
WALLET_PATH = os.getenv("WALLET_PATH", "wallet/keypair.json")

# ─────────────────────────────────────────────
# Robot Physical Defaults
# ─────────────────────────────────────────────
INITIAL_BATTERY = float(os.getenv("INITIAL_BATTERY", "100.0"))       # percentage
BATTERY_DRAIN_RATE = float(os.getenv("BATTERY_DRAIN_RATE", "0.8"))   # % per unit distance
MIN_BATTERY_THRESHOLD = float(os.getenv("MIN_BATTERY_THRESHOLD", "15.0"))  # abort below this
CHARGE_RATE = float(os.getenv("CHARGE_RATE", "5.0"))                 # % per second charging
ROBOT_SPEED = float(os.getenv("ROBOT_SPEED", "2.5"))                 # units per second

# Initial coordinates (simulated campus environment)
INITIAL_LAT = float(os.getenv("INITIAL_LAT", "37.7749"))
INITIAL_LON = float(os.getenv("INITIAL_LON", "-122.4194"))

# ─────────────────────────────────────────────
# Task Marketplace Configuration
# ─────────────────────────────────────────────
TASK_SCAN_INTERVAL = float(os.getenv("TASK_SCAN_INTERVAL", "2.0"))     # seconds between scans
MAX_TASK_DISTANCE = float(os.getenv("MAX_TASK_DISTANCE", "50.0"))      # max distance willing to travel
MIN_REWARD_SOL = float(os.getenv("MIN_REWARD_SOL", "0.05"))           # minimum reward to consider
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "1"))
TASK_TIMEOUT = float(os.getenv("TASK_TIMEOUT", "120.0"))               # seconds before task expires
NUM_DEMO_TASKS = int(os.getenv("NUM_DEMO_TASKS", "3"))                # tasks to run in demo mode

# ─────────────────────────────────────────────
# Bid Configuration
# ─────────────────────────────────────────────
BID_ACCEPTANCE_RATE = float(os.getenv("BID_ACCEPTANCE_RATE", "0.95"))  # 95% acceptance for demo reliability
BID_RESPONSE_TIME = float(os.getenv("BID_RESPONSE_TIME", "1.5"))      # seconds to wait for response
BID_MARKUP = float(os.getenv("BID_MARKUP", "0.10"))                   # 10% markup on base cost

# ─────────────────────────────────────────────
# Settlement & Slashing
# ─────────────────────────────────────────────
PLATFORM_FEE_RATE = float(os.getenv("PLATFORM_FEE_RATE", "0.05"))     # 5% platform fee
SLASHING_RATE = float(os.getenv("SLASHING_RATE", "0.25"))             # 25% stake slashed on failure
ESCROW_HOLD_TIME = float(os.getenv("ESCROW_HOLD_TIME", "1.0"))        # seconds to simulate escrow
FAILURE_PROBABILITY = float(os.getenv("FAILURE_PROBABILITY", "0.10")) # 10% chance of task failure

# ─────────────────────────────────────────────
# BFT Verification
# ─────────────────────────────────────────────
NUM_VALIDATORS = int(os.getenv("NUM_VALIDATORS", "5"))
MIN_CONSENSUS = int(os.getenv("MIN_CONSENSUS", "3"))                  # 3 of 5 must agree
VALIDATOR_RESPONSE_TIME = float(os.getenv("VALIDATOR_RESPONSE_TIME", "0.5"))

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"

# ─────────────────────────────────────────────
# Navigation Simulation
# ─────────────────────────────────────────────
NAV_UPDATE_INTERVAL = float(os.getenv("NAV_UPDATE_INTERVAL", "0.3"))  # seconds between position updates
NAV_WAYPOINT_JITTER = float(os.getenv("NAV_WAYPOINT_JITTER", "0.001"))  # coordinate noise

# ─────────────────────────────────────────────
# Display Configuration
# ─────────────────────────────────────────────
ENABLE_ANIMATIONS = os.getenv("ENABLE_ANIMATIONS", "true").lower() == "true"
DEMO_SPEED = float(os.getenv("DEMO_SPEED", "1.0"))  # 1.0 = normal, 0.5 = fast, 2.0 = slow

# ─────────────────────────────────────────────
# Failure Scenarios (Showcase Mode)
# ─────────────────────────────────────────────
BATTERY_FAILURE_PROB = float(os.getenv("BATTERY_FAILURE_PROB", "0.15"))      # low battery reject
PROOF_REJECTION_PROB = float(os.getenv("PROOF_REJECTION_PROB", "0.12"))      # BFT proof rejection
TIMEOUT_FAILURE_PROB = float(os.getenv("TIMEOUT_FAILURE_PROB", "0.08"))      # task timeout
NAV_INTERRUPT_PROB = float(os.getenv("NAV_INTERRUPT_PROB", "0.10"))          # nav interruption
VALIDATOR_DISAGREE_PROB = float(os.getenv("VALIDATOR_DISAGREE_PROB", "0.20"))# validator disagreement

# ─────────────────────────────────────────────
# Multi-Robot Competition (Showcase Mode)
# ─────────────────────────────────────────────
SHOWCASE_ROBOTS = int(os.getenv("SHOWCASE_ROBOTS", "4"))                    # fleet size

# ─────────────────────────────────────────────
# Webots Integration
# ─────────────────────────────────────────────
WEBOTS_ENABLED = os.getenv("WEBOTS_ENABLED", "false").lower() == "true"
WEBOTS_DATA_DIR = os.path.abspath(os.getenv("WEBOTS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webots_data")))
WEBOTS_POLL_INTERVAL = float(os.getenv("WEBOTS_POLL_INTERVAL", "0.2"))       # seconds
WEBOTS_ARRIVAL_THRESHOLD = float(os.getenv("WEBOTS_ARRIVAL_THRESHOLD", "0.3"))  # meters
WEBOTS_NAV_TIMEOUT = float(os.getenv("WEBOTS_NAV_TIMEOUT", "120"))           # seconds

# Coordinate mapping: Webots 20m arena ↔ GPS campus
WEBOTS_ARENA_HALF = 10.0
WEBOTS_GPS_LAT_CENTER = 37.7750
WEBOTS_GPS_LON_CENTER = -122.41875
WEBOTS_GPS_LAT_HALF_RANGE = 0.002
WEBOTS_GPS_LON_HALF_RANGE = 0.00325

# ─────────────────────────────────────────────
# Application Metadata
# ─────────────────────────────────────────────
APP_NAME = "RoboLedger"
APP_TAGLINE = "Decentralized Robot Coordination & Settlement Protocol"
APP_VERSION = "0.3.0"
