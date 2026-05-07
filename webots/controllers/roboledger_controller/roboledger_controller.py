"""
RoboLedger Webots Controller
============================
Reads target coordinates from RoboLedger JSON bridge and controls the robot.
Writes live position and battery back to the JSON bridge.
"""

import sys
import os
import json
import time
import math
from controller import Supervisor

# Locate data directory (two levels up, then webots_data)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
DATA_DIR = os.path.join(PROJECT_ROOT, "webots_data")

TARGET_FILE = os.path.join(DATA_DIR, "robot_target.json")
POSITION_FILE = os.path.join(DATA_DIR, "robot_position.json")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Robot constants
MAX_SPEED = 6.28  # e-puck max speed
ARRIVAL_THRESHOLD = 0.15
SLOWDOWN_THRESHOLD = 0.5


def _safe_read_json(path, retries=3):
    for attempt in range(retries):
        try:
            if not os.path.exists(path):
                return None
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            if attempt < retries - 1:
                time.sleep(0.01)
    return None


def _atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp_path, path)
    except Exception as e:
        # Fallback direct write
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


def get_bearing_in_degrees(compass_values):
    """Convert Webots compass values to a bearing in degrees."""
    rad = math.atan2(compass_values[0], compass_values[2])
    bearing = (rad - 1.5708) / math.pi * 180.0
    if bearing < 0.0:
        bearing += 360.0
    return bearing


class RoboLedgerController:
    def __init__(self):
        # We use Supervisor to allow drawing target markers
        self.robot = Supervisor()
        self.timestep = int(self.robot.getBasicTimeStep())
        
        # Initialize motors
        self.left_motor = self.robot.getDevice('left wheel motor')
        self.right_motor = self.robot.getDevice('right wheel motor')
        self.left_motor.setPosition(float('inf'))
        self.right_motor.setPosition(float('inf'))
        self.left_motor.setVelocity(0.0)
        self.right_motor.setVelocity(0.0)
        
        # Initialize sensors
        self.gps = self.robot.getDevice('gps')
        self.gps.enable(self.timestep)
        
        self.compass = self.robot.getDevice('compass')
        self.compass.enable(self.timestep)
        
        # State
        self.current_task_id = ""
        self.target_x = 0.0
        self.target_z = 0.0
        self.status = "idle"
        self.battery = 100.0
        
        # Target marker
        self.marker_node = None
        self._init_marker()
        
        print(f"[Webots] RoboLedger controller initialized. Data dir: {DATA_DIR}")

    def _init_marker(self):
        """Create a visual marker for the target destination."""
        root_children = self.robot.getRoot().getField("children")
        marker_string = (
            'Transform { translation 0 -100 0 children [ '
            'Shape { appearance PBRAppearance { baseColor 1 0 0 roughness 0.5 metalness 0 } '
            'geometry Sphere { radius 0.1 } } ] }'
        )
        root_children.importMFNodeFromString(-1, marker_string)
        self.marker_node = root_children.getMFNode(-1)
        
    def update_marker(self, x, z):
        """Move the target marker to the current destination."""
        if self.marker_node:
            translation_field = self.marker_node.getField("translation")
            translation_field.setSFVec3f([x, 0.1, z])
            
    def hide_marker(self):
        """Hide the target marker under the floor."""
        if self.marker_node:
            translation_field = self.marker_node.getField("translation")
            translation_field.setSFVec3f([0, -100, 0])

    def read_target(self):
        """Read target from RoboLedger JSON."""
        target_data = _safe_read_json(TARGET_FILE)
        if not target_data:
            return False
            
        task_id = target_data.get("task_id", "")
        
        # If task changed or status changed to navigating
        if task_id != self.current_task_id or (target_data.get("status") == "navigating" and self.status != "navigating"):
            self.current_task_id = task_id
            self.target_x = target_data.get("target_x", 0.0)
            self.target_z = target_data.get("target_z", 0.0)
            
            if self.current_task_id:
                self.status = "navigating"
                self.update_marker(self.target_x, self.target_z)
                print(f"[Webots] New target received: {self.current_task_id} at ({self.target_x:.2f}, {self.target_z:.2f})")
            else:
                self.status = "idle"
                self.hide_marker()
                
        return True

    def write_position(self, x, z):
        """Write current position back to RoboLedger JSON."""
        data = {
            "robot_id": "ROBO-001",
            "x": x,
            "z": z,
            "battery": self.battery,
            "status": self.status,
            "timestamp": int(time.time()),
            "task_id": self.current_task_id
        }
        _atomic_write_json(POSITION_FILE, data)

    def navigate_step(self, cur_x, cur_z, cur_bearing):
        """Calculate motor speeds to move toward target."""
        if not self.current_task_id or self.status == "arrived":
            self.left_motor.setVelocity(0.0)
            self.right_motor.setVelocity(0.0)
            return
            
        # Calculate distance and angle to target
        dx = self.target_x - cur_x
        dz = self.target_z - cur_z
        distance = math.sqrt(dx*dx + dz*dz)
        
        # Arrival check
        if distance < ARRIVAL_THRESHOLD:
            self.status = "arrived"
            self.left_motor.setVelocity(0.0)
            self.right_motor.setVelocity(0.0)
            self.hide_marker()
            print(f"[Webots] Arrived at destination for task {self.current_task_id}")
            return
            
        # Angle to target (Webots coordinate system: Z is forward)
        target_angle_rad = math.atan2(dx, dz)
        target_bearing = (target_angle_rad - 1.5708) / math.pi * 180.0
        if target_bearing < 0.0:
            target_bearing += 360.0
            
        # Calculate heading error
        error = target_bearing - cur_bearing
        # Normalize to [-180, 180]
        if error > 180.0:
            error -= 360.0
        elif error < -180.0:
            error += 360.0
            
        # Smooth slowdown as we approach target
        speed_multiplier = 1.0
        if distance < SLOWDOWN_THRESHOLD:
            speed_multiplier = max(0.2, distance / SLOWDOWN_THRESHOLD)
            
        base_speed = MAX_SPEED * speed_multiplier
        
        # Proportional steering
        steering = error * 0.05
        
        # Limit steering
        steering = max(-base_speed, min(base_speed, steering))
        
        left_speed = base_speed - steering
        right_speed = base_speed + steering
        
        # Cap at max speed
        left_speed = max(-MAX_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(-MAX_SPEED, min(MAX_SPEED, right_speed))
        
        self.left_motor.setVelocity(left_speed)
        self.right_motor.setVelocity(right_speed)

    def run(self):
        """Main control loop."""
        print("[Webots] Control loop started.")
        
        # Wait for sensors to initialize
        for _ in range(5):
            self.robot.step(self.timestep)
            
        last_print_time = 0
        
        while self.robot.step(self.timestep) != -1:
            # Read sensors
            gps_vals = self.gps.getValues()
            if math.isnan(gps_vals[0]):
                continue
                
            cur_x = gps_vals[0]
            cur_z = gps_vals[2]
            
            compass_vals = self.compass.getValues()
            cur_bearing = get_bearing_in_degrees(compass_vals)
            
            # Read target from RoboLedger
            self.read_target()
            
            # Update navigation
            self.navigate_step(cur_x, cur_z, cur_bearing)
            
            # Write position back to RoboLedger
            self.write_position(cur_x, cur_z)
            
            # Print debug info occasionally
            now = time.time()
            if now - last_print_time > 2.0 and self.status == "navigating":
                dist = math.sqrt((self.target_x - cur_x)**2 + (self.target_z - cur_z)**2)
                print(f"[Webots] Navigating... Dist: {dist:.2f}m | Heading Error: {cur_bearing:.1f}°")
                last_print_time = now


if __name__ == "__main__":
    controller = RoboLedgerController()
    controller.run()
