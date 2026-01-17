# Project Chronos - Complete Demo Script

This is a **beginner-friendly, step-by-step guide** to demonstrate the full Chronos digital twin crisis system.

**Estimated Time**: 10-15 minutes for complete demo

---

## 📋 Prerequisites Checklist

Before starting, make sure you have:

- [ ] Docker Desktop installed and running
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] All dependencies installed (see README.md)
- [ ] Infrastructure services running (MongoDB, NATS)

---

## 🚀 Part 1: Initial Setup (5 minutes)

### Step 1: Start Infrastructure Services

Open a terminal and run:

```bash
# Navigate to infrastructure directory
cd infra

# Start MongoDB and NATS
docker-compose up -d

# Wait 10 seconds for services to start
# Then verify they're running
docker-compose ps
```

**Expected Output:**
```
NAME              STATUS          PORTS
chronos-mongodb   Up (healthy)    0.0.0.0:27017->27017/tcp
chronos-nats      Up              0.0.0.0:4222->4222/tcp
```

**If services aren't running:**
- Check Docker Desktop is running
- Check for port conflicts (27017, 4222)
- Run `docker-compose logs` to see errors

### Step 2: Set Up Environment Variables (Optional)

Create a `.env` file in the project root:

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

**Minimum required for demo:**
- No variables needed! System works with defaults.

**Optional (for enhanced features):**
- `GEMINI_API_KEY` - For AI recovery plans (Google Gemini)
- `LLM_SERVICE_API_KEY` - For AI recovery plans (Cerebras - free tier)
- `ELEVENLABS_API_KEY` - For voice announcements
- `SENTRY_DSN` - For error tracking

See README.md for how to get these API keys.

### Step 3: Start the Dashboard

Open a **new terminal** and run:

```bash
# Navigate to dashboard
cd dashboard

# Start the dashboard
npm run dev
```

**Expected Output:**
```
> dashboard@0.1.0 dev
> next dev

  ▲ Next.js 14.2.35
  - Local:        http://localhost:3000
  - ready started server on 0.0.0.0:3000
```

**Open your browser to:** http://localhost:3000

You should see the Chronos Control Center dashboard (may be empty until events are generated).

---

## 🎬 Part 2: Start Agent Services (5 minutes)

You need to open **separate terminal windows** for each service. Keep them all open!

### Terminal 1: State Logger

**Purpose**: Logs all events to MongoDB

```bash
# Navigate to agents directory
cd agents

# Run state logger
python state_logger.py
```

**Expected Output:**
```
Starting State Logger Service
============================================================
Connecting to MongoDB...
Connected to MongoDB
Subscribed to: chronos.events.power.failure
...
State Logger is running. Logging events to MongoDB...
```

**✅ Keep this terminal open!**

### Terminal 2: Crisis Generator

**Purpose**: Generates power failure events

```bash
# In agents directory
python crisis_generator.py
```

**Expected Output:**
```
Starting Crisis Generator Service
============================================================
Connecting to message broker...
Connected to message broker
Starting periodic event generator (interval: 5s)
Press 'f' - Force power failure
Press 'q' - Quit
```

**✅ Keep this terminal open!**

**You'll see events being generated every 5 seconds automatically.**

### Terminal 3: Coordinator Agent

**Purpose**: Coordinates framework comparisons

```bash
# In agents directory
python coordinator_agent.py
```

**Expected Output:**
```
Starting Coordinator Agent
============================================================
Initialized frameworks: ['RULES_ENGINE', 'SINGLE_LLM', 'AGENTIC_MESH']
Selected framework for execution: AGENTIC_MESH
Connecting to message broker...
Connected to message broker
Subscribed to: chronos.events.power.failure
Coordinator Agent is running. Waiting for events...
```

**✅ Keep this terminal open!**

### Terminal 4: Autonomy Router

**Purpose**: Routes decisions based on autonomy level

```bash
# In agents directory
python autonomy_router.py
```

**Expected Output:**
```
Starting Autonomy Router
============================================================
Current Autonomy: NORMAL
Subscribed Topics:
  - chronos.events.operator.status
  - chronos.events.recovery.plan
Autonomy Router is running. Waiting for events...
```

**✅ Keep this terminal open!**

### Terminal 5: Stress Monitor (Optional)

**Purpose**: Monitors operator stress and sets autonomy level

```bash
# In agents directory
python stress_monitor.py
```

**Expected Output:**
```
Starting Stress Monitor Service
Mode: demo
Press 's' - Set stress HIGH
Press 'n' - Set stress NORMAL
Current autonomy level: NORMAL
```

**✅ Keep this terminal open!**

### Terminal 6: Recovery Planner (Optional - Only if you have Gemini API key)

**Purpose**: Generates AI recovery plans using Gemini

```bash
# In agents directory (or ai directory)
python ai/recovery_planner.py
```

**Only run this if you set `GEMINI_API_KEY` in your `.env` file!**

**Expected Output:**
```
Starting Recovery Planner Service
Connecting to message broker...
Connected to message broker
Subscribed to: chronos.events.power.failure
Recovery Planner is running. Waiting for events...
```

**✅ Keep this terminal open!**

---

## 🎯 Part 3: Running the Demo (5 minutes)

### Demo Flow Overview

1. **Observe automatic events** (every 5 seconds)
2. **Trigger manual failure** (press 'f')
3. **Watch AI generate recovery plan** (if Gemini is set up)
4. **Toggle autonomy to HIGH** (press 's' in stress monitor)
5. **See autonomous execution** (autonomy router takes action)
6. **View dashboard updates** (real-time event feed)

### Step-by-Step Demo

#### Step 1: Observe Automatic Events

**What to do:**
- Look at the **Crisis Generator** terminal
- You'll see events being generated every 5 seconds
- Check the **Dashboard** (http://localhost:3000) - it should be updating

**What you'll see:**
- Power failure events for random sectors
- Events appearing in the dashboard timeline
- Sector health cards updating

**Expected:**
- Dashboard shows events in real-time
- Sector cards show voltage and load
- Timeline feed shows event icons

#### Step 2: Trigger Manual Power Failure

**What to do:**
1. Go to **Crisis Generator** terminal
2. Press `f` (lowercase) and press Enter

**Expected Output:**
```
>>> FORCING POWER FAILURE <<<
POWER FAILURE EVENT
Sector: sector-1
Severity: CRITICAL
Voltage: 0.0V
Load: 100.0%
Published to topic: chronos.events.power.failure
```

**What happens:**
- Event is published to message broker
- Coordinator agent receives it
- Frameworks generate recovery plans
- Dashboard updates immediately

**Check Dashboard:**
- New event appears in timeline
- Sector card turns red (CRITICAL)
- Recovery plan panel updates (if Gemini is set up)

#### Step 3: View Framework Comparison (If Coordinator is Running)

**What to do:**
1. Go to **Coordinator Agent** terminal
2. Look for comparison output

**Expected Output:**
```
POWER FAILURE DETECTED - DISPATCHING TO FRAMEWORKS
Event ID: xxx
Sector: sector-1
Frameworks: ['RULES_ENGINE', 'SINGLE_LLM', 'AGENTIC_MESH']

Framework RULES_ENGINE completed in 2.5ms
Framework SINGLE_LLM completed in 1234.5ms
Framework AGENTIC_MESH completed in 2345.6ms

COMPARISON SUMMARY
RULES_ENGINE: 2.5ms, 6 actions, confidence: 1.0
SINGLE_LLM: 1234.5ms, 5 actions, confidence: 0.8
AGENTIC_MESH: 2345.6ms, 7 actions, confidence: 0.9
Selected: AGENTIC_MESH
```

**Check Dashboard:**
- Go to **http://localhost:3000/compare**
- See side-by-side framework comparison
- Compare execution times, actions, confidence scores

#### Step 4: Toggle Autonomy to HIGH

**What to do:**
1. Go to **Stress Monitor** terminal
2. Press `s` (lowercase) and press Enter

**Expected Output:**
```
>>> Stress level set to HIGH <<<
OPERATOR STATUS EVENT
Autonomy Level: HIGH
Published to topic: chronos.events.operator.status
```

**What happens:**
- Autonomy level changes to HIGH
- Autonomy Router receives the update
- System can now execute actions autonomously

**Check Dashboard:**
- Autonomy badge changes from "NORMAL" to "HIGH AUTONOMY"
- Badge turns purple/red gradient

#### Step 5: See Autonomous Execution

**What to do:**
1. Trigger another power failure (press `f` in Crisis Generator)
2. Watch **Autonomy Router** terminal

**Expected Output:**
```
RECOVERY PLAN RECEIVED
Plan ID: RP-MESH-2024-XXXXX
Current Autonomy: HIGH

Publishing audit.decision event (HIGH autonomy)
Decision ID: DEC-2024-XXXXX
Action: execute_recovery_plan_XXX

Publishing system.action event
Action: execute_recovery_plan
```

**What happens:**
- Recovery plan is received
- Since autonomy is HIGH, system automatically executes
- Audit decision is published
- System action is published

**Check Dashboard:**
- Go to **http://localhost:3000/audit**
- See audit decisions with Solana hashes
- See system actions being executed

#### Step 6: View Recovery Plan (If Gemini is Set Up)

**What to do:**
1. Check **Recovery Planner** terminal (if running)
2. Look for Gemini plan generation

**Expected Output:**
```
POWER FAILURE EVENT RECEIVED
Sector: sector-1
Calling Gemini API to generate recovery plan...
Recovery plan generated:
Plan ID: RP-GEMINI-2024-XXXXX
Steps: [step1, step2, step3, ...]
Published to topic: chronos.events.recovery.plan
```

**Check Dashboard:**
- Main dashboard shows "Latest Recovery Plan" panel
- See plan steps and estimated completion
- View assigned agents

**Without Gemini:**
- System uses fallback recovery plans
- Still works, just not AI-generated

#### Step 7: View Event Timeline

**What to do:**
1. Go to **http://localhost:3000**
2. Scroll down to "Event Timeline"
3. Watch events appear in real-time

**What you'll see:**
- Color-coded event icons (⚡, 📋, 👤, etc.)
- Event summaries
- Relative timestamps ("5m ago")
- Status badges (CRITICAL, ERROR, WARNING, INFO)

#### Step 8: View Sector Map

**What to do:**
1. Go to **http://localhost:3000/map**
2. See sector health cards

**What you'll see:**
- Three sector cards (sector-1, sector-2, sector-3)
- Color-coded status (green/yellow/red)
- Voltage and load readings
- Real-time updates

---

## 🎤 Part 4: Advanced Features (Optional)

### Voice Announcements (If ElevenLabs is Set Up)

**What to do:**
1. Set `ELEVENLABS_API_KEY` in `.env`
2. Trigger a power failure
3. Listen for voice announcement

**Expected:**
- Audio plays: "Power failure detected in sector-1..."
- Or console output if API unavailable

### Framework Comparison

**What to do:**
1. Go to **http://localhost:3000/compare**
2. Select a comparison run
3. Compare framework results side-by-side

**What you'll see:**
- Execution times
- Number of actions
- Confidence scores
- Priority violations
- Plan summaries

### Audit Trail

**What to do:**
1. Go to **http://localhost:3000/audit**
2. View audit decisions
3. See Solana hashes (if Solana is configured)

**What you'll see:**
- All autonomous decisions
- Decision reasoning
- SHA-256 hashes
- Timestamps

---

## 🧹 Part 5: Cleanup

### Stop All Services

**Stop Python services:**
- Press `Ctrl+C` in each terminal window
- Or close the terminal windows

**Stop Dashboard:**
- Press `Ctrl+C` in dashboard terminal

**Stop Infrastructure:**
```bash
cd infra
docker-compose down
```

### Verify Cleanup

```bash
# Check no containers are running
docker ps

# Should show no chronos containers
```

---

## 📊 Demo Checklist

Use this checklist to ensure you've covered everything:

- [ ] Infrastructure services running (MongoDB, NATS)
- [ ] Dashboard accessible at http://localhost:3000
- [ ] State logger running and connected
- [ ] Crisis generator running and generating events
- [ ] Coordinator agent running and processing events
- [ ] Autonomy router running
- [ ] Stress monitor running
- [ ] Dashboard showing real-time events
- [ ] Manual failure triggered (pressed 'f')
- [ ] Autonomy toggled to HIGH (pressed 's')
- [ ] Autonomous execution observed
- [ ] Framework comparison viewed
- [ ] Recovery plan generated (if Gemini set up)
- [ ] Voice announcement heard (if ElevenLabs set up)

---

## 🐛 Troubleshooting During Demo

### Problem: Events not appearing in dashboard

**Solution:**
1. Check State Logger is running
2. Check MongoDB is running: `docker ps | grep mongo`
3. Refresh dashboard (F5)
4. Check browser console for errors (F12)

### Problem: No recovery plans generated

**Solution:**
1. Check if Recovery Planner is running
2. Check if Gemini API key is set
3. Check Recovery Planner terminal for errors
4. System will use fallback plans if Gemini unavailable

### Problem: Autonomy badge not updating

**Solution:**
1. Check Stress Monitor is running
2. Press 's' in Stress Monitor terminal
3. Wait 5-10 seconds for dashboard refresh
4. Manually refresh dashboard (F5)

### Problem: Coordinator agent not processing

**Solution:**
1. Check Coordinator Agent terminal for errors
2. Verify NATS is running: `docker ps | grep nats`
3. Check connection logs in terminal

---

## 🎓 What You've Learned

After completing this demo, you understand:

1. **Event-Driven Architecture**: How events flow through the system
2. **Service Communication**: How services communicate via message broker
3. **Autonomous Decision Making**: How the system makes decisions based on autonomy level
4. **Framework Comparison**: How different AI frameworks compare
5. **Real-Time Monitoring**: How the dashboard shows system state
6. **Fault Tolerance**: How the system handles failures gracefully

---

## 🚀 Next Steps

1. **Experiment with different scenarios**: Trigger multiple failures
2. **Try different autonomy modes**: Toggle between HIGH and NORMAL
3. **Compare frameworks**: See how different frameworks respond
4. **Explore the code**: Understand how each service works
5. **Add your own features**: Extend the system with new capabilities

---

## 📝 Demo Script Summary

**Quick Reference:**

1. Start infrastructure: `cd infra && docker-compose up -d`
2. Start dashboard: `cd dashboard && npm run dev`
3. Start agents: Run each in separate terminals
4. Trigger failure: Press `f` in crisis generator
5. Toggle autonomy: Press `s` in stress monitor
6. View dashboard: http://localhost:3000

**Happy demoing! 🎉**
