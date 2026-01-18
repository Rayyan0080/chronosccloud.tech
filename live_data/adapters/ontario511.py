"""
Ontario 511 road conditions adapter.

Fetches road conditions, incidents, and closures from Ontario 511 API.
Filters to Eastern region and Ottawa bounding box, normalizes to geo.incident and geo.risk_area.
"""

import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import requests

from agents.shared.schema import (
    BaseEvent,
    GeoIncidentEvent,
    GeoRiskAreaEvent,
    Severity,
    GeoIncidentDetails,
    GeoRiskAreaDetails,
    GeospatialStyle,
)
from agents.shared.constants import (
    GEO_INCIDENT_TOPIC,
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

# Rate limiting: Ontario 511 API allows 10 calls per 60 seconds
MIN_REQUEST_INTERVAL_SECONDS = 6.0  # 60 / 10 = 6 seconds between requests
_last_request_time: Optional[float] = None


def _rate_limit() -> None:
    """Rate limit requests to avoid exceeding Ontario 511 API limits (10 calls per 60 seconds)."""
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


class Ontario511Adapter(LiveAdapter):
    """Adapter for Ontario 511 road conditions and incidents."""
    
    def __init__(self):
        super().__init__("ontario511", poll_interval_seconds=120)
        self._mode = "mock"  # Default to mock
        
        # Ontario 511 REST API - public, no authentication required
        # API Documentation: https://511on.ca/developers/doc
        # Rate limit: 10 calls per 60 seconds
        base_url = os.getenv(
            "ONTARIO511_API_BASE_URL",
            "https://511on.ca/api/v2/get"
        )
        
        # Use custom URL if provided, otherwise use default Events endpoint
        self._incidents_url = os.getenv("ONTARIO511_INCIDENTS_URL")
        if not self._incidents_url:
            # Default to Events endpoint for Eastern region
            # Note: Ontario 511 API may support region filtering via query params
            self._incidents_url = f"{base_url}/event?format=json&language=en"
        
        # Check global LIVE_MODE setting
        from live_data.base import is_live_mode_enabled
        if not is_live_mode_enabled():
            # Force mock mode if LIVE_MODE=off
            self._mode = "mock"
            logger.info("LIVE_MODE=off: Forcing mock mode")
        else:
            # Enable live mode if URL is configured (always true with default)
            self._mode = "live"
        
        logger.info(f"Ontario511Adapter initialized in {self._mode} mode")
    
    def fetch(self) -> List[Dict]:
        """Fetch Ontario 511 road conditions and incidents."""
        try:
            if self._mode == "live" and self._incidents_url:
                return self._fetch_live_data()
            else:
                return self._generate_mock_data()
            
        except Exception as e:
            logger.error(f"Error fetching Ontario 511 data: {e}", exc_info=True)
            # Fallback to mock on error
            if self._mode == "live":
                logger.warning("Falling back to mock data due to error")
                self._mode = "mock"
            return self._generate_mock_data()
    
    def _fetch_live_data(self) -> List[Dict]:
        """Fetch live data from Ontario 511 API with rate limiting and Ottawa bbox filtering."""
        try:
            # Apply rate limiting
            _rate_limit()
            
            headers = {
                "User-Agent": "Chronos-Cloud/1.0",  # Identify our application
            }
            
            response = requests.get(self._incidents_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Ontario 511 Events API returns a list of events or GeoJSON FeatureCollection
            if isinstance(data, list):
                events = data
            elif isinstance(data, dict):
                # Check for common response wrapper formats
                if "events" in data:
                    events = data["events"]
                elif "data" in data:
                    events = data["data"]
                elif "items" in data:
                    events = data["items"]
                elif data.get("type") == "FeatureCollection":
                    # GeoJSON FeatureCollection
                    events = data.get("features", [])
                else:
                    # Assume it's a single event object
                    events = [data]
            else:
                logger.warning(f"Unexpected response format from Ontario 511 API: {type(data)}")
                return []
            
            # Filter to Ottawa bounding box and high-impact events
            filtered_events = []
            for event in events:
                # Extract coordinates
                lat, lon = self._extract_coordinates(event)
                
                if not _is_within_ottawa_bbox(lat, lon):
                    continue
                
                # Filter to high-impact events (closures, accidents, major construction)
                event_type = self._extract_event_type(event).lower()
                if self._is_high_impact(event_type, event):
                    filtered_events.append(event)
            
            logger.info(f"Fetched {len(events)} events from Ontario 511 API, filtered to {len(filtered_events)} high-impact events in Ottawa region")
            return filtered_events
            
        except ImportError:
            logger.warning("requests library not available, using mock data")
            self._mode = "mock"
            return self._generate_mock_data()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching from Ontario 511 API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
        except Exception as e:
            logger.error(f"Unexpected error fetching from Ontario 511 API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def _extract_coordinates(self, event: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from event (handles GeoJSON and regular formats)."""
        # Handle GeoJSON Feature format
        if isinstance(event, dict) and event.get("type") == "Feature":
            geometry = event.get("geometry", {})
            properties = event.get("properties", {})
            coordinates = geometry.get("coordinates", [])
            
            if geometry.get("type") == "Point" and len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]
                return lat, lon
        else:
            # Regular event object - extract coordinates from various possible fields
            lat = (
                event.get("Latitude") or
                event.get("latitude") or
                event.get("lat") or
                None
            )
            lon = (
                event.get("Longitude") or
                event.get("longitude") or
                event.get("lon") or
                event.get("lng") or
                None
            )
            
            if lat is not None and lon is not None:
                return float(lat), float(lon)
        
        return None, None
    
    def _extract_event_type(self, event: Dict) -> str:
        """Extract event type from event object."""
        if isinstance(event, dict) and event.get("type") == "Feature":
            properties = event.get("properties", {})
            return (
                properties.get("EventType") or
                properties.get("eventType") or
                properties.get("type") or
                "unknown"
            )
        else:
            return (
                event.get("EventType") or
                event.get("eventType") or
                event.get("type") or
                "unknown"
            )
    
    def _is_high_impact(self, event_type: str, event: Dict) -> bool:
        """Determine if event is high-impact (closures, accidents, major construction)."""
        event_type_lower = event_type.lower()
        
        # High-impact event types
        high_impact_types = [
            "closure", "road_closed", "full_closure",
            "accident", "crash", "collision",
            "emergency", "hazard",
            "construction", "roadwork", "maintenance",
        ]
        
        # Check if event type matches high-impact
        if any(impact_type in event_type_lower for impact_type in high_impact_types):
            return True
        
        # Check for full closure flag
        if isinstance(event, dict) and event.get("type") == "Feature":
            properties = event.get("properties", {})
            if properties.get("IsFullClosure") or properties.get("is_full_closure"):
                return True
        else:
            if event.get("IsFullClosure") or event.get("is_full_closure"):
                return True
        
        return False
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """
        Normalize Ontario 511 incident into geo.incident or geo.risk_area events.
        
        - Point incidents (accidents, closures) -> geo.incident
        - Area incidents (construction zones, road segments) -> geo.risk_area
        """
        events = []
        
        try:
            # Extract coordinates
            lat, lon = self._extract_coordinates(raw_item)
            
            if lat is None or lon is None:
                logger.warning(f"Skipping event - no valid coordinates")
                return []
            
            # Extract event details
            if isinstance(raw_item, dict) and raw_item.get("type") == "Feature":
                properties = raw_item.get("properties", {})
                event_id = str(properties.get("ID") or properties.get("id") or properties.get("SourceId") or uuid4())
                event_type = self._extract_event_type(raw_item)
                description = (
                    properties.get("Description") or
                    properties.get("description") or
                    properties.get("message") or
                    properties.get("headline") or
                    ""
                )
                severity_raw = (
                    properties.get("Severity") or
                    properties.get("severity") or
                    properties.get("priority") or
                    "info"
                ).lower()
                roadway = properties.get("RoadwayName") or properties.get("roadway") or properties.get("highway") or "Unknown"
                lanes_affected = properties.get("LanesAffected") or properties.get("lanes_affected")
                is_full_closure = properties.get("IsFullClosure") or properties.get("is_full_closure") or False
                start_date = properties.get("StartDate") or properties.get("start_time") or properties.get("start_date")
                end_date = properties.get("PlannedEndDate") or properties.get("end_time") or properties.get("end_date")
                reported = properties.get("Reported") or properties.get("reported")
                last_updated = properties.get("LastUpdated") or properties.get("last_updated")
                organization = properties.get("Organization") or properties.get("organization")
                
                # Check for secondary coordinates (indicates area/segment)
                lat_secondary = properties.get("LatitudeSecondary") or properties.get("latitude_secondary")
                lon_secondary = properties.get("LongitudeSecondary") or properties.get("longitude_secondary")
            else:
                event_id = str(raw_item.get("ID") or raw_item.get("id") or raw_item.get("SourceId") or uuid4())
                event_type = self._extract_event_type(raw_item)
                description = (
                    raw_item.get("Description") or
                    raw_item.get("description") or
                    raw_item.get("message") or
                    raw_item.get("headline") or
                    ""
                )
                severity_raw = (
                    raw_item.get("Severity") or
                    raw_item.get("severity") or
                    raw_item.get("priority") or
                    "info"
                ).lower()
                roadway = raw_item.get("RoadwayName") or raw_item.get("roadway") or raw_item.get("highway") or "Unknown"
                lanes_affected = raw_item.get("LanesAffected") or raw_item.get("lanes_affected")
                is_full_closure = raw_item.get("IsFullClosure") or raw_item.get("is_full_closure") or False
                start_date = raw_item.get("StartDate") or raw_item.get("start_time") or raw_item.get("start_date")
                end_date = raw_item.get("PlannedEndDate") or raw_item.get("end_time") or raw_item.get("end_date")
                reported = raw_item.get("Reported") or raw_item.get("reported")
                last_updated = raw_item.get("LastUpdated") or raw_item.get("last_updated")
                organization = raw_item.get("Organization") or raw_item.get("organization")
                
                # Check for secondary coordinates (indicates area/segment)
                lat_secondary = raw_item.get("LatitudeSecondary") or raw_item.get("latitude_secondary")
                lon_secondary = raw_item.get("LongitudeSecondary") or raw_item.get("longitude_secondary")
            
            # Map severity
            if severity_raw == "critical" or is_full_closure or "closure" in event_type.lower():
                severity = Severity.CRITICAL
            elif severity_raw == "high" or "accident" in event_type.lower() or "crash" in event_type.lower():
                severity = Severity.ERROR
            elif severity_raw == "medium" or "construction" in event_type.lower():
                severity = Severity.WARNING
            else:
                severity = Severity.INFO
            
            # Build summary with public-facing description
            if description:
                summary = description
            else:
                summary = f"{event_type.replace('_', ' ').title()} on {roadway}"
            
            # Extract timestamp
            event_timestamp = last_updated or reported or start_date or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Convert timestamp format if needed
            if isinstance(event_timestamp, int):
                # Unix timestamp (seconds since epoch)
                try:
                    dt = datetime.fromtimestamp(event_timestamp, tz=timezone.utc)
                    event_timestamp = dt.isoformat().replace("+00:00", "Z")
                except (ValueError, OSError):
                    # If timestamp is invalid, use current time
                    event_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            elif isinstance(event_timestamp, str):
                # String timestamp - handle various formats
                if "T" not in event_timestamp and " " in event_timestamp:
                    try:
                        dt = datetime.strptime(event_timestamp, "%Y-%m-%d %H:%M:%S")
                        event_timestamp = dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                    except ValueError:
                        try:
                            dt = datetime.strptime(event_timestamp, "%Y-%m-%d %H:%M")
                            event_timestamp = dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                        except ValueError:
                            # If parsing fails, use current time
                            event_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                elif not event_timestamp.endswith("Z") and "+" not in event_timestamp:
                    # Ensure timezone is present
                    try:
                        dt = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        event_timestamp = dt.isoformat().replace("+00:00", "Z")
                    except ValueError:
                        event_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Determine sector
            sector_id = f"ontario-{roadway.lower().replace(' ', '-')}"
            
            # Determine if this is a point incident or area/risk zone
            # If secondary coordinates exist, it's likely a road segment/area
            # If full closure or construction, treat as risk area
            # Otherwise, treat as point incident
            has_area_geometry = (
                lat_secondary is not None and lon_secondary is not None and
                _is_within_ottawa_bbox(lat_secondary, lon_secondary)
            )
            
            is_construction = "construction" in event_type.lower() or "roadwork" in event_type.lower()
            is_closure = "closure" in event_type.lower() or is_full_closure
            
            if has_area_geometry or is_construction or (is_closure and lanes_affected and lanes_affected > 1):
                # Area/risk zone -> geo.risk_area
                # Use Circle geometry if only primary point, or Polygon if secondary coordinates exist
                if has_area_geometry:
                    # Create a simple rectangle polygon from primary and secondary points
                    # Expand slightly to create a visible area
                    lat_min = min(lat, lat_secondary)
                    lat_max = max(lat, lat_secondary)
                    lon_min = min(lon, lon_secondary)
                    lon_max = max(lon, lon_secondary)
                    
                    # Add small buffer (approximately 0.01 degrees ~ 1km)
                    lat_buffer = 0.005
                    lon_buffer = 0.005
                    
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon_min - lon_buffer, lat_min - lat_buffer],
                            [lon_max + lon_buffer, lat_min - lat_buffer],
                            [lon_max + lon_buffer, lat_max + lat_buffer],
                            [lon_min - lon_buffer, lat_max + lat_buffer],
                            [lon_min - lon_buffer, lat_min - lat_buffer],  # Close polygon
                        ]]
                    }
                else:
                    # Use Circle for construction zones or closures without secondary coordinates
                    # Default radius: 1000 meters for construction, 500 meters for closures
                    if is_construction:
                        radius_meters = 1000
                    else:
                        radius_meters = 500
                    
                    geometry = {
                        "type": "Circle",
                        "coordinates": [lon, lat],
                        "radius_meters": radius_meters
                    }
                
                risk_area_details = GeoRiskAreaDetails(
                    id=f"ONTARIO511-{event_id}",
                    geometry=geometry,
                    style=GeospatialStyle(
                        color="orange" if is_construction else "red",
                        opacity=0.5 if is_construction else 0.6,
                        outline=True
                    ),
                    risk_level=severity.value,
                    risk_type=event_type.lower(),
                    description=description or summary
                )
                
                geo_risk_area = GeoRiskAreaEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ontario511",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=risk_area_details
                )
                events.append(geo_risk_area)
            else:
                # Point incident -> geo.incident
                incident_details = GeoIncidentDetails(
                    id=f"ONTARIO511-{event_id}",
                    geometry={
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    style=GeospatialStyle(
                        color="red",
                        opacity=0.7,
                        outline=True
                    ),
                    incident_type=event_type.lower(),
                    description=description or summary,
                    status="active" if not end_date else "resolved"
                )
                
                geo_incident = GeoIncidentEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ontario511",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=incident_details
                )
                events.append(geo_incident)
            
        except Exception as e:
            logger.error(f"Error normalizing Ontario 511 item: {e}", exc_info=True)
        
        return events
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        return status
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock Ontario 511 data within Ottawa bounding box."""
        incidents = []
        
        # Ontario highways near Ottawa
        highways = [
            "Highway 417", "Highway 416", "Highway 401",
            "Highway 7", "Highway 17", "Highway 15",
        ]
        
        # High-impact incident types
        incident_types = [
            ("accident", "collision"),
            ("construction", "roadwork"),
            ("closure", "road_closed"),
            ("emergency", "hazard"),
        ]
        
        directions = ["eastbound", "westbound", "northbound", "southbound", "both"]
        
        for i in range(random.randint(1, 4)):
            highway = random.choice(highways)
            event_type, event_subtype = random.choice(incident_types)
            
            # Determine severity based on type
            if event_type == "closure":
                severity = "critical"
            elif event_type == "accident":
                severity = "high"
            elif event_type == "construction":
                severity = "medium"
            else:
                severity = "info"
            
            # Generate coordinates within Ottawa bounding box
            lat = OTTAWA_BBOX["lat_min"] + random.uniform(0, OTTAWA_BBOX["lat_max"] - OTTAWA_BBOX["lat_min"])
            lon = OTTAWA_BBOX["lon_min"] + random.uniform(0, OTTAWA_BBOX["lon_max"] - OTTAWA_BBOX["lon_min"])
            
            description = f"{event_type.replace('_', ' ').title()} on {highway}"
            
            incident = {
                "ID": f"ONTARIO511_{i + 1000}",
                "EventType": event_type,
                "eventSubType": event_subtype,
                "Description": description,
                "Severity": severity,
                "RoadwayName": highway,
                "Latitude": lat,
                "Longitude": lon,
                "direction": random.choice(directions),
                "kilometer": random.randint(1, 200),
                "location_description": f"Near {random.choice(['Ottawa', 'Kanata', 'Orleans', 'Barrhaven', 'Nepean'])}",
                "StartDate": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "PlannedEndDate": None if random.random() > 0.5 else (datetime.now(timezone.utc).replace(hour=18, minute=0)).strftime("%Y-%m-%d %H:%M:%S"),
                "Reported": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "LastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "status": random.choice(["active", "cleared", "monitoring"]),
                "LanesAffected": random.randint(1, 3) if event_type == "construction" else None,
                "IsFullClosure": event_type == "closure",
                "weather_related": random.choice([True, False]),
                "Organization": "Ontario 511",
            }
            
            # Add secondary coordinates for construction/closure to create area geometry
            if event_type in ["construction", "closure"] and random.random() > 0.5:
                incident["LatitudeSecondary"] = lat + random.uniform(-0.01, 0.01)
                incident["LongitudeSecondary"] = lon + random.uniform(-0.01, 0.01)
            
            incidents.append(incident)
        
        return incidents


# Register adapter on module import
register_adapter(Ontario511Adapter)
