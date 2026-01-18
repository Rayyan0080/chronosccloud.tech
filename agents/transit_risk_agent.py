"""
Transit Risk Agent

Subscribes to transit.vehicle.position and transit.trip.update events.
Maintains rolling windows (last 15 minutes) for Ottawa region.
Detects delay clusters, headway anomalies, and stationary vehicles.
Publishes transit.disruption.risk and transit.hotspot events.

Transit data is informational only - NOT FOR OPERATIONAL USE
"""

import asyncio
import logging
import math
import os
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish, subscribe
from agents.shared.schema import (
    TransitDisruptionRiskEvent,
    TransitHotspotEvent,
    Severity,
)
from agents.shared.constants import (
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    TRANSIT_DISRUPTION_RISK_TOPIC,
    TRANSIT_HOTSPOT_TOPIC,
    DISCLAIMER_TRANSIT,
)
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_received_event,
    capture_published_event,
    capture_exception,
    add_breadcrumb,
    set_tag,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
WINDOW_MINUTES = 15  # Rolling window size
ANALYSIS_INTERVAL_SECONDS = 30  # Run analysis every 30 seconds
OTTAWA_BOUNDS = {
    "min_lat": 45.0,
    "max_lat": 46.0,
    "min_lon": -76.0,
    "max_lon": -75.0,
}

# Detection thresholds
DELAY_CLUSTER_MIN_TRIPS = 3  # Minimum trips in a delay cluster
DELAY_CLUSTER_MIN_DELAY_SECONDS = 300  # 5 minutes minimum delay
DELAY_CLUSTER_RADIUS_METERS = 2000  # 2km radius for clustering
HEADWAY_GAP_MINUTES = 15  # Minimum gap to consider an anomaly
STATIONARY_THRESHOLD_METERS = 50  # Vehicle must move less than 50m
STATIONARY_MIN_MINUTES = 5  # Must be stationary for at least 5 minutes
HOTSPOT_MIN_VEHICLES = 5  # Minimum vehicles for a hotspot
HOTSPOT_RADIUS_METERS = 1000  # 1km radius for hotspots


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def is_in_ottawa(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Check if coordinates are within Ottawa region bounds.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if within bounds, False otherwise
    """
    if lat is None or lon is None:
        return False
    
    return (
        OTTAWA_BOUNDS["min_lat"] <= lat <= OTTAWA_BOUNDS["max_lat"]
        and OTTAWA_BOUNDS["min_lon"] <= lon <= OTTAWA_BOUNDS["max_lon"]
    )


class TransitRiskAgent:
    """Agent that analyzes transit data and detects risks."""
    
    def __init__(self):
        """Initialize the transit risk agent."""
        # Rolling windows: deque of (timestamp, data) tuples
        self.vehicle_positions: deque = deque(maxlen=10000)  # Last 15 minutes worth
        self.trip_updates: deque = deque(maxlen=10000)
        
        # Track vehicle positions over time for stationary detection
        # vehicle_id -> list of (timestamp, lat, lon) tuples
        self.vehicle_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Track published risks/hotspots to avoid duplicates
        self.published_risks: Dict[str, datetime] = {}  # risk_id -> last_published
        self.published_hotspots: Dict[str, datetime] = {}  # hotspot_id -> last_published
        
    def _clean_old_data(self) -> None:
        """Remove data older than WINDOW_MINUTES from rolling windows."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
        
        # Clean vehicle positions - ensure timestamps are timezone-aware
        while self.vehicle_positions:
            timestamp = self.vehicle_positions[0][0]
            # Ensure timestamp is timezone-aware
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                # Update the tuple with timezone-aware timestamp
                self.vehicle_positions[0] = (timestamp, self.vehicle_positions[0][1])
            
            if timestamp < cutoff_time:
                self.vehicle_positions.popleft()
            else:
                break
        
        # Clean trip updates - ensure timestamps are timezone-aware
        while self.trip_updates:
            timestamp = self.trip_updates[0][0]
            # Ensure timestamp is timezone-aware
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                # Update the tuple with timezone-aware timestamp
                self.trip_updates[0] = (timestamp, self.trip_updates[0][1])
            
            if timestamp < cutoff_time:
                self.trip_updates.popleft()
            else:
                break
        
        # Clean vehicle history - ensure timestamps are timezone-aware
        for vehicle_id in list(self.vehicle_history.keys()):
            history = self.vehicle_history[vehicle_id]
            while history:
                timestamp = history[0][0]
                # Ensure timestamp is timezone-aware
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                    # Update the tuple with timezone-aware timestamp
                    history[0] = (timestamp, history[0][1], history[0][2])
                
                if timestamp < cutoff_time:
                    history.popleft()
                else:
                    break
            
            if not history:
                del self.vehicle_history[vehicle_id]
    
    def _detect_delay_clusters(self) -> List[Dict[str, Any]]:
        """
        Detect clusters of delayed trips in the same geographic area.
        
        Returns:
            List of delay cluster dictionaries
        """
        clusters = []
        
        # Get recent trip updates with delays
        recent_updates = [
            data for timestamp, data in self.trip_updates
            if data.get("delay") and data.get("delay", 0) >= DELAY_CLUSTER_MIN_DELAY_SECONDS
            and data.get("latitude") and data.get("longitude")
            and is_in_ottawa(data.get("latitude"), data.get("longitude"))
        ]
        
        if len(recent_updates) < DELAY_CLUSTER_MIN_TRIPS:
            return clusters
        
        # Simple clustering: group trips within DELAY_CLUSTER_RADIUS_METERS
        processed = set()
        
        for i, update1 in enumerate(recent_updates):
            if i in processed:
                continue
            
            cluster = [update1]
            processed.add(i)
            
            for j, update2 in enumerate(recent_updates[i+1:], start=i+1):
                if j in processed:
                    continue
                
                distance = haversine_distance(
                    update1["latitude"], update1["longitude"],
                    update2["latitude"], update2["longitude"]
                )
                
                if distance <= DELAY_CLUSTER_RADIUS_METERS:
                    cluster.append(update2)
                    processed.add(j)
            
            if len(cluster) >= DELAY_CLUSTER_MIN_TRIPS:
                # Calculate cluster center and average delay
                avg_lat = sum(u["latitude"] for u in cluster) / len(cluster)
                avg_lon = sum(u["longitude"] for u in cluster) / len(cluster)
                avg_delay = sum(u["delay"] for u in cluster) / len(cluster)
                routes = list(set(u.get("route_id") for u in cluster if u.get("route_id")))
                
                clusters.append({
                    "center_lat": avg_lat,
                    "center_lon": avg_lon,
                    "radius_meters": DELAY_CLUSTER_RADIUS_METERS,
                    "trip_count": len(cluster),
                    "average_delay_seconds": avg_delay,
                    "affected_routes": routes,
                    "trips": cluster,
                })
        
        return clusters
    
    def _detect_headway_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect gaps in vehicle headways for route corridors.
        
        Returns:
            List of headway anomaly dictionaries
        """
        anomalies = []
        
        # Group vehicles by route
        route_vehicles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for timestamp, position in self.vehicle_positions:
            if not position.get("route_id") or not position.get("latitude") or not position.get("longitude"):
                continue
            if not is_in_ottawa(position.get("latitude"), position.get("longitude")):
                continue
            
            route_vehicles[position["route_id"]].append({
                **position,
                "timestamp": timestamp,
            })
        
        # For each route, sort by timestamp and detect gaps
        for route_id, vehicles in route_vehicles.items():
            if len(vehicles) < 2:
                continue
            
            # Ensure all timestamps are timezone-aware before sorting
            for v in vehicles:
                if v["timestamp"].tzinfo is None:
                    # Convert naive datetime to timezone-aware (assume UTC)
                    v["timestamp"] = v["timestamp"].replace(tzinfo=timezone.utc)
            
            # Sort by timestamp
            vehicles.sort(key=lambda v: v["timestamp"])
            
            # Calculate time gaps between consecutive vehicles
            for i in range(len(vehicles) - 1):
                gap_minutes = (vehicles[i+1]["timestamp"] - vehicles[i]["timestamp"]).total_seconds() / 60
                
                if gap_minutes >= HEADWAY_GAP_MINUTES:
                    # Calculate midpoint location
                    mid_lat = (vehicles[i]["latitude"] + vehicles[i+1]["latitude"]) / 2
                    mid_lon = (vehicles[i]["longitude"] + vehicles[i+1]["longitude"]) / 2
                    
                    anomalies.append({
                        "route_id": route_id,
                        "gap_minutes": gap_minutes,
                        "location_lat": mid_lat,
                        "location_lon": mid_lon,
                        "radius_meters": 500,  # Small radius for point anomaly
                        "vehicle_before": vehicles[i].get("vehicle_id"),
                        "vehicle_after": vehicles[i+1].get("vehicle_id"),
                    })
        
        return anomalies
    
    def _detect_stationary_vehicles(self) -> List[Dict[str, Any]]:
        """
        Detect vehicles that have been stationary for extended periods.
        
        Returns:
            List of stationary vehicle dictionaries
        """
        stationary = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=STATIONARY_MIN_MINUTES)
        
        for vehicle_id, history in self.vehicle_history.items():
            if len(history) < 2:
                continue
            
            # Check if vehicle has recent positions - ensure timestamps are timezone-aware
            recent_positions = []
            for ts, lat, lon in history:
                # Ensure timestamp is timezone-aware
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff_time:
                    recent_positions.append((ts, lat, lon))
            
            if len(recent_positions) < 2:
                continue
            
            # Check if vehicle moved less than threshold
            first_pos = recent_positions[0]
            last_pos = recent_positions[-1]
            
            distance = haversine_distance(
                first_pos[1], first_pos[2],
                last_pos[1], last_pos[2]
            )
            
            if distance <= STATIONARY_THRESHOLD_METERS:
                # Vehicle is stationary
                stationary.append({
                    "vehicle_id": vehicle_id,
                    "latitude": last_pos[1],
                    "longitude": last_pos[2],
                    "radius_meters": 100,  # Small radius for point incident
                    "stationary_minutes": (datetime.now(timezone.utc) - first_pos[0]).total_seconds() / 60,
                })
        
        return stationary
    
    def _detect_congestion_hotspots(self) -> List[Dict[str, Any]]:
        """
        Detect areas with high vehicle density (congestion hotspots).
        
        Returns:
            List of hotspot dictionaries
        """
        hotspots = []
        
        # Get recent vehicle positions in Ottawa
        recent_positions = [
            data for timestamp, data in self.vehicle_positions
            if data.get("latitude") and data.get("longitude")
            and is_in_ottawa(data.get("latitude"), data.get("longitude"))
        ]
        
        if len(recent_positions) < HOTSPOT_MIN_VEHICLES:
            return hotspots
        
        # Simple clustering: group vehicles within HOTSPOT_RADIUS_METERS
        processed = set()
        
        for i, pos1 in enumerate(recent_positions):
            if i in processed:
                continue
            
            cluster = [pos1]
            processed.add(i)
            
            for j, pos2 in enumerate(recent_positions[i+1:], start=i+1):
                if j in processed:
                    continue
                
                distance = haversine_distance(
                    pos1["latitude"], pos1["longitude"],
                    pos2["latitude"], pos2["longitude"]
                )
                
                if distance <= HOTSPOT_RADIUS_METERS:
                    cluster.append(pos2)
                    processed.add(j)
            
            if len(cluster) >= HOTSPOT_MIN_VEHICLES:
                # Calculate cluster center
                avg_lat = sum(p["latitude"] for p in cluster) / len(cluster)
                avg_lon = sum(p["longitude"] for p in cluster) / len(cluster)
                routes = list(set(p.get("route_id") for p in cluster if p.get("route_id")))
                vehicles = [p.get("vehicle_id") for p in cluster if p.get("vehicle_id")]
                
                # Calculate average delay if available
                delays = [p.get("delay", 0) for p in cluster if p.get("delay")]
                avg_delay = sum(delays) / len(delays) if delays else 0
                
                hotspots.append({
                    "center_lat": avg_lat,
                    "center_lon": avg_lon,
                    "radius_meters": HOTSPOT_RADIUS_METERS,
                    "vehicle_count": len(cluster),
                    "average_delay_minutes": avg_delay / 60 if avg_delay else 0,
                    "affected_routes": routes,
                    "affected_vehicles": vehicles[:10],  # Limit to first 10
                })
        
        return hotspots
    
    async def _publish_disruption_risk(
        self,
        cause: str,
        risk_score: float,
        location: Dict[str, Any],
        affected_routes: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Publish a transit.disruption.risk event.
        
        Args:
            cause: Risk cause ("delay_cluster", "headway_gap", "stalled_vehicle")
            risk_score: Risk score (0.0-1.0)
            location: Location dict with lat, lon, radius_meters
            affected_routes: List of affected route IDs
            description: Risk description
        """
        try:
            risk_id = f"RISK-{cause.upper()}-{str(uuid4())[:8].upper()}"
            
            # Determine severity level from risk score
            if risk_score >= 0.8:
                severity_level = "critical"
                severity = Severity.CRITICAL
            elif risk_score >= 0.6:
                severity_level = "high"
                severity = Severity.WARNING
            elif risk_score >= 0.4:
                severity_level = "medium"
                severity = Severity.WARNING
            else:
                severity_level = "low"
                severity = Severity.INFO
            
            # Avoid duplicate publications (same risk within 5 minutes)
            if risk_id in self.published_risks:
                last_published = self.published_risks[risk_id]
                if (datetime.now(timezone.utc) - last_published).total_seconds() < 300:
                    return  # Skip duplicate
            
            event = TransitDisruptionRiskEvent(
                event_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                source="transit-risk-agent",
                severity=severity,
                sector_id="ottawa-transit",
                summary=f"Transit disruption risk detected: {cause}",
                correlation_id=risk_id,
                details={
                    "risk_id": risk_id,
                    "risk_type": "delay" if cause == "delay_cluster" else "service_interruption",
                    "severity_level": severity_level,
                    "affected_routes": affected_routes or [],
                    "location": {
                        "latitude": location.get("lat") or location.get("center_lat") or location.get("location_lat"),
                        "longitude": location.get("lon") or location.get("center_lon") or location.get("location_lon"),
                        "radius_meters": location.get("radius_meters", 500),
                    },
                    "confidence_score": risk_score,
                    "risk_score": risk_score,
                    "cause": cause,
                    "description": description or f"Detected {cause} in transit network",
                }
            )
            
            event_dict = event.dict()
            await publish(TRANSIT_DISRUPTION_RISK_TOPIC, event_dict)
            
            self.published_risks[risk_id] = datetime.now(timezone.utc)
            
            capture_published_event(
                TRANSIT_DISRUPTION_RISK_TOPIC,
                event_dict["event_id"],
                {"risk_id": risk_id, "cause": cause, "risk_score": risk_score}
            )
            
            logger.info(f"Published disruption risk: {risk_id} ({cause}, score: {risk_score:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to publish disruption risk: {e}", exc_info=True)
            capture_exception(e, {"cause": cause, "operation": "publish_disruption_risk"})
    
    async def _publish_hotspot(
        self,
        hotspot_data: Dict[str, Any],
    ) -> None:
        """
        Publish a transit.hotspot event.
        
        Args:
            hotspot_data: Hotspot data dictionary
        """
        try:
            hotspot_id = f"HOTSPOT-{str(uuid4())[:8].upper()}"
            
            # Calculate congestion score (0.0-1.0)
            vehicle_count = hotspot_data.get("vehicle_count", 0)
            avg_delay = hotspot_data.get("average_delay_minutes", 0)
            congestion_score = min(1.0, (vehicle_count / 20.0) * 0.7 + (avg_delay / 10.0) * 0.3)
            
            # Determine severity
            if congestion_score >= 0.8:
                severity_str = "critical"
                severity = Severity.CRITICAL
            elif congestion_score >= 0.6:
                severity_str = "high"
                severity = Severity.WARNING
            elif congestion_score >= 0.4:
                severity_str = "medium"
                severity = Severity.WARNING
            else:
                severity_str = "low"
                severity = Severity.INFO
            
            # Avoid duplicate publications (same hotspot within 5 minutes)
            if hotspot_id in self.published_hotspots:
                last_published = self.published_hotspots[hotspot_id]
                if (datetime.now(timezone.utc) - last_published).total_seconds() < 300:
                    return  # Skip duplicate
            
            event = TransitHotspotEvent(
                event_id=str(uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                source="transit-risk-agent",
                severity=severity,
                sector_id="ottawa-transit",
                summary=f"Transit congestion hotspot detected ({hotspot_data.get('vehicle_count', 0)} vehicles)",
                correlation_id=hotspot_id,
                details={
                    "hotspot_id": hotspot_id,
                    "hotspot_type": "congestion",
                    "location": {
                        "latitude": hotspot_data.get("center_lat"),
                        "longitude": hotspot_data.get("center_lon"),
                        "radius_meters": hotspot_data.get("radius_meters"),
                    },
                    "affected_routes": hotspot_data.get("affected_routes", []),
                    "affected_vehicles": hotspot_data.get("affected_vehicles", []),
                    "severity": severity_str,
                    "start_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                    "vehicle_count": hotspot_data.get("vehicle_count", 0),
                    "average_delay": hotspot_data.get("average_delay_minutes", 0),
                    "description": f"Congestion hotspot with {hotspot_data.get('vehicle_count', 0)} vehicles",
                }
            )
            
            event_dict = event.dict()
            await publish(TRANSIT_HOTSPOT_TOPIC, event_dict)
            
            self.published_hotspots[hotspot_id] = datetime.now(timezone.utc)
            
            capture_published_event(
                TRANSIT_HOTSPOT_TOPIC,
                event_dict["event_id"],
                {"hotspot_id": hotspot_id, "vehicle_count": hotspot_data.get("vehicle_count", 0)}
            )
            
            logger.info(f"Published hotspot: {hotspot_id} ({hotspot_data.get('vehicle_count', 0)} vehicles)")
            
        except Exception as e:
            logger.error(f"Failed to publish hotspot: {e}", exc_info=True)
            capture_exception(e, {"operation": "publish_hotspot"})
    
    async def _analyze_and_publish(self) -> None:
        """Run analysis and publish detected risks and hotspots."""
        try:
            logger.debug("Running transit risk analysis...")
            
            # Clean old data
            self._clean_old_data()
            
            # Detect delay clusters
            delay_clusters = self._detect_delay_clusters()
            for cluster in delay_clusters:
                risk_score = min(1.0, (cluster["trip_count"] / 10.0) * 0.5 + (cluster["average_delay_seconds"] / 600.0) * 0.5)
                await self._publish_disruption_risk(
                    cause="delay_cluster",
                    risk_score=risk_score,
                    location={
                        "center_lat": cluster["center_lat"],
                        "center_lon": cluster["center_lon"],
                        "radius_meters": cluster["radius_meters"],
                    },
                    affected_routes=cluster["affected_routes"],
                    description=f"Delay cluster: {cluster['trip_count']} trips delayed by avg {cluster['average_delay_seconds']/60:.1f} minutes",
                )
            
            # Detect headway anomalies
            headway_anomalies = self._detect_headway_anomalies()
            for anomaly in headway_anomalies:
                risk_score = min(1.0, anomaly["gap_minutes"] / 30.0)  # Normalize to 0-1
                await self._publish_disruption_risk(
                    cause="headway_gap",
                    risk_score=risk_score,
                    location={
                        "location_lat": anomaly["location_lat"],
                        "location_lon": anomaly["location_lon"],
                        "radius_meters": anomaly["radius_meters"],
                    },
                    affected_routes=[anomaly["route_id"]] if anomaly.get("route_id") else None,
                    description=f"Headway gap: {anomaly['gap_minutes']:.1f} minutes on route {anomaly.get('route_id', 'UNKNOWN')}",
                )
            
            # Detect stationary vehicles
            stationary_vehicles = self._detect_stationary_vehicles()
            for vehicle in stationary_vehicles:
                risk_score = min(1.0, vehicle["stationary_minutes"] / 15.0)  # Normalize to 0-1
                await self._publish_disruption_risk(
                    cause="stalled_vehicle",
                    risk_score=risk_score,
                    location={
                        "latitude": vehicle["latitude"],
                        "longitude": vehicle["longitude"],
                        "radius_meters": vehicle["radius_meters"],
                    },
                    description=f"Stationary vehicle {vehicle['vehicle_id']} for {vehicle['stationary_minutes']:.1f} minutes",
                )
            
            # Detect congestion hotspots
            hotspots = self._detect_congestion_hotspots()
            for hotspot in hotspots:
                await self._publish_hotspot(hotspot)
            
            if delay_clusters or headway_anomalies or stationary_vehicles or hotspots:
                logger.info(
                    f"Analysis complete: {len(delay_clusters)} delay clusters, "
                    f"{len(headway_anomalies)} headway anomalies, "
                    f"{len(stationary_vehicles)} stationary vehicles, "
                    f"{len(hotspots)} hotspots"
                )
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}", exc_info=True)
            capture_exception(e, {"operation": "analyze_and_publish"})
    
    async def _handle_vehicle_position(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle transit.vehicle.position event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))
            add_breadcrumb("received_vehicle_position", {"vehicle_id": payload.get("details", {}).get("vehicle_id")})
            
            details = payload.get("details", {})
            # Parse timestamp, ensuring it's timezone-aware
            ts_str = payload.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            
            # Add to rolling window
            position_data = {
                "vehicle_id": details.get("vehicle_id"),
                "route_id": details.get("route_id"),
                "trip_id": details.get("trip_id"),
                "latitude": details.get("latitude"),
                "longitude": details.get("longitude"),
                "bearing": details.get("bearing"),
                "speed": details.get("speed"),
                "timestamp": timestamp,
            }
            
            self.vehicle_positions.append((timestamp, position_data))
            
            # Track vehicle history for stationary detection
            if position_data["vehicle_id"] and position_data["latitude"] and position_data["longitude"]:
                self.vehicle_history[position_data["vehicle_id"]].append((
                    timestamp,
                    position_data["latitude"],
                    position_data["longitude"],
                ))
            
            logger.debug(f"Received vehicle position: {position_data.get('vehicle_id')} on route {position_data.get('route_id')}")
            
        except Exception as e:
            logger.error(f"Error handling vehicle position: {e}", exc_info=True)
            capture_exception(e, {"operation": "handle_vehicle_position"})
    
    async def _handle_trip_update(self, topic: str, payload: Dict[str, Any]) -> None:
        """Handle transit.trip.update event."""
        try:
            capture_received_event(topic, payload.get("event_id", "unknown"))
            add_breadcrumb("received_trip_update", {"trip_id": payload.get("details", {}).get("trip_id")})
            
            details = payload.get("details", {})
            # Parse timestamp, ensuring it's timezone-aware
            ts_str = payload.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            
            # Try to get location from vehicle position if available
            vehicle_id = details.get("vehicle_id")
            latitude = None
            longitude = None
            
            if vehicle_id:
                # Find latest position for this vehicle
                for ts, pos in reversed(self.vehicle_positions):
                    if pos.get("vehicle_id") == vehicle_id:
                        latitude = pos.get("latitude")
                        longitude = pos.get("longitude")
                        break
            
            # Add to rolling window
            update_data = {
                "trip_id": details.get("trip_id"),
                "route_id": details.get("route_id"),
                "vehicle_id": vehicle_id,
                "delay": details.get("delay"),
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
            }
            
            self.trip_updates.append((timestamp, update_data))
            
            logger.debug(f"Received trip update: {update_data.get('trip_id')} on route {update_data.get('route_id')} (delay: {update_data.get('delay', 0)}s)")
            
        except Exception as e:
            logger.error(f"Error handling trip update: {e}", exc_info=True)
            capture_exception(e, {"operation": "handle_trip_update"})
    
    async def run(self) -> None:
        """Run the transit risk agent."""
        logger.info("=" * 60)
        logger.info("Starting Transit Risk Agent")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  Window Size: {WINDOW_MINUTES} minutes")
        logger.info(f"  Analysis Interval: {ANALYSIS_INTERVAL_SECONDS} seconds")
        logger.info(f"  Ottawa Bounds: {OTTAWA_BOUNDS}")
        logger.info("=" * 60)
        
        # Initialize Sentry
        init_sentry("transit_risk_agent", "N/A")
        capture_startup("transit_risk_agent", {
            "window_minutes": WINDOW_MINUTES,
            "analysis_interval_seconds": ANALYSIS_INTERVAL_SECONDS,
        })
        
        # Connect to message broker
        try:
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")
        except Exception as e:
            logger.error(f"Failed to connect to message broker: {e}", exc_info=True)
            capture_exception(e, {"operation": "broker_connect"})
            return
        
        # Subscribe to events
        try:
            await subscribe(TRANSIT_VEHICLE_POSITION_TOPIC, self._handle_vehicle_position)
            logger.info(f"Subscribed to: {TRANSIT_VEHICLE_POSITION_TOPIC}")
            
            await subscribe(TRANSIT_TRIP_UPDATE_TOPIC, self._handle_trip_update)
            logger.info(f"Subscribed to: {TRANSIT_TRIP_UPDATE_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}", exc_info=True)
            capture_exception(e, {"operation": "subscribe"})
            return
        
        logger.info("=" * 60)
        logger.info("Transit Risk Agent is running")
        logger.info(f"{DISCLAIMER_TRANSIT}")
        logger.info("=" * 60)
        
        # Start periodic analysis
        try:
            while True:
                await asyncio.sleep(ANALYSIS_INTERVAL_SECONDS)
                await self._analyze_and_publish()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            capture_exception(e, {"operation": "main_loop"})
            raise
        finally:
            await broker.disconnect()
            logger.info("Disconnected from message broker")


async def main() -> None:
    """Main entry point."""
    agent = TransitRiskAgent()
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

