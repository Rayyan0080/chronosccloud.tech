"""
Ottawa traffic and road conditions adapter.

Fetches traffic incidents, construction, and special events from Ottawa traffic data services.
Normalizes into geo.incident (point incidents) and geo.risk_area (construction corridors).
"""

import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
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

# Rate limiting: minimum seconds between requests
MIN_REQUEST_INTERVAL_SECONDS = 2.0
_last_request_time: Optional[float] = None


def _rate_limit() -> None:
    """Rate limit requests to avoid hammering endpoints."""
    global _last_request_time
    current_time = time.time()
    if _last_request_time is not None:
        elapsed = current_time - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            sleep_time = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
    _last_request_time = time.time()


class OttawaTrafficAdapter(LiveAdapter):
    """Adapter for Ottawa traffic and road conditions."""
    
    def __init__(self):
        super().__init__("ottawa_traffic", poll_interval_seconds=60)
        self._mode = "mock"  # Default to mock
        
        # Ottawa Traffic provides public JSON feeds - no API key required
        # URL: https://traffic.ottawa.ca/map/service/events?accept-language=en
        self._incidents_url = os.getenv(
            "OTTAWA_TRAFFIC_INCIDENTS_URL",
            "https://traffic.ottawa.ca/map/service/events?accept-language=en"
        )
        
        # Optional API key for future use (if they add authentication)
        self._api_key = os.getenv("OTTAWA_TRAFFIC_API_KEY")
        
        # Check global LIVE_MODE setting
        from live_data.base import is_live_mode_enabled
        if not is_live_mode_enabled():
            # Force mock mode if LIVE_MODE=off
            self._mode = "mock"
            logger.info("LIVE_MODE=off: Forcing mock mode")
        elif self._incidents_url:
            # Enable live mode if URL is configured (default URL is public, so always try live first)
            self._mode = "live"
        
        logger.info(f"OttawaTrafficAdapter initialized in {self._mode} mode")
    
    def fetch(self) -> List[Dict]:
        """Fetch Ottawa traffic incidents and conditions."""
        try:
            if self._mode == "live":
                return self._fetch_live_data()
            else:
                return self._generate_mock_data()
            
        except Exception as e:
            logger.error(f"Error fetching Ottawa traffic data: {e}", exc_info=True)
            # Fallback to mock on error
            if self._mode == "live":
                logger.warning("Falling back to mock data due to error")
                self._mode = "mock"
            return self._generate_mock_data()
    
    def _fetch_live_data(self) -> List[Dict]:
        """Fetch live data from Ottawa Traffic API with rate limiting."""
        try:
            # Apply rate limiting
            _rate_limit()
            
            headers = {}
            # Add optional Authorization header if API key is provided
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            
            response = requests.get(self._incidents_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Ottawa Traffic API returns events as a list or object with events array
            if isinstance(data, list):
                events = data
            elif isinstance(data, dict) and "events" in data:
                events = data["events"]
            elif isinstance(data, dict):
                # Sometimes the response is a single event object
                events = [data]
            else:
                logger.warning(f"Unexpected response format from Ottawa Traffic API: {type(data)}")
                return []
            
            logger.info(f"Fetched {len(events)} raw events from Ottawa Traffic API")
            return events
            
        except ImportError:
            logger.warning("requests library not available, using mock data")
            self._mode = "mock"
            return self._generate_mock_data()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching from Ottawa Traffic API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
        except Exception as e:
            logger.error(f"Unexpected error fetching from Ottawa Traffic API: {e}", exc_info=True)
            self._mode = "mock"
            return self._generate_mock_data()
    
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """
        Normalize traffic incident into geo.incident or geo.risk_area events.
        
        - Point incidents (collisions, road closures) -> geo.incident
        - Construction corridors/impacted areas -> geo.risk_area (Circle if only point given)
        """
        events = []
        
        try:
            # Extract event type and map to category
            event_type_raw = raw_item.get("EventType", "").lower()
            event_subtype = raw_item.get("eventSubType", "").lower()
            
            # Determine category from event type
            category = "unknown"
            if "collision" in event_type_raw or "accident" in event_type_raw or "incident" in event_type_raw:
                category = "collision"
            elif "closure" in event_type_raw or "closed" in event_type_raw:
                category = "road_closure"
            elif "construction" in event_type_raw:
                category = "construction"
            elif "special" in event_type_raw or "event" in event_type_raw:
                category = "special_event"
            
            # Map category to severity according to requirements
            if category == "collision":
                severity = Severity.ERROR  # high
            elif category == "road_closure":
                severity = Severity.ERROR  # high
            elif category == "construction":
                severity = Severity.WARNING  # medium
            elif category == "special_event":
                severity = Severity.WARNING  # medium
            else:
                severity = Severity.INFO  # default for unknown
            
            # Extract geodata (GeoJSON Point)
            geodata = raw_item.get("geodata", {})
            coordinates = geodata.get("coordinates", []) if isinstance(geodata, dict) else []
            
            longitude = coordinates[0] if len(coordinates) > 0 else None
            latitude = coordinates[1] if len(coordinates) > 1 else None
            
            # Skip if no valid coordinates
            if latitude is None or longitude is None:
                logger.warning(f"Skipping event {raw_item.get('Id')} - no valid coordinates")
                return []
            
            # Extract public-facing description fields
            headline = raw_item.get("headline", "")
            message = raw_item.get("message", "")
            description = message if message else headline
            
            # Build location description
            location_parts = []
            main_street = raw_item.get("mainStreet")
            cross_street1 = raw_item.get("crossStreet1")
            cross_street2 = raw_item.get("crossStreet2")
            
            if main_street:
                location_parts.append(main_street)
            if cross_street1:
                if cross_street2:
                    location_parts.append(f"between {cross_street1} and {cross_street2}")
                else:
                    location_parts.append(f"at {cross_street1}")
            
            location_desc = ", ".join(location_parts) if location_parts else "Ottawa"
            
            # Build summary with public-facing description
            summary = description if description else f"{category.replace('_', ' ').title()} on {location_desc}"
            
            # Extract timestamps
            created_time = raw_item.get("Created")
            updated_time = raw_item.get("Updated")
            event_timestamp = updated_time or created_time or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Convert timestamp format if needed (Ottawa API uses "YYYY-MM-DD HH:MM" format)
            if isinstance(event_timestamp, str) and " " in event_timestamp and "T" not in event_timestamp:
                try:
                    dt = datetime.strptime(event_timestamp, "%Y-%m-%d %H:%M")
                    event_timestamp = dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                except ValueError:
                    pass  # Keep original if parsing fails
            
            # Determine event type: geo.incident for point incidents, geo.risk_area for construction corridors
            incident_id = str(raw_item.get("Id", uuid4()))
            sector_id = f"ottawa-{raw_item.get('area', 'unknown').lower().replace(' ', '-')}"
            
            if category in ["collision", "road_closure"]:
                # Point incidents -> geo.incident
                incident_details = GeoIncidentDetails(
                    id=f"OTTAWA-TRAFFIC-{incident_id}",
                    geometry={
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    style=GeospatialStyle(
                        color="red",
                        opacity=0.7,
                        outline=True
                    ),
                    incident_type=category,
                    description=description or summary,
                    status=raw_item.get("status", "active").lower()
                )
                
                geo_incident = GeoIncidentEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ottawa_traffic",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=incident_details
                )
                events.append(geo_incident)
                
            elif category == "construction":
                # Construction corridors -> geo.risk_area (Circle if only point given)
                # Default radius for construction zones: 500 meters
                construction_radius = 500
                
                risk_area_details = GeoRiskAreaDetails(
                    id=f"OTTAWA-CONSTRUCTION-{incident_id}",
                    geometry={
                        "type": "Circle",
                        "coordinates": [longitude, latitude],
                        "radius_meters": construction_radius
                    },
                    style=GeospatialStyle(
                        color="orange",
                        opacity=0.5,
                        outline=True
                    ),
                    risk_level=severity.value,
                    risk_type="construction",
                    description=description or summary
                )
                
                geo_risk_area = GeoRiskAreaEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ottawa_traffic",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=risk_area_details
                )
                events.append(geo_risk_area)
                
            elif category == "special_event":
                # Special events -> geo.risk_area (Circle)
                # Default radius for special events: 1000 meters
                event_radius = 1000
                
                risk_area_details = GeoRiskAreaDetails(
                    id=f"OTTAWA-EVENT-{incident_id}",
                    geometry={
                        "type": "Circle",
                        "coordinates": [longitude, latitude],
                        "radius_meters": event_radius
                    },
                    style=GeospatialStyle(
                        color="yellow",
                        opacity=0.4,
                        outline=True
                    ),
                    risk_level=severity.value,
                    risk_type="special_event",
                    description=description or summary
                )
                
                geo_risk_area = GeoRiskAreaEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ottawa_traffic",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=risk_area_details
                )
                events.append(geo_risk_area)
            else:
                # Unknown category -> default to geo.incident
                incident_details = GeoIncidentDetails(
                    id=f"OTTAWA-UNKNOWN-{incident_id}",
                    geometry={
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    style=GeospatialStyle(
                        color="gray",
                        opacity=0.6,
                        outline=True
                    ),
                    incident_type=category,
                    description=description or summary,
                    status=raw_item.get("status", "active").lower()
                )
                
                geo_incident = GeoIncidentEvent(
                    event_id=str(uuid4()),
                    timestamp=event_timestamp,
                    source="ottawa_traffic",
                    severity=severity,
                    sector_id=sector_id,
                    summary=summary,
                    correlation_id=None,
                    details=incident_details
                )
                events.append(geo_incident)
            
        except Exception as e:
            logger.error(f"Error normalizing Ottawa traffic item: {e}", exc_info=True)
        
        return events
    
    def get_status(self) -> Dict:
        """Get adapter status including mode."""
        status = super().get_status()
        status["mode"] = self._mode
        return status
    
    def _generate_mock_data(self) -> List[Dict]:
        """Generate mock Ottawa traffic data."""
        incidents = []
        
        # Common Ottawa streets
        streets = [
            "Highway 417", "Highway 416", "Bank Street", "Elgin Street",
            "Rideau Street", "Wellington Street", "Carling Avenue",
            "Baseline Road", "Hunt Club Road", "St. Laurent Boulevard",
        ]
        
        # Event categories matching requirements
        event_categories = [
            ("collision", "incident"),
            ("road_closure", "closure"),
            ("construction", "construction"),
            ("special_event", "special_event"),
        ]
        
        for i in range(random.randint(2, 6)):
            category, event_type = random.choice(event_categories)
            
            # Map category to severity
            if category in ["collision", "road_closure"]:
                severity = "error"  # high
            else:
                severity = "warning"  # medium
            
            # Extract geodata format
            latitude = 45.4215 + random.uniform(-0.15, 0.15)
            longitude = -75.6972 + random.uniform(-0.15, 0.15)
            
            street = random.choice(streets)
            headline = f"{category.replace('_', ' ').title()} on {street}"
            message = f"Traffic {category.replace('_', ' ')} affecting {street}. Please use alternate routes."
            
            incident = {
                "Id": i + 1000,
                "EventType": event_type,
                "eventSubType": category,
                "headline": headline,
                "message": message,
                "priority": "HIGH" if severity == "error" else "MEDIUM",
                "status": random.choice(["ACTIVE", "SCHEDULED"]),
                "Created": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "Updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "geodata": {
                    "type": "Point",
                    "coordinates": [longitude, latitude]
                },
                "mainStreet": street,
                "crossStreet1": random.choice(streets) if random.random() > 0.5 else None,
                "crossStreet2": random.choice(streets) if random.random() > 0.3 else None,
                "area": random.choice(["Downtown", "Kanata", "Orleans", "Barrhaven", "Nepean"]),
                "cause": random.choice(["Accident", "Construction", "Weather", "Event"]) if category == "collision" else None,
            }
            incidents.append(incident)
        
        return incidents


# Register adapter on module import
register_adapter(OttawaTrafficAdapter)
