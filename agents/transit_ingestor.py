"""
Transit Ingestor Service

Fetches OC Transpo GTFS-RT feeds and publishes transit events.
Runs every 10 seconds to fetch vehicle positions and trip updates.

Transit data is informational only - NOT FOR OPERATIONAL USE
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, publish
from agents.shared.schema import (
    TransitGTFSRTFetchStartedEvent,
    TransitVehiclePositionEvent,
    TransitTripUpdateEvent,
    Severity,
)
from agents.shared.constants import (
    TRANSIT_GTFSRT_FETCH_STARTED_TOPIC,
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    DISCLAIMER_TRANSIT,
)
from agents.shared.sentry import (
    init_sentry,
    capture_startup,
    capture_published_event,
    capture_exception,
    add_breadcrumb,
    set_tag,
)

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import transit_octranspo module
try:
    from transit_octranspo import (
        fetch_gtfsrt_feed,
        parse_vehicle_positions,
        parse_trip_updates,
        is_mock_mode,
        get_feed_url,
        get_transit_mode,
    )
    TRANSIT_CLIENT_AVAILABLE = True
except ImportError as e:
    TRANSIT_CLIENT_AVAILABLE = False
    logger.warning(f"transit_octranspo module not available: {e}")

# Configuration
FETCH_INTERVAL_SECONDS = 10
MAX_CONSECUTIVE_FAILURES = 3  # Switch to mock mode after 3 consecutive failures

# State tracking
_consecutive_failures = 0
_using_mock_mode = False


async def publish_fetch_started_event(feed_type: str, feed_url: str, expected_entities: Optional[int] = None) -> None:
    """
    Publish transit.gtfsrt.fetch.started event.
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        feed_url: Feed URL
        expected_entities: Expected number of entities (optional)
    """
    try:
        fetch_id = f"FETCH-{str(uuid4())[:8].upper()}"
        
        event = TransitGTFSRTFetchStartedEvent(
            event_id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="transit-ingestor",
            severity=Severity.INFO,
            sector_id="ottawa-transit",
            summary=f"GTFS-RT {feed_type} feed fetch started",
            correlation_id=fetch_id,
            details={
                "feed_url": feed_url,
                "feed_type": feed_type,
                "fetch_id": fetch_id,
                "expected_entities": expected_entities,
            }
        )
        
        event_dict = event.dict()
        await publish(TRANSIT_GTFSRT_FETCH_STARTED_TOPIC, event_dict)
        
        capture_published_event(
            TRANSIT_GTFSRT_FETCH_STARTED_TOPIC,
            event_dict["event_id"],
            {"feed_type": feed_type, "fetch_id": fetch_id}
        )
        
        logger.info(f"Published fetch started event for {feed_type} (fetch_id: {fetch_id})")
        
    except Exception as e:
        logger.error(f"Failed to publish fetch started event: {e}", exc_info=True)
        capture_exception(e, {"feed_type": feed_type, "operation": "publish_fetch_started"})


async def publish_vehicle_position_event(position: Any) -> None:
    """
    Publish transit.vehicle.position event from VehiclePosition model.
    
    Args:
        position: VehiclePosition model instance
    """
    try:
        # Convert position to dict for event details
        position_dict = position.to_dict()
        
        # Build summary
        route_str = f"Route {position_dict.get('route_id', 'UNKNOWN')}" if position_dict.get('route_id') else "Unknown route"
        summary = f"Vehicle {position_dict.get('vehicle_id', 'UNKNOWN')} position update on {route_str}"
        
        event = TransitVehiclePositionEvent(
            event_id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="transit-ingestor",
            severity=Severity.INFO,
            sector_id="ottawa-transit",
            summary=summary,
            correlation_id=position_dict.get("trip_id") or position_dict.get("vehicle_id"),
            details={
                "vehicle_id": position_dict.get("vehicle_id"),
                "trip_id": position_dict.get("trip_id"),
                "route_id": position_dict.get("route_id"),
                "latitude": position_dict.get("latitude"),
                "longitude": position_dict.get("longitude"),
                "bearing": position_dict.get("bearing"),
                "speed": position_dict.get("speed"),
                "occupancy_status": position_dict.get("occupancy_status"),
                "current_stop_sequence": position_dict.get("current_stop_sequence"),
                "current_status": position_dict.get("current_status"),
                "timestamp": position_dict.get("timestamp"),
            }
        )
        
        event_dict = event.dict()
        await publish(TRANSIT_VEHICLE_POSITION_TOPIC, event_dict)
        
        capture_published_event(
            TRANSIT_VEHICLE_POSITION_TOPIC,
            event_dict["event_id"],
            {
                "vehicle_id": position_dict.get("vehicle_id"),
                "route_id": position_dict.get("route_id"),
                "trip_id": position_dict.get("trip_id"),
            }
        )
        
        logger.debug(f"Published vehicle position: {position_dict.get('vehicle_id')} on route {position_dict.get('route_id')}")
        
    except Exception as e:
        logger.error(f"Failed to publish vehicle position event: {e}", exc_info=True)
        capture_exception(e, {"vehicle_id": position_dict.get("vehicle_id") if 'position_dict' in locals() else "unknown", "operation": "publish_vehicle_position"})


async def publish_trip_update_event(update: Any) -> None:
    """
    Publish transit.trip.update event from TripUpdate model.
    
    Args:
        update: TripUpdate model instance
    """
    try:
        # Convert update to dict for event details
        update_dict = update.to_dict()
        
        # Build summary
        route_str = f"Route {update_dict.get('route_id', 'UNKNOWN')}" if update_dict.get('route_id') else "Unknown route"
        delay_str = f" (delay: {update_dict.get('delay', 0)}s)" if update_dict.get('delay') else ""
        summary = f"Trip {update_dict.get('trip_id', 'UNKNOWN')} update on {route_str}{delay_str}"
        
        event = TransitTripUpdateEvent(
            event_id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="transit-ingestor",
            severity=Severity.INFO if not update_dict.get("delay") or update_dict.get("delay", 0) <= 300 else Severity.WARNING,
            sector_id="ottawa-transit",
            summary=summary,
            correlation_id=update_dict.get("trip_id"),
            details={
                "trip_id": update_dict.get("trip_id"),
                "route_id": update_dict.get("route_id"),
                "vehicle_id": update_dict.get("vehicle_id"),
                "stop_time_updates": update_dict.get("stop_time_updates"),
                "delay": update_dict.get("delay"),
                "timestamp": update_dict.get("timestamp"),
            }
        )
        
        event_dict = event.dict()
        await publish(TRANSIT_TRIP_UPDATE_TOPIC, event_dict)
        
        capture_published_event(
            TRANSIT_TRIP_UPDATE_TOPIC,
            event_dict["event_id"],
            {
                "trip_id": update_dict.get("trip_id"),
                "route_id": update_dict.get("route_id"),
                "vehicle_id": update_dict.get("vehicle_id"),
                "delay": update_dict.get("delay"),
            }
        )
        
        logger.debug(f"Published trip update: {update_dict.get('trip_id')} on route {update_dict.get('route_id')} (delay: {update_dict.get('delay', 0)}s)")
        
    except Exception as e:
        logger.error(f"Failed to publish trip update event: {e}", exc_info=True)
        capture_exception(e, {"trip_id": update_dict.get("trip_id") if 'update_dict' in locals() else "unknown", "operation": "publish_trip_update"})


async def fetch_and_publish_vehicle_positions() -> bool:
    """
    Fetch vehicle positions feed and publish each position as an event.
    
    Returns:
        True if successful, False otherwise
    """
    global _consecutive_failures, _using_mock_mode
    
    try:
        feed_url = get_feed_url("vehicle_positions")
        
        # Publish fetch started event
        await publish_fetch_started_event("vehicle_positions", feed_url)
        
        add_breadcrumb("fetching_vehicle_positions", {"feed_url": feed_url})
        
        # Fetch feed
        feed_data = await fetch_gtfsrt_feed("vehicle_positions")
        
        # Parse vehicle positions
        positions = parse_vehicle_positions(feed_data)
        
        logger.info(f"Fetched {len(positions)} vehicle positions from {feed_url}")
        
        # Publish each position
        published_count = 0
        for position in positions:
            try:
                await publish_vehicle_position_event(position)
                published_count += 1
            except Exception as e:
                logger.warning(f"Failed to publish position for vehicle {position.vehicle_id}: {e}")
                capture_exception(e, {"vehicle_id": position.vehicle_id})
        
        logger.info(f"Published {published_count}/{len(positions)} vehicle position events")
        
        # Reset failure counter on success
        _consecutive_failures = 0
        if _using_mock_mode:
            logger.info("Switched back to real API mode after successful fetch")
            _using_mock_mode = False
        
        return True
        
    except Exception as e:
        _consecutive_failures += 1
        logger.error(f"Failed to fetch vehicle positions (consecutive failures: {_consecutive_failures}): {e}", exc_info=True)
        capture_exception(e, {"operation": "fetch_vehicle_positions", "consecutive_failures": _consecutive_failures})
        
        # Switch to mock mode if too many failures
        if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES and not _using_mock_mode:
            logger.warning(f"Switching to mock mode after {_consecutive_failures} consecutive failures")
            _using_mock_mode = True
            set_tag("mock_mode", "true")
            # Try again with mock mode
            return await fetch_and_publish_vehicle_positions()
        
        return False


async def fetch_and_publish_trip_updates() -> bool:
    """
    Fetch trip updates feed and publish each update as an event.
    
    Returns:
        True if successful, False otherwise
    """
    global _consecutive_failures, _using_mock_mode
    
    try:
        feed_url = get_feed_url("trip_updates")
        
        # Publish fetch started event
        await publish_fetch_started_event("trip_updates", feed_url)
        
        add_breadcrumb("fetching_trip_updates", {"feed_url": feed_url})
        
        # Fetch feed
        feed_data = await fetch_gtfsrt_feed("trip_updates")
        
        # Parse trip updates
        updates = parse_trip_updates(feed_data)
        
        logger.info(f"Fetched {len(updates)} trip updates from {feed_url}")
        
        # Publish each update
        published_count = 0
        for update in updates:
            try:
                await publish_trip_update_event(update)
                published_count += 1
            except Exception as e:
                logger.warning(f"Failed to publish update for trip {update.trip_id}: {e}")
                capture_exception(e, {"trip_id": update.trip_id})
        
        logger.info(f"Published {published_count}/{len(updates)} trip update events")
        
        # Reset failure counter on success
        _consecutive_failures = 0
        if _using_mock_mode:
            logger.info("Switched back to real API mode after successful fetch")
            _using_mock_mode = False
        
        return True
        
    except Exception as e:
        _consecutive_failures += 1
        logger.error(f"Failed to fetch trip updates (consecutive failures: {_consecutive_failures}): {e}", exc_info=True)
        capture_exception(e, {"operation": "fetch_trip_updates", "consecutive_failures": _consecutive_failures})
        
        # Switch to mock mode if too many failures
        if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES and not _using_mock_mode:
            logger.warning(f"Switching to mock mode after {_consecutive_failures} consecutive failures")
            _using_mock_mode = True
            set_tag("mock_mode", "true")
            # Try again with mock mode
            return await fetch_and_publish_trip_updates()
        
        return False


async def fetch_cycle() -> None:
    """
    Single fetch cycle: fetch both vehicle positions and trip updates.
    """
    logger.info("=" * 60)
    logger.info("Starting transit feed fetch cycle")
    logger.info("=" * 60)
    
    # Fetch vehicle positions
    vehicle_success = await fetch_and_publish_vehicle_positions()
    
    # Fetch trip updates
    trip_success = await fetch_and_publish_trip_updates()
    
    if vehicle_success and trip_success:
        logger.info("Fetch cycle completed successfully")
    else:
        logger.warning(f"Fetch cycle completed with errors (vehicles: {vehicle_success}, trips: {trip_success})")


async def main() -> None:
    """Main entry point for the transit ingestor service."""
    global _using_mock_mode
    
    logger.info("=" * 60)
    logger.info("Starting Transit Ingestor Service")
    logger.info("=" * 60)
    logger.info(f"Fetch Interval: {FETCH_INTERVAL_SECONDS} seconds")
    logger.info(f"Max Consecutive Failures: {MAX_CONSECUTIVE_FAILURES}")
    
    # Initialize Sentry
    init_sentry("transit_ingestor", "N/A")
    capture_startup("transit_ingestor", {
        "fetch_interval_seconds": FETCH_INTERVAL_SECONDS,
        "max_consecutive_failures": MAX_CONSECUTIVE_FAILURES,
    })
    
    # Check if transit client is available
    if not TRANSIT_CLIENT_AVAILABLE:
        logger.error("transit_octranspo module not available. Cannot start service.")
        logger.error("Install dependencies: pip install -r transit_octranspo/requirements.txt")
        return
    
    # Check transit mode
    transit_mode = get_transit_mode()
    logger.info(f"Transit mode: {transit_mode}")
    
    if transit_mode == "mock":
        logger.warning("=" * 60)
        logger.warning("⚠️  RUNNING IN MOCK MODE ⚠️")
        logger.warning("=" * 60)
        logger.warning("Using synthetic transit data generator.")
        logger.warning(f"{DISCLAIMER_TRANSIT}")
        logger.warning("=" * 60)
        _using_mock_mode = True
        set_tag("mock_mode", "true")
        set_tag("transit_mode", "mock")
    else:
        logger.info("Using real OC Transpo GTFS-RT API")
        _using_mock_mode = False
        set_tag("mock_mode", "false")
        set_tag("transit_mode", "live")
    
    # Initialize broker connection
    try:
        broker = await get_broker()
        if not await broker.is_connected():
            logger.error("Failed to connect to message broker")
            return
        logger.info(f"Connected to message broker: {type(broker).__name__}")
    except Exception as e:
        logger.error(f"Failed to initialize message broker: {e}", exc_info=True)
        capture_exception(e, {"operation": "broker_init"})
        return
    
    logger.info("=" * 60)
    logger.info("Transit Ingestor Service started successfully")
    logger.info("=" * 60)
    
    # Main loop: fetch every FETCH_INTERVAL_SECONDS
    try:
        while True:
            await fetch_cycle()
            logger.info(f"Waiting {FETCH_INTERVAL_SECONDS} seconds until next fetch...")
            await asyncio.sleep(FETCH_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        capture_exception(e, {"operation": "main_loop"})
        raise


if __name__ == "__main__":
    asyncio.run(main())

