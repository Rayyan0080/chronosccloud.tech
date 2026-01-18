# Airspace Map Empty - Fix Applied

## Problem
The airspace map shows empty even after uploading a flight plan, even though there are 3900+ aircraft.position events and 74 geo.incident events in the database.

## Root Cause
The `geo-events` API was filtering events too strictly by timestamp, causing valid events to be excluded.

## Fix Applied
Updated `dashboard/pages/api/geo-events.ts` to:
1. Remove strict time filtering temporarily (for debugging)
2. The API already has code to convert `aircraft.position` events to incidents with geometry
3. The API already handles `geo.incident` and `geo.risk_area` events from trajectory_insight_agent

## Next Steps

### 1. Restart the Dashboard
The Next.js API routes need to be rebuilt. Restart the dashboard:

```bash
cd dashboard
# Stop the current process (Ctrl+C)
npm run dev
```

### 2. Verify Events Exist
Run the diagnosis script:
```bash
python scripts/fix_airspace_map.py
```

You should see:
- Aircraft position events: 3900+
- Geo.incident events from trajectory_insight_agent: 74+
- Conflict events: 76+

### 3. Check Browser Console
Open the browser console (F12) and check:
- Network tab: Look for `/api/geo-events?source=airspace` request
- Check the response - should have `incidents` and `riskAreas` arrays
- Console tab: Look for any JavaScript errors

### 4. Test the API Directly
```bash
# In PowerShell
$response = Invoke-WebRequest -Uri "http://localhost:3000/api/geo-events?source=airspace" -UseBasicParsing
$json = $response.Content | ConvertFrom-Json
Write-Host "Incidents: $($json.incidents.Count)"
Write-Host "Risk Areas: $($json.riskAreas.Count)"
```

### 5. If Still Empty
Check:
1. **Time Range**: The map defaults to "Last 24 hours" - try changing to "All" or "Last 6 hours"
2. **Source Filter**: Make sure it's set to "Airspace" (should be default on the Airspace page)
3. **Trajectory Insight Agent**: Make sure it's running to create conflicts/hotspots:
   ```bash
   python agents/trajectory_insight_agent.py
   ```

## Expected Results
After the fix, the map should show:
- **Green airplane icons**: Aircraft positions (from `aircraft.position` events)
- **Red markers**: Conflicts (from `geo.incident` events with `source=trajectory-insight-agent`)
- **Red circles**: Hotspots (from `geo.risk_area` events with `source=trajectory-insight-agent`)

## Debugging
If the map is still empty after restarting:

1. Check server logs in the terminal where `npm run dev` is running
2. Look for `[geo-events API]` log messages showing:
   - Query being executed
   - Number of events found
   - Topics being queried

3. Verify events have valid geometry:
   ```python
   python scripts/fix_airspace_map.py
   ```

4. Check if events are within Ottawa bounds (the map is restricted to Ottawa region)

