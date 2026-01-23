/**
 * Radar coordinate conversion utilities
 * Converts lat/lon to local radar coordinates (x, y in kilometers)
 */

// Ottawa downtown coordinates (radar center)
export const OTTAWA_RADAR_CENTER = {
  lat: 45.4215,
  lon: -75.6972,
};

// Default radar range in kilometers
export const DEFAULT_RADAR_RANGE_KM = 60;

/**
 * Calculate haversine distance between two points in kilometers
 */
export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);
  
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Calculate bearing from point 1 to point 2 in degrees (0° = North, clockwise)
 */
export function bearing(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const dLon = toRadians(lon2 - lon1);
  const lat1Rad = toRadians(lat1);
  const lat2Rad = toRadians(lat2);
  
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x =
    Math.cos(lat1Rad) * Math.sin(lat2Rad) -
    Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  
  let bearing = Math.atan2(y, x);
  bearing = toDegrees(bearing);
  bearing = (bearing + 360) % 360; // Normalize to 0-360
  
  return bearing;
}

/**
 * Convert geographic coordinates to radar screen coordinates
 * @param center - Radar center {lat, lon}
 * @param point - Point to convert {lat, lon}
 * @param maxKm - Maximum range in kilometers
 * @returns {x, y} in kilometers from center, distance in km, bearing in degrees, or null if out of range
 */
export function geoToRadar(
  center: { lat: number; lon: number },
  point: { lat: number; lon: number },
  maxKm: number = DEFAULT_RADAR_RANGE_KM
): { x: number; y: number; distance: number; bearing: number } | null {
  const dist = haversineDistance(center.lat, center.lon, point.lat, point.lon);
  
  // Filter out points beyond range
  if (dist > maxKm) {
    return null;
  }
  
  const bear = bearing(center.lat, center.lon, point.lat, point.lon);
  
  // Convert polar coordinates (distance, bearing) to Cartesian (x, y)
  // x = distance * sin(bearing), y = distance * cos(bearing)
  // Note: In radar, y is typically "up" (North), x is "right" (East)
  // Bearing is 0° at North, increasing clockwise
  const bearingRad = toRadians(bear);
  const x = dist * Math.sin(bearingRad); // East (right)
  const y = dist * Math.cos(bearingRad); // North (up)
  
  return { x, y, distance: dist, bearing: bear };
}

/**
 * Convert radar screen coordinates (x, y in km) to canvas pixel coordinates
 * @param x - X coordinate in kilometers (East)
 * @param y - Y coordinate in kilometers (North)
 * @param canvasWidth - Canvas width in pixels
 * @param canvasHeight - Canvas height in pixels
 * @param maxKm - Maximum range in kilometers
 * @returns {canvasX, canvasY} in pixels
 */
export function radarToCanvas(
  x: number,
  y: number,
  canvasWidth: number,
  canvasHeight: number,
  maxKm: number = DEFAULT_RADAR_RANGE_KM
): { canvasX: number; canvasY: number } {
  // Canvas center
  const centerX = canvasWidth / 2;
  const centerY = canvasHeight / 2;
  
  // Scale factor: pixels per kilometer
  const scale = Math.min(canvasWidth, canvasHeight) / (2 * maxKm);
  
  // Convert to canvas coordinates (y is inverted in canvas: top is 0)
  const canvasX = centerX + x * scale;
  const canvasY = centerY - y * scale; // Invert y axis
  
  return { canvasX, canvasY };
}

/**
 * Helper: Convert degrees to radians
 */
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Helper: Convert radians to degrees
 */
function toDegrees(radians: number): number {
  return radians * (180 / Math.PI);
}

