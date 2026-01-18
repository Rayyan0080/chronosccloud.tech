"""
OpenSky Network flight data adapter.

Fetches real-time aircraft positions and flight data for Ottawa area.
"""

import logging
import os
import random
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from agents.shared.schema import BaseEvent, Severity
from live_data.base import LiveAdapter
from live_data.runner import register_adapter

logger = logging.getLogger(__name__)

# Ottawa area bounds (approximate)
OTTAWA_LAT_MIN = 45.0
OTTAWA_LAT_MAX = 46.0
OTTAWA_LON_MIN = -76.0
OTTAWA_LON_MAX = -75.0


class OpenSkyAdapter(LiveAdapter):
    """Adapter for OpenSky Network flight data."""
    
    def __init__(self):
        super().__init__("opensky", poll_interval_seconds=45)
        self._mode = "mock"  # Default to mock
        
        # OpenSky Network is free but requires authentication for higher rate limits
        api_username = os.getenv("OPENSKY_USERNAME")
        api_password = os.getenv("OPENSKY_PASSWORD")
        if api_username and api_password:
            self._mode = "live"
            self._api_username = api_username
            self._api_password = api_password
    
    def fetch(self) -> List[Dict]:
        """Fetch aircraft states from OpenSky Network."""
        try:
            if self._mode == "live":
                return self._fetch_live_data()
            else:
                return self._generate_mock_data()
                
        except Exception as e:
            logger.error(f"Error fetching OpenSky data: {e}", exc_info=True)
            return []
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """Normalize aircraft state into ChronosEvent objects."""
        events = []
        
        try:
            callsign = raw_item.get("callsign", "").strip()
            if not callsign:
                return events  # Skip aircraft without callsign
            
            # Determine severity based on altitude and proximity
            altitude = raw_item.get("baro_altitude", 0) or 0
            if altitude < 1000:  # Low altitude
                severity = Severity.WARNING
            elif altitude < 500:
                severity = Severity.ERROR
            else:
                severity = Severity.INFO
            
            event = BaseEvent(
                event_id=str(uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                source="opensky_adapter",
                severity=severity,
                sector_id="ottawa-airspace",
                summary=f"Aircraft {callsign} in Ottawa airspace",
                details={
                    "icao24": raw_item.get("icao24"),
                    "callsign": callsign,
                    "latitude": raw_item.get("latitude"),
                    "longitude": raw_item.get("longitude"),
                    "baro_altitude": raw_item.get("baro_altitude"),
                    "velocity": raw_item.get("velocity"),
                    "heading": raw_item.get("heading"),
                    "vertical_rate": raw_item.get("vertical_rate"),
                    "on_ground": raw_item.get("on_ground", False),
                    "time_position": raw_item.get("time_position"),
                },
            )
            events.append(event)
            
        except Exception as e:
            logger.error(f"Error normalizing OpenSky item: {e}", exc_info=True)
        
        return events
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        return status
    
    def _fetch_live_data(self) -> List[Dict]:
        """Fetch live data from OpenSky Network API."""
        try:
            import requests
            
            # OpenSky Network API endpoint
            url = "https://opensky-network.org/api/states/all"
            params = {
                "lamin": OTTAWA_LAT_MIN,
                "lamax": OTTAWA_LAT_MAX,
                "lomin": OTTAWA_LON_MIN,
                "lomax": OTTAWA_LON_MAX,
            }
            
            # Add authentication if available
            auth = None
            if hasattr(self, "_api_username") and hasattr(self, "_api_password"):
                auth = (self._api_username, self._api_password)
            
            response = requests.get(url, params=params, auth=auth, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            states = data.get("states", [])
            
            # Convert OpenSky format to our format
            aircraft = []
            for state in states:
                if len(state) >= 17:  # OpenSky states array has 17+ elements
                    aircraft.append({
                        "icao24": state[0],
                        "callsign": state[1],
                        "latitude": state[6],
                        "longitude": state[5],
                        "baro_altitude": state[7],
                        "velocity": state[9],
                        "heading": state[10],
                        "vertical_rate": state[11],
                        "on_ground": state[8],
                        "time_position": state[3],
                    })
            
            return aircraft
            
        except ImportError:
            logger.warning("requests library not available, using mock data")
            self._mode = "mock"
            return self._generate_mock_data()
        except Exception as e:
            logger.error(f"Error fetching from OpenSky API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock aircraft data."""
        aircraft = []
        
        # Common aircraft callsigns
        callsigns = [
            "ACA123", "WS456", "JZA789", "RJA012", "UAL345",
            "DAL678", "SWA901", "AAL234", "NKS567", "F9X890",
        ]
        
        for i in range(random.randint(5, 15)):
            aircraft.append({
                "icao24": f"{random.randint(0x100000, 0xFFFFFF):06x}",
                "callsign": random.choice(callsigns),
                "latitude": OTTAWA_LAT_MIN + random.uniform(0, OTTAWA_LAT_MAX - OTTAWA_LAT_MIN),
                "longitude": OTTAWA_LON_MIN + random.uniform(0, OTTAWA_LON_MAX - OTTAWA_LON_MIN),
                "baro_altitude": random.uniform(500, 12000),  # meters
                "velocity": random.uniform(100, 250),  # m/s
                "heading": random.uniform(0, 360),
                "vertical_rate": random.uniform(-10, 10),  # m/s
                "on_ground": random.choice([True, False]),
                "time_position": int(datetime.utcnow().timestamp()),
            })
        
        return aircraft


# Register adapter on module import
register_adapter(OpenSkyAdapter)

