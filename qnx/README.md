# QNX Services

QNX-based services and integrations for Project Chronos.

## Overview

This directory contains QNX-specific components that simulate real-time power grid monitoring systems running in a QNX environment.

## Components

### grid_sim.cpp

A C++ simulator that mimics a QNX-based power grid monitoring system. It emits newline-delimited JSON power events to stdout every 5 seconds.

**Features:**
- Deterministic event loop (logs "[QNX] deterministic loop")
- Emits events for 3 sectors (sector-1, sector-2, sector-3)
- Includes voltage, load, and timestamp
- Simulates both normal and failure scenarios

**Compilation:**
```bash
g++ -o grid_sim grid_sim.cpp -std=c++11
```

**Usage:**
```bash
./grid_sim
```

**Output Format:**
Each line is a JSON object:
```json
{"sector_id":"sector-1","voltage":125.50,"load":67.30,"timestamp":"2024-01-15T14:30:00.123Z","status":"normal"}
```

### qnx_event_source.py

Python service that reads QNX events from stdin and publishes them to the message broker (Solace or NATS).

**Location:** `agents/qnx_event_source.py`

**Features:**
- Reads newline-delimited JSON from stdin
- Converts QNX events to Chronos power.failure events
- Publishes to message broker
- Filters normal events (only publishes failures/warnings)

## Running in QNX VM

### Setup

1. **Compile the simulator in QNX:**
   ```bash
   # In QNX environment
   g++ -o grid_sim grid_sim.cpp -std=c++11
   ```

2. **Set up Python environment:**
   - Install Python 3.10+ in QNX or use a Python container
   - Install dependencies: `pip install -r agents/shared/requirements.txt`

3. **Configure message broker:**
   - Set Solace environment variables (if using Solace)
   - Or ensure NATS is accessible from QNX VM

### Execution

**Option 1: Direct Pipe (Recommended)**
```bash
# In QNX VM or container
./grid_sim | python agents/qnx_event_source.py
```

**Option 2: Named Pipe**
```bash
# Terminal 1: Run simulator
./grid_sim > /tmp/qnx_events.pipe

# Terminal 2: Run event source
python agents/qnx_event_source.py < /tmp/qnx_events.pipe
```

**Option 3: Network Stream (Advanced)**
```bash
# In QNX: Stream to network
./grid_sim | nc hostname 9999

# On host: Receive and process
nc -l 9999 | python agents/qnx_event_source.py
```

## Integration with Chronos

The QNX grid simulator integrates with Project Chronos as follows:

```
QNX VM/Container
    │
    ├─ grid_sim.cpp (C++)
    │     │
    │     └─> stdout (newline-delimited JSON)
    │           │
    │           └─> pipe
    │                 │
    └─> qnx_event_source.py (Python)
          │
          └─> Message Broker (Solace/NATS)
                │
                └─> Chronos Services
                      ├─> Crisis Generator
                      ├─> Recovery Planner
                      ├─> Autonomy Router
                      └─> Dashboard
```

## Event Flow

1. **QNX Grid Simulator** (`grid_sim.cpp`):
   - Runs deterministic loop every 5 seconds
   - Emits JSON events for each sector
   - Outputs to stdout

2. **QNX Event Source** (`qnx_event_source.py`):
   - Reads from stdin (piped from grid_sim)
   - Parses JSON events
   - Converts to Chronos power.failure event format
   - Publishes to message broker

3. **Chronos Services**:
   - Receive power.failure events
   - Generate recovery plans
   - Route based on autonomy level
   - Display in dashboard

## Environment Variables

For the event source service:

```bash
# Solace (if using)
SOLACE_HOST=xxx.messaging.solace.cloud
SOLACE_PORT=55555
SOLACE_VPN=default
SOLACE_USERNAME=your_username
SOLACE_PASSWORD=your_password

# NATS (if using)
NATS_HOST=localhost
NATS_PORT=4222
```

## Testing Locally (Without QNX VM)

You can test the integration without a QNX VM:

```bash
# Compile simulator (works on Linux/Mac, or use WSL on Windows)
g++ -o grid_sim qnx/grid_sim.cpp -std=c++11

# Run simulator and pipe to event source
./grid_sim | python agents/qnx_event_source.py
```

Or use a simple test:

```bash
# Generate test events
echo '{"sector_id":"sector-1","voltage":0,"load":100,"timestamp":"2024-01-15T12:00:00Z","status":"failure"}' | python agents/qnx_event_source.py
```

## Troubleshooting

**Events not appearing:**
- Check message broker connection
- Verify stdin is being read (check logs)
- Ensure JSON format is correct

**Connection issues:**
- Verify Solace/NATS is accessible from QNX environment
- Check firewall rules
- Verify environment variables are set

**Compilation errors:**
- Ensure C++11 support: `g++ --version`
- Check QNX development tools are installed

## Development

To modify the simulator:
1. Edit `grid_sim.cpp`
2. Recompile: `g++ -o grid_sim grid_sim.cpp -std=c++11`
3. Test: `./grid_sim | head -n 5` (should show 5 events)

To modify event processing:
1. Edit `agents/qnx_event_source.py`
2. Test with: `echo '{"sector_id":"sector-1","voltage":0,"load":100}' | python agents/qnx_event_source.py`
