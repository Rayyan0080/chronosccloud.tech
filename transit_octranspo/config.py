"""
Configuration management for OC Transpo GTFS-RT client.

Handles environment variable loading and API configuration.
"""

import os
from typing import Optional


def get_octranspo_api_key() -> Optional[str]:
    """
    Get OC Transpo subscription key from environment variable.
    
    Note: OC Transpo uses "Ocp-Apim-Subscription-Key" header, but we call it
    "API key" for simplicity. The environment variable can be either:
    - OCTRANSPO_API_KEY (for backward compatibility)
    - OCTRANSPO_SUBSCRIPTION_KEY (preferred)
    
    Returns:
        Subscription key string or None if not set
    """
    # Check both variable names for flexibility
    return os.getenv("OCTRANSPO_SUBSCRIPTION_KEY") or os.getenv("OCTRANSPO_API_KEY")


def get_gtfsrt_base_url() -> str:
    """
    Get GTFS-RT base URL from environment variable.
    
    Defaults to OC Transpo developer portal base URL.
    
    Returns:
        Base URL string
    """
    return os.getenv(
        "OCTRANSPO_GTFSRT_BASE_URL",
        "https://nextrip-public-api.azure-api.net/octranspo"
    )


def get_vehicle_positions_path() -> str:
    """
    Get vehicle positions feed path from environment variable.
    
    Returns:
        Feed path string
    """
    return os.getenv(
        "OCTRANSPO_FEED_VEHICLE_POSITIONS_PATH",
        "/gtfs-rt-vp/beta/v1/VehiclePositions"
    )


def get_trip_updates_path() -> str:
    """
    Get trip updates feed path from environment variable.
    
    Returns:
        Feed path string
    """
    return os.getenv(
        "OCTRANSPO_FEED_TRIP_UPDATES_PATH",
        "/gtfs-rt-tp/beta/v1/TripUpdates"
    )


def get_transit_mode() -> str:
    """
    Get transit mode from environment variable.
    
    Returns:
        "live" or "mock"
        
    Environment Variables:
        TRANSIT_MODE: Explicit mode ("live" or "mock")
        If not set, auto-detects: "live" if OCTRANSPO_API_KEY exists, "mock" otherwise
    """
    mode = os.getenv("TRANSIT_MODE", "").lower().strip()
    
    if mode in ["live", "mock"]:
        return mode
    
    # Auto-detect: if API key exists, use live mode
    if get_octranspo_api_key():
        return "live"
    
    return "mock"


def is_mock_mode() -> bool:
    """
    Check if running in mock mode.
    
    Returns:
        True if in mock mode, False otherwise
    """
    return get_transit_mode() == "mock"


def get_feed_url(feed_type: str) -> str:
    """
    Get full feed URL for the specified feed type.
    
    Args:
        feed_type: Feed type ("vehicle_positions" or "trip_updates")
        
    Returns:
        Full feed URL string
        
    Raises:
        ValueError: If feed_type is invalid
    """
    base_url = get_gtfsrt_base_url()
    
    if feed_type == "vehicle_positions":
        path = get_vehicle_positions_path()
    elif feed_type == "trip_updates":
        path = get_trip_updates_path()
    else:
        raise ValueError(f"Invalid feed_type: {feed_type}. Must be 'vehicle_positions' or 'trip_updates'")
    
    # Remove leading slash from path if base_url already has trailing slash
    if base_url.endswith("/") and path.startswith("/"):
        path = path[1:]
    
    return f"{base_url}{path}"

