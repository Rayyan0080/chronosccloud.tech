# Live Data Adapters Configuration

This document explains how to configure the live data adapters for real-time data feeds.

## Overview

The live data adapters fetch real-time information from various public data sources. Most adapters use public URLs that don't require API keys, but some support optional authentication for higher rate limits or additional features.

## Adapter Configuration

### OC Transpo Transit Data

**Adapter:** `oc_transpo`

**Data Source:** OC Transpo GTFS-RT feeds

**Configuration:**
- **Mode:** Automatically determined by `TRANSIT_MODE` environment variable
- **API Key:** `OCTRANSPO_SUBSCRIPTION_KEY` or `OCTRANSPO_API_KEY` (for live mode)
- **Poll Interval:** 30 seconds

**How to Get Access:**
1. Visit [OC Transpo Developer Portal](https://www.octranspo.com/en/plan-your-trip/travel-tools/developer-tools/)
2. Register for an API subscription key
3. Set `OCTRANSPO_SUBSCRIPTION_KEY` in your `.env` file

**Example:**
```bash
TRANSIT_MODE=live
OCTRANSPO_SUBSCRIPTION_KEY=your_subscription_key_here
```

---

### Ottawa Traffic Incidents

**Adapter:** `ottawa_traffic`

**Data Source:** [City of Ottawa Traffic Data](https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources/about-the-data)

**Configuration:**
- **URL:** `OTTAWA_TRAFFIC_INCIDENTS_URL` (defaults to public endpoint)
- **Optional API Key:** `OTTAWA_TRAFFIC_API_KEY` (if authentication is added in the future)
- **Poll Interval:** 60 seconds

**How to Get the URL:**
1. Visit [Ottawa Traffic Data & Resources](https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources/about-the-data)
2. Find the "Traffic Events Data" section
3. The public JSON endpoint is:
   - **English:** `https://traffic.ottawa.ca/map/service/events?accept-language=en`
   - **French:** `https://traffic.ottawa.ca/map/service/events?accept-language=fr`

**Example:**
```bash
# No API key required - uses public endpoint by default
OTTAWA_TRAFFIC_INCIDENTS_URL=https://traffic.ottawa.ca/map/service/events?accept-language=en

# Optional: If they add authentication in the future
OTTAWA_TRAFFIC_API_KEY=your_key_here
```

**Data Format:**
The API returns JSON with the following fields:
- `Id` - Unique event ID
- `EventType` - Type of event (CONSTRUCTION, SPECIAL_EVENT, INCIDENT)
- `headline` - Short description
- `message` - Detailed message
- `geodata` - GeoJSON geometry (Point coordinates)
- `mainStreet`, `crossStreet1`, `crossStreet2` - Street information
- `priority` - Impact level (LOW, MEDIUM, HIGH, UNKNOWN)
- `status` - Event status (ACTIVE, SCHEDULED, ARCHIVED)

---

### OpenSky Network Flight Data

**Adapter:** `opensky`

**Data Source:** [OpenSky Network](https://opensky-network.org/)

**Configuration:**
- **Username:** `OPENSKY_USERNAME` (optional, for higher rate limits)
- **Password:** `OPENSKY_PASSWORD` (optional, for higher rate limits)
- **Poll Interval:** 45 seconds

**How to Get Access:**
1. Visit [OpenSky Network](https://opensky-network.org/)
2. Register for a free account (optional, but recommended for higher rate limits)
3. Set credentials in your `.env` file

**Example:**
```bash
# Optional: Without credentials, uses public API with lower rate limits
# With credentials, you get higher rate limits
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
```

**Note:** OpenSky Network is free and open. Credentials are optional but recommended for production use to avoid rate limiting.

---

### Ontario 511 Road Conditions

**Adapter:** `ontario511`

**Data Source:** [Ontario 511 REST API](https://511on.ca/developers/doc)

**Configuration:**
- **Base URL:** `ONTARIO511_API_BASE_URL` (optional, defaults to `https://511on.ca/api/v2/get`)
- **Custom URL:** `ONTARIO511_INCIDENTS_URL` (optional, defaults to Events endpoint)
- **No API Key Required** - Public API with rate limiting
- **Poll Interval:** 120 seconds (well within rate limits)

**How to Use:**
1. Visit [Ontario 511 API Documentation](https://511on.ca/developers/doc)
2. The API is **public and free** - no registration or API key needed
3. Default endpoint: `https://511on.ca/api/v2/get/event?format=json&language=en`
4. Rate limit: **10 calls per 60 seconds** (our poll interval is 120s, so we're safe)

**Available Endpoints:**
- Events: `/api/v2/get/event` (default)
- Construction: `/api/v2/get/constructionprojects`
- Cameras: `/api/v2/get/cameras`
- Road Conditions: `/api/v2/get/roadconditions`
- Alerts: `/api/v2/get/alerts`
- And more - see [full API documentation](https://511on.ca/developers/doc)

**Example:**
```bash
# Default: Uses Events endpoint automatically
# No configuration needed - works out of the box!

# Optional: Use a different endpoint
ONTARIO511_INCIDENTS_URL=https://511on.ca/api/v2/get/constructionprojects?format=json&language=en

# Optional: Custom base URL (if API changes)
ONTARIO511_API_BASE_URL=https://511on.ca/api/v2/get
```

**Note:** The Ontario 511 API is public and requires no authentication. Rate limiting is enforced per IP/user agent, not by API key. Our adapter respects the 10 calls/60 seconds limit by polling every 120 seconds.

---

## Environment Variables Summary

Add these to your `.env` file:

```bash
# Live Data Adapters
LIVE_ADAPTERS=oc_transpo,ottawa_traffic,opensky,ontario511

# OC Transpo
TRANSIT_MODE=live
OCTRANSPO_SUBSCRIPTION_KEY=your_key_here

# Ottawa Traffic (public URL, no key required)
OTTAWA_TRAFFIC_INCIDENTS_URL=https://traffic.ottawa.ca/map/service/events?accept-language=en

# OpenSky Network (optional credentials)
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password

# Ontario 511 (URL required, key optional)
ONTARIO511_INCIDENTS_URL=https://511on.ca/api/incidents/geojson
ONTARIO511_API_KEY=your_key_here  # Only if registration required
```

## Running the Adapters

Start the live data runner:

```bash
python live_data/runner.py
```

The runner will:
1. Load all adapters specified in `LIVE_ADAPTERS`
2. Show which adapters are in **LIVE** vs **MOCK** mode
3. Poll each adapter on its configured interval
4. Publish normalized events to the message broker
5. Handle errors gracefully (fallback to mock if live fails)

## Troubleshooting

### Adapter shows as MOCK when it should be LIVE

1. Check that the required environment variables are set
2. For URL-based adapters, verify the URL is accessible:
   ```bash
   curl https://traffic.ottawa.ca/map/service/events?accept-language=en
   ```
3. Check adapter logs for connection errors

### API Rate Limiting

- OpenSky Network: Register for credentials to get higher rate limits
- Ottawa Traffic: Public endpoint, no rate limits mentioned
- Ontario 511: Check developer resources for rate limit information

### Authentication Errors

- Verify API keys are correct
- Check if the API requires a specific header format
- Some APIs use `Authorization: Bearer <key>`, others use `X-API-Key: <key>`

## References

- [Ottawa Traffic Data & Resources](https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources/about-the-data)
- [Ontario 511 Developer Resources](https://511on.ca/developers/resources)
- [OpenSky Network](https://opensky-network.org/)
- [OC Transpo Developer Tools](https://www.octranspo.com/en/plan-your-trip/travel-tools/developer-tools/)

