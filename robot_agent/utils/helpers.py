"""
RoboLedger — Helper Utilities
==============================
Common utility functions used across all modules.

Includes:
    - Haversine distance calculation
    - Coordinate formatting
    - Time formatting
    - Random jitter for simulation realism
    - ID generation
"""

import math
import time
import random
import hashlib
import uuid
from datetime import datetime


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    Uses the Haversine formula. Returns distance in kilometers.
    
    For our simulation, we scale this to "campus units" for realism.
    
    Args:
        lat1, lon1: Starting coordinates
        lat2, lon2: Destination coordinates
        
    Returns:
        Distance in simulation units (roughly campus-scale)
    """
    R = 6371.0  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance_km = R * c
    # Scale to campus units (1 unit ≈ 100m) for simulation
    return distance_km * 10


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Simple 2D euclidean distance for local navigation."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def format_coordinates(lat: float, lon: float) -> str:
    """Format coordinates for display."""
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"


def format_sol(amount: float) -> str:
    """Format SOL amount for display."""
    return f"◎ {amount:.4f} SOL"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_timestamp() -> str:
    """Get current timestamp formatted for logs."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def generate_task_id() -> str:
    """Generate a unique task identifier."""
    return f"TASK-{uuid.uuid4().hex[:8].upper()}"


def generate_proof_id() -> str:
    """Generate a unique proof identifier."""
    return f"PROOF-{uuid.uuid4().hex[:10].upper()}"


def generate_tx_hash() -> str:
    """Generate a mock Solana transaction hash."""
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:64]


def generate_block_hash() -> str:
    """Generate a mock recent blockhash."""
    return hashlib.sha256(f"block-{time.time()}".encode()).hexdigest()[:44]


def add_jitter(value: float, jitter_range: float = 0.001) -> float:
    """Add random noise to a value for simulation realism."""
    return value + random.uniform(-jitter_range, jitter_range)


def add_coordinate_jitter(lat: float, lon: float, jitter: float = 0.0005):
    """Add small random GPS noise to coordinates."""
    return (
        add_jitter(lat, jitter),
        add_jitter(lon, jitter)
    )


def calculate_eta(distance: float, speed: float) -> float:
    """Calculate estimated time of arrival in seconds."""
    if speed <= 0:
        return float('inf')
    return distance / speed


def interpolate_position(start: tuple, end: tuple, progress: float) -> tuple:
    """
    Linear interpolation between two coordinate points.
    
    Args:
        start: (lat, lon) starting position
        end: (lat, lon) ending position
        progress: 0.0 to 1.0 completion percentage
        
    Returns:
        (lat, lon) interpolated position
    """
    progress = max(0.0, min(1.0, progress))
    lat = start[0] + (end[0] - start[0]) * progress
    lon = start[1] + (end[1] - start[1]) * progress
    return (lat, lon)


def hash_payload(data: str) -> str:
    """Create SHA-256 hash of a data payload."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def mock_latency(base_ms: float = 200, jitter_ms: float = 100) -> float:
    """
    Simulate network latency for realistic demo timing.
    Returns seconds to sleep.
    """
    latency = base_ms + random.uniform(-jitter_ms, jitter_ms)
    return max(50, latency) / 1000.0


def random_validator_name() -> str:
    """Generate a random validator node name."""
    prefixes = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Theta", "Iota"]
    return f"Validator-{random.choice(prefixes)}-{random.randint(1, 99):02d}"


def truncate_hash(hash_str: str, length: int = 8) -> str:
    """Truncate a hash for display, showing first and last N chars."""
    if len(hash_str) <= length * 2:
        return hash_str
    return f"{hash_str[:length]}...{hash_str[-length:]}"
