"""
RoboLedger — GPS Proof Generator
==================================
Generates cryptographic proof payloads for completed task deliveries.

Architecture Note:
    The GPS proof is the core evidence that a robot completed its task.
    It includes position data, timestamps, path hash, and completion status.
    This payload gets signed by the robot's keypair before on-chain submission.
    
    In production, this would integrate with actual GPS/SLAM sensors.
    In simulation, we generate realistic proof data from the navigation module.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import helpers


class GPSProof:
    """
    Represents a GPS-based proof of task completion.
    
    Contains all evidence needed to verify a robot completed
    a task: position data, timestamps, path information.
    """
    
    def __init__(
        self,
        robot_id: str,
        task_id: str,
        start_position: tuple,
        end_position: tuple,
        path_waypoints: list = None,
        completion_status: str = "COMPLETED",
        metadata: dict = None,
    ):
        """
        Create a new GPS proof.
        
        Args:
            robot_id: Unique robot identifier
            task_id: Task being proven
            start_position: (lat, lon) starting coordinates
            end_position: (lat, lon) ending coordinates
            path_waypoints: List of (lat, lon) waypoints traversed
            completion_status: COMPLETED | PARTIAL | FAILED
            metadata: Additional proof metadata
        """
        self.proof_id = helpers.generate_proof_id()
        self.robot_id = robot_id
        self.task_id = task_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.epoch_time = int(time.time())
        self.start_position = start_position
        self.end_position = end_position
        self.path_waypoints = path_waypoints or []
        self.completion_status = completion_status
        self.distance_traveled = self._calculate_total_distance()
        self.path_hash = self._compute_path_hash()
        self.metadata = metadata or {}
    
    def _calculate_total_distance(self) -> float:
        """Calculate total distance traveled along the path."""
        if not self.path_waypoints or len(self.path_waypoints) < 2:
            return helpers.haversine_distance(
                self.start_position[0], self.start_position[1],
                self.end_position[0], self.end_position[1]
            )
        
        total = 0.0
        for i in range(len(self.path_waypoints) - 1):
            total += helpers.haversine_distance(
                self.path_waypoints[i][0], self.path_waypoints[i][1],
                self.path_waypoints[i + 1][0], self.path_waypoints[i + 1][1]
            )
        return total
    
    def _compute_path_hash(self) -> str:
        """Compute a hash of the navigation path for integrity verification."""
        path_data = json.dumps({
            "start": self.start_position,
            "end": self.end_position,
            "waypoints_count": len(self.path_waypoints),
            "distance": round(self.distance_traveled, 4),
        }, sort_keys=True)
        return helpers.hash_payload(path_data)
    
    def to_dict(self) -> dict:
        """Serialize proof to dictionary."""
        return {
            "proof_id": self.proof_id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "epoch_time": self.epoch_time,
            "start_position": {
                "lat": self.start_position[0],
                "lon": self.start_position[1],
            },
            "end_position": {
                "lat": self.end_position[0],
                "lon": self.end_position[1],
            },
            "waypoints_count": len(self.path_waypoints),
            "distance_traveled": round(self.distance_traveled, 4),
            "path_hash": self.path_hash,
            "completion_status": self.completion_status,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Serialize proof to deterministic JSON string (for signing)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
    
    def to_bytes(self) -> bytes:
        """Serialize proof to bytes (for cryptographic signing)."""
        return self.to_json().encode("utf-8")
    
    def get_display_info(self) -> dict:
        """Get human-readable proof information for terminal display."""
        return {
            "Proof ID": self.proof_id,
            "Task": self.task_id,
            "Robot": self.robot_id,
            "Timestamp": self.timestamp[:19],
            "Start": helpers.format_coordinates(*self.start_position),
            "End": helpers.format_coordinates(*self.end_position),
            "Distance": f"{self.distance_traveled:.2f} units",
            "Waypoints": str(len(self.path_waypoints)),
            "Path Hash": helpers.truncate_hash(self.path_hash),
            "Status": self.completion_status,
        }


def generate_proof(
    robot_id: str,
    task_id: str,
    start_pos: tuple,
    end_pos: tuple,
    waypoints: list = None,
    success: bool = True,
) -> GPSProof:
    """
    Factory function to generate a GPS proof from navigation results.
    
    Args:
        robot_id: Robot that completed the task
        task_id: Task identifier
        start_pos: Starting coordinates
        end_pos: Ending coordinates
        waypoints: Path taken
        success: Whether task completed successfully
        
    Returns:
        GPSProof: Signed-ready proof payload
    """
    status = "COMPLETED" if success else "FAILED"
    
    return GPSProof(
        robot_id=robot_id,
        task_id=task_id,
        start_position=start_pos,
        end_position=end_pos,
        path_waypoints=waypoints,
        completion_status=status,
        metadata={
            "protocol_version": "1.0",
            "proof_type": "GPS_NAVIGATION",
            "network": "solana-devnet",
        }
    )
