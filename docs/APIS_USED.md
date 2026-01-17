# APIs Used in Project Chronos

This document lists **all external APIs and services** used in Project Chronos, their purpose, and setup requirements.

---

## 📊 Summary Table

| API/Service | Purpose | Required | Fallback Available | Cost |
|-------------|---------|----------|-------------------|------|
| **Google Gemini API** | AI recovery plan generation | ❌ Optional | ✅ Yes (fallback plans) | Free tier available |
| **Cerebras API** | AI recovery plan generation (alternative) | ❌ Optional | ✅ Yes (fallback plans) | Free tier: 1M tokens/day |
| **ElevenLabs API** | Voice announcements (TTS) | ❌ Optional | ✅ Yes (console output) | Free tier available |
| **Sentry API** | Error tracking & monitoring | ❌ Optional | ✅ Yes (no tracking) | Free tier available |
| **Solace PubSub+** | Message broker (production) | ❌ Optional | ✅ Yes (NATS) | Free tier available |
| **Solana RPC** | Blockchain audit logging | ❌ Optional | ✅ Yes (console output) | Free (public RPC) |
| **NATS** | Message broker (local) | ✅ Default | ❌ No (core service) | Free (self-hosted) |
| **MongoDB** | Event storage | ✅ Default | ❌ No (core service) | Free (self-hosted) |

---

## 🔍 Detailed API Information

### 1. Google Gemini API

**Purpose**: Generate AI-powered recovery plans for power failure events

**Location**: `ai/llm_client.py` (via `_get_recovery_plan_gemini`)

**Endpoint**: 
- `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent`

**Environment Variable**: 
```bash
GEMINI_API_KEY=your_api_key_here
```

**How to Get API Key**:
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

**Usage**:
- Called by `ai/recovery_planner.py` when processing power failure events
- Generates structured JSON recovery plans
- Includes steps, estimated completion, assigned agents
- Used if Cerebras is not configured

**Fallback**: 
- If API key is missing or API fails, system tries Cerebras, then fallback plans
- System works without Gemini API

**Cost**: 
- Free tier: 60 requests/minute
- Paid plans available

**Status**: ✅ **Optional** - System works without it

---

### 1b. Cerebras API (Alternative LLM)

**Purpose**: Generate AI-powered recovery plans using Cerebras (free tier available)

**Location**: `ai/llm_client.py` (via `_get_recovery_plan_cerebras`)

**Endpoint**: 
- `https://api.cerebras.ai/v1/chat/completions` (default)

**Environment Variables**: 
```bash
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_cerebras_api_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

**How to Get API Key**:
1. Visit: https://cloud.cerebras.ai
2. Sign up for free account
3. Create an API key
4. Copy the key

**Usage**:
- Called by `ai/recovery_planner.py` when processing power failure events
- Takes priority over Gemini if both are configured
- Uses OpenAI-compatible API format
- Generates structured JSON recovery plans

**Models Available**:
- `openai/zai-glm-4.7` (default, faster)
- `openai/qwen-3-235b-a22b-instruct-2507` (larger, more capable)

**Fallback**: 
- If API key is missing or API fails, system tries Gemini, then fallback plans
- System works without Cerebras API

**Cost**: 
- Free tier: 1M tokens/day
- No credit card required

**Status**: ✅ **Optional** - System works without it

**Reference**: [Cerebras Setup Guide](https://github.com/SolaceDev/solace-agent-mesh-hackathon-quickstart/blob/main/docs/llm-setup.md)

---

### 2. ElevenLabs API

**Purpose**: Text-to-speech voice announcements for critical events

**Location**: `voice/elevenlabs_client.py`

**Endpoint**: 
- `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`

**Environment Variables**: 
```bash
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional
```

**How to Get API Key**:
1. Visit: https://elevenlabs.io
2. Sign up for free account
3. Go to Profile → API Keys
4. Create new API key

**Usage**:
- Called by `agents/crisis_generator.py` for power failure announcements
- Called by `agents/autonomy_router.py` for autonomy takeover announcements
- Converts text to speech and plays audio

**Fallback**: 
- If API key is missing or API fails, system uses color-coded console output
- System works without ElevenLabs API

**Cost**: 
- Free tier: 10,000 characters/month
- Paid plans available

**Status**: ✅ **Optional** - System works without it

---

### 3. Sentry API

**Purpose**: Error tracking, performance monitoring, and observability

**Location**: `agents/shared/sentry.py`

**Endpoint**: 
- `https://xxx.ingest.sentry.io/xxx` (DSN-specific)

**Environment Variables**: 
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development  # Optional
SENTRY_RELEASE=1.0.0  # Optional
SENTRY_TRACES_SAMPLE_RATE=0.1  # Optional
```

**How to Get DSN**:
1. Visit: https://sentry.io
2. Sign up for free account
3. Create a new project
4. Copy DSN from project settings

**Usage**:
- Initialized by all agent services on startup
- Captures: startup events, received events, published events, exceptions
- Tags: service_name, autonomy_mode, event_type

**Fallback**: 
- If DSN is missing, Sentry is simply not initialized
- System works normally without error tracking

**Cost**: 
- Free tier: 5,000 events/month
- Paid plans available

**Status**: ✅ **Optional** - System works without it

---

### 4. Solace PubSub+ (Message Broker)

**Purpose**: Production-grade message broker for event-driven architecture

**Location**: `agents/shared/messaging.py` (SolaceBackend)

**Endpoint**: 
- `tcp://{SOLACE_HOST}:{SOLACE_PORT}` (typically port 55555)

**Environment Variables**: 
```bash
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

**How to Get Credentials**:
1. Visit: https://console.solace.cloud
2. Sign up for free account
3. Create a messaging service
4. Go to "Connect" tab
5. Copy connection details

**Usage**:
- Used as message broker if `SOLACE_HOST` is set
- Automatically detected and used instead of NATS
- Handles all event pub/sub operations

**Fallback**: 
- If `SOLACE_HOST` is not set, system uses NATS (default)
- Automatic fallback if Solace connection fails

**Cost**: 
- Free tier: 10,000 messages/day
- Paid plans available

**Status**: ✅ **Optional** - NATS is default

---

### 5. Solana RPC API

**Purpose**: Blockchain-based immutable audit logging

**Location**: `agents/solana_audit_logger.py`

**Endpoint**: 
- Public RPC: `https://api.mainnet-beta.solana.com`
- Or custom RPC endpoint

**Environment Variables**: 
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key_here
```

**How to Get**:
1. Use public Solana RPC (free, no setup needed)
2. Or use custom RPC provider (e.g., QuickNode, Alchemy)
3. Generate Solana wallet for private key

**Usage**:
- Called by `agents/solana_audit_logger.py` when audit decisions are made
- Writes SHA-256 hash of audit decisions to Solana Memo program
- Provides immutable audit trail

**Fallback**: 
- If credentials are missing, system prints hash to console
- System works without blockchain logging

**Cost**: 
- Public RPC: Free (rate limited)
- Custom RPC: Varies by provider

**Status**: ✅ **Optional** - System works without it

---

### 6. NATS (Message Broker)

**Purpose**: Local message broker for event-driven architecture

**Location**: `agents/shared/messaging.py` (NATSBackend)

**Endpoint**: 
- `nats://localhost:4222` (default)

**Environment Variables**: 
```bash
NATS_HOST=localhost  # Default
NATS_PORT=4222  # Default
```

**How to Run**:
- Started via Docker Compose: `cd infra && docker-compose up -d nats`
- Or install NATS server locally

**Usage**:
- Default message broker if Solace is not configured
- Handles all event pub/sub operations
- Used by all agent services

**Fallback**: 
- None - this is the default broker
- Required for system operation

**Cost**: 
- Free (open source, self-hosted)

**Status**: ✅ **Required** (default) - Core service

---

### 7. MongoDB

**Purpose**: Event storage and persistence

**Location**: `agents/state_logger.py`, `dashboard/lib/mongodb.ts`

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

**How to Run**:
- Started via Docker Compose: `cd infra && docker-compose up -d mongodb`
- Or install MongoDB locally

**Usage**:
- Stores all events from message broker
- Used by dashboard to display events
- Used by query scripts to retrieve events

**Fallback**: 
- None - required for event persistence
- Dashboard won't work without it

**Cost**: 
- Free (open source, self-hosted)

**Status**: ✅ **Required** - Core service

---

## 🔄 API Call Flow

### Power Failure Event Flow

```
1. Crisis Generator
   └─> Publishes power.failure event
       └─> (Optional) ElevenLabs API: Voice announcement

2. Coordinator Agent
   └─> Receives event
       └─> Dispatches to frameworks
           └─> (Optional) Gemini API: Generate recovery plan
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

---

## 💰 Cost Summary

### Free Tier Available

All optional APIs offer free tiers:

- **Google Gemini**: 60 requests/minute (free)
- **ElevenLabs**: 10,000 characters/month (free)
- **Sentry**: 5,000 events/month (free)
- **Solace PubSub+**: 10,000 messages/day (free)
- **Solana RPC**: Free public RPC (rate limited)

### Total Cost for Full Setup

**Minimum (Required Services Only)**:
- $0 - NATS and MongoDB are free (self-hosted)

**With All Optional APIs (Free Tiers)**:
- $0 - All APIs have free tiers sufficient for development/demo

**Production (Paid Tiers)**:
- Varies based on usage and provider pricing

---

## 🎯 Quick Reference

### Required APIs (Core Functionality)
- ✅ **NATS** - Message broker (default)
- ✅ **MongoDB** - Event storage

### Optional APIs (Enhanced Features)
- 🔵 **Google Gemini** - AI recovery plans
- 🔵 **ElevenLabs** - Voice announcements
- 🔵 **Sentry** - Error tracking
- 🔵 **Solace PubSub+** - Production message broker
- 🔵 **Solana** - Blockchain audit logging

### API Status Check

**To check which APIs are configured:**

```bash
# Check environment variables
echo $GEMINI_API_KEY        # Google Gemini
echo $ELEVENLABS_API_KEY    # ElevenLabs
echo $SENTRY_DSN            # Sentry
echo $SOLACE_HOST           # Solace
echo $SOLANA_RPC_URL        # Solana
```

**Or check service logs:**
- Look for "API key not set" messages
- Look for "Connected to..." messages
- Look for "fallback" messages

---

## 📝 Environment Variables Summary

### Required (for basic operation)
```bash
# None! System works with defaults
```

### Optional (for enhanced features)
```bash
# AI Recovery Plans
GEMINI_API_KEY=your_key

# Voice Announcements
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Error Tracking
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development

# Production Message Broker
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# Blockchain Audit Logging
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key
```

---

## 🔒 Security Notes

1. **Never commit API keys to git** - Use `.env` file (already in `.gitignore`)
2. **Rotate keys regularly** - Especially for production
3. **Use environment-specific keys** - Different keys for dev/staging/prod
4. **Monitor API usage** - Check usage in provider dashboards
5. **Set up rate limiting** - Protect against abuse

---

## 🆘 API Troubleshooting

### Gemini API Not Working
- Check API key is correct
- Verify you have quota/credits
- Check internet connection
- System uses fallback plans

### ElevenLabs API Not Working
- Check API key is correct
- Verify you have character credits
- Check audio playback is enabled
- System uses console output

### Sentry Not Capturing Events
- Check DSN is correct
- Verify project is active
- Check network connectivity
- System works without Sentry

### Solace Connection Failed
- Check credentials are correct
- Verify service is running
- Check network/firewall
- System falls back to NATS

### Solana Transaction Failed
- Check RPC URL is accessible
- Verify private key is valid
- Check you have SOL for fees
- System prints hash to console

---

## 📚 Additional Resources

- **Gemini API Docs**: https://ai.google.dev/docs
- **ElevenLabs API Docs**: https://elevenlabs.io/docs
- **Sentry Docs**: https://docs.sentry.io
- **Solace Docs**: https://docs.solace.com
- **Solana Docs**: https://docs.solana.com

---

**Last Updated**: 2024-01-17

