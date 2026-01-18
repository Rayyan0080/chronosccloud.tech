"""
OC Transpo transit data adapter.

Fetches real-time transit data from OC Transpo GTFS-RT feeds.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from agents.shared.schema import BaseEvent, Severity
from live_data.base import LiveAdapter
from live_data.runner import register_adapter

logger = logging.getLogger(__name__)


class OCTranspoAdapter(LiveAdapter):
    """Adapter for OC Transpo transit data."""
    
    def __init__(self):
        super().__init__("oc_transpo", poll_interval_seconds=30)
        self._mode = "mock"  # Will be determined on first fetch
        self._api_key = os.getenv("OCTRANSPO_SUBSCRIPTION_KEY") or os.getenv("OCTRANSPO_API_KEY")
        
        if self._api_key:
            self._mode = "live"
    
    def fetch(self) -> List[Dict]:
        """Fetch OC Transpo vehicle positions and trip updates."""
        try:
            # Try to use existing transit_octranspo module
            try:
                import asyncio
                from transit_octranspo.client import fetch_gtfsrt_feed
                from transit_octranspo.config import get_transit_mode
                
                mode = get_transit_mode()
                self._mode = mode
                
                # Fetch vehicle positions (async function, run in event loop)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                vehicle_feed = loop.run_until_complete(fetch_gtfsrt_feed("vehicle_positions"))
                if vehicle_feed and "entity" in vehicle_feed:
                    return vehicle_feed["entity"]
                
                return []
                
            except ImportError:
                logger.warning("transit_octranspo module not available, using mock data")
                self._mode = "mock"
                return self._generate_mock_data()
                
        except Exception as e:
            logger.error(f"Error fetching OC Transpo data: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """Normalize OC Transpo entity into ChronosEvent objects."""
        events = []
        
        try:
            # Handle vehicle position entities
            if "vehicle" in raw_item:
                vehicle = raw_item["vehicle"]
                position = vehicle.get("position", {})
                trip = vehicle.get("trip", {})
                
                event = BaseEvent(
                    event_id=str(uuid4()),
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source="oc_transpo_adapter",
                    severity=Severity.INFO,
                    sector_id="ottawa-transit",
                    summary=f"Vehicle {vehicle.get('vehicle', {}).get('id', 'unknown')} position update",
                    details={
                        "vehicle_id": vehicle.get("vehicle", {}).get("id"),
                        "trip_id": trip.get("trip_id"),
                        "route_id": trip.get("route_id"),
                        "latitude": position.get("latitude"),
                        "longitude": position.get("longitude"),
                        "bearing": position.get("bearing"),
                        "speed": position.get("speed"),
                        "timestamp": vehicle.get("timestamp"),
                    },
                )
                events.append(event)
            
            # Handle trip update entities
            elif "trip_update" in raw_item:
                trip_update = raw_item["trip_update"]
                trip = trip_update.get("trip", {})
                
                event = BaseEvent(
                    event_id=str(uuid4()),
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source="oc_transpo_adapter",
                    severity=Severity.INFO,
                    sector_id="ottawa-transit",
                    summary=f"Trip {trip.get('trip_id', 'unknown')} update",
                    details={
                        "trip_id": trip.get("trip_id"),
                        "route_id": trip.get("route_id"),
                        "vehicle_id": trip_update.get("vehicle", {}).get("id"),
                        "delay": trip_update.get("delay"),
                        "stop_time_updates": [
                            {
                                "stop_id": stu.get("stop_id"),
                                "arrival_delay": stu.get("arrival", {}).get("delay"),
                                "departure_delay": stu.get("departure", {}).get("delay"),
                            }
                            for stu in trip_update.get("stop_time_update", [])
                        ],
                    },
                )
                events.append(event)
                
        except Exception as e:
            logger.error(f"Error normalizing OC Transpo item: {e}", exc_info=True)
        
        return events
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        return status
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock OC Transpo data for testing."""
        import random
        
        mock_entities = []
        for i in range(random.randint(3, 8)):
            entity = {
                "id": f"mock_vehicle_{i}",
                "vehicle": {
                    "trip": {
                        "trip_id": f"mock_trip_{i}",
                        "route_id": f"{random.choice(['1', '2', '4', '7', '95'])}",
                    },
                    "vehicle": {
                        "id": f"mock_vehicle_{i}",
                        "label": f"Vehicle {i}",
                    },
                    "position": {
                        "latitude": 45.4215 + random.uniform(-0.1, 0.1),
                        "longitude": -75.6972 + random.uniform(-0.1, 0.1),
                        "bearing": random.uniform(0, 360),
                        "speed": random.uniform(0, 15),
                    },
                    "timestamp": int(datetime.utcnow().timestamp()),
                },
            }
            mock_entities.append(entity)
        
        return mock_entities


# Register adapter on module import
register_adapter(OCTranspoAdapter)

