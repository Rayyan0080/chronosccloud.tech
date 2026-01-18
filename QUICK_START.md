# 🚀 Quick Start Guide - Running Project Chronos

This guide will help you run the **entire Project Chronos system** from scratch.

**Estimated Time**: 10-15 minutes

---

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ **Docker Desktop** installed and running
- ✅ **Python 3.10+** installed
- ✅ **Node.js 18+** installed
- ✅ **Git** (optional, for cloning)

Verify installations:
```bash
docker --version
python --version
node --version
```

---

## 🎯 Step-by-Step Setup

### Step 1: Start Infrastructure Services (2 minutes)

Open a terminal and run:

```bash
# Navigate to infrastructure directory
cd infra

# Start MongoDB and NATS using Docker
docker-compose up -d

# Wait 10 seconds, then verify services are running
docker-compose ps
```

**Expected Output:**
```
NAME              STATUS          PORTS
chronos-mongodb   Up (healthy)    0.0.0.0:27017->27017/tcp
chronos-nats      Up              0.0.0.0:4222->4222/tcp
```

**If services fail to start:**
- Make sure Docker Desktop is running
- Check if ports 27017 or 4222 are already in use
- Run `docker-compose logs` to see errors

---

### Step 2: Install Python Dependencies (3 minutes)

Open a **new terminal** (keep the infrastructure terminal running) and run:

**Windows (PowerShell):**
```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r agents/shared/requirements.txt
pip install -r ai/requirements.txt
pip install -r voice/requirements.txt
```

**Mac/Linux:**
```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r agents/shared/requirements.txt
pip install -r ai/requirements.txt
pip install -r voice/requirements.txt
```

---

### Step 3: Install Dashboard Dependencies (2 minutes)

Open a **new terminal** and run:

```bash
# Navigate to dashboard directory
cd dashboard

# Install Node.js dependencies
npm install
```

---

### Step 4: Configure Environment Variables (Optional - 2 minutes)

Create a `.env` file in the **project root**:

**Windows (PowerShell):**
```powershell
# Copy example file
Copy-Item .env.example .env

# Edit with notepad
notepad .env
```

**Mac/Linux:**
```bash
# Copy example file
cp .env.example .env

# Edit with your preferred editor
nano .env
```

**Minimum for basic operation:** No variables needed! System works with defaults.

**Optional (for enhanced features):**
- `GEMINI_API_KEY` - For AI recovery plans (Google Gemini)
- `LLM_SERVICE_API_KEY` - For AI recovery plans (Cerebras - free tier)
- `ELEVENLABS_API_KEY` - For voice announcements
- `SENTRY_DSN` - For error tracking

See `README.md` for detailed API key setup instructions.

---

### Step 5: Start All Services

You'll need **multiple terminal windows** open. Here's the recommended order:

#### Terminal 1: State Logger (Required)
```bash
cd agents
python state_logger.py
```

**Expected Output:**
```
Connected to MongoDB
Subscribed to all event topics
State Logger running...
```

#### Terminal 2: Dashboard (Required)
```bash
cd dashboard
npm run dev
```

**Expected Output:**
```
> dashboard@0.1.0 dev
> next dev
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
```

Open your browser to: **http://localhost:3000**

#### Terminal 3: Crisis Generator (Required for Power Domain)
```bash
cd agents
python crisis_generator.py
```

**Expected Output:**
```
Crisis Generator running...
Press 'f' to trigger a power failure manually
```

#### Terminal 4: Coordinator Agent (Required)
```bash
cd agents
python coordinator_agent.py
```

**Expected Output:**
```
Coordinator Agent running...
Waiting for events...
```

#### Terminal 5: Autonomy Router (Required)
```bash
cd agents
python autonomy_router.py
```

**Expected Output:**
```
Autonomy Router running...
Subscribed to operator.status and recovery.plan
```

#### Terminal 6: Transit Ingestor (Required for Transit Domain)
```bash
cd agents
python transit_ingestor.py
```

**Expected Output:**
```
Transit mode: mock  (or "live" if using real API)
Starting Transit Ingestor Service
Connected to message broker
Transit Ingestor Service started successfully
```

**Note:** Look for the startup line `"Transit mode: mock"` or `"Transit mode: live"`.

#### Terminal 7: Transit Risk Agent (Required for Transit Domain)
```bash
cd agents
python transit_risk_agent.py
```

**Expected Output:**
```
Starting Transit Risk Agent
Subscribed to: chronos.events.transit.vehicle.position
Subscribed to: chronos.events.transit.trip.update
Transit Risk Agent is running
```

#### Terminal 8: Trajectory Insight Agent (Required for Airspace Domain)
```bash
cd agents
python trajectory_insight_agent.py
```

**Expected Output:**
```
Trajectory Insight Agent running...
Waiting for flight.parsed events...
```

#### Terminal 9: Ottawa Overlay Generator (Optional - for Map Demo)
```bash
cd agents
python ottawa_overlay_generator.py
```

**Expected Output:**
```
Ottawa Overlay Generator running...
Generating overlay events every 30 seconds...
```

#### Terminal 10: Stress Monitor (Optional)
```bash
cd agents
python stress_monitor.py
```

**Expected Output:**
```
Stress Monitor running...
Press 's' for HIGH stress, 'n' for NORMAL
```

#### Terminal 11: Solana Audit Logger (Optional)
```bash
cd agents
python solana_audit_logger.py
```

**Expected Output:**
```
Solana Audit Logger running...
Subscribed to audit.decision events
```

---

## 🎮 Testing the System

### Test 1: Power Domain

1. In **Terminal 3** (Crisis Generator), press `f` to trigger a power failure
2. Watch events flow through the system
3. Check the dashboard at http://localhost:3000
4. See events appear in the timeline

### Test 2: Transit Domain

1. **Check Transit Ingestor:**
   - In Terminal 6, wait 10 seconds
   - You should see: `"Fetched X vehicle positions"` and `"Published X vehicle position events"`
   - Check startup message shows: `"Transit mode: mock"` or `"Transit mode: live"`

2. **Check Transit Risk Agent:**
   - In Terminal 7, wait 30 seconds
   - You should see: `"Analysis complete: X delay clusters, X headway anomalies..."`

3. **Check Dashboard:**
   - Go to http://localhost:3000
   - Look for transit events in timeline:
     - `transit.vehicle.position`
     - `transit.trip.update`
     - `transit.disruption.risk` (if risks detected)
     - `transit.hotspot` (if hotspots detected)

4. **Check Transit Mode Badge:**
   - In dashboard navigation bar (top right)
   - If in mock mode, you should see: **"⚠️ Transit: MOCK"** badge

5. **Test Map with Transit Data:**
   - Go to http://localhost:3000/map
   - Set Source filter to "Transit"
   - You should see transit incidents/risks on the map

### Test 3: Airspace Domain

1. Go to dashboard: http://localhost:3000/airspace
2. Click "Upload Plan" tab
3. Upload a flight plan JSON file (see `dashboard/test_flight_plan.json`)
4. Watch conflicts and hotspots get detected
5. Check the map at http://localhost:3000/map to see geospatial overlays

### Test 4: Map Visualization

1. Go to dashboard: http://localhost:3000/map
2. If `ottawa_overlay_generator.py` is running, you'll see:
   - Risk areas (red circles)
   - Incidents (red markers)
3. Use controls to toggle incidents and risk heat
4. Filter by time range and severity

---

## 📊 Service Overview

### Core Services (Required)

| Service | Purpose | Terminal |
|---------|---------|----------|
| **State Logger** | Logs all events to MongoDB | Terminal 1 |
| **Dashboard** | Web UI for monitoring | Terminal 2 |
| **Crisis Generator** | Generates power failure events | Terminal 3 |
| **Coordinator Agent** | Coordinates framework comparisons | Terminal 4 |
| **Autonomy Router** | Routes decisions based on autonomy | Terminal 5 |
| **Trajectory Insight Agent** | Analyzes flight trajectories | Terminal 6 |

### Optional Services

| Service | Purpose | Terminal |
|---------|---------|----------|
| **Ottawa Overlay Generator** | Generates demo geospatial overlays | Terminal 7 |
| **Stress Monitor** | Monitors operator stress | Terminal 8 |
| **Solana Audit Logger** | Logs audit decisions to blockchain | Terminal 9 |

---

## 🛑 Stopping the System

### Stop Python Services

Press `Ctrl+C` in each terminal window running Python services.

### Stop Dashboard

Press `Ctrl+C` in the dashboard terminal.

### Stop Infrastructure

```bash
cd infra
docker-compose down
```

---

## 🔍 Verifying Everything is Running

### Check Docker Services
```bash
cd infra
docker-compose ps
```

### Check MongoDB Connection
```bash
# Should see connection logs in state_logger terminal
```

### Check NATS Connection
```bash
# Should see connection logs in agent terminals
```

### Check Dashboard
Open browser: http://localhost:3000

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to MongoDB"

**Solution:**
```bash
cd infra
docker-compose restart mongodb
docker-compose logs mongodb
```

### Problem: "Cannot connect to NATS"

**Solution:**
```bash
cd infra
docker-compose restart nats
docker-compose logs nats
```

### Problem: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure you're in the project root
# Install dependencies again
pip install -r agents/shared/requirements.txt
```

### Problem: "Port already in use"

**Solution:**
- Check if another instance is running
- Change ports in `infra/docker-compose.yml` if needed
- Kill the process using the port

### Problem: "Dashboard not loading"

**Solution:**
```bash
cd dashboard
npm run dev
# Check terminal for errors
```

---

## 📚 Next Steps

1. **Explore the Dashboard**: Navigate to different pages
   - `/` - Main dashboard
   - `/map` - 3D map visualization
   - `/airspace` - Airspace management
   - `/compare` - Framework comparison
   - `/audit` - Audit decisions

2. **Read Documentation**:
   - `README.md` - Complete project documentation
   - `docs/demo_script.md` - Step-by-step demo guide
   - `docs/agentic_compare.md` - Framework comparison details

3. **Try Different Features**:
   - Upload flight plans
   - Trigger power failures
   - Toggle autonomy modes
   - View geospatial overlays

---

## 🎉 You're All Set!

The system is now running. Start exploring and testing different features!

**Need Help?** Check the main `README.md` for detailed documentation.

