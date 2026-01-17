# Project Chronos

**Project Chronos** is a **software-only digital twin crisis management system** built using a **fault-tolerant, event-driven architecture**.

It simulates, detects, and responds to crisis scenarios in real time using autonomous agents, AI-driven predictions, and voice-based interaction—designed to be **demo-first**, **production-ready**, and **modular by default**.

---

## 📋 Table of Contents

- [What Problem Does Chronos Solve?](#-what-problem-does-chronos-solve)
- [Prerequisites](#-prerequisites)
- [Quick Start Guide](#-quick-start-guide)
- [Complete Setup Instructions](#-complete-setup-instructions)
- [Environment Variables](#-environment-variables)
- [Running the System](#-running-the-system)
- [Dashboard](#-dashboard)
- [API Keys Setup](#-api-keys-setup-optional)
- [Troubleshooting](#-troubleshooting)
- [Architecture](#-architecture-overview)

---

## 🚀 What Problem Does Chronos Solve?

Traditional crisis-response systems are often:
- Rigid and slow to adapt
- Tightly coupled to hardware
- Hard to demonstrate or iterate quickly

**Chronos flips this model** by providing a fully software-based digital twin that:
- Reacts to real-time events
- Coordinates autonomous agents
- Uses AI to predict outcomes
- Supports voice-driven commands
- Remains resilient even when components fail

---

## 📦 Prerequisites

Before you begin, make sure you have:

1. **Docker Desktop** installed and running
   - Download: https://www.docker.com/products/docker-desktop
   - Verify: Open Docker Desktop and ensure it's running

2. **Python 3.10 or higher**
   - Download: https://www.python.org/downloads/
   - Verify: Open terminal and run `python --version`

3. **Node.js 18 or higher**
   - Download: https://nodejs.org/
   - Verify: Open terminal and run `node --version`

4. **Git** (optional, for cloning)
   - Download: https://git-scm.com/downloads

---

## ⚡ Quick Start Guide

### Step 1: Start Infrastructure (5 minutes)

```bash
# Navigate to infrastructure directory
cd infra

# Start MongoDB and NATS using Docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see `chronos-mongodb` and `chronos-nats` running.

### Step 2: Install Python Dependencies

```bash
# From project root directory
cd agents/shared
pip install -r requirements.txt

# Install AI service dependencies
cd ../../ai
pip install -r requirements.txt

# Install voice service dependencies
cd ../voice
pip install -r requirements.txt
```

### Step 3: Install Dashboard Dependencies

```bash
# From project root
cd dashboard
npm install
```

### Step 4: Start the Dashboard

```bash
# Still in dashboard directory
npm run dev
```

Open your browser to: **http://localhost:3000**

### Step 5: Start Agent Services

Open **separate terminal windows** for each service:

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

**Terminal 5 - Stress Monitor:**
```bash
cd agents
python stress_monitor.py
```

### Step 6: Test the System

1. In the **Crisis Generator** terminal, press `f` to trigger a power failure
2. Watch the dashboard update in real-time
3. See events flow through the system

**🎉 Congratulations! The system is running!**

---

## 🔧 Complete Setup Instructions

### 1. Environment Variables Setup

Create a `.env` file in the **project root** directory:

**Windows (PowerShell):**
```powershell
# Copy the example file
Copy-Item .env.example .env

# Or create manually
New-Item -Path .env -ItemType File
```

**Mac/Linux:**
```bash
# Copy the example file
cp .env.example .env
```

Then edit `.env` and add your configuration (see [Environment Variables](#-environment-variables) section below).

### 2. Infrastructure Services

The system needs MongoDB and NATS running. Use Docker Compose:

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

### 3. Python Environment Setup

**Create a virtual environment (recommended):**

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
# Agent dependencies
pip install -r agents/shared/requirements.txt

# AI service dependencies
pip install -r ai/requirements.txt

# Voice service dependencies
pip install -r voice/requirements.txt
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

### Required Variables (for basic operation)

These work with defaults - no setup needed:
- `NATS_HOST` (default: `localhost`)
- `NATS_PORT` (default: `4222`)
- `MONGO_HOST` (default: `localhost`)
- `MONGO_PORT` (default: `27017`)

### Optional Variables (for enhanced features)

#### Google Gemini API (for AI recovery plans)

```bash
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
```

**How to get Gemini API key:**
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add to `.env`

#### ElevenLabs Voice (for voice announcements)

```bash
# Get your API key from: https://elevenlabs.io
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Optional, uses default if not set
```

**How to get ElevenLabs API key:**
1. Go to https://elevenlabs.io
2. Sign up for a free account
3. Go to your profile → API Keys
4. Create a new API key
5. Copy and add to `.env`

#### Sentry (for error tracking)

```bash
# Get your DSN from: https://sentry.io
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=development  # Optional
SENTRY_RELEASE=1.0.0  # Optional
```

**How to get Sentry DSN:**
1. Go to https://sentry.io
2. Sign up for a free account
3. Create a new project (select "Python" platform)
4. Copy the DSN from project settings
5. Add to `.env`

**Detailed step-by-step guide**: See `docs/SENTRY_SETUP.md` for complete instructions

#### Solace PubSub+ (for production message broker)

```bash
# Only needed if using Solace instead of NATS
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password
```

**How to get Solace credentials:**
1. Go to https://console.solace.cloud
2. Sign up for a free account
3. Create a messaging service
4. Go to "Connect" tab
5. Copy connection details

#### Solana (for blockchain audit logging)

```bash
# Only needed for blockchain audit logging
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=your_private_key_here
```

### Framework Configuration

```bash
# Which frameworks to enable (comma-separated)
ENABLED_FRAMEWORKS=RULES_ENGINE,SINGLE_LLM,AGENTIC_MESH

# Which framework to use for execution
SELECTED_FRAMEWORK=AGENTIC_MESH
```

### Complete .env Example

See `.env.example` file in the project root for a complete template with all variables.

---

## 🏃 Running the System

### Starting All Services

You need to run multiple services simultaneously. Here are your options:

#### Option 1: Separate Terminal Windows (Recommended for beginners)

Open 5-6 terminal windows and run one service in each:

1. **State Logger** - Logs all events to MongoDB
2. **Crisis Generator** - Generates power failure events
3. **Coordinator Agent** - Coordinates framework comparisons
4. **Autonomy Router** - Routes decisions based on autonomy level
5. **Stress Monitor** - Monitors operator stress (optional)
6. **Recovery Planner** - Generates AI recovery plans (if Gemini API key is set)

#### Option 2: Background Jobs (PowerShell)

```powershell
# Start all services in background
Start-Job -ScriptBlock { cd agents; python state_logger.py }
Start-Job -ScriptBlock { cd agents; python crisis_generator.py }
Start-Job -ScriptBlock { cd agents; python coordinator_agent.py }
Start-Job -ScriptBlock { cd agents; python autonomy_router.py }

# View running jobs
Get-Job

# Stop all jobs
Get-Job | Stop-Job
```

#### Option 3: Using the Start Script

```powershell
# Windows
.\agents\start_services.ps1

# Mac/Linux
./agents/start_services.sh
```

### Service Order

Start services in this order:

1. **Infrastructure** (Docker): MongoDB, NATS
2. **State Logger**: Must be running to log events
3. **Crisis Generator**: Generates test events
4. **Coordinator Agent**: Processes events
5. **Autonomy Router**: Routes decisions
6. **Dashboard**: Web interface

### Verifying Services

**Check if services are running:**

```bash
# Check Docker services
docker ps

# Check if MongoDB is accessible
# (Should see connection logs in state_logger terminal)

# Check if NATS is accessible
# (Should see connection logs in agent terminals)
```

---

## 🖥️ Dashboard

### Accessing the Dashboard

1. Start the dashboard: `cd dashboard && npm run dev`
2. Open browser: **http://localhost:3000**

### Dashboard Pages

- **/** - Main dashboard with:
  - Power sector health cards (green/yellow/red)
  - Airspace congestion gauge
  - Autonomy mode badge
  - Latest recovery plan panel
  - Event timeline feed

- **/map** - Sector map view
- **/compare** - Agentic framework comparison
- **/audit** - Audit decisions and Solana hashes

### Dashboard Features

- **Auto-refresh**: Updates every 5 seconds
- **Real-time events**: See events as they happen
- **Color-coded status**: Visual indicators for system health
- **Dark mode**: Easy on the eyes

---

## 🔑 API Keys Setup (Optional)

### LLM API (Gemini or Cerebras)

**Purpose**: Generates AI-powered recovery plans

**Option 1: Google Gemini**
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key
5. Add to `.env`: `GEMINI_API_KEY=your_key_here`

**Option 2: Cerebras (Free Tier - Recommended)**
1. Visit: https://cloud.cerebras.ai
2. Sign up for free account
3. Create an API key
4. Add to `.env`:
   ```bash
   LLM_SERVICE_ENDPOINT=https://api.cerebras.ai/v1
   LLM_SERVICE_API_KEY=your_key_here
   LLM_SERVICE_PLANNING_MODEL_NAME=openai/zai-glm-4.7
   LLM_SERVICE_GENERAL_MODEL_NAME=openai/zai-glm-4.7
   ```

**Priority**: Cerebras → Gemini → Fallback plans

**Without API keys**: System uses fallback recovery plans (still works!)

### ElevenLabs Voice

**Purpose**: Voice announcements for critical events

**Setup:**
1. Visit: https://elevenlabs.io
2. Sign up for free account
3. Go to Profile → API Keys
4. Create new API key
5. Add to `.env`: `ELEVENLABS_API_KEY=your_key_here`

**Without API key**: System uses console output (still works!)

### Sentry

**Purpose**: Error tracking and monitoring

**Setup:**
1. Visit: https://sentry.io
2. Sign up for free account
3. Create new project
4. Copy DSN from project settings
5. Add to `.env`: `SENTRY_DSN=your_dsn_here`

**Without Sentry**: System works normally, just no error tracking

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to MongoDB"

**Solution:**
```bash
# Check if MongoDB is running
cd infra
docker-compose ps

# If not running, start it
docker-compose up -d mongodb

# Check logs
docker-compose logs mongodb
```

### Problem: "Cannot connect to NATS"

**Solution:**
```bash
# Check if NATS is running
cd infra
docker-compose ps

# If not running, start it
docker-compose up -d nats

# Check logs
docker-compose logs nats
```

### Problem: "ModuleNotFoundError: No module named 'agents'"

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
# Check if dashboard is running
cd dashboard
npm run dev

# Check for errors in terminal
# Make sure port 3000 is not in use
```

### Problem: "Gemini API errors"

**Solution:**
- Check your API key is correct in `.env`
- Verify you have API credits/quota
- Check internet connection
- System will use fallback plans if API fails

### Problem: "Services not communicating"

**Solution:**
1. Verify all services are running
2. Check NATS is accessible: `docker ps | grep nats`
3. Check MongoDB is accessible: `docker ps | grep mongo`
4. Look for connection errors in service logs

### Getting Help

- Check service logs for error messages
- Verify all prerequisites are installed
- Ensure Docker Desktop is running
- Check that ports are not in use

---

## 🏗️ Architecture Overview

```
Chronos-Cloud/
├── qnx/              # QNX-based services and integrations
├── agents/           # Autonomous agent services
│   ├── crisis_generator.py      # Generates power failure events
│   ├── coordinator_agent.py    # Coordinates framework comparisons
│   ├── autonomy_router.py       # Routes decisions based on autonomy
│   ├── state_logger.py          # Logs all events to MongoDB
│   ├── stress_monitor.py        # Monitors operator stress
│   └── frameworks/              # Decision frameworks
├── ai/               # AI/ML services
│   ├── gemini_client.py         # Google Gemini API client
│   └── recovery_planner.py      # Generates recovery plans
├── voice/            # Voice processing
│   └── elevenlabs_client.py      # ElevenLabs TTS client
├── dashboard/        # Web-based monitoring UI
│   └── pages/                   # Dashboard pages
├── infra/            # Infrastructure
│   └── docker-compose.yml       # Docker services
└── docs/             # Documentation
```

### Event Flow

1. **Crisis Generator** → Publishes `power.failure` events
2. **Coordinator Agent** → Receives events, dispatches to frameworks
3. **Frameworks** → Generate recovery plans (Rules Engine, LLM, Agentic Mesh)
4. **Recovery Planner** → Uses Gemini to generate AI plans
5. **Autonomy Router** → Routes based on autonomy level (HIGH/NORMAL)
6. **State Logger** → Logs all events to MongoDB
7. **Dashboard** → Displays events in real-time

---

## 📚 Additional Documentation

- **Demo Script**: See `docs/demo_script.md` for step-by-step demo instructions
- **Agentic Compare**: See `docs/agentic_compare.md` for framework comparison details
- **Observability**: See `docs/observability.md` for Sentry setup
- **QNX Integration**: See `qnx/README.md` for QNX simulator setup
- **Voice Services**: See `voice/README.md` for ElevenLabs setup

---

## 🎯 Next Steps

1. **Run the demo**: Follow `docs/demo_script.md`
2. **Explore the dashboard**: Open http://localhost:3000
3. **Trigger events**: Press `f` in crisis generator terminal
4. **Watch the system respond**: See events flow through the system
5. **Try different autonomy modes**: Use stress monitor to toggle HIGH/NORMAL

---

## 📄 License

*Add license information here*

---

## 📬 Support

For bugs, ideas, or questions, please open an issue in the repository.

**Happy coding! 🚀**
