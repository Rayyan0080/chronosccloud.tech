# Test Flight Plan Files

Two test flight plan JSON files are provided for testing the Airspace dashboard:

## Files

### 1. `test_flight_plan_simple.json`
**Purpose**: Quick test with 3 flights
- Simple routes
- All valid data
- Good for basic functionality testing

### 2. `test_flight_plan.json`
**Purpose**: Comprehensive test with 10 flights
- Multiple overlapping routes (will generate conflicts)
- Multiple flights from same origin (will generate hotspots)
- **Includes violations**:
  - `VIOL808`: Low altitude (8,500 ft) - below minimum
  - `SPEED909`: High speed (650 knots) - above maximum
  - `HIGH1010`: High altitude (52,000 ft) - above maximum
- Good for testing all dashboard features

## How to Use

1. **Start the system**:
   ```bash
   # Terminal 1: Start infrastructure
   cd infra
   docker-compose up -d
   
   # Terminal 2: Start trajectory insight agent
   cd ..
   python agents/trajectory_insight_agent.py
   
   # Terminal 3: Start coordinator agent (if needed)
   python agents/coordinator_agent.py
   
   # Terminal 4: Start dashboard
   cd dashboard
   npm run dev
   ```

2. **Upload via Dashboard**:
   - Navigate to http://localhost:3000/airspace
   - Click on "Upload Plan" tab
   - Click "Select JSON File"
   - Choose either test file
   - Click "Upload Plan"

3. **View Results**:
   - **Overview**: See counts and risk scores
   - **Map**: View trajectories (placeholder visualization)
   - **Conflicts**: See detected conflicts with solutions
   - **Hotspots**: See congestion hotspots with mitigations
   - **Validation**: See altitude/speed violations with fixes

## Expected Results

### With `test_flight_plan.json`:
- **10 flights** uploaded
- **Multiple conflicts** (flights sharing waypoints at similar times)
- **Hotspots** (multiple flights from KJFK)
- **3 violations**:
  - Altitude violation (too low: 8,500 ft)
  - Speed violation (too high: 650 knots)
  - Altitude violation (too high: 52,000 ft)

### With `test_flight_plan_simple.json`:
- **3 flights** uploaded
- **Fewer conflicts** (simpler routes)
- **No violations** (all within valid ranges)

## File Format

Each flight must include:
- `ACID`: Aircraft callsign (string)
- `Plane type`: Aircraft model (string)
- `route`: Array of waypoint codes (minimum 2)
- `altitude`: Cruising altitude in feet (0-50,000)
- `departure airport`: Origin airport code (string)
- `arrival airport`: Destination airport code (string)
- `departure time`: ISO 8601 timestamp (string)
- `aircraft speed`: Speed in knots (0-1,000)
- `passengers`: Number of passengers (integer, >= 0)
- `is_cargo`: Boolean flag

## Notes

- All data is **SYNTHETIC** and for demonstration only
- The system will generate a `plan_id` after upload
- Events are published to MongoDB and visible in the dashboard
- Filter by `plan_id` to see events for a specific plan

