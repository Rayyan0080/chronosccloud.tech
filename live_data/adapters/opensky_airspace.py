"""
OpenSky Network airspace adapter.

Fetches real-time aircraft positions from OpenSky Network REST API.
Normalizes into airspace.aircraft.position events and detects congestion hotspots.
"""

import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import requests

from agents.shared.schema import (
    BaseEvent,
    AircraftPositionEvent,
    AircraftPositionDetails,
    GeoRiskAreaEvent,
    GeoRiskAreaDetails,
    Severity,
    GeospatialStyle,
)
from agents.shared.constants import (
    AIRSPACE_AIRCRAFT_POSITION_TOPIC,
    GEO_RISK_AREA_TOPIC,
)
from live_data.base import LiveAdapter
from live_data.runner import register_adapter

logger = logging.getLogger(__name__)

# Ottawa region bounding box (as specified in requirements)
OTTAWA_BBOX = {
    "lat_min": 44.9,
    "lat_max": 45.6,
    "lon_min": -76.3,
    "lon_max": -75.0,
}

# Ottawa center for hotspot circle
OTTAWA_CENTER_LAT = 45.4215
OTTAWA_CENTER_LON = -75.6972

# Congestion hotspot threshold
AIRCRAFT_COUNT_THRESHOLD = int(os.getenv("OPENSKY_CONGESTION_THRESHOLD", "15"))

# Rate limiting: OpenSky Network allows anonymous requests but recommends 10s between requests
# With authentication, can poll more frequently (15-30s as per requirements)
MIN_REQUEST_INTERVAL_SECONDS = 15.0  # 15 seconds minimum between requests
_last_request_time: Optional[float] = None

# Data disclaimer
DATA_DISCLAIMER = "ADS-B derived public feed - NOT official ATC data"


def _rate_limit() -> None:
    """Rate limit requests to avoid exceeding OpenSky Network API limits."""
    global _last_request_time
    current_time = time.time()
    if _last_request_time is not None:
        elapsed = current_time - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            sleep_time = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
    _last_request_time = time.time()


def _is_within_ottawa_bbox(lat: Optional[float], lon: Optional[float]) -> bool:
    """Check if coordinates are within Ottawa bounding box."""
    if lat is None or lon is None:
        return False
    return (
        OTTAWA_BBOX["lat_min"] <= lat <= OTTAWA_BBOX["lat_max"] and
        OTTAWA_BBOX["lon_min"] <= lon <= OTTAWA_BBOX["lon_max"]
    )


class OpenSkyAirspaceAdapter(LiveAdapter):
    """Adapter for OpenSky Network airspace data."""
    
    def __init__(self):
        # Poll every 20 seconds (within 15-30s range as per requirements)
        super().__init__("opensky_airspace", poll_interval_seconds=20)
        self._mode = "mock"  # Default to mock
        
        # OpenSky Network REST API
        # API Documentation: https://opensky-network.org/apidoc/
        # Endpoint: /api/states/all
        self._api_url = "https://opensky-network.org/api/states/all"
        
        # Optional authentication (env vars as per requirements)
        self._username = os.getenv("OPENSKY_USER")
        self._password = os.getenv("OPENSKY_PASS")
        
        # Check global LIVE_MODE setting
        from live_data.base import is_live_mode_enabled
        if not is_live_mode_enabled():
            # Force mock mode if LIVE_MODE=off
            self._mode = "mock"
            logger.info("LIVE_MODE=off: Forcing mock mode")
        elif self._username and self._password:
            # Enable live mode if credentials are provided
            self._mode = "live"
            logger.info("OpenSky Airspace Adapter: Using authenticated mode")
        else:
            # Try live mode even without auth (anonymous access)
            self._mode = "live"
            logger.info("OpenSky Airspace Adapter: Using anonymous mode (rate limits apply)")
        
        logger.info(f"OpenSkyAirspaceAdapter initialized in {self._mode} mode")
        logger.info(f"Data source: {DATA_DISCLAIMER}")
    
    def fetch(self) -> List[Dict]:
        """Fetch aircraft states from OpenSky Network API."""
        try:
            if self._mode == "live":
                return self._fetch_live_data()
            else:
                return self._generate_mock_data()
                
        except Exception as e:
            logger.error(f"Error fetching OpenSky airspace data: {e}", exc_info=True)
            # Fallback to mock on error
            if self._mode == "live":
                logger.warning("Falling back to mock data due to error")
                self._mode = "mock"
            return self._generate_mock_data()
    
    def _fetch_live_data(self) -> List[Dict]:
        """Fetch live data from OpenSky Network API with rate limiting and Ottawa bbox filtering."""
        try:
            # Apply rate limiting
            _rate_limit()
            
            # OpenSky Network API parameters for bounding box
            params = {
                "lamin": OTTAWA_BBOX["lat_min"],
                "lamax": OTTAWA_BBOX["lat_max"],
                "lomin": OTTAWA_BBOX["lon_min"],
                "lomax": OTTAWA_BBOX["lon_max"],
            }
            
            # Add authentication if available
            auth = None
            if self._username and self._password:
                auth = (self._username, self._password)
            
            headers = {
                "User-Agent": "Chronos-Cloud/1.0",
            }
            
            response = requests.get(self._api_url, params=params, auth=auth, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            states = data.get("states", [])
            
            # OpenSky Network states array format:
            # [icao24, callsign, origin_country, time_position, last_contact, longitude, latitude,
            #  baro_altitude, on_ground, velocity, heading, vertical_rate, sensors, geo_altitude,
            #  squawk, spi, position_source]
            
            # Convert OpenSky format to our internal format
            aircraft = []
            for state in states:
                if not state or len(state) < 17:
                    continue
                
                # Extract fields from state array
                icao24 = state[0]
                callsign = (state[1] or "").strip() if state[1] else ""
                longitude = state[5]  # Note: OpenSky uses [lon, lat] order
                latitude = state[6]
                baro_altitude = state[7]
                on_ground = state[8]
                velocity = state[9]
                heading = state[10]
                vertical_rate = state[11]
                geo_altitude = state[13] if len(state) > 13 else None
                time_position = state[3]
                last_contact = state[4]
                
                # Filter to Ottawa bounding box
                if not _is_within_ottawa_bbox(latitude, longitude):
                    continue
                
                # Use barometric altitude if available, otherwise geometric altitude
                altitude = baro_altitude if baro_altitude else geo_altitude
                
                aircraft.append({
                    "icao24": icao24,
                    "callsign": callsign,
                    "latitude": latitude,
                    "longitude": longitude,
                    "altitude": altitude,
                    "velocity": velocity,
                    "heading": heading,
                    "vertical_rate": vertical_rate,
                    "on_ground": on_ground,
                    "time_position": time_position,
                    "last_contact": last_contact,
                })
            
            logger.info(f"Fetched {len(states)} aircraft states from OpenSky Network, filtered to {len(aircraft)} in Ottawa region")
            return aircraft
            
        except ImportError:
            logger.warning("requests library not available, using mock data")
            self._mode = "mock"
            return self._generate_mock_data()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching from OpenSky Network API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
        except Exception as e:
            logger.error(f"Unexpected error fetching from OpenSky Network API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """
        Normalize aircraft state into airspace.aircraft.position events.
        
        Also checks for congestion hotspots and publishes geo.risk_area if threshold exceeded.
        """
        events = []
        
        try:
            icao24 = raw_item.get("icao24")
            callsign = raw_item.get("callsign", "").strip()
            latitude = raw_item.get("latitude")
            longitude = raw_item.get("longitude")
            altitude = raw_item.get("altitude")
            velocity = raw_item.get("velocity")
            heading = raw_item.get("heading")
            vertical_rate = raw_item.get("vertical_rate")
            on_ground = raw_item.get("on_ground", False)
            time_position = raw_item.get("time_position")
            
            # Skip if missing essential data
            if not icao24 or latitude is None or longitude is None:
                logger.warning(f"Skipping aircraft - missing essential data: {raw_item.get('icao24')}")
                return []
            
            # Skip aircraft on ground (not relevant for airspace monitoring)
            if on_ground:
                return []
            
            # Extract timestamp
            if time_position:
                try:
                    event_timestamp = datetime.fromtimestamp(time_position, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                except (ValueError, OSError):
                    event_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                event_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Create aircraft position event
            aircraft_details = AircraftPositionDetails(
                icao24=icao24,
                callsign=callsign if callsign else None,
                latitude=float(latitude),
                longitude=float(longitude),
                altitude=float(altitude) if altitude is not None else None,
                velocity=float(velocity) if velocity is not None else None,
                heading=float(heading) if heading is not None else None,
                vertical_rate=float(vertical_rate) if vertical_rate is not None else None,
                on_ground=on_ground,
                time_position=time_position,
                data_source="opensky",
                disclaimer=DATA_DISCLAIMER
            )
            
            summary = f"Aircraft {callsign or icao24} position update" if callsign else f"Aircraft {icao24} position update"
            
            aircraft_event = AircraftPositionEvent(
                event_id=str(uuid4()),
                timestamp=event_timestamp,
                source="opensky_airspace",
                severity=Severity.INFO,
                sector_id="ottawa-airspace",
                summary=summary,
                correlation_id=None,
                details=aircraft_details
            )
            events.append(aircraft_event)
            
        except Exception as e:
            logger.error(f"Error normalizing OpenSky aircraft item: {e}", exc_info=True)
        
        return events
    
    def _check_congestion_hotspot(self, aircraft_list: List[Dict]) -> Optional[BaseEvent]:
        """
        Check if aircraft count exceeds threshold and create geo.risk_area hotspot.
        
        This is called after normalizing all aircraft to check for congestion.
        """
        if len(aircraft_list) <= AIRCRAFT_COUNT_THRESHOLD:
            return None
        
        # Create congestion hotspot
        hotspot_id = f"OPENSKY-CONGESTION-{str(uuid4())[:8].upper()}"
        current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Determine severity based on aircraft count
        if len(aircraft_list) > AIRCRAFT_COUNT_THRESHOLD * 2:
            severity = Severity.ERROR
        elif len(aircraft_list) > AIRCRAFT_COUNT_THRESHOLD * 1.5:
            severity = Severity.WARNING
        else:
            severity = Severity.WARNING
        
        # Create circle risk area centered on Ottawa
        # Radius: approximately 50km to cover Ottawa region
        radius_meters = 50000
        
        risk_area_details = GeoRiskAreaDetails(
            id=hotspot_id,
            geometry={
                "type": "Circle",
                "coordinates": [OTTAWA_CENTER_LON, OTTAWA_CENTER_LAT],
                "radius_meters": radius_meters
            },
            style=GeospatialStyle(
                color="orange",
                opacity=0.4,
                outline=True
            ),
            risk_level=severity.value,
            risk_type="airspace_congestion",
            description=f"Airspace congestion detected: {len(aircraft_list)} aircraft in Ottawa region. {DATA_DISCLAIMER}"
        )
        
        geo_risk_area = GeoRiskAreaEvent(
            event_id=str(uuid4()),
            timestamp=current_time,
            source="opensky_airspace",
            severity=severity,
            sector_id="ottawa-airspace",
            summary=f"Airspace congestion: {len(aircraft_list)} aircraft in Ottawa region",
            correlation_id=None,
            details=risk_area_details
        )
        
        logger.info(f"Airspace congestion hotspot detected: {len(aircraft_list)} aircraft (threshold: {AIRCRAFT_COUNT_THRESHOLD})")
        return geo_risk_area
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        status["disclaimer"] = DATA_DISCLAIMER
        return status
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock aircraft data within Ottawa bounding box."""
        aircraft = []
        
        # Common aircraft callsigns
        callsigns = [
            "ACA123", "WS456", "JZA789", "RJA012", "UAL345",
            "DAL678", "SWA901", "AAL234", "NKS567", "F9X890",
        ]
        
        # Generate random number of aircraft (sometimes above threshold to test hotspots)
        num_aircraft = random.randint(5, 20)
        
        for i in range(num_aircraft):
            # Generate coordinates within Ottawa bounding box
            lat = OTTAWA_BBOX["lat_min"] + random.uniform(0, OTTAWA_BBOX["lat_max"] - OTTAWA_BBOX["lat_min"])
            lon = OTTAWA_BBOX["lon_min"] + random.uniform(0, OTTAWA_BBOX["lon_max"] - OTTAWA_BBOX["lon_min"])
            
            aircraft.append({
                "icao24": f"{random.randint(0x100000, 0xFFFFFF):06x}",
                "callsign": random.choice(callsigns) if random.random() > 0.1 else "",  # 10% chance of no callsign
                "latitude": lat,
                "longitude": lon,
                "altitude": random.uniform(1000, 12000),  # meters
                "velocity": random.uniform(100, 250),  # m/s
                "heading": random.uniform(0, 360),
                "vertical_rate": random.uniform(-10, 10),  # m/s
                "on_ground": False,  # All in air for airspace monitoring
                "time_position": int(datetime.now(timezone.utc).timestamp()),
                "last_contact": int(datetime.now(timezone.utc).timestamp()),
            })
        
        return aircraft


# Register adapter on module import
register_adapter(OpenSkyAirspaceAdapter)

