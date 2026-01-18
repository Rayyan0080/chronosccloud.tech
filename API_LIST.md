# Complete List of APIs Used in Project Chronos

This document provides a **comprehensive list of all APIs and services** integrated into Project Chronos.

---

## 📊 Quick Summary

| # | API/Service | Category | Required | Status |
|---|------------|----------|----------|--------|
| 1 | **Google Gemini API** | AI/LLM | ❌ Optional | ✅ Integrated |
| 2 | **Cerebras API** | AI/LLM | ❌ Optional | ✅ Integrated |
| 3 | **ElevenLabs API** | Voice/TTS | ❌ Optional | ✅ Integrated |
| 4 | **Sentry API** | Observability | ❌ Optional | ✅ Integrated |
| 5 | **Solace PubSub+** | Message Broker | ❌ Optional | ✅ Integrated |
| 6 | **Solana RPC** | Blockchain | ❌ Optional | ✅ Integrated |
| 7 | **NATS** | Message Broker | ✅ Default | ✅ Integrated |
| 8 | **MongoDB** | Database | ✅ Required | ✅ Integrated |
| 9 | **OC Transpo GTFS-RT** | Transit Data | ❌ Optional | ✅ Integrated |
| 10 | **OpenSky Network API** | Airspace Data | ❌ Optional | ✅ Integrated |
| 11 | **Ottawa Traffic API** | Traffic Data | ❌ Optional | ✅ Integrated |
| 12 | **Ontario 511 API** | Traffic Data | ❌ Optional | ✅ Integrated |
| 14 | **OpenStreetMap Tiles** | Map Tiles | ✅ Default | ✅ Integrated |
| 15 | **Browser Web Speech API** | Voice/TTS | ✅ Default | ✅ Integrated |

---

## 🔍 Detailed API List

### 1. Google Gemini API

**Purpose**: AI-powered recovery plan generation

**Endpoint**: 
- `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent`

**Environment Variable**: 
```bash
GEMINI_API_KEY=your_api_key_here
```

**Location**: `ai/llm_client.py`

**Status**: ✅ **Optional** - Has fallback to rules-based plans

**Cost**: Free tier: 60 requests/minute

**Documentation**: https://ai.google.dev/docs

---

### 2. Cerebras API

**Purpose**: Alternative AI/LLM provider for recovery plan generation

**Endpoint**: 
- `https://api.cerebras.ai/v1/chat/completions`

**Environment Variables**: 
```bash
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_cerebras_api_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

**Location**: `ai/llm_client.py`

**Status**: ✅ **Optional** - Has fallback to Gemini, then rules

**Cost**: Free tier: 1M tokens/day

**Documentation**: https://cloud.cerebras.ai

---

### 3. ElevenLabs API

**Purpose**: High-quality text-to-speech voice announcements

**Endpoint**: 
- `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`

**Environment Variables**: 
```bash
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional
```

**Location**: `voice/elevenlabs_client.py`, `dashboard/lib/voiceAnnouncements.ts`

**Status**: ✅ **Optional** - Has fallback to browser Web Speech API or console

**Cost**: Free tier: 10,000 characters/month

**Documentation**: https://elevenlabs.io/docs

---

### 4. Sentry API

**Purpose**: Error tracking, performance monitoring, and observability

**Endpoint**: 
- `https://xxx.ingest.sentry.io/xxx` (DSN-specific)

**Environment Variables**: 
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development  # Optional
SENTRY_RELEASE=1.0.0  # Optional
```

**Location**: `agents/shared/sentry.py`

**Status**: ✅ **Optional** - System works without it

**Cost**: Free tier: 5,000 events/month

**Documentation**: https://docs.sentry.io

---

### 5. Solace PubSub+ Cloud

**Purpose**: Production-grade message broker for event-driven architecture

**Endpoint**: 
- `tcp://{SOLACE_HOST}:{SOLACE_PORT}` (typically port 55555 or 55443 for TLS)

**Environment Variables**: 
```bash
BROKER_BACKEND=solace
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555  # or 55443 for TLS
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

**Location**: `agents/shared/messaging.py` (SolaceBackend)

**Status**: ✅ **Optional** - NATS is default

**Cost**: Free tier: 10,000 messages/day

**Documentation**: https://docs.solace.com

---

### 6. Solana RPC API

**Purpose**: Blockchain-based immutable audit logging

**Endpoint**: 
- Public RPC: `https://api.mainnet-beta.solana.com`
- Or custom RPC endpoint (e.g., QuickNode, Alchemy)

**Environment Variables**: 
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key_here
```

**Location**: `agents/solana_audit_logger.py`

**Status**: ✅ **Optional** - Has fallback to console hash logging

**Cost**: Free (public RPC, rate limited)

**Documentation**: https://docs.solana.com

---

### 7. NATS (Message Broker)

**Purpose**: Local message broker for event-driven architecture

**Endpoint**: 
- `nats://localhost:4222` (default)

**Environment Variables**: 
```bash
NATS_HOST=localhost  # Default
NATS_PORT=4222  # Default
```

**Location**: `agents/shared/messaging.py` (NATSBackend)

**Status**: ✅ **Required** (default) - Core service

**Cost**: Free (open source, self-hosted via Docker)

**Documentation**: https://docs.nats.io

---

### 8. MongoDB

**Purpose**: Event storage and persistence

**Endpoint**: 
- `mongodb://localhost:27017` (default)

**Environment Variables**: 
```bash
MONGO_HOST=localhost  # Default
MONGO_PORT=27017  # Default
MONGO_USER=chronos  # Default
MONGO_PASS=chronos  # Default
MONGO_DB=chronos  # Default
```

**Location**: `agents/state_logger.py`, `dashboard/lib/mongodb.ts`

**Status**: ✅ **Required** - Core service

**Cost**: Free (open source, self-hosted via Docker)

**Documentation**: https://docs.mongodb.com

---

### 9. OC Transpo GTFS-RT API

**Purpose**: Real-time transit data (vehicle positions and trip updates)

**Endpoint**: 
- Vehicle Positions: `https://api.octranspo.com/v2/gtfsrt/VehiclePositions.pb`
- Trip Updates: `https://api.octranspo.com/v2/gtfsrt/TripUpdates.pb`

**Environment Variables**: 
```bash
TRANSIT_MODE=live  # or "mock"
OCTRANSPO_API_KEY=your_subscription_key_here
OCTRANSPO_GTFSRT_BASE_URL=https://api.octranspo.com/v2
OCTRANSPO_VEHICLE_POSITIONS_PATH=/gtfsrt/VehiclePositions.pb
OCTRANSPO_TRIP_UPDATES_PATH=/gtfsrt/TripUpdates.pb
```

**Location**: `live_data/adapters/oc_transpo_gtfsrt.py`

**Status**: ✅ **Optional** - Has fallback to mock mode

**Cost**: Free (requires OC Transpo developer account)

**Documentation**: https://www.octranspo.com/en/plan-your-trip/travel-tools/developers/

---

### 10. OpenSky Network API

**Purpose**: Real-time aircraft position data (ADS-B)

**Endpoint**: 
- `https://opensky-network.org/api/states/all?lamin={lat_min}&lamax={lat_max}&lomin={lon_min}&lomax={lon_max}`

**Environment Variables**: 
```bash
OPENSKY_USERNAME=your_username  # Optional (for higher rate limits)
OPENSKY_PASSWORD=your_password  # Optional
OPENSKY_CONGESTION_THRESHOLD=15  # Optional (default: 15 aircraft)
```

**Location**: `live_data/adapters/opensky_airspace.py`

**Status**: ✅ **Optional** - Has fallback to mock mode

**Cost**: Free (public API, credentials optional for higher limits)

**Documentation**: https://opensky-network.org/apidoc/

---

### 11. Ottawa Traffic API

**Purpose**: Road incidents, construction, and special events

**Endpoint**: 
- `https://traffic.ottawa.ca/map/service/events?accept-language=en`

**Environment Variables**: 
```bash
OTTAWA_TRAFFIC_INCIDENTS_URL=https://traffic.ottawa.ca/map/service/events?accept-language=en
OTTAWA_TRAFFIC_API_KEY=your_key_here  # Optional (if authentication added)
```

**Location**: `live_data/adapters/ottawa_traffic.py`

**Status**: ✅ **Optional** - Has fallback to mock mode

**Cost**: Free (public API, no authentication required)

**Documentation**: https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources

---

### 12. Ontario 511 API

**Purpose**: Highway incidents and road closures

**Endpoint**: 
- `https://511on.ca/api/v2/get/event?format=json&language=en`

**Environment Variables**: 
```bash
ONTARIO511_INCIDENTS_URL=https://511on.ca/api/v2/get/event?format=json&language=en
ONTARIO511_API_BASE_URL=https://511on.ca/api/v2/get  # Optional
```

**Location**: `live_data/adapters/ontario511.py`

**Status**: ✅ **Optional** - Has fallback to mock mode

**Cost**: Free (public API)

**Documentation**: https://511on.ca/developers/resources

---

### 14. OpenStreetMap Tiles

**Purpose**: Map tile rendering for dashboard map

**Endpoint**: 
- `https://tile.openstreetmap.org/{z}/{x}/{y}.png`

**Location**: `dashboard/components/OttawaMapClean.tsx`

**Status**: ✅ **Default** - Used for map rendering

**Cost**: Free (open source, public tiles)

**Documentation**: https://www.openstreetmap.org/copyright

**Note**: Uses MapLibre GL JS for rendering

---

### 15. Browser Web Speech API

**Purpose**: Browser-native text-to-speech (fallback for ElevenLabs)

**Endpoint**: 
- Browser-native API (no external endpoint)

**Location**: `dashboard/lib/voiceAnnouncements.ts`

**Status**: ✅ **Default** - Always available in browser

**Cost**: Free (browser-native)

**Documentation**: https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis

---

## 📋 API Categories

### Core Services (Required)
- ✅ **NATS** - Message broker
- ✅ **MongoDB** - Event storage
- ✅ **OpenStreetMap** - Map tiles
- ✅ **Browser Web Speech API** - Voice synthesis

### AI/LLM Services (Optional)
- 🔵 **Google Gemini API** - AI recovery plans
- 🔵 **Cerebras API** - Alternative AI provider

### Voice Services (Optional)
- 🔵 **ElevenLabs API** - High-quality TTS
- ✅ **Browser Web Speech API** - Fallback TTS

### Observability (Optional)
- 🔵 **Sentry API** - Error tracking

### Message Brokers (Optional)
- 🔵 **Solace PubSub+** - Production broker
- ✅ **NATS** - Default broker

### Blockchain (Optional)
- 🔵 **Solana RPC** - Audit logging

### Live Data Sources (Optional)
- 🔵 **OC Transpo GTFS-RT** - Transit data
- 🔵 **OpenSky Network** - Aircraft positions
- 🔵 **Ottawa Traffic** - Road incidents
- 🔵 **Ontario 511** - Highway incidents

---

## 💰 Cost Summary

### Free Tier Available
All optional APIs offer free tiers sufficient for development and demos:

- **Google Gemini**: 60 requests/minute (free)
- **Cerebras**: 1M tokens/day (free)
- **ElevenLabs**: 10,000 characters/month (free)
- **Sentry**: 5,000 events/month (free)
- **Solace PubSub+**: 10,000 messages/day (free)
- **Solana RPC**: Free public RPC (rate limited)
- **OC Transpo**: Free (developer account)
- **OpenSky Network**: Free (public API)
- **Ottawa Traffic**: Free (public API)
- **Ontario 511**: Free (public API)

### Total Cost
- **Minimum Setup**: $0 (NATS + MongoDB only)
- **Full Setup (Free Tiers)**: $0 (all APIs have free tiers)
- **Production**: Varies based on usage

---

## 🔄 API Usage Flow

### Power Failure Event Flow
```
1. Crisis Generator
   └─> Publishes power.failure event
       └─> (Optional) ElevenLabs API: Voice announcement

2. Coordinator Agent
   └─> Receives event
       └─> Dispatches to frameworks
           └─> (Optional) Gemini/Cerebras API: Generate recovery plan
       └─> (Optional) Sentry API: Log event

3. Autonomy Router
   └─> Receives recovery plan
       └─> If HIGH autonomy: Executes action
           └─> (Optional) ElevenLabs API: Voice announcement
       └─> (Optional) Sentry API: Log decision

4. State Logger
   └─> Logs all events to MongoDB
       └─> (Optional) Sentry API: Log received event

5. Solana Audit Logger
   └─> Receives audit.decision
       └─> (Optional) Solana RPC: Write hash to blockchain
```

### Live Data Flow
```
1. Live Data Runner
   └─> Polls enabled adapters
       ├─> OC Transpo GTFS-RT API: Fetch vehicle positions
       ├─> OpenSky Network API: Fetch aircraft positions
       ├─> Ottawa Traffic API: Fetch road incidents
       └─> Ontario 511 API: Fetch highway incidents
   └─> Normalizes to Chronos events
   └─> Publishes to message broker
```

---

## 🎯 Quick Reference

### Required APIs (Core Functionality)
- ✅ **NATS** - Message broker (default)
- ✅ **MongoDB** - Event storage
- ✅ **OpenStreetMap** - Map tiles
- ✅ **Browser Web Speech API** - Voice synthesis

### Optional APIs (Enhanced Features)
- 🔵 **Google Gemini** - AI recovery plans
- 🔵 **Cerebras** - Alternative AI provider
- 🔵 **ElevenLabs** - Voice announcements
- 🔵 **Sentry** - Error tracking
- 🔵 **Solace PubSub+** - Production message broker
- 🔵 **Solana** - Blockchain audit logging
- 🔵 **OC Transpo GTFS-RT** - Transit data
- 🔵 **OpenSky Network** - Aircraft positions
- 🔵 **Ottawa Traffic** - Road incidents
- 🔵 **Ontario 511** - Highway incidents

---

## 📝 Environment Variables Checklist

### Required (None - System works with defaults)
```bash
# No required environment variables!
```

### Optional (All have fallbacks)
```bash
# AI Recovery Plans
GEMINI_API_KEY=your_key
LLM_SERVICE_API_KEY=your_cerebras_key

# Voice Announcements
ELEVENLABS_API_KEY=your_key

# Error Tracking
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Production Message Broker
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# Blockchain Audit
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key

# Live Data Sources
OCTRANSPO_API_KEY=your_key
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
```

---

## 🔒 Security Notes

1. **Never commit API keys to git** - Use `.env` file (already in `.gitignore`)
2. **Rotate keys regularly** - Especially for production
3. **Use environment-specific keys** - Different keys for dev/staging/prod
4. **Monitor API usage** - Check usage in provider dashboards
5. **Set up rate limiting** - Protect against abuse
6. **Mask secrets in logs** - System automatically masks sensitive data

---

## 📚 Additional Resources

- **Complete API Documentation**: See `docs/APIS_USED.md`
- **Setup Guides**: See `docs/` directory for individual API setup guides
- **Environment Variables**: See `.env.example` for all available options

---

**Last Updated**: 2026-01-17

