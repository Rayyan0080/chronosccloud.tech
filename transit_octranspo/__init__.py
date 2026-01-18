"""
OC Transpo GTFS-RT client module.

Provides functions to fetch and decode real-time transit data from OC Transpo.
"""

from .client import fetch_gtfsrt_feed, parse_vehicle_positions, parse_trip_updates
from .models import VehiclePosition, TripUpdate, StopTimeUpdate
from .config import (
    get_octranspo_api_key,
    get_gtfsrt_base_url,
    get_vehicle_positions_path,
    get_trip_updates_path,
    is_mock_mode,
    get_feed_url,
    get_transit_mode,
)
from .static_gtfs import (
    load_gtfs_to_mongodb,
    get_stop_info,
    get_route_info,
    is_gtfs_available,
    get_gtfs_zip_path,
)

__all__ = [
    "fetch_gtfsrt_feed",
    "parse_vehicle_positions",
    "parse_trip_updates",
    "VehiclePosition",
    "TripUpdate",
    "StopTimeUpdate",
    "get_octranspo_api_key",
    "get_gtfsrt_base_url",
    "get_vehicle_positions_path",
    "get_trip_updates_path",
    "is_mock_mode",
    "get_feed_url",
    "get_transit_mode",
    "load_gtfs_to_mongodb",
    "get_stop_info",
    "get_route_info",
    "is_gtfs_available",
    "get_gtfs_zip_path",
]

