"""
Ottawa Overlay Generator Service

Generates synthetic geospatial overlay events (geo.incident and geo.risk_area) for Ottawa region.
Publishes events every 30 seconds with stable random seed option for repeatable demos.
"""

import asyncio
import logging
import os
import random
import sys
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import GeoIncidentEvent, GeoRiskAreaEvent, Severity
from agents.shared.constants import GEO_INCIDENT_TOPIC, GEO_RISK_AREA_TOPIC
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_published_event,
    capture_exception,
    add_breadcrumb,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ottawa center coordinates
OTTAWA_LAT = 45.4215
OTTAWA_LON = -75.6972

# Configuration
PUBLISH_INTERVAL_SECONDS = int(os.getenv("OTTAWA_OVERLAY_INTERVAL", "30"))
RANDOM_SEED = os.getenv("OTTAWA_OVERLAY_SEED", None)  # Set for stable/repeatable demo

# Risk area summaries
RISK_AREA_SUMMARIES = [
    "Congestion hotspot near downtown corridor",
    "Potential conflict cluster",
    "High workload sector",
    "Traffic density zone",
    "Resource contention area",
    "Operational stress point",
    "Capacity bottleneck region",
    "Coordination complexity zone",
]

# Incident summaries
INCIDENT_SUMMARIES = [
    "Traffic incident detected",
    "Resource allocation conflict",
    "Operational anomaly",
    "Capacity threshold exceeded",
    "Coordination delay",
    "System overload warning",
    "Response time degradation",
    "Resource contention",
    "Operational bottleneck",
    "Performance degradation",
    "Service disruption",
    "Coordination failure",
]

# Severity mapping
SEVERITY_LEVELS = {
    "low": Severity.INFO,
    "medium": Severity.WARNING,
    "high": Severity.MODERATE,
    "critical": Severity.CRITICAL,
}

# Color mapping based on severity
SEVERITY_COLORS = {
    "low": "yellow",
    "medium": "orange",
    "high": "red",
    "critical": "#FF0000",  # Bright red
}

# Opacity mapping based on severity
SEVERITY_OPACITY = {
    "low": 0.4,
    "medium": 0.5,
    "high": 0.6,
    "critical": 0.7,
}


def generate_offset_coordinates(
    center_lat: float, center_lon: float, max_offset_km: float, rng: random.Random
) -> Tuple[float, float]:
    """
    Generate random coordinates offset from center.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        max_offset_km: Maximum offset in kilometers
        rng: Random number generator instance
        
    Returns:
        Tuple of (latitude, longitude)
    """
    # Convert km to degrees (approximate: 1 degree lat ≈ 111 km)
    max_offset_deg = max_offset_km / 111.0
    
    # Generate random offset
    offset_lat = rng.uniform(-max_offset_deg, max_offset_deg)
    offset_lon = rng.uniform(-max_offset_deg, max_offset_deg)
    
    new_lat = center_lat + offset_lat
    new_lon = center_lon + offset_lon
    
    # Clamp to valid ranges
    new_lat = max(-90, min(90, new_lat))
    new_lon = max(-180, min(180, new_lon))
    
    return new_lat, new_lon


def generate_risk_area(
    area_id: int, center_lat: float, center_lon: float, rng: random.Random
) -> Dict:
    """
    Generate a synthetic risk area event.
    
    Args:
        area_id: Unique identifier for this risk area
        center_lat: Center latitude
        center_lon: Center longitude
        rng: Random number generator instance
        
    Returns:
        Dictionary containing risk area event data
    """
    # Generate offset from center (within 10km)
    lat, lon = generate_offset_coordinates(center_lat, center_lon, 10.0, rng)
    
    # Random radius between 1500-5000 meters
    radius_meters = rng.uniform(1500, 5000)
    
    # Random severity (weighted towards medium/high)
    severity_weights = {"low": 0.2, "medium": 0.3, "high": 0.4, "critical": 0.1}
    risk_level = rng.choices(
        list(severity_weights.keys()), weights=list(severity_weights.values())
    )[0]
    
    severity = SEVERITY_LEVELS[risk_level]
    color = SEVERITY_COLORS[risk_level]
    opacity = SEVERITY_OPACITY[risk_level]
    
    # Random summary
    summary = rng.choice(RISK_AREA_SUMMARIES)
    
    risk_area_id = f"RISK-OTTAWA-{area_id:03d}"
    
    event_data = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "ottawa-overlay-generator",
        "severity": severity.value,
        "sector_id": "ottawa-region",
        "summary": summary,
        "correlation_id": str(uuid4()),
        "details": {
            "id": risk_area_id,
            "geometry": {
                "type": "Circle",
                "coordinates": [lon, lat],
                "radius_meters": radius_meters,
            },
            "style": {
                "color": color,
                "opacity": opacity,
                "outline": True,
            },
            "risk_level": risk_level,
            "risk_type": "operational_hotspot",
            "description": f"{summary} in Ottawa region (radius: {radius_meters:.0f}m)",
        },
    }
    
    return event_data


def generate_incident(
    incident_id: int,
    risk_area_center: Tuple[float, float],
    risk_area_radius: float,
    rng: random.Random,
) -> Dict:
    """
    Generate a synthetic incident event clustered around a risk area.
    
    Args:
        incident_id: Unique identifier for this incident
        risk_area_center: Center of the risk area (lat, lon)
        risk_area_radius: Radius of the risk area in meters
        rng: Random number generator instance
        
    Returns:
        Dictionary containing incident event data
    """
    # Generate point within or near the risk area
    # Convert radius to km for offset calculation
    radius_km = risk_area_radius / 1000.0
    # Clustering: most incidents within 80% of radius, some outside
    if rng.random() < 0.8:
        max_offset = radius_km * 0.8
    else:
        max_offset = radius_km * 1.5  # Some outside the area
    
    lat, lon = generate_offset_coordinates(
        risk_area_center[0], risk_area_center[1], max_offset, rng
    )
    
    # Random severity (weighted towards warning/error)
    severity_weights = {
        "low": 0.1,
        "medium": 0.3,
        "high": 0.4,
        "critical": 0.2,
    }
    severity_level = rng.choices(
        list(severity_weights.keys()), weights=list(severity_weights.values())
    )[0]
    
    severity = SEVERITY_LEVELS[severity_level]
    color = SEVERITY_COLORS[severity_level]
    opacity = SEVERITY_OPACITY[severity_level]
    
    # Random summary
    summary = rng.choice(INCIDENT_SUMMARIES)
    
    incident_id_str = f"INCIDENT-OTTAWA-{incident_id:03d}"
    
    event_data = {
        "event_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "ottawa-overlay-generator",
        "severity": severity.value,
        "sector_id": "ottawa-region",
        "summary": summary,
        "correlation_id": str(uuid4()),
        "details": {
            "id": incident_id_str,
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "style": {
                "color": color,
                "opacity": opacity,
                "outline": True,
            },
            "incident_type": "operational_incident",
            "description": f"{summary} at coordinates ({lat:.4f}, {lon:.4f})",
            "status": "active",
        },
    }
    
    return event_data


async def generate_and_publish_overlays(broker, rng: random.Random) -> None:
    """
    Generate and publish risk areas and incidents.
    
    Args:
        broker: Message broker instance
        rng: Random number generator instance
    """
    logger.info("=" * 80)
    logger.info("Generating Ottawa overlay events...")
    logger.info("=" * 80)
    
    # Generate 3-6 risk areas
    num_risk_areas = rng.randint(3, 6)
    risk_areas: List[Dict] = []
    risk_area_centers: List[Tuple[Tuple[float, float], float]] = []
    
    logger.info(f"Generating {num_risk_areas} risk areas...")
    
    for i in range(1, num_risk_areas + 1):
        risk_area = generate_risk_area(i, OTTAWA_LAT, OTTAWA_LON, rng)
        risk_areas.append(risk_area)
        
        # Store center and radius for incident clustering
        geometry = risk_area["details"]["geometry"]
        center = (geometry["coordinates"][1], geometry["coordinates"][0])  # (lat, lon)
        radius = geometry["radius_meters"]
        risk_area_centers.append((center, radius))
        
        logger.info(
            f"  Risk Area {i}: {risk_area['details']['id']} - "
            f"{risk_area['summary']} (radius: {radius:.0f}m)"
        )
    
    # Generate 5-12 incidents clustered around risk areas
    num_incidents = rng.randint(5, 12)
    incidents: List[Dict] = []
    
    logger.info(f"Generating {num_incidents} incidents...")
    
    for i in range(1, num_incidents + 1):
        # Choose a random risk area to cluster around
        risk_area_center, risk_area_radius = rng.choice(risk_area_centers)
        
        incident = generate_incident(i, risk_area_center, risk_area_radius, rng)
        incidents.append(incident)
        
        logger.info(
            f"  Incident {i}: {incident['details']['id']} - "
            f"{incident['summary']} (severity: {incident['severity']})"
        )
    
    # Publish risk areas
    logger.info("=" * 80)
    logger.info(f"Publishing {len(risk_areas)} risk area events...")
    logger.info("=" * 80)
    
    for risk_area in risk_areas:
        try:
            await publish(GEO_RISK_AREA_TOPIC, risk_area)
            capture_published_event(
                GEO_RISK_AREA_TOPIC,
                risk_area.get("event_id", "unknown"),
                {
                    "risk_area_id": risk_area["details"]["id"],
                    "risk_level": risk_area["details"]["risk_level"],
                },
            )
            add_breadcrumb(
                category="overlay_generator",
                message=f"Published risk area {risk_area['details']['id']}",
                data={"risk_level": risk_area["details"]["risk_level"]},
            )
            logger.info(f"✓ Published risk area: {risk_area['details']['id']}")
        except Exception as e:
            logger.error(f"✗ Failed to publish risk area: {e}")
            capture_exception(e, {"risk_area_id": risk_area.get("details", {}).get("id")})
    
    # Publish incidents
    logger.info("=" * 80)
    logger.info(f"Publishing {len(incidents)} incident events...")
    logger.info("=" * 80)
    
    for incident in incidents:
        try:
            await publish(GEO_INCIDENT_TOPIC, incident)
            capture_published_event(
                GEO_INCIDENT_TOPIC,
                incident.get("event_id", "unknown"),
                {
                    "incident_id": incident["details"]["id"],
                    "severity": incident["severity"],
                },
            )
            add_breadcrumb(
                category="overlay_generator",
                message=f"Published incident {incident['details']['id']}",
                data={"severity": incident["severity"]},
            )
            logger.info(f"✓ Published incident: {incident['details']['id']}")
        except Exception as e:
            logger.error(f"✗ Failed to publish incident: {e}")
            capture_exception(e, {"incident_id": incident.get("details", {}).get("id")})
    
    logger.info("=" * 80)
    logger.info(
        f"✓ Overlay generation complete: {len(risk_areas)} risk areas, {len(incidents)} incidents"
    )
    logger.info("=" * 80)


async def main() -> None:
    """Main entry point for the Ottawa overlay generator."""
    # Initialize Sentry
    init_sentry("ottawa_overlay_generator")
    capture_startup(
        "ottawa_overlay_generator",
        {
            "service_type": "overlay_generator",
            "publish_interval": PUBLISH_INTERVAL_SECONDS,
            "random_seed": RANDOM_SEED,
        },
    )
    
    # Initialize random number generator with seed if provided
    if RANDOM_SEED:
        seed_value = int(RANDOM_SEED)
        logger.info(f"Using stable random seed: {seed_value}")
        rng = random.Random(seed_value)
    else:
        logger.info("Using random seed (non-deterministic)")
        rng = random.Random()
    
    logger.info("=" * 80)
    logger.info("OTTAWA OVERLAY GENERATOR")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  Publish Interval: {PUBLISH_INTERVAL_SECONDS} seconds")
    logger.info(f"  Random Seed: {RANDOM_SEED or 'None (random)'}")
    logger.info(f"  Ottawa Center: ({OTTAWA_LAT}, {OTTAWA_LON})")
    logger.info("=" * 80)
    
    # Connect to message broker
    logger.info("Connecting to message broker...")
    broker = await get_broker()
    logger.info("Connected to message broker")
    
    logger.info("=" * 80)
    logger.info("Starting overlay generation loop...")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    try:
        while True:
            await generate_and_publish_overlays(broker, rng)
            logger.info(f"Waiting {PUBLISH_INTERVAL_SECONDS} seconds until next generation...")
            await asyncio.sleep(PUBLISH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await broker.disconnect()
        logger.info("Disconnected from message broker")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        capture_exception(e, {"service": "ottawa_overlay_generator", "error_type": "fatal"})
        sys.exit(1)

