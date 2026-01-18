# Airspace Map is Empty - Solution

## Problem
The Airspace map is showing empty because there are no airspace events in the database.

## Solution: Upload a Flight Plan

The map needs flight plan data to display. Here's how to populate it:

### Option 1: Upload via Dashboard (Recommended)

1. **Go to the Airspace Management page** in the dashboard
2. **Click the "Upload Plan" tab**
3. **Select a test flight plan file:**
   - `dashboard/test_flight_plan_simple.json`
   - `dashboard/test_flight_plan.json`
   - `dashboard/test_flight_plan_3d_map.json`
4. **Click "Upload Flight Plan"**
5. **Wait a few seconds** for processing
6. **Switch to the "Map" tab** to see the results

### Option 2: Use the Populate Script

Run the populate script:
```bash
python scripts/populate_airspace_map.py
```

This will:
- Create an Ottawa-area test flight plan if needed
- Process it through the flight_plan_ingestor
- Check if events were created

### Option 3: Start Required Agents

For the map to show conflicts and hotspots, you need:

1. **Flight Plan Ingestor** (processes uploads):
   ```bash
   python agents/flight_plan_ingestor.py <path_to_flight_plan.json>
   ```

2. **Trajectory Insight Agent** (detects conflicts/hotspots):
   ```bash
   python agents/trajectory_insight_agent.py
   ```

3. **State Logger** (stores events in MongoDB):
   ```bash
   python agents/state_logger.py
   ```

## What the Map Shows

Once data is loaded, the map will display:
- **Purple airplane icons**: Flight trajectories
- **Red markers**: Conflicts between flights
- **Red circles/polygons**: Risk areas and hotspots
- **Color-coded by severity**: High/Critical (red), Medium (orange), Low (yellow)

## Quick Test

1. Open dashboard: http://localhost:3000/airspace
2. Go to "Upload Plan" tab
3. Upload `dashboard/test_flight_plan_simple.json`
4. Wait 5-10 seconds
5. Go to "Map" tab
6. You should see flight trajectories and conflicts!

## Troubleshooting

**If the map is still empty after uploading:**

1. Check browser console for errors (F12)
2. Verify agents are running:
   ```bash
   # Check if trajectory_insight_agent is running
   python agents/trajectory_insight_agent.py
   ```
3. Check database for events:
   ```bash
   python -c "from pymongo import MongoClient; client = MongoClient('mongodb://chronos:chronos@localhost:27017/chronos?authSource=admin'); db = client.chronos; print('Airspace events:', db.events.count_documents({'topic': {'$regex': 'airspace'}}))"
   ```
4. Make sure the map source filter is set to "Airspace" (should be default on the Airspace page)

