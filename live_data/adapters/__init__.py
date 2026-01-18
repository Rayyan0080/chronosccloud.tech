"""
Live data adapters.

Each adapter module should:
1. Import and subclass LiveAdapter
2. Implement fetch() and normalize() methods
3. Register itself with the runner

Example:
    from live_data.base import LiveAdapter
    from live_data.runner import register_adapter
    
    class MyAdapter(LiveAdapter):
        def __init__(self):
            super().__init__("my_adapter", poll_interval_seconds=30)
        
        def fetch(self):
            # Fetch data from API
            pass
        
        def normalize(self, raw_item):
            # Convert to BaseEvent objects
            pass
    
    # Register on module import
    register_adapter(MyAdapter)
"""

