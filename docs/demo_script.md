# Project Chronos - 2-Minute Demo Script

This script guides you through a complete demonstration of the Chronos digital twin crisis system.

## Prerequisites

- Docker Desktop running
- Python 3.10+ installed
- Node.js 18+ installed
- MongoDB, NATS, and services running

## Pre-Demo Setup (5 minutes)

### 1. Start Infrastructure Services

```bash
# Start MongoDB and NATS
cd infra
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Install Python Dependencies

```bash
# From project root
cd agents/shared
pip install -r requirements.txt

# Install AI service dependencies
cd ../../ai
pip install -r requirements.txt
```

### 3. Install Dashboard Dependencies

```bash
cd dashboard
npm install
```

### 4. Set Environment Variables

Create `.env` files as needed:

```bash
# For agents (optional - defaults work for local)
# No .env needed for basic demo

# For dashboard
cd dashboard
cp .env.example .env.local
# Edit .env.local with MongoDB connection if needed
```

## Demo Flow (2 Minutes)

### Terminal Setup

Open **4 terminal windows**:

- **Terminal 1**: Infrastructure & Services
- **Terminal 2**: Crisis Generator
- **Terminal 3**: Stress Monitor
- **Terminal 4**: Dashboard

---

### Step 1: Start Core Services (30 seconds)

**Terminal 1** - Start all agent services:

```bash
# Start state logger (logs events to MongoDB)
python agents/state_logger.py

# In a new tab/window, start autonomy router
python agents/autonomy_router.py

# In another tab/window, start Solana audit logger (optional)
python agents/solana_audit_logger.py
```

**Terminal 4** - Start dashboard:

```bash
cd dashboard
npm run dev
```

**Wait for**: Dashboard to load at http://localhost:3000

**Check**: All services show "Connected to message broker" messages

---

### Step 2: Trigger Power Failure (10 seconds)

**Terminal 2** - Start crisis generator:

```bash
python agents/crisis_generator.py
```

**Action**: Wait 5 seconds for automatic failure, OR press **'f'** to force immediate failure

**Expected Output**:
```
POWER FAILURE EVENT
Event ID: 550e8400-...
Severity: error
Sector: sector-2
Details:
  Voltage: 23.45V
  Load: 67.89%
```

**Dashboard Check**: Open http://localhost:3000 - you should see the power failure event appear

---

### Step 3: Show Gemini Recovery Plan (15 seconds)

**Terminal 2** - Keep crisis generator running

**Action**: The system will automatically generate a recovery plan (if GEMINI_API_KEY is set) or use fallback plan

**To show Gemini integration** (optional):
```bash
# Set Gemini API key
export GEMINI_API_KEY=your_api_key_here

# Restart any service that uses Gemini (recovery plans are auto-generated)
```

**Expected**: Recovery plan event published with:
- Plan ID (e.g., RP-2024-001)
- Recovery steps
- Estimated completion time
- Assigned agents

**Dashboard Check**: Refresh http://localhost:3000 - recovery plan should appear in event feed

---

### Step 4: Toggle Stress to HIGH (10 seconds)

**Terminal 3** - Start stress monitor:

```bash
python agents/stress_monitor.py
```

**Action**: Press **'s'** to set stress HIGH

**Expected Output**:
```
>>> Stress level set to HIGH <<<
OPERATOR STATUS EVENT
Autonomy Level: HIGH
```

**Dashboard Check**: 
- http://localhost:3000 - Autonomy badge should show "🔴 HIGH AUTONOMY"
- Event feed should show operator status event

---

### Step 5: Show Autonomy Takeover (20 seconds)

**Terminal 3** - Keep stress monitor running (stress should be HIGH)

**Action**: Wait for next recovery plan or trigger another failure in Terminal 2 (press 'f')

**Expected Behavior**:
- With HIGH autonomy: System automatically executes actions
- Look for `audit.decision` event with `decision_type: "automated"`
- Look for `system.action` event showing execution

**Terminal 1** - Check autonomy router output:
```
AUTONOMY LEVEL UPDATE
Autonomy Level: NORMAL → HIGH

RECOVERY PLAN RECEIVED
Publishing audit.decision event (HIGH autonomy)
Publishing system.action event
```

**Dashboard Check**: 
- http://localhost:3000/audit - Should show automated decisions
- Event feed should show both audit.decision and system.action events

---

### Step 6: Show Audit Hash + Solana (15 seconds)

**Terminal 1** - Check Solana audit logger output:

**Expected Output** (demo mode):
```
[SOLANA] would log hash: a1b2c3d4e5f6...
[SOLANA] Decision ID: DEC-2024-001
[SOLANA] Action: execute_recovery_plan_RP-2024-001
```

**For Real Solana Integration** (optional):
```bash
export SOLANA_RPC_URL=https://api.devnet.solana.com
export SOLANA_PRIVATE_KEY=your_private_key_here

# Restart Solana audit logger
python agents/solana_audit_logger.py
```

**Dashboard Check**: 
- http://localhost:3000/audit
- Each audit decision shows:
  - Decision details
  - Computed SHA-256 hash
  - "[SOLANA] would log hash: ..." message

**Optional**: Click Solana hash to view on Solana Explorer (if using real Solana)

---

### Step 7: Show Dashboard Updating Live (20 seconds)

**Dashboard**: Open http://localhost:3000 in browser

**Navigate through pages**:

1. **Event Feed** (`/`):
   - Shows last 50 events
   - Auto-refreshes every 5 seconds
   - Autonomy badge in header
   - Events appear in real-time

2. **Sector Map** (`/map`):
   - 3x1 grid of sectors
   - Color-coded by status:
     - 🟢 Green = Normal
     - 🟡 Yellow = Warning
     - 🟠 Orange = Error
     - 🔴 Red = Critical
   - Auto-refreshes every 5 seconds

3. **Audit Page** (`/audit`):
   - List of all audit decisions
   - Shows decision type, maker, action
   - Displays computed Solana hash
   - Auto-refreshes every 10 seconds

**Action**: 
- Trigger more failures in Terminal 2 (press 'f')
- Toggle stress in Terminal 3 (press 's' for HIGH, 'n' for NORMAL)
- Watch dashboard update in real-time

---

## Quick Demo Commands (All-in-One)

For a faster demo, run these in separate terminals:

```bash
# Terminal 1: Infrastructure
cd infra && docker-compose up -d

# Terminal 2: State Logger
python agents/state_logger.py

# Terminal 3: Autonomy Router
python agents/autonomy_router.py

# Terminal 4: Solana Audit Logger
python agents/solana_audit_logger.py

# Terminal 5: Crisis Generator
python agents/crisis_generator.py
# Press 'f' to trigger failures

# Terminal 6: Stress Monitor
python agents/stress_monitor.py
# Press 's' for HIGH, 'n' for NORMAL

# Terminal 7: Dashboard
cd dashboard && npm run dev
# Open http://localhost:3000
```

## Demo Highlights

1. **Event-Driven Architecture**: All services communicate via NATS
2. **AI-Powered Recovery**: Gemini generates recovery plans (or fallback)
3. **Adaptive Autonomy**: System adjusts based on operator stress
4. **Blockchain Audit Trail**: Solana hash for immutable logging
5. **Real-Time Dashboard**: Live updates across all views
6. **Fault Tolerance**: Services work even if integrations fail

## Troubleshooting

### Services won't connect to NATS
```bash
# Check NATS is running
docker ps | grep nats

# Check NATS logs
docker logs chronos-nats
```

### MongoDB connection errors
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Check MongoDB logs
docker logs chronos-mongodb
```

### Dashboard shows no events
- Ensure `state_logger.py` is running
- Check MongoDB connection in dashboard `.env.local`
- Verify events are being published (check crisis generator output)

### Autonomy not changing
- Ensure `stress_monitor.py` is running
- Press 's' to set HIGH (not just once, may need to press again)
- Check `autonomy_router.py` is receiving operator.status events

## Cleanup

After demo:

```bash
# Stop all Python services (Ctrl+C in each terminal)

# Stop infrastructure
cd infra
docker-compose down

# Optional: Clear MongoDB data
docker volume rm chronos-cloud_mongodb_data
```

## Next Steps

- Add more sectors
- Integrate real Solana mainnet
- Add voice commands
- Connect QNX systems
- Deploy to production

---

**Total Demo Time**: ~2 minutes (excluding setup)
**Key Message**: Autonomous crisis response system with blockchain audit trail

