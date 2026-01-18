"""
OC Transpo GTFS-RT adapter for live data system.

Fetches real-time transit data from OC Transpo GTFS-RT feeds (Vehicle Positions + Trip Updates),
decodes protobuf, and normalizes into Chronos events.
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from agents.shared.schema import (
    BaseEvent,
    Severity,
    TransitVehiclePositionEvent,
    TransitTripUpdateEvent,
    GeoIncidentEvent,
    TransitVehiclePositionDetails,
    TransitTripUpdateDetails,
    GeoIncidentDetails,
)
from agents.shared.constants import (
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    GEO_INCIDENT_TOPIC,
)
from live_data.base import LiveAdapter
from live_data.runner import register_adapter

logger = logging.getLogger(__name__)

# Severe delay threshold (10 minutes = 600 seconds)
SEVERE_DELAY_THRESHOLD_SECONDS = 600


class OCTranspoGTFSRTAdapter(LiveAdapter):
    """Adapter for OC Transpo GTFS-RT feeds (Vehicle Positions + Trip Updates)."""
    
    def __init__(self):
        super().__init__("oc_transpo_gtfsrt", poll_interval_seconds=30)
        self._mode = "mock"  # Default to mock
        
        # Get configuration from environment variables
        self._api_key = os.getenv("OCTRANSPO_API_KEY") or os.getenv("OCTRANSPO_SUBSCRIPTION_KEY")
        self._base_url = os.getenv(
            "OCTRANSPO_GTFSRT_BASE_URL",
            "https://nextrip-public-api.azure-api.net/octranspo"
        )
        self._vehicle_positions_path = os.getenv(
            "OCTRANSPO_VEHICLE_POSITIONS_PATH",
            "/gtfs-rt-vp/beta/v1/VehiclePositions"
        )
        self._trip_updates_path = os.getenv(
            "OCTRANSPO_TRIP_UPDATES_PATH",
            "/gtfs-rt-tp/beta/v1/TripUpdates"
        )
        
        # Check global LIVE_MODE setting
        from live_data.base import is_live_mode_enabled
        if not is_live_mode_enabled():
            # Force mock mode if LIVE_MODE=off
            self._mode = "mock"
            logger.info("LIVE_MODE=off: Forcing mock mode")
        elif self._api_key:
            # Enable live mode if API key is available and LIVE_MODE=on
            self._mode = "live"
        
        # Track if we've published mock.enabled event
        self._mock_enabled_published = False
    
    def fetch(self) -> List[Dict]:
        """Fetch OC Transpo GTFS-RT feeds (Vehicle Positions + Trip Updates)."""
        try:
            if self._mode == "live":
                return self._fetch_live_data()
            else:
                # Return mock.enabled event once as first item
                if not self._mock_enabled_published:
                    mock_data = self._generate_mock_data()
                    # Prepend mock.enabled event
                    mock_data.insert(0, {"_mock_enabled": True, "_event": self._create_mock_enabled_event()})
                    self._mock_enabled_published = True
                    return mock_data
                return self._generate_mock_data()
                
        except Exception as e:
            logger.error(f"Error fetching OC Transpo GTFS-RT data: {e}", exc_info=True)
            # Fallback to mock on error
            if self._mode == "live":
                logger.warning("Falling back to mock mode due to error")
                self._mode = "mock"
                if not self._mock_enabled_published:
                    mock_data = self._generate_mock_data()
                    # Prepend mock.enabled event
                    mock_data.insert(0, {"_mock_enabled": True, "_event": self._create_mock_enabled_event()})
                    self._mock_enabled_published = True
                    return mock_data
            return self._generate_mock_data()
    
    def _fetch_live_data(self) -> List[Dict]:
        """Fetch live GTFS-RT data from OC Transpo API."""
        try:
            import requests
            try:
                from transit_octranspo.decode import decode_feed_message, PROTOBUF_AVAILABLE
            except ImportError:
                logger.warning("transit_octranspo.decode module not available")
                PROTOBUF_AVAILABLE = False
                decode_feed_message = None
            
            if not PROTOBUF_AVAILABLE or decode_feed_message is None:
                logger.warning("GTFS-RT protobuf library not available, using mock data")
                self._mode = "mock"
                return self._generate_mock_data()
            
            all_items = []
            
            # Fetch Vehicle Positions feed
            try:
                vp_url = f"{self._base_url.rstrip('/')}{self._vehicle_positions_path}"
                headers = {
                    "Ocp-Apim-Subscription-Key": self._api_key,
                }
                
                response = requests.get(vp_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Decode protobuf
                feed_data = decode_feed_message(response.content)
                entities = feed_data.get("entity", [])
                
                for entity in entities:
                    if "vehicle" in entity:
                        entity["_feed_type"] = "vehicle_positions"
                        all_items.append(entity)
                
                logger.debug(f"Fetched {len([e for e in all_items if e.get('_feed_type') == 'vehicle_positions'])} vehicle positions")
                
            except Exception as vp_error:
                logger.error(f"Error fetching vehicle positions: {vp_error}", exc_info=True)
            
            # Fetch Trip Updates feed
            try:
                tu_url = f"{self._base_url.rstrip('/')}{self._trip_updates_path}"
                headers = {
                    "Ocp-Apim-Subscription-Key": self._api_key,
                }
                
                response = requests.get(tu_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Decode protobuf
                feed_data = decode_feed_message(response.content)
                entities = feed_data.get("entity", [])
                
                for entity in entities:
                    if "trip_update" in entity:
                        entity["_feed_type"] = "trip_updates"
                        all_items.append(entity)
                
                logger.debug(f"Fetched {len([e for e in all_items if e.get('_feed_type') == 'trip_updates'])} trip updates")
                
            except Exception as tu_error:
                logger.error(f"Error fetching trip updates: {tu_error}", exc_info=True)
            
            if all_items:
                logger.info(f"Fetched {len(all_items)} total GTFS-RT entities from OC Transpo")
            
            return all_items
            
        except ImportError:
            logger.warning("requests library not available, using mock data")
            self._mode = "mock"
            return self._generate_mock_data()
        except Exception as e:
            logger.error(f"Error fetching from OC Transpo GTFS-RT API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """Normalize GTFS-RT entity into ChronosEvent objects."""
        events = []
        
        try:
            # Handle special mock.enabled event
            if raw_item.get("_mock_enabled") and "_event" in raw_item:
                events.append(raw_item["_event"])
                return events
            
            feed_type = raw_item.get("_feed_type", "unknown")
            
            if feed_type == "vehicle_positions" and "vehicle" in raw_item:
                # Normalize vehicle position
                vehicle_data = raw_item["vehicle"]
                trip = vehicle_data.get("trip", {})
                vehicle = vehicle_data.get("vehicle", {})
                position = vehicle_data.get("position", {})
                
                vehicle_id = vehicle.get("id", "unknown")
                latitude = position.get("latitude")
                longitude = position.get("longitude")
                
                # Convert timestamp
                timestamp = vehicle_data.get("timestamp")
                if isinstance(timestamp, datetime):
                    timestamp_str = timestamp.isoformat().replace("+00:00", "Z")
                elif timestamp and isinstance(timestamp, (int, float)):
                    timestamp_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    timestamp_str = timestamp_dt.isoformat().replace("+00:00", "Z")
                else:
                    timestamp_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                
                # Convert status enum to string
                current_status = vehicle_data.get("current_status")
                if isinstance(current_status, int):
                    status_map = {0: "INCOMING_AT", 1: "STOPPED_AT", 2: "IN_TRANSIT_TO"}
                    current_status = status_map.get(current_status, "UNKNOWN")
                
                # Convert occupancy enum to string
                occupancy_status = vehicle_data.get("occupancy_status")
                if isinstance(occupancy_status, int):
                    occupancy_map = {
                        0: "EMPTY",
                        1: "MANY_SEATS_AVAILABLE",
                        2: "FEW_SEATS_AVAILABLE",
                        3: "STANDING_ROOM_ONLY",
                        4: "CRUSHED_STANDING_ROOM_ONLY",
                        5: "FULL",
                        6: "NOT_ACCEPTING_PASSENGERS",
                    }
                    occupancy_status = occupancy_map.get(occupancy_status, "UNKNOWN")
                
                event = TransitVehiclePositionEvent(
                    event_id=str(uuid4()),
                    timestamp=timestamp_str,
                    source="oc_transpo_gtfsrt_adapter",
                    severity=Severity.INFO,
                    sector_id="ottawa-transit",
                    summary=f"Vehicle {vehicle_id} position update",
                    details=TransitVehiclePositionDetails(
                        vehicle_id=vehicle_id,
                        trip_id=trip.get("trip_id"),
                        route_id=trip.get("route_id"),
                        latitude=latitude,
                        longitude=longitude,
                        bearing=position.get("bearing"),
                        speed=position.get("speed"),
                        occupancy_status=occupancy_status,
                        current_stop_sequence=vehicle_data.get("current_stop_sequence"),
                        current_status=current_status,
                        timestamp=timestamp_str,
                    ),
                )
                events.append(event)
                
            elif feed_type == "trip_updates" and "trip_update" in raw_item:
                # Normalize trip update
                trip_update_data = raw_item["trip_update"]
                trip = trip_update_data.get("trip", {})
                vehicle = trip_update_data.get("vehicle", {})
                
                trip_id = trip.get("trip_id", "unknown")
                
                # Calculate delay from stop time updates
                delay_seconds = None
                stop_time_updates = []
                
                for stu in trip_update_data.get("stop_time_update", []):
                    stu_dict = {
                        "stop_sequence": stu.get("stop_sequence"),
                        "stop_id": stu.get("stop_id"),
                    }
                    
                    # Extract arrival/departure delays
                    arrival = stu.get("arrival", {})
                    departure = stu.get("departure", {})
                    
                    if arrival:
                        if "delay" in arrival and arrival["delay"] is not None:
                            if delay_seconds is None or arrival["delay"] > delay_seconds:
                                delay_seconds = arrival["delay"]
                            stu_dict["arrival_delay"] = arrival["delay"]
                        if "time" in arrival and arrival["time"]:
                            arrival_time = arrival["time"]
                            if isinstance(arrival_time, datetime):
                                stu_dict["arrival_time"] = arrival_time.isoformat().replace("+00:00", "Z")
                            elif isinstance(arrival_time, (int, float)):
                                arrival_time_dt = datetime.fromtimestamp(arrival_time, tz=timezone.utc)
                                stu_dict["arrival_time"] = arrival_time_dt.isoformat().replace("+00:00", "Z")
                    
                    if departure:
                        if "delay" in departure and departure["delay"] is not None:
                            if delay_seconds is None or departure["delay"] > delay_seconds:
                                delay_seconds = departure["delay"]
                            stu_dict["departure_delay"] = departure["delay"]
                        if "time" in departure and departure["time"]:
                            departure_time = departure["time"]
                            if isinstance(departure_time, datetime):
                                stu_dict["departure_time"] = departure_time.isoformat().replace("+00:00", "Z")
                            elif isinstance(departure_time, (int, float)):
                                departure_time_dt = datetime.fromtimestamp(departure_time, tz=timezone.utc)
                                stu_dict["departure_time"] = departure_time_dt.isoformat().replace("+00:00", "Z")
                    
                    stop_time_updates.append(stu_dict)
                
                # Use trip_update delay if available
                if delay_seconds is None:
                    delay_seconds = trip_update_data.get("delay")
                
                # Convert timestamp
                timestamp = trip_update_data.get("timestamp")
                if isinstance(timestamp, datetime):
                    timestamp_str = timestamp.isoformat().replace("+00:00", "Z")
                elif timestamp and isinstance(timestamp, (int, float)):
                    timestamp_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    timestamp_str = timestamp_dt.isoformat().replace("+00:00", "Z")
                else:
                    timestamp_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                
                event = TransitTripUpdateEvent(
                    event_id=str(uuid4()),
                    timestamp=timestamp_str,
                    source="oc_transpo_gtfsrt_adapter",
                    severity=Severity.INFO,
                    sector_id="ottawa-transit",
                    summary=f"Trip {trip_id} update",
                    details=TransitTripUpdateDetails(
                        trip_id=trip_id,
                        route_id=trip.get("route_id"),
                        vehicle_id=vehicle.get("id"),
                        stop_time_updates=stop_time_updates if stop_time_updates else None,
                        delay=delay_seconds,
                        timestamp=timestamp_str,
                    ),
                )
                events.append(event)
                
                # Emit geo.incident for severe delays (>600s = 10 minutes)
                if delay_seconds and delay_seconds > SEVERE_DELAY_THRESHOLD_SECONDS:
                    # Try to get vehicle position for location
                    # For now, we'll create a point at a default location or use route info
                    # In a real system, you'd match trip_id to vehicle position
                    geo_event = self._create_delay_incident(trip_id, delay_seconds, trip.get("route_id"))
                    if geo_event:
                        events.append(geo_event)
            
        except Exception as e:
            logger.error(f"Error normalizing GTFS-RT item: {e}", exc_info=True)
        
        return events
    
    def _create_delay_incident(self, trip_id: str, delay_seconds: int, route_id: Optional[str]) -> Optional[GeoIncidentEvent]:
        """Create a geo.incident event for severe delay."""
        try:
            # Use a default Ottawa location (could be enhanced to use actual vehicle position)
            # For now, use a central Ottawa coordinate
            latitude = 45.4215
            longitude = -75.6972
            
            delay_minutes = delay_seconds // 60
            
            event = GeoIncidentEvent(
                event_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                source="oc_transpo_gtfsrt_adapter",
                severity=Severity.WARNING if delay_seconds < 1200 else Severity.ERROR,
                sector_id="ottawa-transit",
                summary=f"Severe transit delay: {delay_minutes} minutes",
                details=GeoIncidentDetails(
                    id=f"DELAY-{trip_id}-{str(uuid4())[:8].upper()}",
                    geometry={
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    style={
                        "color": "red",
                        "opacity": 0.7,
                        "outline": True,
                    },
                    incident_type="transit_delay",
                    description=f"Trip {trip_id} (Route {route_id or 'unknown'}) delayed by {delay_minutes} minutes ({delay_seconds}s)",
                    status="active",
                ),
            )
            return event
        except Exception as e:
            logger.error(f"Error creating delay incident: {e}", exc_info=True)
            return None
    
    def _create_mock_enabled_event(self) -> BaseEvent:
        """Create transit.mock.enabled event."""
        return BaseEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            source="oc_transpo_gtfsrt_adapter",
            severity=Severity.INFO,
            sector_id="ottawa-transit",
            summary="OC Transpo GTFS-RT adapter running in mock mode",
            details={
                "reason": "API key missing or fetch failed",
                "adapter_name": self.name,
                "mode": "mock",
            },
        )
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        return status
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock GTFS-RT data for testing."""
        mock_items = []
        
        # Generate mock vehicle positions
        for i in range(random.randint(5, 15)):
            vehicle_entity = {
                "id": f"mock_vehicle_{i}",
                "_feed_type": "vehicle_positions",
                "vehicle": {
                    "trip": {
                        "trip_id": f"mock_trip_{i}",
                        "route_id": random.choice(["1", "2", "4", "7", "95", "97"]),
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
                    "current_stop_sequence": random.randint(1, 50),
                    "current_status": random.choice([0, 1, 2]),  # INCOMING_AT, STOPPED_AT, IN_TRANSIT_TO
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                    "occupancy_status": random.choice([0, 1, 2, 3, 4, 5]),
                },
            }
            mock_items.append(vehicle_entity)
        
        # Generate mock trip updates (some with severe delays)
        for i in range(random.randint(3, 10)):
            delay = random.choice([0, 30, 120, 300, 650, 900])  # Some severe delays >600s
            trip_entity = {
                "id": f"mock_trip_update_{i}",
                "_feed_type": "trip_updates",
                "trip_update": {
                    "trip": {
                        "trip_id": f"mock_trip_{i}",
                        "route_id": random.choice(["1", "2", "4", "7", "95", "97"]),
                    },
                    "vehicle": {
                        "id": f"mock_vehicle_{i}",
                    },
                    "stop_time_update": [
                        {
                            "stop_sequence": j,
                            "stop_id": f"STOP_{j}",
                            "arrival": {
                                "delay": delay if j == 0 else delay + random.randint(-30, 30),
                                "time": int(datetime.now(timezone.utc).timestamp()) + delay,
                            },
                            "departure": {
                                "delay": delay if j == 0 else delay + random.randint(-30, 30),
                                "time": int(datetime.now(timezone.utc).timestamp()) + delay + 60,
                            },
                        }
                        for j in range(random.randint(1, 3))
                    ],
                    "delay": delay,
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                },
            }
            mock_items.append(trip_entity)
        
        return mock_items


# Register adapter on module import
register_adapter(OCTranspoGTFSRTAdapter)

