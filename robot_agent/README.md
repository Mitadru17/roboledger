# 🤖 RoboLedger

**Decentralized Robot Coordination & Settlement Protocol on Solana**

> An autonomous robot agent simulation system for decentralized task execution, proof verification, and automatic settlement — built for hackathons and university robotics labs.

---

## 🏗️ Architecture

```
robot_agent/
│
├── main.py                    # Entry point — cinematic demo launcher
├── config.py                  # Central configuration (env-driven)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
│
├── wallet/                    # 🔑 Solana Wallet Management
│   ├── keypair_loader.py      # Ed25519 keypair generation & loading
│   └── keypair.json           # Auto-generated wallet (gitignored)
│
├── chain/                     # 🔗 Solana Integration
│   ├── rpc_client.py          # Devnet RPC connection & health checks
│   ├── task_reader.py         # Mock task marketplace with realistic data
│   ├── bid_submission.py      # Competitive bid creation & submission
│   ├── proof_submission.py    # On-chain proof submission pipeline
│   └── settlement.py          # Escrow release, rewards & slashing
│
├── simulator/                 # 🚀 Robot Simulation Engine
│   ├── robot_state.py         # State machine with validated transitions
│   ├── navigation.py          # Waypoint navigation with progress bars
│   ├── battery.py             # Battery drain & charging model
│   └── lifecycle.py           # Main orchestration loop
│
├── proof/                     # 🔐 Cryptographic Proof System
│   ├── gps_proof.py           # GPS proof payload generation
│   ├── signer.py              # Ed25519 proof signing
│   └── verifier.py            # Signature verification & BFT consensus
│
├── utils/                     # 🛠️ Utilities
│   ├── logger.py              # Rich terminal visualization
│   └── helpers.py             # Distance, formatting, ID generation
│
└── logs/                      # 📝 Runtime log files
```

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.9+
- pip

### 2. Setup

```bash
# Clone and navigate
cd roboledger/robot_agent

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Copy and customize .env
copy .env.example .env
```

### 3. Run the Demo

```bash
# Standard demo (3 task cycles)
python main.py

# Fast mode for quick demos
python main.py --fast

# Custom cycles and robot name
python main.py --cycles 5 --name "DeliveryBot-X7"

# Offline mode (skip Solana connection)
python main.py --offline

# Multi-robot swarm simulation (3 robots)
python main.py --robots 3 --fast
```

## 🎬 Demo Lifecycle

```
[🤖 Robot Agent Started]
       ↓
[📡 Scanning Task Marketplace...]
       ↓
[📋 Task Detected: DELIVERY-7A3F]
       ↓
[🧠 Evaluating: Battery ✓ Distance ✓ Reward ✓ → Score: 87/100]
       ↓
[💰 Bid Submitted: 0.15 SOL → Accepted ✓]
       ↓
[🚀 Navigating: ████████████░░░░ 75% | ETA: 12s]
       ↓
[📍 GPS Proof Generated: hash=0x7f3a...]
       ↓
[🔐 Proof Signed: sig=0x9b2c...]
       ↓
[✅ BFT Verified: 4/5 validators approved]
       ↓
[💸 Settlement: +0.15 SOL → Balance: 1.85 SOL]
```

## 🧠 Task Evaluation Scoring

Tasks are scored on a 100-point scale:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Battery Feasibility | 30 pts | Can complete task with safety margin |
| Reward Value | 25 pts | SOL reward amount relative to thresholds |
| Distance Efficiency | 25 pts | Reward per distance unit ratio |
| Priority Bonus | 20 pts | HIGH > MEDIUM > LOW priority tasks |

## 🔐 Proof System

1. **GPS Proof Generation** — Creates a proof payload with robot ID, task ID, timestamps, coordinates, path hash, and completion status
2. **Ed25519 Signing** — Signs the proof with the robot's Solana keypair using the same algorithm Solana uses for transactions
3. **BFT Verification** — Simulates 5 validator nodes independently checking the proof, requiring 3/5 consensus (Byzantine Fault Tolerance)

## 💰 Settlement

- **Success**: Task reward released from escrow minus 5% platform fee
- **Failure**: 25% of task reward slashed from robot's balance

## 🔧 Configuration

All settings can be customized via environment variables or `.env` file. See `.env.example` for all options:

- `SOLANA_RPC_URL` — Solana RPC endpoint
- `ROBOT_NAME` — Robot display name
- `DEMO_SPEED` — Animation speed (0.5=fast, 1.0=normal, 2.0=slow)
- `FAILURE_PROBABILITY` — Chance of simulated task failure (0.0-1.0)
- `NUM_DEMO_TASKS` — Default number of task cycles

## 🧪 Testing

```bash
# Run the full demo
python main.py

# Quick smoke test (fast mode, 1 cycle)
python main.py --fast --cycles 1

# Stress test (5 cycles, watch for errors)
python main.py --cycles 5

# Offline test (no network needed)
python main.py --offline --fast --cycles 2
```

## 📋 Task Types

| Type | Description | Reward Range |
|------|-------------|-------------|
| DELIVERY | Transport items between campus buildings | 0.10 - 0.35 SOL |
| INSPECTION | Check equipment and infrastructure | 0.08 - 0.20 SOL |
| PATROL | Security and surveillance routes | 0.12 - 0.28 SOL |
| SAMPLE_COLLECTION | Gather data and physical samples | 0.15 - 0.40 SOL |

## 🛡️ Error Handling

- **Battery abort**: Navigation stops if battery drops below threshold
- **Bid rejection**: Automatically retries with next-best ranked task
- **Proof failure**: Slashing penalty applied, robot continues operation
- **Network errors**: Graceful fallback to offline simulation
- **Keyboard interrupt**: Clean shutdown with session summary
- **Multi-robot**: Each agent runs independently with its own state

---

**Built for hackathons. Powered by Solana. 🚀**
