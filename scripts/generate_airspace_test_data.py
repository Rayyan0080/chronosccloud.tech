"""
Generate test airspace aircraft position events for the dashboard.

This script publishes aircraft position events to the message broker,
which will be logged by state_logger and displayed in the dashboard.

Usage:
    python scripts/generate_airspace_test_data.py [--count N] [--interval SECONDS]
    
    --count: Number of aircraft to generate (default: 18, enough to show congestion)
    --interval: Seconds between updates (default: 10)
"""

import asyncio
import argparse
import logging
import os
import random
import sys
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

# Add project root to Python path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import AIRSPACE_AIRCRAFT_POSITION_TOPIC
from agents.shared.schema import AircraftPositionEvent, AircraftPositionDetails, Severity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ottawa bounding box
OTTAWA_BBOX = {
    "lat_min": 44.9,
    "lat_max": 45.6,
    "lon_min": -76.3,
    "lon_max": -75.0,
}

# Common aircraft callsigns
CALLSIGNS = [
    "ACA123", "WS456", "JZA789", "RJA012", "UAL345",
    "DAL678", "SWA901", "AAL234", "NKS567", "F9X890",
    "BAW123", "AFR456", "LUF789", "KLM012", "EZY345",
    "RYR678", "TAP901", "IBE234", "AFL567", "UAE890",
]


def generate_aircraft_event(icao24: str, callsign: str, lat: float, lon: float) -> dict:
    """Generate a single aircraft position event."""
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    details = AircraftPositionDetails(
        icao24=icao24,
        callsign=callsign,
        latitude=lat,
        longitude=lon,
        altitude=random.uniform(5000, 12000),  # meters
        velocity=random.uniform(150, 250),  # m/s
        heading=random.uniform(0, 360),
        vertical_rate=random.uniform(-5, 5),  # m/s
        on_ground=False,
        time_position=int(datetime.now(timezone.utc).timestamp()),
        data_source="test_data",
        disclaimer="Test data for dashboard demonstration"
    )
    
    event = AircraftPositionEvent(
        event_id=str(uuid4()),
        timestamp=current_time,
        source="test_airspace_generator",
        severity=Severity.INFO,
        sector_id="ottawa-airspace",
        summary=f"Aircraft {callsign} position update",
        correlation_id=None,
        details=details
    )
    
    return event.model_dump()


async def publish_aircraft_batch(count: int) -> None:
    """Publish a batch of aircraft position events."""
    broker = await get_broker()
    
    if not await broker.is_connected():
        logger.error("Failed to connect to message broker")
        return
    
    logger.info(f"Publishing {count} aircraft position events...")
    
    events_published = 0
    for i in range(count):
        # Generate random position within Ottawa bounding box
        lat = OTTAWA_BBOX["lat_min"] + random.uniform(
            0, OTTAWA_BBOX["lat_max"] - OTTAWA_BBOX["lat_min"]
        )
        lon = OTTAWA_BBOX["lon_min"] + random.uniform(
            0, OTTAWA_BBOX["lon_max"] - OTTAWA_BBOX["lon_min"]
        )
        
        # Generate ICAO24 address
        icao24 = f"{random.randint(0x100000, 0xFFFFFF):06x}"
        callsign = random.choice(CALLSIGNS)
        
        # Generate and publish event
        event = generate_aircraft_event(icao24, callsign, lat, lon)
        
        try:
            await publish(AIRSPACE_AIRCRAFT_POSITION_TOPIC, event)
            events_published += 1
            logger.debug(f"Published aircraft {callsign} ({icao24})")
        except Exception as e:
            logger.error(f"Failed to publish aircraft event: {e}")
    
    logger.info(f"✓ Published {events_published}/{count} aircraft position events")
    
    # Calculate expected congestion
    congestion = min(100, (count / 15) * 100)
    logger.info(f"Expected congestion: {congestion:.1f}% ({count} aircraft / 15 threshold)")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate test airspace aircraft position events")
    parser.add_argument(
        "--count",
        type=int,
        default=18,
        help="Number of aircraft to generate (default: 18, shows ~120%% congestion)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="Seconds between updates (default: 10.0, set to 0 for one-time run)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously, updating aircraft positions at interval"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("AIRSPACE TEST DATA GENERATOR")
    logger.info("=" * 80)
    logger.info(f"Aircraft count: {args.count}")
    logger.info(f"Update interval: {args.interval}s")
    logger.info(f"Mode: {'Continuous' if args.continuous else 'One-time'}")
    logger.info("=" * 80)
    
    try:
        if args.continuous and args.interval > 0:
            logger.info("Running in continuous mode. Press Ctrl+C to stop.")
            while True:
                await publish_aircraft_batch(args.count)
                logger.info(f"Waiting {args.interval} seconds before next update...")
                await asyncio.sleep(args.interval)
        else:
            await publish_aircraft_batch(args.count)
            logger.info("Done! Check the dashboard to see the airspace congestion gauge.")
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        broker = await get_broker()
        await broker.disconnect()
        logger.info("Disconnected from message broker")


if __name__ == "__main__":
    asyncio.run(main())

