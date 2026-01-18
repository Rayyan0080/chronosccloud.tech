# OC Transpo GTFS-RT Client

Client module for fetching and decoding real-time transit data from OC Transpo GTFS-RT feeds.

## Features

- ✅ Fetches GTFS-RT feeds from OC Transpo API
- ✅ Decodes protobuf messages into Python dictionaries
- ✅ Typed models for VehiclePosition and TripUpdate
- ✅ Caching (30 second TTL)
- ✅ Timeout (5 seconds)
- ✅ Retry with exponential backoff (2 retries)
- ✅ Mock feed generator (if API key missing)

## Installation

```bash
# Install dependencies
pip install -r transit_octranspo/requirements.txt
```

Required packages:
- `gtfs-realtime-bindings` - Google Transit GTFS-RT protobuf bindings
- `aiohttp` - Async HTTP client (preferred)
- `requests` - Sync HTTP client (fallback)
- `python-dotenv` - Environment variable loading

## Configuration

Set environment variables in `.env`:

```bash
# OC Transpo Subscription Key (required for real feeds)
# You can use either variable name:
OCTRANSPO_SUBSCRIPTION_KEY=your_subscription_key_here
# OR (for backward compatibility):
OCTRANSPO_API_KEY=your_subscription_key_here

# Base URL (defaults to OC Transpo developer portal)
OCTRANSPO_GTFSRT_BASE_URL=https://nextrip-public-api.azure-api.net/octranspo

# Feed paths (defaults shown - matches OC Transpo API)
OCTRANSPO_FEED_VEHICLE_POSITIONS_PATH=/gtfs-rt-vp/beta/v1/VehiclePositions
OCTRANSPO_FEED_TRIP_UPDATES_PATH=/gtfs-rt-tp/beta/v1/TripUpdates
```

**Note**: If `OCTRANSPO_SUBSCRIPTION_KEY` (or `OCTRANSPO_API_KEY`) is not set, the client automatically uses a mock feed generator that produces realistic synthetic data for testing/demo purposes.

## Usage

### Fetch Vehicle Positions

```python
import asyncio
from transit_octranspo import fetch_gtfsrt_feed, parse_vehicle_positions

async def main():
    # Fetch vehicle positions feed
    feed_data = await fetch_gtfsrt_feed("vehicle_positions")
    
    # Parse into typed models
    positions = parse_vehicle_positions(feed_data)
    
    for position in positions:
        print(f"Vehicle {position.vehicle_id} on route {position.route_id} at {position.latitude}, {position.longitude}")

asyncio.run(main())
```

### Fetch Trip Updates

```python
import asyncio
from transit_octranspo import fetch_gtfsrt_feed, parse_trip_updates

async def main():
    # Fetch trip updates feed
    feed_data = await fetch_gtfsrt_feed("trip_updates")
    
    # Parse into typed models
    updates = parse_trip_updates(feed_data)
    
    for update in updates:
        print(f"Trip {update.trip_id} on route {update.route_id} - delay: {update.delay}s")

asyncio.run(main())
```

### Using Models Directly

```python
from transit_octranspo.models import VehiclePosition, TripUpdate

# Create vehicle position
position = VehiclePosition(
    vehicle_id="VEH-12345",
    route_id="95",
    latitude=45.4215,
    longitude=-75.6972,
    speed=12.5
)

# Convert to dictionary for event publishing
position_dict = position.to_dict()
```

## Mock Mode

If `OCTRANSPO_API_KEY` is not set, the client automatically generates realistic mock data:

- **Vehicle Positions**: 20-30 vehicles with random positions around Ottawa
- **Trip Updates**: 15-25 trips with realistic stop time updates and delays
- Uses actual OC Transpo route numbers (95, 97, 61, 85, 87, 88, 91, 94)
- Coordinates centered on Ottawa (45.4215, -75.6972)

## Error Handling

The client includes robust error handling:

- **Timeout**: 5 second timeout per request
- **Retries**: 2 retries with exponential backoff (1s, 2s)
- **Fallback**: Automatically falls back to mock data if API fails
- **Caching**: 30 second cache to reduce API calls

## Module Structure

```
transit_octranspo/
├── __init__.py          # Module exports
├── config.py            # Environment variable configuration
├── client.py            # Main fetch function with caching/retry
├── decode.py            # Protobuf decoding utilities
├── models.py            # Typed models (VehiclePosition, TripUpdate)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## API Reference

### `fetch_gtfsrt_feed(feed_type: str) -> Dict[str, Any]`

Fetch and decode GTFS-RT feed.

**Args:**
- `feed_type`: "vehicle_positions" or "trip_updates"

**Returns:**
- Dictionary with `header` and `entity` keys

**Raises:**
- `ValueError`: If feed_type is invalid

### `parse_vehicle_positions(feed_data: Dict[str, Any]) -> List[VehiclePosition]`

Parse vehicle positions from decoded feed.

**Returns:**
- List of `VehiclePosition` models

### `parse_trip_updates(feed_data: Dict[str, Any]) -> List[TripUpdate]`

Parse trip updates from decoded feed.

**Returns:**
- List of `TripUpdate` models

## Getting OC Transpo Subscription Key

1. Visit: https://www.octranspo.com/en/plan-your-trip/travel-tools/developers/
2. Sign up for developer account
3. Request API access (subscribe to the GTFS-RT product)
4. Copy your **Subscription Key** (not API key - OC Transpo uses Azure API Management)
5. Add to `.env`: 
   ```bash
   OCTRANSPO_SUBSCRIPTION_KEY=your_subscription_key_here
   # OR use the alias:
   OCTRANSPO_API_KEY=your_subscription_key_here
   ```

**Important:** OC Transpo uses Azure API Management, so you'll get a **Subscription Key**, not a traditional API key. The client uses the `Ocp-Apim-Subscription-Key` header automatically.

## Static GTFS Data (Optional)

For improved map labels and stop information, you can load static GTFS data:

### Download GTFS Zip

1. Download OC Transpo GTFS static feed from: https://www.octranspo.com/en/plan-your-trip/travel-tools/developers/
2. Save the zip file locally (e.g., `data/octranspo-gtfs.zip`)

### Load GTFS to MongoDB

Set the path in `.env`:
```bash
OCTRANSPO_GTFS_ZIP_PATH=/path/to/octranspo-gtfs.zip
```

Then load the data:
```bash
# From project root
python -m transit_octranspo.static_gtfs

# Or specify path directly
python -m transit_octranspo.static_gtfs /path/to/octranspo-gtfs.zip
```

This will:
- Parse `stops.txt` and store in MongoDB `transit_stops` collection
- Parse `routes.txt` and store in MongoDB `transit_routes` collection
- Create indexes for fast lookups

### Using Static GTFS Data

```python
from transit_octranspo.static_gtfs import get_stop_info, get_route_info

# Get stop information
stop = get_stop_info("STOP-12345")
if stop:
    print(f"Stop: {stop['name']} at {stop['lat']}, {stop['lon']}")

# Get route information
route = get_route_info("95")
if route:
    print(f"Route: {route['short_name']} - {route['long_name']}")
```

**Note**: Static GTFS is completely optional. The system works without it, but map labels will be improved if available.

## Disclaimer

**Transit data is informational only** - This system processes OC Transpo GTFS-RT feeds for demonstration purposes. Always verify real-time data with official OC Transpo sources for operational use.

