"""
Base adapter interface for live data sources.

All live data adapters must implement this interface to be used by the runner.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from agents.shared.schema import BaseEvent


def is_live_mode_enabled() -> bool:
    """
    Check if LIVE_MODE is enabled globally.
    
    Returns:
        True if LIVE_MODE=on, False if LIVE_MODE=off or not set
    """
    live_mode = os.getenv("LIVE_MODE", "off").lower().strip()
    return live_mode == "on"


class LiveAdapter(ABC):
    """
    Base class for live data adapters.
    
    Each adapter:
    - Fetches raw data from an external source
    - Normalizes raw data into ChronosEvent objects
    - Has a configurable poll interval
    """
    
    def __init__(self, name: str, poll_interval_seconds: int = 60):
        """
        Initialize the adapter.
        
        Args:
            name: Unique name for this adapter (e.g., 'oc_transpo', 'ottawa_traffic')
            poll_interval_seconds: How often to poll this adapter (default: 60 seconds)
        """
        self.name = name
        self.poll_interval_seconds = poll_interval_seconds
    
    @abstractmethod
    def fetch(self) -> List[Dict]:
        """
        Fetch raw data from the external source.
        
        Returns:
            List of raw data items (dicts) from the source API/feed.
            Returns empty list if no data available or on error.
        
        Raises:
            Any exception should be caught by the runner and logged.
        """
        pass
    
    @abstractmethod
    def normalize(self, raw_item: Dict) -> List[BaseEvent]:
        """
        Normalize a raw data item into one or more ChronosEvent objects.
        
        Args:
            raw_item: A single raw data item (dict) from fetch()
        
        Returns:
            List of BaseEvent objects ready to be published.
            Can return multiple events from a single raw item.
            Returns empty list if item should be skipped.
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this adapter is enabled.
        
        Override this method to add custom enable/disable logic
        (e.g., based on environment variables, feature flags).
        
        Returns:
            True if adapter should be used, False otherwise.
        """
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get adapter status information.
        
        Returns:
            Dict with status info (e.g., {'mode': 'live', 'last_fetch': '...'})
        """
        return {
            "name": self.name,
            "poll_interval_seconds": self.poll_interval_seconds,
            "enabled": self.is_enabled(),
        }

