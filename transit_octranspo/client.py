"""
OC Transpo GTFS-RT client with caching, timeout, retry, and backoff.

Fetches real-time transit data from OC Transpo GTFS-RT feeds.
Falls back to mock feed generator if API key is missing.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, skip

from .config import (
    get_octranspo_api_key,
    get_feed_url,
    is_mock_mode,
    get_transit_mode,
)
from .decode import decode_feed_message, PROTOBUF_AVAILABLE
from .models import VehiclePosition, TripUpdate, StopTimeUpdate

logger = logging.getLogger(__name__)

# Cache configuration
_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl: Dict[str, float] = {}
CACHE_TTL_SECONDS = 30  # Cache for 30 seconds


def _get_from_cache(feed_type: str) -> Optional[Dict[str, Any]]:
    """
    Get cached feed data if available and not expired.
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        
    Returns:
        Cached feed data or None if not available/expired
    """
    cache_key = f"feed_{feed_type}"
    
    if cache_key not in _cache:
        return None
    
    if cache_key not in _cache_ttl:
        return None
    
    if time.time() > _cache_ttl[cache_key]:
        # Cache expired
        _cache.pop(cache_key, None)
        _cache_ttl.pop(cache_key, None)
        return None
    
    return _cache[cache_key]


def _set_cache(feed_type: str, data: Dict[str, Any]) -> None:
    """
    Store feed data in cache.
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        data: Feed data to cache
    """
    cache_key = f"feed_{feed_type}"
    _cache[cache_key] = data
    _cache_ttl[cache_key] = time.time() + CACHE_TTL_SECONDS


async def fetch_gtfsrt_feed(feed_type: str) -> Dict[str, Any]:
    """
    Fetch GTFS-RT feed from OC Transpo API.
    
    Features:
    - 5 second timeout
    - 2 retries with exponential backoff
    - 30 second caching
    - Automatic fallback to mock data if API key missing
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        
    Returns:
        Dictionary containing decoded feed message
        
    Raises:
        ValueError: If feed_type is invalid
        ImportError: If protobuf library is not available (and not in mock mode)
    """
    if feed_type not in ["vehicle_positions", "trip_updates"]:
        raise ValueError(f"Invalid feed_type: {feed_type}. Must be 'vehicle_positions' or 'trip_updates'")
    
    # Check cache first
    cached_data = _get_from_cache(feed_type)
    if cached_data:
        logger.debug(f"Returning cached {feed_type} feed")
        return cached_data
    
    # Check transit mode
    transit_mode = get_transit_mode()
    if transit_mode == "mock":
        logger.info(f"Transit mode: mock - using mock {feed_type} feed generator")
        mock_data = _generate_mock_feed(feed_type)
        _set_cache(feed_type, mock_data)
        return mock_data
    
    # Fetch from API with retry logic
    url = get_feed_url(feed_type)
    subscription_key = get_octranspo_api_key()  # Returns subscription key
    
    max_retries = 2
    timeout = 5.0
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Fetching {feed_type} feed from {url} (attempt {attempt + 1}/{max_retries + 1})")
            
            # Use asyncio timeout
            feed_data = await asyncio.wait_for(
                _fetch_feed_http(url, subscription_key),
                timeout=timeout
            )
            
            # Decode protobuf
            if not PROTOBUF_AVAILABLE:
                logger.warning("Protobuf library not available, returning raw feed data")
                # Return a basic structure even without protobuf decoding
                return {
                    "header": {
                        "gtfs_realtime_version": "2.0",
                        "incrementality": 0,
                        "timestamp": int(datetime.utcnow().timestamp()),
                    },
                    "entity": [],
                }
            
            decoded_data = decode_feed_message(feed_data)
            
            # Cache the result
            _set_cache(feed_type, decoded_data)
            
            logger.info(f"Successfully fetched and decoded {feed_type} feed ({len(decoded_data.get('entity', []))} entities)")
            return decoded_data
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {feed_type} feed (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                backoff_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"Failed to fetch {feed_type} feed after {max_retries + 1} attempts")
                # Fallback to mock data on final failure
                logger.warning("Falling back to mock feed generator")
                mock_data = _generate_mock_feed(feed_type)
                _set_cache(feed_type, mock_data)
                return mock_data
                
        except Exception as e:
            logger.error(f"Error fetching {feed_type} feed: {e} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                backoff_time = 2 ** attempt
                logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                logger.error(f"Failed to fetch {feed_type} feed after {max_retries + 1} attempts")
                # Fallback to mock data on final failure
                logger.warning("Falling back to mock feed generator")
                mock_data = _generate_mock_feed(feed_type)
                _set_cache(feed_type, mock_data)
                return mock_data


async def _fetch_feed_http(url: str, subscription_key: Optional[str]) -> bytes:
    """
    Fetch GTFS-RT feed via HTTP.
    
    Args:
        url: Feed URL
        subscription_key: OC Transpo subscription key for authentication
                          (uses Ocp-Apim-Subscription-Key header)
        
    Returns:
        Raw protobuf bytes
        
    Raises:
        Exception: If HTTP request fails
    """
    try:
        import aiohttp
        
        headers = {}
        if subscription_key:
            # OC Transpo uses Ocp-Apim-Subscription-Key header
            headers["Ocp-Apim-Subscription-Key"] = subscription_key
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                
                return await response.read()
                
    except ImportError:
        # Fallback to requests if aiohttp not available
        import requests
        
        headers = {}
        if subscription_key:
            # OC Transpo uses Ocp-Apim-Subscription-Key header
            headers["Ocp-Apim-Subscription-Key"] = subscription_key
        
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.content


def _generate_mock_feed(feed_type: str) -> Dict[str, Any]:
    """
    Generate realistic mock GTFS-RT feed data for testing/demo.
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        
    Returns:
        Dictionary containing mock feed message
    """
    logger.info(f"Generating mock {feed_type} feed")
    
    # Ottawa center coordinates
    ottawa_lat = 45.4215
    ottawa_lon = -75.6972
    
    # Common OC Transpo routes
    routes = ["95", "97", "61", "85", "87", "88", "91", "94"]
    
    header = {
        "gtfs_realtime_version": "2.0",
        "incrementality": 0,  # FULL_DATASET
        "timestamp": int(datetime.utcnow().timestamp()),
    }
    
    entities = []
    
    if feed_type == "vehicle_positions":
        # Generate 20-30 mock vehicle positions
        num_vehicles = random.randint(20, 30)
        
        for i in range(num_vehicles):
            vehicle_id = f"VEH-{str(uuid4())[:8].upper()}"
            route_id = random.choice(routes)
            trip_id = f"TRIP-{route_id}-{random.randint(1000, 9999)}"
            
            # Random position around Ottawa
            lat = ottawa_lat + random.uniform(-0.1, 0.1)
            lon = ottawa_lon + random.uniform(-0.1, 0.1)
            
            entity = {
                "id": vehicle_id,
                "is_deleted": False,
                "vehicle": {
                    "trip": {
                        "trip_id": trip_id,
                        "route_id": route_id,
                    },
                    "vehicle": {
                        "id": vehicle_id,
                        "label": f"{route_id}-{random.randint(1, 99)}",
                    },
                    "position": {
                        "latitude": lat,
                        "longitude": lon,
                        "bearing": random.uniform(0, 360),
                        "speed": random.uniform(5, 15),  # m/s
                    },
                    "current_stop_sequence": random.randint(1, 50),
                    "current_status": random.choice([0, 1, 2]),  # INCOMING_AT=0, STOPPED_AT=1, IN_TRANSIT_TO=2
                    "occupancy_status": random.choice([0, 1, 2, 3, 4, 5, 6]),  # Enum values
                    "timestamp": int(datetime.utcnow().timestamp()),
                }
            }
            entities.append(entity)
    
    elif feed_type == "trip_updates":
        # Generate 15-25 mock trip updates
        num_trips = random.randint(15, 25)
        
        for i in range(num_trips):
            route_id = random.choice(routes)
            trip_id = f"TRIP-{route_id}-{random.randint(1000, 9999)}"
            vehicle_id = f"VEH-{str(uuid4())[:8].upper()}"
            
            # Generate 3-8 stop time updates per trip
            num_stops = random.randint(3, 8)
            stop_updates = []
            base_time = datetime.utcnow()
            
            for j in range(num_stops):
                stop_sequence = j + 1
                arrival_time = base_time + timedelta(minutes=5 * stop_sequence)
                departure_time = arrival_time + timedelta(minutes=1)
                
                # Random delay (-2 to +10 minutes)
                delay = random.randint(-120, 600)
                
                stop_update = {
                    "stop_sequence": stop_sequence,
                    "stop_id": f"STOP-{route_id}-{stop_sequence:03d}",
                    "arrival": {
                        "time": int((arrival_time + timedelta(seconds=delay)).timestamp()),
                        "delay": delay,
                    },
                    "departure": {
                        "time": int((departure_time + timedelta(seconds=delay)).timestamp()),
                        "delay": delay,
                    },
                }
                stop_updates.append(stop_update)
            
            # Overall trip delay (average of stop delays)
            avg_delay = sum(su["arrival"]["delay"] for su in stop_updates) // len(stop_updates) if stop_updates else 0
            
            entity = {
                "id": trip_id,
                "is_deleted": False,
                "trip_update": {
                    "trip": {
                        "trip_id": trip_id,
                        "route_id": route_id,
                    },
                    "vehicle": {
                        "id": vehicle_id,
                        "label": f"{route_id}-{random.randint(1, 99)}",
                    },
                    "stop_time_update": stop_updates,
                    "delay": avg_delay,
                    "timestamp": int(datetime.utcnow().timestamp()),
                }
            }
            entities.append(entity)
    
    return {
        "header": header,
        "entity": entities,
    }


def parse_vehicle_positions(feed_data: Dict[str, Any]) -> List[VehiclePosition]:
    """
    Parse vehicle positions from decoded feed data.
    
    Args:
        feed_data: Decoded feed message dictionary
        
    Returns:
        List of VehiclePosition models
    """
    positions = []
    
    for entity in feed_data.get("entity", []):
        if "vehicle" not in entity:
            continue
        
        veh_data = entity["vehicle"]
        trip_data = veh_data.get("trip", {})
        vehicle_data = veh_data.get("vehicle", {})
        pos_data = veh_data.get("position", {})
        
        # Handle timestamp (could be datetime or int)
        timestamp = veh_data.get("timestamp")
        if isinstance(timestamp, int):
            timestamp = datetime.fromtimestamp(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = None
        
        position = VehiclePosition(
            vehicle_id=vehicle_data.get("id") or entity.get("id", "UNKNOWN"),
            trip_id=trip_data.get("trip_id"),
            route_id=trip_data.get("route_id"),
            latitude=pos_data.get("latitude"),
            longitude=pos_data.get("longitude"),
            bearing=pos_data.get("bearing"),
            speed=pos_data.get("speed"),
            occupancy_status=veh_data.get("occupancy_status"),
            current_stop_sequence=veh_data.get("current_stop_sequence"),
            current_status=veh_data.get("current_status"),
            timestamp=timestamp,
        )
        
        positions.append(position)
    
    return positions


def parse_trip_updates(feed_data: Dict[str, Any]) -> List[TripUpdate]:
    """
    Parse trip updates from decoded feed data.
    
    Args:
        feed_data: Decoded feed message dictionary
        
    Returns:
        List of TripUpdate models
    """
    updates = []
    
    for entity in feed_data.get("entity", []):
        if "trip_update" not in entity:
            continue
        
        tu_data = entity["trip_update"]
        trip_data = tu_data.get("trip", {})
        vehicle_data = tu_data.get("vehicle", {})
        
        # Parse stop time updates
        stop_updates = []
        for stu_data in tu_data.get("stop_time_update", []):
            arrival = stu_data.get("arrival", {})
            departure = stu_data.get("departure", {})
            
            # Handle timestamps (could be datetime or int)
            arrival_time = arrival.get("time")
            if isinstance(arrival_time, int):
                arrival_time = datetime.fromtimestamp(arrival_time)
            elif not isinstance(arrival_time, datetime):
                arrival_time = None
            
            departure_time = departure.get("time")
            if isinstance(departure_time, int):
                departure_time = datetime.fromtimestamp(departure_time)
            elif not isinstance(departure_time, datetime):
                departure_time = None
            
            stop_update = StopTimeUpdate(
                stop_sequence=stu_data.get("stop_sequence"),
                stop_id=stu_data.get("stop_id"),
                arrival_time=arrival_time,
                departure_time=departure_time,
                arrival_delay=arrival.get("delay"),
                departure_delay=departure.get("delay"),
            )
            stop_updates.append(stop_update)
        
        # Handle timestamp (could be datetime or int)
        timestamp = tu_data.get("timestamp")
        if isinstance(timestamp, int):
            timestamp = datetime.fromtimestamp(timestamp)
        elif not isinstance(timestamp, datetime):
            timestamp = None
        
        trip_update = TripUpdate(
            trip_id=trip_data.get("trip_id") or entity.get("id", "UNKNOWN"),
            route_id=trip_data.get("route_id"),
            vehicle_id=vehicle_data.get("id"),
            stop_time_updates=stop_updates if stop_updates else None,
            delay=tu_data.get("delay"),
            timestamp=timestamp,
        )
        
        updates.append(trip_update)
    
    return updates

