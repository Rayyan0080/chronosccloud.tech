# 🧪 Testing Guide - Project Chronos

This guide will help you test the entire Chronos system, including all domains (Power, Airspace, Transit).

---

## 📋 Prerequisites Check

Before testing, verify you have:

```bash
# Check Docker is running
docker ps

# Check Python version (3.10+)
python --version

# Check Node.js version (18+)
node --version
```

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Start Infrastructure

```bash
# Navigate to infra directory
cd infra

# Start MongoDB and NATS
docker-compose up -d

# Verify they're running
docker-compose ps
```

**Expected:** Both `chronos-mongodb` and `chronos-nats` should show as "Up"

### Step 2: Install Dependencies (One-Time Setup)

**Python:**
```bash
# From project root
pip install -r agents/shared/requirements.txt
pip install -r ai/requirements.txt
pip install -r voice/requirements.txt
pip install -r transit_octranspo/requirements.txt
```

**Dashboard:**
```bash
cd dashboard
npm install
```

### Step 3: Configure Transit Mode (Optional)

**Important:** `OCTRANSPO_API_KEY` is **OPTIONAL**. The system works perfectly without it using synthetic mock data.

Edit `.env` file in project root:

**Option 1: Mock Mode (Recommended for Testing - No API Key Needed)**
```bash
# Use synthetic transit data - no API key required
TRANSIT_MODE=mock
```

**Option 2: Live Mode (Requires OC Transpo Subscription Key)**
```bash
# Use real OC Transpo GTFS-RT feeds
TRANSIT_MODE=live
OCTRANSPO_SUBSCRIPTION_KEY=your_subscription_key_here
# OR use the alias:
OCTRANSPO_API_KEY=your_subscription_key_here
```

**Option 3: Auto-Detect (Default)**
```bash
# Don't set TRANSIT_MODE - it will auto-detect:
# - "live" if OCTRANSPO_SUBSCRIPTION_KEY or OCTRANSPO_API_KEY exists
# - "mock" if subscription key is missing
```

**Getting an OC Transpo Subscription Key (Only if you want live data):**
1. Visit: https://www.octranspo.com/en/plan-your-trip/travel-tools/developers/
2. Sign up for a developer account
3. Subscribe to the GTFS-RT product (Vehicle Positions and/or Trip Updates)
4. Copy your **Subscription Key** (OC Transpo uses Azure API Management)
5. Add to `.env`: 
   ```bash
   OCTRANSPO_SUBSCRIPTION_KEY=your_subscription_key_here
   # OR use the alias:
   OCTRANSPO_API_KEY=your_subscription_key_here
   ```

**Note:** OC Transpo uses Azure API Management, so you'll receive a **Subscription Key** (not a traditional API key). The client automatically uses the correct `Ocp-Apim-Subscription-Key` header.

**For testing/demos, mock mode is recommended** - it works immediately without any API setup!

---

## 🎮 Starting All Services

Open **separate terminal windows** for each service:

### Terminal 1: State Logger (Required)
```bash
cd agents
python state_logger.py
```

**Look for:**
```
Connected to MongoDB
Subscribed to: chronos.events.power.failure
Subscribed to: chronos.events.transit.vehicle.position
...
State Logger is running
```

### Terminal 2: Dashboard (Required)
```bash
cd dashboard
npm run dev
```

**Look for:**
```
▲ Next.js 14.x.x
- Local: http://localhost:3000
```

Open browser: **http://localhost:3000**

### Terminal 3: Crisis Generator (Power Domain)
```bash
cd agents
python crisis_generator.py
```

**Look for:**
```
Crisis Generator running...
Press 'f' to trigger a power failure manually
```

### Terminal 4: Coordinator Agent (Required)
```bash
cd agents
python coordinator_agent.py
```

**Look for:**
```
Coordinator Agent running...
Subscribed to: chronos.events.power.failure
Waiting for events...
```

### Terminal 5: Autonomy Router (Required)
```bash
cd agents
python autonomy_router.py
```

**Look for:**
```
Autonomy Router running...
Subscribed to operator.status and recovery.plan
```

### Terminal 6: Transit Ingestor (Transit Domain)
```bash
cd agents
python transit_ingestor.py
```

**Look for:**
```
Transit mode: mock  (or "live" if using real API)
Starting Transit Ingestor Service
Connected to message broker
Transit Ingestor Service started successfully
```

**Check:** You should see `"Transit mode: mock"` or `"Transit mode: live"` printed once at startup.

### Terminal 7: Transit Risk Agent (Transit Domain)
```bash
cd agents
python transit_risk_agent.py
```

**Look for:**
```
Starting Transit Risk Agent
Subscribed to: chronos.events.transit.vehicle.position
Subscribed to: chronos.events.transit.trip.update
Transit Risk Agent is running
```

### Terminal 8: Trajectory Insight Agent (Airspace Domain - Optional)
```bash
cd agents
python trajectory_insight_agent.py
```

**Look for:**
```
Trajectory Insight Agent running...
Waiting for flight.parsed events...
```

### Terminal 9: Stress Monitor (Optional)
```bash
cd agents
python stress_monitor.py
```

**Look for:**
```
Stress Monitor running...
Press 's' for HIGH stress, 'n' for NORMAL
```

---

## ✅ Testing Each Domain

### Test 1: Power Domain

1. **Trigger a power failure:**
   - In Terminal 3 (Crisis Generator), press `f`
   - You should see: `"Published power.failure event for sector X"`

2. **Check the dashboard:**
   - Go to http://localhost:3000
   - You should see:
     - New event in the timeline
     - Sector health card updates (voltage/load changes)
     - Recovery plan panel (if coordinator generated one)

3. **Check State Logger:**
   - In Terminal 1, you should see: `"Logged event: power.failure"`

4. **Check Coordinator:**
   - In Terminal 4, you should see: `"Received power.failure event"` and `"Published recovery.plan"`

**✅ Success Indicators:**
- Events appear in dashboard timeline
- Sector cards show status changes
- Recovery plans are generated
- No errors in any terminal

---

### Test 2: Transit Domain

1. **Verify Transit Ingestor is running:**
   - In Terminal 6, you should see every 10 seconds:
     ```
     Starting transit feed fetch cycle
     Fetched X vehicle positions
     Published X vehicle position events
     Fetched X trip updates
     Published X trip update events
     ```

2. **Check Transit Risk Agent:**
   - In Terminal 7, wait 30 seconds
   - You should see:
     ```
     Running transit risk analysis...
     Analysis complete: X delay clusters, X headway anomalies, X stationary vehicles, X hotspots
     ```

3. **Check Dashboard:**
   - Go to http://localhost:3000
   - Look for transit events in the timeline:
     - `transit.vehicle.position`
     - `transit.trip.update`
     - `transit.disruption.risk` (if risks detected)
     - `transit.hotspot` (if hotspots detected)

4. **Check Transit Mode Badge:**
   - In the dashboard navigation bar (top right)
   - If in mock mode, you should see: **"⚠️ Transit: MOCK"** badge
   - If in live mode, no badge appears

5. **Test Map with Transit Data:**
   - Go to http://localhost:3000/map
   - Set Source filter to "Transit"
   - You should see:
     - Red markers for stalled vehicles (if any)
     - Red circles for delay clusters/headway gaps (if any)

**✅ Success Indicators:**
- Transit events appear every 10 seconds
- Risk analysis runs every 30 seconds
- Events appear in dashboard
- Mock mode badge shows (if `TRANSIT_MODE=mock`)
- Map shows transit incidents/risks

---

### Test 3: Airspace Domain

1. **Upload a flight plan:**
   - Go to http://localhost:3000/airspace
   - Click "Upload Plan" tab
   - Upload `dashboard/test_flight_plan.json` (or create your own)
   - You should see: `"Plan uploaded successfully"`

2. **Check Trajectory Insight Agent:**
   - In Terminal 8, you should see:
     ```
     Received flight.parsed event
     Analyzing trajectories...
     Published conflict.detected events
     Published hotspot.detected events
     ```

3. **Check Dashboard:**
   - Go to http://localhost:3000/airspace
   - Click "Overview" tab - should show flight count, conflicts, hotspots
   - Click "Conflicts" tab - should list detected conflicts
   - Click "Hotspots" tab - should list detected hotspots

4. **Check Map:**
   - Go to http://localhost:3000/map
   - Set Source filter to "Flights"
   - You should see:
     - Flight trajectories (lines)
     - Conflict markers (red points)
     - Hotspot circles (red translucent)

**✅ Success Indicators:**
- Flight plan uploads successfully
- Conflicts and hotspots are detected
- Map shows flight trajectories and risks
- Events appear in timeline

---

### Test 4: Map Visualization

1. **Go to Map Page:**
   - Navigate to http://localhost:3000/map
   - You should see a 3D globe centered on Ottawa

2. **Test Filters:**
   - **Source Filter:** Try "All", "Flights", "Power", "Transit"
   - **Severity Filter:** Try "All", "Low", "Medium", "High", "Critical"
   - **Time Range:** Try "1h", "6h", "24h"
   - Events should filter accordingly

3. **Test Transit Stops (if GTFS loaded):**
   - Check "Show Transit Stops" checkbox
   - Zoom in (camera height < 50km)
   - You should see cyan markers with stop names
   - If not zoomed in, checkbox shows "(zoom in)" hint

4. **Test Controls:**
   - Click "Reset View" - should re-center on Ottawa
   - Pan and zoom - events should update dynamically

**✅ Success Indicators:**
- Map loads without errors
- Filters work correctly
- Events render as markers/circles
- Transit stops appear when zoomed in (if GTFS loaded)

---

## 🔍 Verification Checklist

### Infrastructure
- [ ] MongoDB is running (`docker-compose ps` shows "Up")
- [ ] NATS is running (`docker-compose ps` shows "Up")
- [ ] No connection errors in any terminal

### Services
- [ ] State Logger connected to MongoDB
- [ ] Dashboard accessible at http://localhost:3000
- [ ] All agents show "running" or "connected" messages
- [ ] Transit Ingestor shows "Transit mode: mock/live"

### Power Domain
- [ ] Crisis Generator publishes events
- [ ] Events appear in dashboard timeline
- [ ] Sector health cards update
- [ ] Recovery plans are generated

### Transit Domain
- [ ] Transit Ingestor publishes events every 10 seconds
- [ ] Transit Risk Agent analyzes every 30 seconds
- [ ] Transit events appear in dashboard
- [ ] Mock mode badge shows (if applicable)
- [ ] Map shows transit incidents/risks

### Airspace Domain
- [ ] Flight plan uploads successfully
- [ ] Conflicts and hotspots are detected
- [ ] Map shows trajectories and risks

### Map
- [ ] Map loads without errors
- [ ] Filters work correctly
- [ ] Events render properly
- [ ] Transit stops appear when zoomed in (if GTFS loaded)

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to MongoDB"

**Solution:**
```bash
cd infra
docker-compose restart mongodb
docker-compose logs mongodb
```

**Check:** Make sure Docker Desktop is running.

### Problem: "Cannot connect to NATS"

**Solution:**
```bash
cd infra
docker-compose restart nats
docker-compose logs nats
```

### Problem: "Transit mode not showing correctly"

**Solution:**
1. Check `.env` file has `TRANSIT_MODE=mock` or `TRANSIT_MODE=live`
2. Restart Transit Ingestor (Terminal 6)
3. Check startup message shows correct mode

### Problem: "No transit events appearing"

**Solution:**
1. Check Transit Ingestor is running (Terminal 6)
2. Check it shows "Transit mode: mock/live"
3. Wait 10 seconds - events publish every 10 seconds
4. Check State Logger is running (Terminal 1)

### Problem: "Map not loading"

**Solution:**
1. Check browser console for errors
2. Verify Cesium assets are in `dashboard/public/cesium/`
3. Check `NEXT_PUBLIC_CESIUM_ION_TOKEN` if using terrain (optional)

### Problem: "Transit stops not showing"

**Solution:**
1. Make sure GTFS data is loaded:
   ```bash
   python -m transit_octranspo.static_gtfs /path/to/gtfs.zip
   ```
2. Check "Show Transit Stops" is checked
3. Zoom in (camera height < 50km)
4. Check API: http://localhost:3000/api/transit-stops?zoom=15

---

## 🎯 Quick Test Script

Run this to test core functionality:

```bash
# From project root
python scripts/smoke_test.py
```

This will test:
- Message broker connection
- LLM planner
- Sentry integration
- Solana audit logger
- ElevenLabs voice output

---

## 📊 Expected Event Flow

### Power Domain Flow:
1. `crisis_generator.py` → publishes `power.failure`
2. `state_logger.py` → logs to MongoDB
3. `coordinator_agent.py` → receives, generates `recovery.plan`
4. `autonomy_router.py` → receives, publishes `audit.decision` or `approval.required`
5. Dashboard → displays all events

### Transit Domain Flow:
1. `transit_ingestor.py` → publishes `transit.vehicle.position` and `transit.trip.update` every 10s
2. `state_logger.py` → logs to MongoDB
3. `transit_risk_agent.py` → analyzes, publishes `transit.disruption.risk` and `transit.hotspot` every 30s
4. Dashboard → displays events and shows on map

### Airspace Domain Flow:
1. User uploads flight plan → `flight_plan_ingestor.py` publishes `airspace.flight.parsed`
2. `trajectory_insight_agent.py` → analyzes, publishes `airspace.conflict.detected` and `airspace.hotspot.detected`
3. `coordinator_agent.py` → receives, generates `recovery.plan`
4. Dashboard → displays on airspace page and map

---

## 🎉 Success!

If all tests pass, you should see:
- ✅ Events flowing through the system
- ✅ Dashboard updating in real-time
- ✅ Map showing incidents and risks
- ✅ All services running without errors
- ✅ Transit mode badge showing (if mock mode)

**Congratulations! The system is working correctly!** 🚀

