# Map Loading Troubleshooting Guide

## Quick Checks

### 1. Check Browser Console for Errors

**Open Browser Console (F12) and look for:**
- `[Map] Map loaded successfully` - Map initialized correctly
- `[Map] Map style not loaded, waiting...` - Style loading issue
- `Error: Cannot read property 'Map' of undefined` - MapLibre not loaded
- `Failed to load resource: tile.openstreetmap.org` - Network/tile loading issue
- `TypeError: mapContainerRef.current is null` - Container not mounted

### 2. Check if Map Container Exists

**In Browser Console, run:**
```javascript
const container = document.querySelector('[class*="map"]');
console.log('Map container:', container ? 'Found' : 'Not found');
console.log('Container height:', container?.offsetHeight);
```

**Expected**: Container should have a height > 0

### 3. Check MapLibre CSS is Loaded

**In Browser Console, check:**
```javascript
const styles = Array.from(document.styleSheets).find(s => s.href?.includes('maplibre'));
console.log('MapLibre CSS:', styles ? 'Loaded' : 'Not loaded');
```

### 4. Check Network Tab

**Open Network Tab (F12 → Network) and check:**
- Are OpenStreetMap tiles loading? (Look for `tile.openstreetmap.org` requests)
- Are requests returning 200 OK or errors?
- Are there CORS errors?

### 5. Check API Endpoint

**Test the geo-events API:**
```bash
# In terminal
curl http://localhost:3000/api/geo-events?timeRange=24h&severity=all&source=all
```

**Or in browser:**
```
http://localhost:3000/api/geo-events?timeRange=24h&severity=all&source=all
```

**Expected**: Should return JSON with `incidents` and `riskAreas` arrays

## Common Issues and Fixes

### Issue 1: Map Container Has No Height

**Symptom**: Map shows "Loading Map..." but never loads

**Fix**: Check CSS height
```css
/* Ensure map container has height */
.map-container {
  height: 100%;
  min-height: 400px;
}
```

**Check**: In browser console, verify container height:
```javascript
const container = document.querySelector('[class*="map"]');
console.log('Height:', container?.offsetHeight);
```

### Issue 2: MapLibre Not Installed

**Symptom**: `Cannot read property 'Map' of undefined`

**Fix**: Install MapLibre
```bash
cd dashboard
npm install maplibre-gl
```

**Verify**: Check `package.json` has:
```json
"maplibre-gl": "^4.0.0"
```

### Issue 3: CSS Not Loading

**Symptom**: Map loads but looks broken, no tiles visible

**Fix**: Ensure CSS is imported
```typescript
import 'maplibre-gl/dist/maplibre-gl.css';
```

**Check**: In browser DevTools → Network, look for `maplibre-gl.css`

### Issue 4: OpenStreetMap Tiles Not Loading

**Symptom**: Map loads but shows gray/blank tiles

**Possible Causes:**
1. **Network/Firewall blocking**: OpenStreetMap tiles might be blocked
2. **CORS issues**: Check browser console for CORS errors
3. **Rate limiting**: Too many requests to OSM tiles

**Fix 1**: Check network connectivity
```bash
# Test if OpenStreetMap is accessible
curl https://tile.openstreetmap.org/0/0/0.png
```

**Fix 2**: Try alternative tile provider (if OSM is blocked)
- Update `tiles` array in map initialization
- Use a different tile server

**Fix 3**: Check browser console for specific errors

### Issue 5: API Endpoint Not Responding

**Symptom**: Map loads but no markers/events appear

**Check**: Test API endpoint
```bash
curl http://localhost:3000/api/geo-events
```

**Fix**: 
1. Check MongoDB is running: `docker ps | grep mongo`
2. Check state_logger is running
3. Check API route exists: `dashboard/pages/api/geo-events.ts`

### Issue 6: Map Stuck on "Loading Map..."

**Symptom**: Loading spinner never disappears

**Possible Causes:**
1. Map initialization error
2. Style not loading
3. Container not mounted

**Fix**: Check browser console for:
- `[Map] Map loaded successfully` - Should appear
- `[Map] Map style not loaded, waiting...` - Style loading issue
- Any JavaScript errors

**Debug**: Add console logs
```typescript
console.log('Container:', mapContainerRef.current);
console.log('Mounted:', mounted);
console.log('Map ref:', mapRef.current);
```

### Issue 7: Map Renders But No Events

**Symptom**: Map shows but no markers/incidents

**Check**:
1. Are events in MongoDB? Check with:
   ```bash
   python agents/query_events.py
   ```

2. Is API returning data?
   ```bash
   curl http://localhost:3000/api/geo-events
   ```

3. Check browser console for:
   - `[Map] Loaded X incidents, Y risk areas`
   - `[Map] Rendering X incidents`

**Fix**: 
- Ensure `state_logger.py` is running
- Ensure events are being published
- Check MongoDB connection

### Issue 8: SSR/Hydration Errors

**Symptom**: `hydration-error-info.js` errors in console

**Fix**: Map is already using dynamic import with `ssr: false`, but check:
```typescript
// In map.tsx
const OttawaMapClean = dynamic(
  () => import('../components/OttawaMapClean'),
  { ssr: false }
);
```

## Step-by-Step Debugging

### Step 1: Verify Dependencies

```bash
cd dashboard
npm list maplibre-gl
```

**Expected**: Should show `maplibre-gl@4.0.0` or similar

### Step 2: Check Map Component Renders

**In browser console:**
```javascript
// Check if map container exists
document.querySelector('[class*="map"]')
```

### Step 3: Check Map Initialization

**Look for in console:**
```
[Map] Map loaded successfully
[Map] Style data loaded
```

**If missing**: Map initialization failed

### Step 4: Check API Response

**In browser console:**
```javascript
fetch('/api/geo-events?timeRange=24h&severity=all&source=all')
  .then(r => r.json())
  .then(d => console.log('API Response:', d));
```

**Expected**: Should return `{ incidents: [...], riskAreas: [...] }`

### Step 5: Check Network Requests

**In Network tab:**
- Look for `tile.openstreetmap.org` requests
- Check if they return 200 OK
- Check if tiles are loading

## Quick Fixes

### Fix 1: Restart Dashboard

```bash
cd dashboard
# Stop current server (Ctrl+C)
npm run dev
```

### Fix 2: Clear Browser Cache

- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Or clear browser cache

### Fix 3: Check Container Height

**In browser console:**
```javascript
const container = document.querySelector('[class*="map"]');
if (container) {
  container.style.height = '600px'; // Force height
}
```

### Fix 4: Reinstall Dependencies

```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Expected Console Output

**When map loads correctly, you should see:**
```
[Map] Map loaded successfully
[Map] Style data loaded
[Map] API response: Object
[Map] Loaded X incidents, Y risk areas
[Map] Rendering X incidents
[Map] Adding X features to map
```

## Still Not Working?

1. **Check browser console** for specific error messages
2. **Check Network tab** for failed requests
3. **Check if MongoDB is running**: `docker ps | grep mongo`
4. **Check if state_logger is running**
5. **Try a different browser** (Chrome, Firefox, Edge)
6. **Check firewall/network** isn't blocking OpenStreetMap tiles

## Browser Compatibility

**Supported Browsers:**
- Chrome/Edge (recommended)
- Firefox
- Safari (may have issues)

**Not Supported:**
- Internet Explorer

---

**Last Updated**: 2026-01-17

