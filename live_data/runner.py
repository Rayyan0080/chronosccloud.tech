"""
Live data adapter runner.

Loads and polls enabled adapters, publishing normalized events to the message broker.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

# Add project root to Python path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# Also add current directory to path (in case running from project root)
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from agents.shared.messaging import get_broker, publish
from agents.shared.constants import (
    TRANSIT_VEHICLE_POSITION_TOPIC,
    TRANSIT_TRIP_UPDATE_TOPIC,
    GEO_INCIDENT_TOPIC,
    GEO_RISK_AREA_TOPIC,
    AIRSPACE_AIRCRAFT_POSITION_TOPIC,
)
from agents.shared.sentry import (
    init_sentry,
    capture_exception,
    capture_startup,
    add_breadcrumb,
    set_tag,
)
from live_data.base import LiveAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Adapter registry - populated by adapter modules
_adapters: Dict[str, type] = {}
_adapter_instances: Dict[str, LiveAdapter] = {}
_adapter_status: Dict[str, Dict] = {}  # Track adapter health/status
_adapter_disabled_until: Dict[str, Optional[datetime]] = {}  # Temporary disable tracking
_adapter_degraded: Dict[str, bool] = {}  # Track if adapter has degraded to mock mode


def register_adapter(adapter_class: type) -> None:
    """
    Register an adapter class.
    
    Adapter modules should call this to register themselves.
    
    Args:
        adapter_class: Subclass of LiveAdapter
    """
    if not issubclass(adapter_class, LiveAdapter):
        raise ValueError(f"{adapter_class.__name__} must inherit from LiveAdapter")
    
    instance = adapter_class()
    _adapters[instance.name] = adapter_class
    logger.debug(f"Registered adapter: {instance.name}")


def get_enabled_adapters() -> List[str]:
    """
    Get list of enabled adapter names from environment variable.
    
    Returns:
        List of adapter names (e.g., ['oc_transpo', 'ottawa_traffic'])
    """
    adapters_str = os.getenv("LIVE_ADAPTERS", "")
    if not adapters_str:
        return []
    
    # Parse comma-separated list, strip whitespace
    adapters = [name.strip() for name in adapters_str.split(",") if name.strip()]
    return adapters


def load_adapter(name: str) -> Optional[LiveAdapter]:
    """
    Load and instantiate an adapter by name.
    
    Args:
        name: Adapter name (e.g., 'oc_transpo')
    
    Returns:
        Adapter instance or None if not found/disabled
    """
    if name in _adapter_instances:
        return _adapter_instances[name]
    
    # Try to import adapter module
    try:
        import importlib
        module_name = f"live_data.adapters.{name}"
        logger.debug(f"Importing adapter module: {module_name}")
        # Use importlib to ensure module is fully loaded and executed
        try:
            module = importlib.import_module(module_name)
        except Exception as import_error:
            logger.error(f"Error importing module {module_name}: {import_error}", exc_info=True)
            raise
        # Check if registration happened
        adapter_class = _adapters.get(name)
        logger.debug(f"After import, adapter_class for '{name}': {adapter_class is not None}")
        
        if not adapter_class:
            logger.warning(f"Adapter '{name}' not registered after import")
            logger.debug(f"Available adapters: {list(_adapters.keys())}")
            # Try to find and register the adapter class manually
            # Look for classes that end with "Adapter" in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name, None)
                if (isinstance(attr, type) and 
                    issubclass(attr, LiveAdapter) and 
                    attr != LiveAdapter and
                    attr_name.endswith("Adapter")):
                    logger.info(f"Found adapter class {attr_name}, registering manually")
                    try:
                        register_adapter(attr)
                        adapter_class = _adapters.get(name)
                        if adapter_class:
                            break
                    except Exception as reg_error:
                        logger.error(f"Error registering adapter class: {reg_error}")
            
            if not adapter_class:
                logger.error(f"Could not find or register adapter class for '{name}'")
                return None
        
        instance = adapter_class()
        if not instance.is_enabled():
            logger.info(f"Adapter '{name}' is disabled")
            return None
        
        # Check global LIVE_MODE setting
        from live_data.base import is_live_mode_enabled
        if not is_live_mode_enabled():
            # Force mock mode if LIVE_MODE=off
            if hasattr(instance, '_mode'):
                instance._mode = "mock"
                logger.info(f"Adapter '{name}' forced to mock mode (LIVE_MODE=off)")
        
        _adapter_instances[name] = instance
        initial_mode = getattr(instance, '_mode', 'live') if is_live_mode_enabled() else 'mock'
        _adapter_status[name] = {
            "enabled": True,
            "mode": initial_mode,
            "last_fetch": None,
            "last_error": None,
            "fetch_count": 0,
            "event_count": 0,
            "degraded": False,  # Track if adapter degraded from live to mock
        }
        _adapter_disabled_until[name] = None
        _adapter_degraded[name] = False
        
        logger.info(f"Loaded adapter: {name} (poll_interval={instance.poll_interval_seconds}s, mode={initial_mode})")
        return instance
        
    except ImportError as e:
        logger.warning(f"Could not import adapter '{name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading adapter '{name}': {e}", exc_info=True)
        capture_exception(e, {"adapter_name": name, "operation": "load_adapter"})
        return None


async def poll_adapter(adapter: LiveAdapter) -> None:
    """
    Poll a single adapter, fetch data, normalize, and publish events.
    
    Args:
        adapter: Adapter instance to poll
    """
    adapter_name = adapter.name
    
    # Check if adapter is temporarily disabled
    if adapter_name in _adapter_disabled_until:
        disabled_until = _adapter_disabled_until[adapter_name]
        if disabled_until and datetime.utcnow() < disabled_until:
            logger.debug(f"Adapter '{adapter_name}' is temporarily disabled until {disabled_until}")
            return
    
    try:
        add_breadcrumb(f"polling_adapter_{adapter_name}", {"adapter": adapter_name})
        
        # Fetch raw data
        logger.debug(f"Fetching data from adapter: {adapter_name}")
        raw_items = adapter.fetch()
        
        if not raw_items:
            logger.debug(f"No data from adapter: {adapter_name}")
            return
        
        logger.info(f"Fetched {len(raw_items)} items from adapter: {adapter_name}")
        
        # Update status
        _adapter_status[adapter_name]["last_fetch"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        _adapter_status[adapter_name]["fetch_count"] = _adapter_status[adapter_name].get("fetch_count", 0) + 1
        
        # Normalize and publish events
        total_events = 0
        
        # Special handling for opensky_airspace adapter: check for congestion hotspots after processing all aircraft
        is_opensky_airspace = adapter_name == "opensky_airspace"
        processed_aircraft_count = 0
        
        for raw_item in raw_items:
            try:
                events = adapter.normalize(raw_item)
                
                # Track aircraft count for opensky_airspace
                if is_opensky_airspace:
                    # Count aircraft position events (not hotspot events)
                    for event in events:
                        if hasattr(event, "details") and hasattr(event.details, "icao24"):
                            processed_aircraft_count += 1
                
                for event in events:
                    # Convert BaseEvent to dict for publishing
                    if hasattr(event, "model_dump"):
                        event_dict = event.model_dump()
                    elif hasattr(event, "dict"):
                        event_dict = event.dict()
                    else:
                        event_dict = event
                    
                    # Determine topic from event source or use default
                    # Special handling for transit events, geo events, airspace events, and mock.enabled
                    source = event_dict.get("source", "")
                    details = event_dict.get("details", {})
                    
                    # Check for airspace.aircraft.position events
                    if details.get("icao24") is not None and details.get("data_source"):
                        topic = AIRSPACE_AIRCRAFT_POSITION_TOPIC
                    # Check for geo events (has geometry field)
                    # Distinguish between geo.incident and geo.risk_area by checking details structure
                    elif details.get("geometry"):
                        # GeoRiskAreaDetails has risk_type/risk_level, GeoIncidentDetails has incident_type/status
                        if details.get("risk_type") is not None or details.get("risk_level") is not None:
                            topic = GEO_RISK_AREA_TOPIC
                        else:
                            topic = GEO_INCIDENT_TOPIC
                    # Check for transit.mock.enabled
                    elif "transit.mock.enabled" in event_dict.get("summary", "").lower() or "mock mode" in event_dict.get("summary", "").lower():
                        topic = "chronos.events.transit.mock.enabled"
                    # Use specific transit topics for GTFS-RT adapter
                    elif source == "oc_transpo_gtfsrt_adapter":
                        if details.get("vehicle_id"):
                            topic = TRANSIT_VEHICLE_POSITION_TOPIC
                        elif details.get("trip_id"):
                            topic = TRANSIT_TRIP_UPDATE_TOPIC
                        else:
                            topic = f"chronos.events.{adapter_name}.{source}"
                    else:
                        topic = f"chronos.events.{adapter_name}.{source or 'data'}"
                    
                    # Publish event
                    await publish(topic, event_dict)
                    total_events += 1
                    
                    add_breadcrumb(f"published_event_{adapter_name}", {
                        "adapter": adapter_name,
                        "event_id": event_dict.get("event_id"),
                        "topic": topic,
                    })
                
            except Exception as normalize_error:
                logger.error(f"Error normalizing item from adapter '{adapter_name}': {normalize_error}", exc_info=True)
                capture_exception(normalize_error, {
                    "adapter_name": adapter_name,
                    "operation": "normalize",
                    "raw_item": str(raw_item)[:200],  # Truncate for logging
                })
                # Continue with next item
        
        # Check for congestion hotspot for opensky_airspace adapter
        if is_opensky_airspace and processed_aircraft_count > 0:
            try:
                # Import here to avoid circular dependency
                from live_data.adapters.opensky_airspace import OpenSkyAirspaceAdapter, AIRCRAFT_COUNT_THRESHOLD
                
                if processed_aircraft_count > AIRCRAFT_COUNT_THRESHOLD and isinstance(adapter, OpenSkyAirspaceAdapter):
                    hotspot_event = adapter._check_congestion_hotspot(raw_items)
                    if hotspot_event:
                        if hasattr(hotspot_event, "model_dump"):
                            hotspot_dict = hotspot_event.model_dump()
                        elif hasattr(hotspot_event, "dict"):
                            hotspot_dict = hotspot_event.dict()
                        else:
                            hotspot_dict = hotspot_event
                        
                        await publish(GEO_RISK_AREA_TOPIC, hotspot_dict)
                        total_events += 1
                        
                        add_breadcrumb(f"published_hotspot_{adapter_name}", {
                            "adapter": adapter_name,
                            "event_id": hotspot_dict.get("event_id"),
                            "aircraft_count": processed_aircraft_count,
                            "threshold": AIRCRAFT_COUNT_THRESHOLD,
                        })
            except Exception as hotspot_error:
                logger.error(f"Error checking congestion hotspot for '{adapter_name}': {hotspot_error}", exc_info=True)
                capture_exception(hotspot_error, {
                    "adapter_name": adapter_name,
                    "operation": "congestion_hotspot_check",
                })
        
        # Update status
        _adapter_status[adapter_name]["event_count"] = _adapter_status[adapter_name].get("event_count", 0) + total_events
        
        # Check if adapter mode changed (degraded to mock)
        current_mode = getattr(adapter, '_mode', 'unknown')
        if current_mode == 'mock' and _adapter_status[adapter_name].get("mode") == 'live':
            # Adapter degraded from live to mock
            _adapter_status[adapter_name]["mode"] = "mock"
            _adapter_status[adapter_name]["degraded"] = True
            _adapter_degraded[adapter_name] = True
            logger.warning(f"Adapter '{adapter_name}' degraded: falling back to mock mode")
        elif current_mode == 'live' and _adapter_status[adapter_name].get("mode") == 'mock':
            # Adapter recovered from mock to live
            _adapter_status[adapter_name]["mode"] = "live"
            _adapter_status[adapter_name]["degraded"] = False
            _adapter_degraded[adapter_name] = False
            logger.info(f"Adapter '{adapter_name}' recovered: back to live mode")
        else:
            # Update mode if changed
            _adapter_status[adapter_name]["mode"] = current_mode
        
        if total_events > 0:
            logger.info(f"Published {total_events} events from adapter: {adapter_name}")
        
        # Clear any temporary disable if successful
        if adapter_name in _adapter_disabled_until:
            _adapter_disabled_until[adapter_name] = None
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error polling adapter '{adapter_name}': {error_msg}", exc_info=True)
        
        # Check if adapter degraded to mock mode
        current_mode = getattr(adapter, '_mode', 'unknown')
        if current_mode == 'mock' and _adapter_status[adapter_name].get("mode") == 'live':
            _adapter_status[adapter_name]["mode"] = "mock"
            _adapter_status[adapter_name]["degraded"] = True
            _adapter_degraded[adapter_name] = True
            logger.warning(f"Adapter '{adapter_name}' degraded: falling back to mock mode")
        
        # Capture exception in Sentry
        capture_exception(e, {
            "adapter_name": adapter_name,
            "operation": "poll_adapter",
        })
        
        # Update status
        _adapter_status[adapter_name]["last_error"] = error_msg
        
        # Temporarily disable adapter after failures
        # Re-enable after 5 minutes
        disable_duration_minutes = 5
        _adapter_disabled_until[adapter_name] = datetime.utcnow() + timedelta(minutes=disable_duration_minutes)
        
        logger.warning(
            f"Adapter '{adapter_name}' temporarily disabled for {disable_duration_minutes} minutes due to errors"
        )


async def adapter_poll_loop(adapter: LiveAdapter) -> None:
    """
    Run polling loop for a single adapter.
    
    Args:
        adapter: Adapter instance to poll
    """
    adapter_name = adapter.name
    interval = adapter.poll_interval_seconds
    
    logger.info(f"Starting poll loop for adapter: {adapter_name} (interval={interval}s)")
    
    while True:
        try:
            await poll_adapter(adapter)
        except Exception as e:
            # This should never happen, but catch it just in case
            logger.critical(f"Fatal error in poll loop for '{adapter_name}': {e}", exc_info=True)
            capture_exception(e, {
                "adapter_name": adapter_name,
                "operation": "adapter_poll_loop",
            })
        
        # Wait for next poll interval
        await asyncio.sleep(interval)


def get_adapter_status_summary() -> Dict[str, Any]:
    """
    Get summary of all adapter statuses for API/dashboard.
    
    Returns:
        Dict with live_mode, adapters list, and degraded adapters list
    """
    from live_data.base import is_live_mode_enabled
    
    live_mode = is_live_mode_enabled()
    adapters = []
    degraded = []
    
    for name, status in _adapter_status.items():
        adapter_info = {
            "name": name,
            "mode": status.get("mode", "unknown"),
            "enabled": status.get("enabled", False),
            "degraded": status.get("degraded", False),
            "last_fetch": status.get("last_fetch"),
            "last_error": status.get("last_error"),
        }
        adapters.append(adapter_info)
        
        if status.get("degraded", False):
            degraded.append(name)
    
    return {
        "live_mode": "on" if live_mode else "off",
        "adapters": adapters,
        "degraded_adapters": degraded,
    }


async def main() -> None:
    """Main entry point for the live data runner."""
    from live_data.base import is_live_mode_enabled
    
    logger.info("=" * 80)
    logger.info("STARTING LIVE DATA ADAPTER RUNNER")
    logger.info(f"LIVE_MODE: {'ON' if is_live_mode_enabled() else 'OFF'}")
    logger.info("=" * 80)
    logger.info("=" * 80)
    
    # Initialize Sentry
    init_sentry("live_data_runner", "N/A")
    capture_startup("live_data_runner", {})
    
    # Get enabled adapters
    enabled_names = get_enabled_adapters()
    if not enabled_names:
        logger.warning("No adapters enabled. Set LIVE_ADAPTERS environment variable.")
        logger.warning("Example: LIVE_ADAPTERS=oc_transpo,ottawa_traffic,opensky,ontario511")
        return
    
    logger.info(f"Enabled adapters: {', '.join(enabled_names)}")
    
    # Load adapters
    loaded_adapters: List[LiveAdapter] = []
    for name in enabled_names:
        adapter = load_adapter(name)
        if adapter:
            loaded_adapters.append(adapter)
        else:
            logger.warning(f"  ❌ {name}: Failed to load or disabled")
    
    if not loaded_adapters:
        logger.error("No adapters loaded successfully. Exiting.")
        return
    
    # Print startup summary: Live vs Mock
    logger.info("=" * 80)
    logger.info("ADAPTER STATUS SUMMARY")
    logger.info("=" * 80)
    live_adapters = []
    mock_adapters = []
    
    for adapter in loaded_adapters:
        status = adapter.get_status()
        mode = status.get("mode", "unknown").lower()
        if mode == "live":
            live_adapters.append(adapter.name)
        elif mode == "mock":
            mock_adapters.append(adapter.name)
    
    if live_adapters:
        logger.info(f"🟢 LIVE: {', '.join(live_adapters)}")
    if mock_adapters:
        logger.info(f"🟡 MOCK: {', '.join(mock_adapters)}")
    if not live_adapters and not mock_adapters:
        logger.info("⚠️  No adapters with known mode")
    logger.info("=" * 80)
    
    # Connect to message broker
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
    
    # Set Sentry tags
    set_tag("adapters_count", len(loaded_adapters))
    set_tag("adapters", ",".join([a.name for a in loaded_adapters]))
    
    logger.info("=" * 80)
    logger.info("LIVE DATA RUNNER STARTED")
    logger.info(f"Running {len(loaded_adapters)} adapter(s) in parallel")
    logger.info("=" * 80)
    
    # Start polling loops for all adapters in parallel
    try:
        tasks = [adapter_poll_loop(adapter) for adapter in loaded_adapters]
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in runner: {e}", exc_info=True)
        capture_exception(e, {"operation": "main_loop"})
        raise
    finally:
        await broker.disconnect()
        logger.info("Disconnected from message broker")
    
    logger.info("Live data runner stopped.")


if __name__ == "__main__":
    asyncio.run(main())

