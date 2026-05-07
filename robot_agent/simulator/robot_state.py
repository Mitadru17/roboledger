"""
RoboLedger — Robot State Machine
===================================
Manages robot state transitions through the task lifecycle.

States:
    IDLE → SCANNING → EVALUATING → BIDDING → NAVIGATING → 
    PROVING → VERIFYING → SETTLING → IDLE

Each state transition is validated to prevent illegal jumps.
"""

import sys
import os
from enum import Enum
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import logger


class RobotState(Enum):
    """Robot lifecycle states."""
    INITIALIZING = "INITIALIZING"
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    EVALUATING = "EVALUATING"
    BIDDING = "BIDDING"
    NAVIGATING = "NAVIGATING"
    PROVING = "PROVING"
    VERIFYING = "VERIFYING"
    SETTLING = "SETTLING"
    CHARGING = "CHARGING"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


# Valid state transitions
VALID_TRANSITIONS = {
    RobotState.INITIALIZING: [RobotState.IDLE],
    RobotState.IDLE: [RobotState.SCANNING, RobotState.CHARGING, RobotState.SHUTDOWN],
    RobotState.SCANNING: [RobotState.EVALUATING, RobotState.IDLE, RobotState.ERROR],
    RobotState.EVALUATING: [RobotState.BIDDING, RobotState.SCANNING, RobotState.IDLE],
    RobotState.BIDDING: [RobotState.NAVIGATING, RobotState.SCANNING, RobotState.IDLE, RobotState.ERROR],
    RobotState.NAVIGATING: [RobotState.PROVING, RobotState.ERROR, RobotState.IDLE],
    RobotState.PROVING: [RobotState.VERIFYING, RobotState.ERROR],
    RobotState.VERIFYING: [RobotState.SETTLING, RobotState.ERROR],
    RobotState.SETTLING: [RobotState.IDLE, RobotState.ERROR],
    RobotState.CHARGING: [RobotState.IDLE],
    RobotState.ERROR: [RobotState.IDLE, RobotState.SHUTDOWN],
}

# State display icons
STATE_ICONS = {
    RobotState.INITIALIZING: "⚡",
    RobotState.IDLE: "😴",
    RobotState.SCANNING: "📡",
    RobotState.EVALUATING: "🧠",
    RobotState.BIDDING: "💰",
    RobotState.NAVIGATING: "🚀",
    RobotState.PROVING: "📍",
    RobotState.VERIFYING: "🔐",
    RobotState.SETTLING: "💸",
    RobotState.CHARGING: "🔋",
    RobotState.ERROR: "❌",
    RobotState.SHUTDOWN: "⏹️",
}


class Robot:
    """
    Core robot entity managing state, position, battery, and history.
    """

    def __init__(self):
        """Initialize robot with default configuration."""
        self.robot_id = config.ROBOT_ID
        self.name = config.ROBOT_NAME
        self.model = config.ROBOT_MODEL
        self.version = config.ROBOT_VERSION
        
        # State
        self.state = RobotState.INITIALIZING
        self.position = (config.INITIAL_LAT, config.INITIAL_LON)
        self.battery = config.INITIAL_BATTERY
        
        # Financial
        self.balance_sol = 0.0
        self.total_earned = 0.0
        self.total_slashed = 0.0
        
        # Task history
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.current_task = None
        self.task_history = []
        
        # Timing
        self.start_time = datetime.now(timezone.utc)
        self.state_history = []
    
    def transition(self, new_state: RobotState) -> bool:
        """
        Transition to a new state with validation.
        
        Args:
            new_state: Target state
            
        Returns:
            True if transition was valid and executed
        """
        valid = VALID_TRANSITIONS.get(self.state, [])
        if new_state not in valid:
            logger.error(
                f"Invalid state transition: {self.state.value} → {new_state.value}"
            )
            return False
        
        old_state = self.state
        self.state = new_state
        icon = STATE_ICONS.get(new_state, "•")
        
        self.state_history.append({
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.robot(f"{icon} State: {old_state.value} → {new_state.value}")
        return True
    
    def update_position(self, lat: float, lon: float):
        """Update the robot's current position."""
        self.position = (lat, lon)
    
    def drain_battery(self, amount: float):
        """Drain battery by specified percentage."""
        self.battery = max(0, self.battery - amount)
    
    def charge_battery(self, amount: float):
        """Charge battery by specified percentage."""
        self.battery = min(100.0, self.battery + amount)
    
    def add_earnings(self, amount: float):
        """Record earnings from a task."""
        self.balance_sol += amount
        self.total_earned += amount
    
    def apply_slash(self, amount: float):
        """Record slashing penalty."""
        self.balance_sol = max(0, self.balance_sol - amount)
        self.total_slashed += amount
    
    def record_task_completion(self, task_id: str, success: bool, reward: float):
        """Record a completed task."""
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        self.task_history.append({
            "task_id": task_id,
            "success": success,
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability based on task history."""
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.95  # Default for new robots
        return self.tasks_completed / total
    
    @property
    def is_battery_low(self) -> bool:
        """Check if battery is below threshold."""
        return self.battery < config.MIN_BATTERY_THRESHOLD
    
    def get_status(self) -> dict:
        """Get current robot status for display."""
        return {
            "Robot ID": self.robot_id,
            "Name": self.name,
            "Model": self.model,
            "State": f"{STATE_ICONS.get(self.state, '')} {self.state.value}",
            "Position": f"({self.position[0]:.6f}, {self.position[1]:.6f})",
            "Battery": f"{'🔋' if self.battery > 30 else '🪫'} {self.battery:.1f}%",
            "Balance": f"◎ {self.balance_sol:.4f} SOL",
            "Tasks Done": str(self.tasks_completed),
            "Tasks Failed": str(self.tasks_failed),
            "Reliability": f"{self.reliability_score * 100:.1f}%",
        }
