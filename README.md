# Project Chronos - Digital Twin Crisis Management System

**Project Chronos** is a **software-only digital twin crisis management system** built using a **fault-tolerant, event-driven architecture**. It simulates, detects, and responds to crisis scenarios in real time using autonomous agents, AI-driven predictions, voice-based interaction, and live data integration—designed to be **demo-first**, **production-ready**, and **modular by default**.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Domains & Integrations](#-domains--integrations)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Complete Setup](#-complete-setup)
- [Environment Variables](#-environment-variables)
- [Running the System](#-running-the-system)
- [Dashboard Features](#-dashboard-features)
- [API Integrations](#-api-integrations)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)

---

## 🎯 Overview

### What Problem Does Chronos Solve?

Traditional crisis-response systems are often:
- Rigid and slow to adapt
- Tightly coupled to hardware
- Hard to demonstrate or iterate quickly
- Lack real-time data integration
- Don't support multiple decision frameworks

**Chronos flips this model** by providing a fully software-based digital twin that:
- ✅ Reacts to real-time events from multiple domains (power, airspace, transit, traffic)
- ✅ Coordinates autonomous agents with different decision-making frameworks
- ✅ Uses AI (Gemini, Cerebras) to predict outcomes and generate recovery plans
- ✅ Supports voice-driven commands and announcements
- ✅ Integrates live data from public APIs (OC Transpo, OpenSky, Ontario 511, Ottawa Traffic)
- ✅ Provides real-time geospatial visualization with interactive maps
- ✅ Remains resilient even when components fail (graceful fallbacks)
- ✅ Supports blockchain audit logging (Solana)
- ✅ Includes comprehensive observability (Sentry)

---

## ✨ Key Features

### 1. **Multi-Domain Crisis Management**
- **Power Grid**: Simulates power failures across sectors, monitors voltage/load
- **Airspace**: Tracks aircraft positions, detects conflicts and congestion hotspots
- **Transit**: Monitors OC Transpo vehicles, detects delays and disruptions
- **Traffic**: Integrates Ottawa traffic incidents and Ontario 511 road events

### 2. **Agentic Decision Frameworks**
- **Rules Engine**: Deterministic, fast, reliable fallback
- **Single LLM**: AI-powered single-shot decision making (Gemini/Cerebras)
- **Agentic Mesh**: Multi-agent coordination with consensus and LLM escalation
- **Side-by-Side Comparison**: Compare all frameworks simultaneously

### 3. **Real-Time Dashboard**
- **Event Feed**: Live timeline of all system events
- **Interactive Map**: MapLibre GL JS map with:
  - Icon-based markers (aircraft, transit, power, alerts)
  - Color-coded by severity (red/orange/yellow/green)
  - Real-time pings on new events
  - Risk area overlays (circles/polygons)
  - Ottawa region bounds lock
  - Filtering by source, severity, time window
- **Airspace Overview**: Flight planning, conflict detection, hotspot visualization
- **Agentic Compare**: Side-by-side framework comparison with metrics
- **Audit Log**: Blockchain-verified decision audit trail

### 4. **Live Data Integration**
- **OC Transpo GTFS-RT**: Real-time transit vehicle positions and trip updates
- **OpenSky Network**: ADS-B aircraft position data
- **Ottawa Traffic**: Road incidents, construction, special events
- **Ontario 511**: Highway incidents and road closures
- **Mock Mode**: Automatic fallback to synthetic data when APIs unavailable

### 5. **Voice & Audio**
- **ElevenLabs TTS**: High-quality voice announcements for critical events
- **Browser Web Speech API**: Fallback voice synthesis in dashboard
- **Console Output**: Color-coded terminal announcements

### 6. **Observability & Monitoring**
- **Sentry Integration**: Error tracking, performance monitoring, breadcrumbs
- **Health Reports**: Startup configuration status for all services
- **Event Logging**: MongoDB-backed event store with indexing
- **Audit Trail**: Solana blockchain logging for critical decisions

### 7. **Fault Tolerance**
- **Graceful Degradation**: All APIs are optional with clean fallbacks
- **Broker Resilience**: NATS (local) or Solace PubSub+ (production)
- **LLM Fallbacks**: Rules-based plans if AI unavailable
- **Voice Fallbacks**: Console/browser if ElevenLabs unavailable
- **Map Resilience**: Works without Cesium token (ellipsoid terrain)

---

## 🏗️ System Architecture

### Event-Driven Architecture

```
┌─────────────────┐
│  Event Sources  │
├─────────────────┤
│ • Crisis Gen    │
│ • QNX Sim       │
│ • Live Adapters │
│ • Flight Plans  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message Broker  │
├─────────────────┤
│ NATS / Solace   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent Services │
├─────────────────┤
│ • Coordinator   │
│ • Autonomy Router│
│ • State Logger  │
│ • Risk Agents   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Services   │
├─────────────────┤
│ • Gemini        │
│ • Cerebras       │
│ • Rules Engine  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Dashboard     │
├─────────────────┤
│ • Next.js UI    │
│ • Real-time SSE │
│ • MapLibre Map  │
└─────────────────┘
```

### Core Components

1. **Message Broker**: NATS (local) or Solace PubSub+ (production)
2. **Event Store**: MongoDB for persistent event logging
3. **Agent Services**: Python-based microservices
4. **AI Services**: LLM clients (Gemini, Cerebras) with rules fallback
5. **Dashboard**: Next.js React application with real-time updates
6. **Live Data Adapters**: Modular adapters for external data sources

---

## 🌐 Domains & Integrations

### Power Grid Domain
- **Events**: `power.failure`, `recovery.plan`, `system.action`
- **Agents**: `crisis_generator.py`, `coordinator_agent.py`
- **Simulation**: QNX grid simulator (`qnx/grid_sim.cpp`)
- **Visualization**: Sector health cards, power failure markers on map

### Airspace Domain
- **Events**: `airspace.plan.uploaded`, `airspace.flight.parsed`, `airspace.conflict.detected`, `airspace.hotspot.detected`, `airspace.aircraft.position`
- **Agents**: `flight_plan_ingestor.py`, `trajectory_insight_agent.py`, `airspace_deconflict_agent.py`, `airspace_hotspot_agent.py`
- **Data Sources**: OpenSky Network (ADS-B), Flight plan JSON uploads
- **Visualization**: Aircraft icons on map, conflict markers, congestion hotspots

### Transit Domain
- **Events**: `transit.vehicle.position`, `transit.trip.update`, `transit.disruption.risk`, `transit.hotspot`
- **Agents**: `transit_ingestor.py`, `transit_risk_agent.py`
- **Data Sources**: OC Transpo GTFS-RT feeds (Vehicle Positions, Trip Updates)
- **Visualization**: Transit vehicle markers, delay clusters, disruption risk areas

### Traffic Domain
- **Events**: `geo.incident`, `geo.risk_area`
- **Agents**: Live data adapters (`ottawa_traffic.py`, `ontario511.py`)
- **Data Sources**: Ottawa Traffic API, Ontario 511 API
- **Visualization**: Traffic incident markers, construction zones, road closures

---

## 📦 Prerequisites

Before you begin, make sure you have:

1. **Docker Desktop** installed and running
   - Download: https://www.docker.com/products/docker-desktop
   - Verify: `docker --version`

2. **Python 3.10 or higher**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version`

3. **Node.js 18 or higher**
   - Download: https://nodejs.org/
   - Verify: `node --version`

4. **Git** (optional, for cloning)

---

## ⚡ Quick Start

### Step 1: Start Infrastructure (2 minutes)

```bash
# Navigate to infrastructure directory
cd infra

# Start MongoDB and NATS using Docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see `chronos-mongodb` and `chronos-nats` running.

### Step 2: Install Dependencies

**Python Dependencies:**
```bash
# From project root
cd agents/shared
pip install -r requirements.txt

cd ../../ai
pip install -r requirements.txt

cd ../voice
pip install -r requirements.txt

cd ../live_data
pip install -r requirements.txt
```

**Dashboard Dependencies:**
```bash
cd dashboard
npm install
```

### Step 3: Configure Environment (Optional)

Create a `.env` file in the project root (see [Environment Variables](#-environment-variables) section):

```bash
# Copy example
cp .env.example .env

# Edit with your API keys (all optional - system works without them)
```

### Step 4: Start Services

**Terminal 1 - State Logger:**
```bash
cd agents
python state_logger.py
```

**Terminal 2 - Crisis Generator:**
```bash
cd agents
python crisis_generator.py
```

**Terminal 3 - Coordinator Agent:**
```bash
cd agents
python coordinator_agent.py
```

**Terminal 4 - Autonomy Router:**
```bash
cd agents
python autonomy_router.py
```

**Terminal 5 - Live Data Runner (Optional):**
```bash
cd live_data
python runner.py
```

**Terminal 6 - Dashboard:**
```bash
cd dashboard
npm run dev
```

### Step 5: Access Dashboard

Open your browser to: **http://localhost:3000**

**🎉 The system is now running!**

---

## 🔧 Complete Setup

### 1. Environment Variables

Create a `.env` file in the **project root** directory:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Mac/Linux:**
```bash
cp .env.example .env
```

See [Environment Variables](#-environment-variables) section below for all available options.

### 2. Infrastructure Services

```bash
cd infra
docker-compose up -d
```

**Services Started:**
- **MongoDB**: `localhost:27017`
- **NATS**: `localhost:4222`
- **Mongo Express** (optional UI): `http://localhost:8081`

**To stop services:**
```bash
cd infra
docker-compose down
```

### 3. Python Virtual Environment (Recommended)

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r agents/shared/requirements.txt
pip install -r ai/requirements.txt
pip install -r voice/requirements.txt
pip install -r live_data/requirements.txt
```

### 4. Dashboard Setup

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at: **http://localhost:3000**

---

## 🔐 Environment Variables

### Required (Basic Operation)

These work with defaults - no setup needed:
- `NATS_HOST` (default: `localhost`)
- `NATS_PORT` (default: `4222`)
- `MONGO_HOST` (default: `localhost`)
- `MONGO_PORT` (default: `27017`)

### Optional (Enhanced Features)

#### Message Broker

```bash
# Use Solace PubSub+ instead of NATS
BROKER_BACKEND=solace
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

#### AI/LLM Services

**Google Gemini:**
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

**Cerebras (Recommended - Free Tier):**
```bash
LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
LLM_SERVICE_API_KEY=your_key_here
LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
```

**Priority**: Cerebras → Gemini → Rules Fallback

#### Voice Services

**ElevenLabs:**
```bash
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional
```

#### Observability

**Sentry:**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=1.0.0
```

#### Blockchain Audit

**Solana:**
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key_here
```

#### Transit Data

**OC Transpo (Optional - Mock Mode Works Without It):**
```bash
TRANSIT_MODE=mock  # or "live"
OCTRANSPO_API_KEY=your_subscription_key_here
OCTRANSPO_GTFSRT_BASE_URL=https://api.octranspo.com/v2
```

#### Live Data Adapters

```bash
# Global live mode toggle
LIVE_MODE=on  # or "off"

# Enable which adapters to run
LIVE_ADAPTERS=oc_transpo,ottawa_traffic,opensky,ontario511

# OpenSky Network (optional credentials)
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
```

#### Framework Configuration

```bash
# Which frameworks to enable
ENABLED_FRAMEWORKS=RULES_ENGINE,SINGLE_LLM,AGENTIC_MESH

# Which framework to use for execution
SELECTED_FRAMEWORK=AGENTIC_MESH
```

### Complete .env Example

See `.env.example` file in the project root for a complete template.

---

## 🏃 Running the System

### Service Order

Start services in this order:

1. **Infrastructure** (Docker): MongoDB, NATS
2. **State Logger**: Must be running to log events
3. **Crisis Generator**: Generates test events
4. **Coordinator Agent**: Processes events and coordinates frameworks
5. **Autonomy Router**: Routes decisions based on autonomy level
6. **Live Data Runner** (Optional): Fetches live data from external APIs
7. **Dashboard**: Web interface

### Using Start Scripts

**Windows (PowerShell):**
```powershell
.\agents\start_services.ps1
```

**Mac/Linux:**
```bash
./agents/start_services.sh
```

### Verifying Services

```bash
# Check Docker services
docker ps

# Check MongoDB connection
# (Should see connection logs in state_logger terminal)

# Check NATS connection
# (Should see connection logs in agent terminals)
```

---

## 🖥️ Dashboard Features

### Main Dashboard (`/`)

- **Power Sector Health Cards**: Visual indicators (green/yellow/red) for each sector
- **Airspace Congestion Gauge**: Real-time congestion percentage
- **Autonomy Mode Badge**: Current autonomy level (NORMAL/HIGH)
- **Latest Recovery Plan Panel**: Most recent AI-generated recovery plan
- **Event Timeline Feed**: Chronological list of all events with icons
- **Voice Announcements**: Toggle for audio announcements

### Interactive Map (`/map`)

- **MapLibre GL JS**: High-performance 2D map with OpenStreetMap tiles
- **Icon-Based Markers**:
  - 🛫 Aircraft (green airplane icons)
  - 🚌 Transit vehicles (bus icons)
  - ⚡ Power failures (lightning icons)
  - ⚠️ Alerts (warning triangle icons)
  - ● Incidents (colored circles)
- **Color-Coding by Severity**:
  - Red: High/Critical/Error
  - Orange: Medium/Warning
  - Yellow: Low/Info
  - Green: Aircraft (special)
- **Real-Time Pings**: Animated pulse rings on new events
- **Risk Area Overlays**: Translucent circles/polygons for hotspots
- **Ottawa Bounds Lock**: Map restricted to Ottawa region
- **Filters**:
  - Time window (15m/1h/6h/24h)
  - Severity (All/High+Critical/Medium/Low)
  - Source (All/transit/traffic/airspace/power)
- **Dropped Pin Panel**: Click any marker to see detailed information

### Airspace Overview (`/airspace`)

- **Flight Plan Upload**: Upload JSON flight plans
- **Flight List**: All parsed flights with details
- **Conflict Detection**: Visualized conflicts between flights
- **Hotspot Visualization**: Congestion hotspots on map
- **Validation**: Altitude/speed violations with suggested fixes

### Agentic Compare (`/compare`)

- **Side-by-Side Comparison**: All enabled frameworks displayed simultaneously
- **Framework Metrics**:
  - Execution time
  - Number of actions
  - Priority violations
  - Confidence score
  - Model/Provider information
- **Selected Framework**: Highlighted with green border
- **Rerun Capability**: Test same event through all frameworks

### Audit Log (`/audit`)

- **Decision History**: All audit decisions with timestamps
- **Solana Hashes**: Blockchain verification hashes (if configured)
- **Decision Details**: Full context of each decision

---

## 🔌 API Integrations

### Message Brokers

- **NATS**: Local message broker (default, always available)
- **Solace PubSub+**: Production-grade message broker (optional)

### AI/LLM Services

- **Google Gemini**: AI recovery plan generation
- **Cerebras**: Alternative LLM provider (free tier available)

### Voice Services

- **ElevenLabs**: High-quality text-to-speech
- **Browser Web Speech API**: Fallback voice synthesis

### Live Data Sources

- **OC Transpo GTFS-RT**: Real-time transit data
- **OpenSky Network**: ADS-B aircraft position data
- **Ottawa Traffic API**: Road incidents and construction
- **Ontario 511 API**: Highway incidents and closures

### Observability

- **Sentry**: Error tracking and performance monitoring

### Blockchain

- **Solana**: Immutable audit logging

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to MongoDB"

**Solution:**
```bash
cd infra
docker-compose ps
docker-compose up -d mongodb
docker-compose logs mongodb
```

### Problem: "Cannot connect to NATS"

**Solution:**
```bash
cd infra
docker-compose ps
docker-compose up -d nats
docker-compose logs nats
```

### Problem: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure you're running from project root
cd /path/to/Chronos-Cloud

# Install dependencies
pip install -r agents/shared/requirements.txt
```

### Problem: "Dashboard not loading"

**Solution:**
```bash
cd dashboard
npm install
npm run dev
# Check for errors in terminal
# Make sure port 3000 is not in use
```

### Problem: "Map not showing events"

**Solution:**
- Check that `state_logger.py` is running
- Verify events are being published (check agent logs)
- Check browser console for errors
- Ensure MongoDB has events (check with `query_events.py`)

### Problem: "API errors"

**Solution:**
- All APIs are optional - system works with fallbacks
- Check API keys in `.env` file
- Verify internet connection
- Check service logs for specific error messages

---

## 📁 Project Structure

```
Chronos-Cloud/
├── agents/                    # Autonomous agent services
│   ├── crisis_generator.py   # Generates power failure events
│   ├── coordinator_agent.py  # Coordinates framework comparisons
│   ├── autonomy_router.py    # Routes decisions based on autonomy
│   ├── state_logger.py       # Logs all events to MongoDB
│   ├── stress_monitor.py     # Monitors operator stress
│   ├── flight_plan_ingestor.py # Processes flight plan uploads
│   ├── trajectory_insight_agent.py # Analyzes flight trajectories
│   ├── transit_ingestor.py   # Processes transit data
│   ├── transit_risk_agent.py # Detects transit disruptions
│   ├── ottawa_overlay_generator.py # Generates synthetic geo overlays
│   ├── solana_audit_logger.py # Blockchain audit logging
│   ├── frameworks/            # Decision frameworks
│   │   ├── rules_engine.py   # Deterministic rules
│   │   ├── single_llm.py     # Single LLM framework
│   │   └── agentic_mesh.py   # Multi-agent coordination
│   └── shared/              # Shared utilities
│       ├── messaging.py      # Pub/sub interface
│       ├── schema.py         # Event schemas
│       ├── config.py         # Configuration
│       └── sentry.py         # Sentry integration
│
├── ai/                        # AI/ML services
│   ├── llm_client.py         # Unified LLM client
│   ├── gemini_client.py       # Google Gemini client
│   ├── recovery_planner.py   # Recovery plan generation
│   └── prompts.py            # LLM prompts
│
├── voice/                     # Voice processing
│   └── elevenlabs_client.py # ElevenLabs TTS client
│
├── live_data/                 # Live data adapters
│   ├── base.py              # Base adapter interface
│   ├── runner.py            # Adapter runner
│   └── adapters/            # Individual adapters
│       ├── oc_transpo_gtfsrt.py # OC Transpo GTFS-RT
│       ├── opensky_airspace.py  # OpenSky Network
│       ├── ottawa_traffic.py    # Ottawa Traffic
│       └── ontario511.py        # Ontario 511
│
├── dashboard/                 # Web-based monitoring UI
│   ├── pages/               # Next.js pages
│   │   ├── index.tsx        # Main dashboard
│   │   ├── map.tsx          # Interactive map
│   │   ├── airspace/        # Airspace pages
│   │   ├── compare/         # Agentic compare
│   │   └── audit/          # Audit log
│   ├── components/          # React components
│   │   ├── OttawaMapClean.tsx # MapLibre map component
│   │   ├── DroppedPinPanel.tsx # Map marker details
│   │   └── ...              # Other components
│   └── lib/                 # Utilities
│       ├── mongodb.ts       # MongoDB client
│       ├── voiceAnnouncements.ts # Voice synthesis
│       └── eventToGeo.ts   # Geo event conversion
│
├── infra/                     # Infrastructure
│   └── docker-compose.yml   # Docker services
│
├── qnx/                       # QNX integration
│   ├── grid_sim.cpp         # QNX grid simulator
│   └── README.md            # QNX setup guide
│
├── docs/                      # Documentation
│   ├── events.md            # Event schema documentation
│   ├── agentic_compare.md   # Framework comparison guide
│   ├── observability.md     # Sentry setup guide
│   ├── live_data_adapters.md # Adapter documentation
│   └── ...                  # Other docs
│
├── scripts/                   # Utility scripts
│   ├── smoke_test.py       # Integration smoke tests
│   └── verify_live_data.py # Live data verification
│
└── .env.example              # Environment variable template
```

---

## 📚 Documentation

### Core Documentation

- **`QUICK_START.md`**: Step-by-step guide to get started quickly
- **`TESTING_GUIDE.md`**: Comprehensive testing instructions
- **`docs/events.md`**: Complete event schema documentation
- **`docs/agentic_compare.md`**: Agentic framework comparison guide
- **`docs/observability.md`**: Sentry observability setup
- **`docs/live_data_adapters.md`**: Live data adapter documentation

### Setup Guides

- **`docs/SENTRY_SETUP.md`**: Sentry error tracking setup
- **`docs/ELEVENLABS_SETUP.md`**: ElevenLabs voice setup
- **`docs/SOLACE_SIGNUP_GUIDE.md`**: Solace PubSub+ signup guide
- **`docs/CEREBRAS_SETUP.md`**: Cerebras LLM setup
- **`docs/SOLACE_CEREBRAS_SETUP.md`**: Combined Solace + Cerebras setup

### API Documentation

- **`docs/APIS_USED.md`**: List of all APIs used in the project

### Domain-Specific

- **`qnx/README.md`**: QNX grid simulator setup
- **`agents/README.md`**: Agent service documentation
- **`ai/README.md`**: AI service documentation
- **`voice/README.md`**: Voice service documentation

---

## 🎯 Key Capabilities

### Event Processing

- **Real-Time Event Streaming**: Server-Sent Events (SSE) for live updates
- **Event Store**: MongoDB-backed persistent storage with indexing
- **Event Schema**: Standardized JSON event format across all domains
- **Event Correlation**: Correlation IDs for tracking related events

### Decision Making

- **Multi-Framework Support**: Rules Engine, Single LLM, Agentic Mesh
- **Framework Comparison**: Side-by-side comparison with metrics
- **Autonomy Levels**: NORMAL (requires approval) vs HIGH (autonomous)
- **Priority Handling**: Hospital/airport/medevac priority heuristics

### Geospatial Visualization

- **Interactive Map**: MapLibre GL JS with OpenStreetMap tiles
- **Icon-Based Markers**: Different icons for different event types
- **Color-Coding**: Severity-based color scheme
- **Real-Time Pings**: Animated pulse rings on new events
- **Risk Areas**: Circle and polygon overlays for hotspots
- **Ottawa-Focused**: Bounds-locked to Ottawa region

### Live Data Integration

- **Modular Adapters**: Pluggable adapter system for external data
- **Automatic Fallbacks**: Mock mode when APIs unavailable
- **Rate Limiting**: Respects API rate limits
- **Error Handling**: Graceful degradation on adapter failures

### Fault Tolerance

- **Graceful Degradation**: All APIs optional with clean fallbacks
- **Health Reports**: Startup configuration status
- **Error Tracking**: Sentry integration (optional)
- **Retry Logic**: Automatic retries with backoff
- **Timeout Protection**: Prevents hanging on slow APIs

---

## 🚀 Next Steps

1. **Run the Demo**: Follow `QUICK_START.md` or `docs/demo_script.md`
2. **Explore the Dashboard**: Open http://localhost:3000
3. **Trigger Events**: Press `f` in crisis generator terminal
4. **Watch the System Respond**: See events flow through the system
5. **Try Different Modes**: Use stress monitor to toggle HIGH/NORMAL autonomy
6. **Upload Flight Plans**: Test airspace domain with JSON flight plans
7. **Compare Frameworks**: Use Agentic Compare page to see different decision approaches

---

## 📄 License

*Add license information here*

---

## 📬 Support

For bugs, ideas, or questions, please open an issue in the repository.

**Happy coding! 🚀**
