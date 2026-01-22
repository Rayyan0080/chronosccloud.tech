"""
Defense Detector Agent

Monitors multiple event streams to detect potential threats using rule-based analysis.
Subscribes to airspace, transit, traffic, space, and power events to identify:
- Sudden spikes in events in the same area
- Conflicting sensor data
- Environmental risk thresholds
- Multiple system stress within time windows

Emits defense.threat.detected events with confidence scores and severity levels.
"""

import asyncio
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
import math

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, subscribe, publish
from agents.shared.constants import (
    DEFENSE_THREAT_DETECTED_TOPIC,
    DISCLAIMER_DEFENSE,
    # Airspace topics
    AIRSPACE_PLAN_UPLOADED_TOPIC,
    AIRSPACE_AIRCRAFT_POSITION_TOPIC,
    AIRSPACE_FLIGHT_PARSED_TOPIC,
    AIRSPACE_TRAJECTORY_SAMPLED_TOPIC,
    AIRSPACE_CONFLICT_DETECTED_TOPIC,
    AIRSPACE_HOTSPOT_DETECTED_TOPIC,
    AIRSPACE_SOLUTION_PROPOSED_TOPIC,
    AIRSPACE_REPORT_READY_TOPIC,
    AIRSPACE_MITIGATION_APPLIED_TOPIC,
    # Transit topics
    TRANSIT_GTFSRT_FETCH_STARTED_TOPIC,
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    TRANSIT_DISRUPTION_RISK_TOPIC,
    TRANSIT_HOTSPOT_TOPIC,
    TRANSIT_REPORT_READY_TOPIC,
    TRANSIT_MITIGATION_APPLIED_TOPIC,
    # Power topics
    POWER_FAILURE_TOPIC,
    RECOVERY_PLAN_TOPIC,
)
from agents.shared.schema import (
    DefenseThreatDetectedEvent,
    ThreatType,
    ThreatSeverity,
    Severity,
)
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_exception,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
EVENT_SPIKE_WINDOW_SECONDS = 60  # 1 minute window for spike detection
EVENT_SPIKE_THRESHOLD = 10  # Minimum events to trigger spike detection
CONFLICT_DETECTION_WINDOW_SECONDS = 30  # Window for detecting conflicting data
MULTI_SYSTEM_STRESS_WINDOW_SECONDS = 120  # 2 minutes for multi-system stress
DEDUPLICATION_WINDOW_SECONDS = 300  # 5 minutes - threats in same area within this window are deduplicated
SPATIAL_DEDUPLICATION_RADIUS_KM = 5.0  # 5km radius for spatial deduplication

# Environmental risk thresholds
ENVIRONMENTAL_RISK_THRESHOLD = 0.7  # Risk score threshold


class EventLocation:
    """Represents a geographic location from an event."""
    
    def __init__(self, lat: float, lon: float, source: str = "unknown"):
        self.lat = lat
        self.lon = lon
        self.source = source
    
    def distance_km(self, other: 'EventLocation') -> float:
        """Calculate distance in kilometers using Haversine formula."""
        R = 6371  # Earth radius in km
        lat1_rad = math.radians(self.lat)
        lat2_rad = math.radians(other.lat)
        delta_lat = math.radians(other.lat - self.lat)
        delta_lon = math.radians(other.lon - self.lon)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c


class DefenseDetectorAgent:
    """Detects threats from multiple event streams."""
    
    def __init__(self):
        """Initialize the defense detector agent."""
        # Event tracking by area and time
        self.event_history: List[Dict[str, Any]] = []
        self.aircraft_counts: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)  # sector -> [(time, count)]
        self.recent_threats: List[Dict[str, Any]] = []  # For deduplication
        
    def _extract_location(self, payload: Dict[str, Any]) -> Optional[EventLocation]:
        """Extract location from event payload."""
        details = payload.get("details", {})
        
        # Try geometry first
        if "geometry" in payload:
            geom = payload["geometry"]
            if geom.get("type") == "Point" and "coordinates" in geom:
                coords = geom["coordinates"]
                if len(coords) >= 2 and coords[1] is not None and coords[0] is not None:
                    return EventLocation(coords[1], coords[0], "geometry")
        
        # Try details.location
        if "location" in details:
            loc = details["location"]
            if "latitude" in loc and "longitude" in loc:
                lat, lon = loc["latitude"], loc["longitude"]
                if lat is not None and lon is not None:
                    return EventLocation(lat, lon, "location")
            if "lat" in loc and "lon" in loc:
                lat, lon = loc["lat"], loc["lon"]
                if lat is not None and lon is not None:
                    return EventLocation(lat, lon, "location")
        
        # Try details.position
        if "position" in details:
            pos = details["position"]
            if "latitude" in pos and "longitude" in pos:
                lat, lon = pos["latitude"], pos["longitude"]
                if lat is not None and lon is not None:
                    return EventLocation(lat, lon, "position")
            if "lat" in pos and "lon" in pos:
                lat, lon = pos["lat"], pos["lon"]
                if lat is not None and lon is not None:
                    return EventLocation(lat, lon, "position")
        
        # Try direct latitude/longitude in details
        if "latitude" in details and "longitude" in details:
            lat, lon = details["latitude"], details["longitude"]
            if lat is not None and lon is not None:
                return EventLocation(lat, lon, "details")
        if "lat" in details and "lon" in details:
            lat, lon = details["lat"], details["lon"]
            if lat is not None and lon is not None:
                return EventLocation(lat, lon, "details")
        
        # For airspace events, try aircraft position
        if "latitude" in details and "longitude" in details:
            lat, lon = details["latitude"], details["longitude"]
            if lat is not None and lon is not None:
                return EventLocation(lat, lon, "aircraft")
        
        return None
    
    def _get_area_key(self, location: Optional[EventLocation]) -> Optional[str]:
        """Generate a spatial key for area-based grouping (rounded to ~1km grid)."""
        if location is None:
            return None
        if location.lat is None or location.lon is None:
            return None
        # Round to ~1km precision (0.01 degrees ≈ 1km)
        lat_rounded = round(location.lat * 100) / 100
        lon_rounded = round(location.lon * 100) / 100
        return f"{lat_rounded:.2f},{lon_rounded:.2f}"
    
    def _detect_event_spike(self, location: Optional[EventLocation], event_time: datetime) -> Optional[Tuple[float, ThreatSeverity]]:
        """Detect sudden spike in events in the same area."""
        if location is None or location.lat is None or location.lon is None:
            return None
        
        cutoff_time = event_time - timedelta(seconds=EVENT_SPIKE_WINDOW_SECONDS)
        
        # Count events in same area within time window
        area_key = self._get_area_key(location)
        if area_key is None:
            return None
        
        recent_events = [
            e for e in self.event_history
            if e.get("time", datetime.min) >= cutoff_time
            and self._get_area_key(e.get("location")) == area_key
        ]
        
        if len(recent_events) >= EVENT_SPIKE_THRESHOLD:
            # Calculate confidence based on spike magnitude
            spike_magnitude = len(recent_events) / EVENT_SPIKE_THRESHOLD
            confidence = min(0.9, 0.5 + (spike_magnitude - 1) * 0.1)
            
            # Determine severity
            if spike_magnitude >= 3.0:
                severity = ThreatSeverity.CRITICAL
            elif spike_magnitude >= 2.0:
                severity = ThreatSeverity.HIGH
            elif spike_magnitude >= 1.5:
                severity = ThreatSeverity.MED
            else:
                severity = ThreatSeverity.LOW
            
            logger.info(f"Event spike detected: {len(recent_events)} events in {area_key} within {EVENT_SPIKE_WINDOW_SECONDS}s")
            return (confidence, severity)
        
        return None
    
    def _detect_conflicting_sensor_data(self, topic: str, payload: Dict[str, Any], location: EventLocation) -> Optional[Tuple[float, ThreatSeverity]]:
        """Detect conflicting sensor data (e.g., unrealistic aircraft count jumps)."""
        details = payload.get("details", {})
        sector_id = payload.get("sector_id", "")
        
        # Check for aircraft count anomalies
        if "airspace" in topic.lower() and sector_id:
            # Track aircraft counts per sector
            current_count = details.get("aircraft_count") or details.get("count")
            if current_count is not None:
                cutoff_time = datetime.utcnow() - timedelta(seconds=CONFLICT_DETECTION_WINDOW_SECONDS)
                
                # Get recent counts for this sector
                recent_counts = [
                    (t, c) for t, c in self.aircraft_counts[sector_id]
                    if t >= cutoff_time
                ]
                
                if recent_counts:
                    # Check for unrealistic jumps (>50% increase in <30s)
                    last_count = recent_counts[-1][1]
                    if last_count > 0:
                        change_ratio = abs(current_count - last_count) / last_count
                        if change_ratio > 0.5:
                            confidence = min(0.85, 0.6 + change_ratio * 0.5)
                            severity = ThreatSeverity.HIGH if change_ratio > 1.0 else ThreatSeverity.MED
                            logger.warning(f"Conflicting sensor data: Aircraft count jumped from {last_count} to {current_count} in {sector_id}")
                            return (confidence, severity)
                
                # Store current count
                self.aircraft_counts[sector_id].append((datetime.utcnow(), current_count))
                # Keep only recent counts (last hour)
                self.aircraft_counts[sector_id] = [
                    (t, c) for t, c in self.aircraft_counts[sector_id]
                    if t >= datetime.utcnow() - timedelta(hours=1)
                ]
        
        return None
    
    def _detect_environmental_risk(self, payload: Dict[str, Any]) -> Optional[Tuple[float, ThreatSeverity]]:
        """Detect environmental risk crossing threshold."""
        details = payload.get("details", {})
        
        # Check for risk scores
        risk_score = details.get("risk_score") or details.get("risk") or details.get("environmental_risk")
        if risk_score is not None and isinstance(risk_score, (int, float)):
            if risk_score >= ENVIRONMENTAL_RISK_THRESHOLD:
                confidence = min(0.9, 0.7 + (risk_score - ENVIRONMENTAL_RISK_THRESHOLD) * 0.4)
                
                if risk_score >= 0.9:
                    severity = ThreatSeverity.CRITICAL
                elif risk_score >= 0.8:
                    severity = ThreatSeverity.HIGH
                else:
                    severity = ThreatSeverity.MED
                
                logger.warning(f"Environmental risk threshold crossed: {risk_score}")
                return (confidence, severity)
        
        return None
    
    def _detect_multi_system_stress(self, location: Optional[EventLocation], event_time: datetime) -> Optional[Tuple[float, ThreatSeverity]]:
        """Detect multiple system stress within time window."""
        if location is None or location.lat is None or location.lon is None:
            return None
        
        cutoff_time = event_time - timedelta(seconds=MULTI_SYSTEM_STRESS_WINDOW_SECONDS)
        
        # Group events by system type
        area_key = self._get_area_key(location)
        if area_key is None:
            return None
        
        recent_events = []
        for e in self.event_history:
            if e.get("time", datetime.min) >= cutoff_time:
                e_area_key = self._get_area_key(e.get("location"))
                if e_area_key is not None and e_area_key == area_key:
                    recent_events.append(e)
        
        # Count unique systems with stress (high/critical severity)
        stressed_systems = set()
        for event in recent_events:
            severity = event.get("severity", "").lower()
            if severity in ["high", "critical", "moderate"]:
                system_type = event.get("system_type", "unknown")
                stressed_systems.add(system_type)
        
        if len(stressed_systems) >= 3:  # 3+ different systems under stress
            confidence = min(0.95, 0.7 + len(stressed_systems) * 0.05)
            
            if len(stressed_systems) >= 5:
                severity = ThreatSeverity.CRITICAL
            elif len(stressed_systems) >= 4:
                severity = ThreatSeverity.HIGH
            else:
                severity = ThreatSeverity.MED
            
            logger.warning(f"Multi-system stress detected: {len(stressed_systems)} systems under stress in {area_key}")
            return (confidence, severity)
        
        return None
    
    def _is_duplicate_threat(self, location: Optional[EventLocation], threat_type: ThreatType, event_time: datetime) -> bool:
        """Check if this threat is a duplicate of a recently detected threat."""
        if location is None or location.lat is None or location.lon is None:
            return False
        
        cutoff_time = event_time - timedelta(seconds=DEDUPLICATION_WINDOW_SECONDS)
        
        for threat in self.recent_threats:
            if threat.get("time", datetime.min) < cutoff_time:
                continue  # Too old
            
            threat_location = threat.get("location")
            if threat_location and threat_location.lat is not None and threat_location.lon is not None:
                distance = location.distance_km(threat_location)
                if distance <= SPATIAL_DEDUPLICATION_RADIUS_KM and threat.get("threat_type") == threat_type:
                    logger.debug(f"Duplicate threat detected (distance: {distance:.2f}km, type: {threat_type})")
                    return True
        
        return False
    
    def _get_system_type(self, topic: str) -> str:
        """Extract system type from topic."""
        if "airspace" in topic:
            return "airspace"
        elif "transit" in topic:
            return "transit"
        elif "traffic" in topic:
            return "traffic"
        elif "space" in topic:
            return "space"
        elif "power" in topic:
            return "power"
        else:
            return "unknown"
    
    def _get_threat_type(self, topic: str, payload: Dict[str, Any]) -> ThreatType:
        """Determine threat type from event."""
        if "airspace" in topic:
            return ThreatType.AIRSPACE
        elif "power" in topic or "infra" in topic.lower():
            return ThreatType.CYBER_PHYSICAL
        elif "environmental" in topic.lower() or "risk" in topic.lower():
            return ThreatType.ENVIRONMENTAL
        else:
            return ThreatType.CIVIL
    
    def _create_geometry_from_location(self, location: Optional[EventLocation], radius_km: float = 2.0) -> Optional[Dict[str, Any]]:
        """Create a circular geometry (Polygon approximation) from location."""
        if location is None or location.lat is None or location.lon is None:
            return None
        
        # Create a simple square approximation (can be improved to actual circle)
        # 1 degree ≈ 111km, so radius_km / 111 gives approximate degrees
        radius_deg = radius_km / 111.0
        
        # Create a square polygon (simplified circle)
        coords = [
            [location.lon - radius_deg, location.lat - radius_deg],
            [location.lon + radius_deg, location.lat - radius_deg],
            [location.lon + radius_deg, location.lat + radius_deg],
            [location.lon - radius_deg, location.lat + radius_deg],
            [location.lon - radius_deg, location.lat - radius_deg],  # Close polygon
        ]
        
        return {
            "type": "Polygon",
            "coordinates": [coords]
        }
    
    async def _handle_event(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle incoming event and detect threats."""
        try:
            event_id = payload.get("event_id")
            if not event_id:
                return
            
            # Skip defense events to avoid loops
            if "defense" in topic:
                return
            
            # Extract location
            location = self._extract_location(payload)
            if not location or location.lat is None or location.lon is None:
                # Skip events without valid location (can't detect spatial threats)
                logger.debug(f"Skipping event {event_id} from {topic}: no valid location")
                return
            
            event_time = datetime.utcnow()
            system_type = self._get_system_type(topic)
            
            # Store event in history (only events with valid locations)
            self.event_history.append({
                "event_id": event_id,
                "topic": topic,
                "time": event_time,
                "location": location,
                "severity": payload.get("severity", ""),
                "system_type": system_type,
                "payload": payload,
            })
            
            # Keep only recent events (last hour)
            cutoff = event_time - timedelta(hours=1)
            self.event_history = [e for e in self.event_history if e.get("time", datetime.min) >= cutoff]
            
            # Run threat detection rules
            threats_detected = []
            
            # Rule 1: Event spike
            spike_result = self._detect_event_spike(location, event_time)
            if spike_result:
                confidence, severity = spike_result
                threats_detected.append({
                    "type": ThreatType.CIVIL,
                    "confidence": confidence,
                    "severity": severity,
                    "rule": "event_spike",
                    "description": f"Sudden spike of events in area",
                })
            
            # Rule 2: Conflicting sensor data
            conflict_result = self._detect_conflicting_sensor_data(topic, payload, location)
            if conflict_result:
                confidence, severity = conflict_result
                threat_type = self._get_threat_type(topic, payload)
                threats_detected.append({
                    "type": threat_type,
                    "confidence": confidence,
                    "severity": severity,
                    "rule": "conflicting_sensor_data",
                    "description": "Conflicting sensor data detected",
                })
            
            # Rule 3: Environmental risk
            env_result = self._detect_environmental_risk(payload)
            if env_result:
                confidence, severity = env_result
                threats_detected.append({
                    "type": ThreatType.ENVIRONMENTAL,
                    "confidence": confidence,
                    "severity": severity,
                    "rule": "environmental_risk",
                    "description": "Environmental risk threshold crossed",
                })
            
            # Rule 4: Multi-system stress
            stress_result = self._detect_multi_system_stress(location, event_time)
            if stress_result:
                confidence, severity = stress_result
                threats_detected.append({
                    "type": ThreatType.CYBER_PHYSICAL,
                    "confidence": confidence,
                    "severity": severity,
                    "rule": "multi_system_stress",
                    "description": "Multiple systems under stress",
                })
            
            # Emit threat events (with deduplication)
            for threat in threats_detected:
                threat_type = threat["type"]
                
                # Check for duplicates
                if self._is_duplicate_threat(location, threat_type, event_time):
                    logger.debug(f"Skipping duplicate threat: {threat['rule']}")
                    continue
                
                # Create threat event
                threat_id = f"THREAT-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
                
                # Determine sources from recent events in area
                area_key = self._get_area_key(location)
                recent_sources = set()
                if area_key is not None:
                    for e in self.event_history[-20:]:  # Last 20 events
                        e_area_key = self._get_area_key(e.get("location"))
                        if e_area_key is not None and e_area_key == area_key:
                            recent_sources.add(e.get("system_type", "unknown"))
                
                sources = list(recent_sources) if recent_sources else [system_type]
                
                threat_event = DefenseThreatDetectedEvent(
                    event_id=str(uuid4()),
                    timestamp=event_time.isoformat() + "Z",
                    source="defense-detector",
                    severity=Severity.HIGH if threat["severity"] in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL] else Severity.MODERATE,
                    sector_id=payload.get("sector_id", "unknown"),
                    summary=f"Threat {threat_id} detected: {threat['description']}",
                    correlation_id=threat_id,
                    details={
                        "threat_id": threat_id,
                        "threat_type": threat_type.value,
                        "confidence_score": threat["confidence"],
                        "severity": threat["severity"].value,
                        "affected_area": self._create_geometry_from_location(location),
                        "sources": sources,
                        "summary": f"{threat['description']} (Rule: {threat['rule']})",
                        "detected_at": event_time.isoformat() + "Z",
                        "disclaimer": DISCLAIMER_DEFENSE,
                    }
                )
                
                # Publish threat event
                await publish(DEFENSE_THREAT_DETECTED_TOPIC, threat_event.dict())
                logger.warning(f"THREAT DETECTED: {threat_id} - {threat['description']} (confidence: {threat['confidence']:.2f}, severity: {threat['severity'].value})")
                
                # Store for deduplication
                self.recent_threats.append({
                    "threat_id": threat_id,
                    "location": location,
                    "threat_type": threat_type,
                    "time": event_time,
                })
                
                # Keep only recent threats (last hour)
                cutoff = event_time - timedelta(hours=1)
                self.recent_threats = [t for t in self.recent_threats if t.get("time", datetime.min) >= cutoff]
                
                capture_received_event(DEFENSE_THREAT_DETECTED_TOPIC, threat_id, {"threat_type": threat_type.value})
        
        except Exception as e:
            logger.error(f"Error handling event from {topic}: {e}", exc_info=True)
            capture_exception(e, {"topic": topic, "event_id": payload.get("event_id")})
    
    async def run(self) -> None:
        """Main run loop for the defense detector agent."""
        # Initialize Sentry
        init_sentry("defense_detector")
        capture_startup("defense-detector")
        
        # Connect to message broker
        logger.info("Connecting to message broker...")
        broker = await get_broker()
        await broker.connect()
        logger.info("✓ Connected to message broker")
        
        # Subscribe to relevant topics
        topics_to_subscribe = [
            # Airspace topics
            AIRSPACE_PLAN_UPLOADED_TOPIC,
            AIRSPACE_AIRCRAFT_POSITION_TOPIC,
            AIRSPACE_FLIGHT_PARSED_TOPIC,
            AIRSPACE_TRAJECTORY_SAMPLED_TOPIC,
            AIRSPACE_CONFLICT_DETECTED_TOPIC,
            AIRSPACE_HOTSPOT_DETECTED_TOPIC,
            AIRSPACE_SOLUTION_PROPOSED_TOPIC,
            AIRSPACE_REPORT_READY_TOPIC,
            AIRSPACE_MITIGATION_APPLIED_TOPIC,
            # Transit topics
            TRANSIT_GTFSRT_FETCH_STARTED_TOPIC,
            TRANSIT_VEHICLE_POSITION_TOPIC,
            TRANSIT_TRIP_UPDATE_TOPIC,
            TRANSIT_DISRUPTION_RISK_TOPIC,
            TRANSIT_HOTSPOT_TOPIC,
            TRANSIT_REPORT_READY_TOPIC,
            TRANSIT_MITIGATION_APPLIED_TOPIC,
            # Power topics
            POWER_FAILURE_TOPIC,
            RECOVERY_PLAN_TOPIC,
            # Geo topics (for location data)
            "chronos.events.geo.incident",
            "chronos.events.geo.risk_area",
        ]
        
        logger.info(f"Subscribing to {len(topics_to_subscribe)} event topics...")
        for topic in topics_to_subscribe:
            try:
                await subscribe(topic, self._handle_event)
                logger.debug(f"✓ Subscribed to {topic}")
            except Exception as e:
                logger.warning(f"Failed to subscribe to {topic}: {e}")
        
        logger.info("=" * 80)
        logger.info("DEFENSE DETECTOR AGENT RUNNING")
        logger.info("=" * 80)
        logger.info("Monitoring events for threat patterns:")
        logger.info("  - Event spikes in same area")
        logger.info("  - Conflicting sensor data")
        logger.info("  - Environmental risk thresholds")
        logger.info("  - Multi-system stress")
        logger.info(f"Deduplication: {DEDUPLICATION_WINDOW_SECONDS}s window, {SPATIAL_DEDUPLICATION_RADIUS_KM}km radius")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            capture_exception(e, {"service": "defense_detector", "error_type": "fatal"})
            raise
        finally:
            await broker.disconnect()
            logger.info("Disconnected from message broker")
        
        logger.info("Defense Detector Agent stopped")


async def main():
    """Main entry point."""
    agent = DefenseDetectorAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

