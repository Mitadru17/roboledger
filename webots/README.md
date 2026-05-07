# RoboLedger Webots Integration

This directory contains the files required to run a real-time, 3D Webots simulation synchronized with the RoboLedger autonomous protocol.

## Prerequisites
1. **Webots R2023b** (or newer) installed on Windows. Download from [cyberbotics.com](https://cyberbotics.com/).
2. A working Python environment for RoboLedger.

## How it Works
The integration uses a **two-process, JSON file-based bridge**:
1. **Webots Controller (`roboledger_controller.py`)**: Runs inside Webots' Python environment. Controls the robot motors based on GPS/compass data and a target destination.
2. **RoboLedger Engine (`main.py`)**: Runs in a standard terminal. Writes destination coordinates to `webots_data/robot_target.json` and reads live GPS positions from `webots_data/robot_position.json`.

This decoupling prevents any dependency conflicts between Webots' bundled Python and your system Python.

## Setup & Running

1. **Start the Webots Simulation**:
   - Open Webots.
   - Go to `File > Open World...` and select `webots/worlds/roboledger_arena.wbt`.
   - Ensure the simulation is running (press the Play button `▶` if it's paused).
   - You should see the robot and the Webots console waiting for targets.

2. **Start RoboLedger with Webots Flag**:
   - Open your standard terminal.
   - Activate your virtual environment: `.\venv\Scripts\activate`
   - Run the system with the `--webots` flag:
     ```bash
     python main.py --webots --offline
     ```

## What You Will See
- RoboLedger scans the marketplace and evaluates tasks.
- When a task is accepted, it writes the destination coordinates to the bridge.
- The Webots controller picks up the target, spawns a red marker sphere at the destination, and physically drives the e-puck robot there.
- The RoboLedger terminal displays a live progress bar reading the *actual* positions from Webots.
- Upon arrival, RoboLedger generates a cryptographic GPS proof using the real waypoints traversed in the 3D simulation.
- The BFT consensus network verifies the proof, and the escrow is settled!

## Troubleshooting

- **Robot isn't moving**: Ensure Webots is unpaused (`▶`). Ensure the controller in the Webots Scene Tree is set to `roboledger_controller`.
- **Navigation Timeout**: If Webots is running too slow or the target is unreachable, RoboLedger will timeout and simulate a failure (slashing).
- **Coordinate Mismatch**: Ensure `config.py` Webots settings match the 20x20m arena scaling.
