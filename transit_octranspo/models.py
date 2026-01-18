"""
Typed models for OC Transpo GTFS-RT data structures.

Minimal field models for VehiclePosition and TripUpdate.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class VehiclePosition:
    """Minimal vehicle position model."""
    vehicle_id: str
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bearing: Optional[float] = None
    speed: Optional[float] = None
    occupancy_status: Optional[str] = None
    current_stop_sequence: Optional[int] = None
    current_status: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing."""
        # Convert status enum to string if it's an integer
        status = self.current_status
        if isinstance(status, int):
            status_map = {0: "INCOMING_AT", 1: "STOPPED_AT", 2: "IN_TRANSIT_TO"}
            status = status_map.get(status, "UNKNOWN")
        
        # Convert occupancy enum to string if it's an integer
        occupancy = self.occupancy_status
        if isinstance(occupancy, int):
            occupancy_map = {
                0: "EMPTY",
                1: "MANY_SEATS_AVAILABLE",
                2: "FEW_SEATS_AVAILABLE",
                3: "STANDING_ROOM_ONLY",
                4: "CRUSHED_STANDING_ROOM_ONLY",
                5: "FULL",
                6: "NOT_ACCEPTING_PASSENGERS",
            }
            occupancy = occupancy_map.get(occupancy, "UNKNOWN")
        
        return {
            "vehicle_id": self.vehicle_id,
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "bearing": self.bearing,
            "speed": self.speed,
            "occupancy_status": occupancy,
            "current_stop_sequence": self.current_stop_sequence,
            "current_status": status,
            "timestamp": self.timestamp.isoformat() + "Z" if self.timestamp else None,
        }


@dataclass
class StopTimeUpdate:
    """Stop time update model."""
    stop_sequence: Optional[int] = None
    stop_id: Optional[str] = None
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    arrival_delay: Optional[int] = None
    departure_delay: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stop_sequence": self.stop_sequence,
            "stop_id": self.stop_id,
            "arrival_time": self.arrival_time.isoformat() + "Z" if self.arrival_time else None,
            "departure_time": self.departure_time.isoformat() + "Z" if self.departure_time else None,
            "arrival_delay": self.arrival_delay,
            "departure_delay": self.departure_delay,
        }


@dataclass
class TripUpdate:
    """Minimal trip update model."""
    trip_id: str
    route_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    stop_time_updates: Optional[List[StopTimeUpdate]] = None
    delay: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing."""
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "vehicle_id": self.vehicle_id,
            "stop_time_updates": [stu.to_dict() for stu in (self.stop_time_updates or [])],
            "delay": self.delay,
            "timestamp": self.timestamp.isoformat() + "Z" if self.timestamp else None,
        }

