/**
 * Extract ping location from any event, with fallbacks for events without geometry.
 */

// Ottawa coordinates
const OTTAWA_CENTER_LAT = 45.4215;
const OTTAWA_CENTER_LON = -75.6972;
const OTTAWA_AIRPORT_LAT = 45.322;
const OTTAWA_AIRPORT_LON = -75.669;

export type PingLocation = {
  lon: number;
  lat: number;
  source: 'geometry' | 'details' | 'topic_mapping' | 'default';
};

/**
 * Extract ping location from an event with various fallback strategies.
 */
export function eventToPingLocation(event: any): PingLocation {
  // Strategy 1: Use geometry if available
  if (event.geometry) {
    if (event.geometry.type === 'Point' && event.geometry.coordinates) {
      const [lon, lat] = event.geometry.coordinates;
      return { lon, lat, source: 'geometry' };
    }
    if (event.geometry.type === 'Circle' && event.geometry.coordinates) {
      const [lon, lat] = event.geometry.coordinates;
      return { lon, lat, source: 'geometry' };
    }
    if (event.geometry.type === 'Polygon' && event.geometry.coordinates?.[0]?.[0]) {
      const [lon, lat] = event.geometry.coordinates[0][0];
      return { lon, lat, source: 'geometry' };
    }
  }

  // Strategy 2: Extract from details object
  if (event.details) {
    // Check for lat/lon in details
    if (typeof event.details.latitude === 'number' && typeof event.details.longitude === 'number') {
      return { lon: event.details.longitude, lat: event.details.latitude, source: 'details' };
    }
    
    // Check for location object in details
    if (event.details.location) {
      if (typeof event.details.location.latitude === 'number' && typeof event.details.location.longitude === 'number') {
        return { lon: event.details.location.longitude, lat: event.details.location.latitude, source: 'details' };
      }
      if (typeof event.details.location.lat === 'number' && typeof event.details.location.lon === 'number') {
        return { lon: event.details.location.lon, lat: event.details.location.lat, source: 'details' };
      }
    }

    // Check for vehicle position in transit events
    if (event.details.position && typeof event.details.position.latitude === 'number' && typeof event.details.position.longitude === 'number') {
      return { lon: event.details.position.longitude, lat: event.details.position.latitude, source: 'details' };
    }
  }

  // Strategy 3: Map by topic prefix
  const topic = event.topic || '';
  if (topic.startsWith('power.') || topic.includes('power')) {
    // Power events -> Ottawa center (hydro corridor area)
    return { lon: OTTAWA_CENTER_LON, lat: OTTAWA_CENTER_LAT, source: 'topic_mapping' };
  }
  
  if (topic.startsWith('transit.') || topic.includes('transit')) {
    // Transit events -> Ottawa center (unless vehicle position provided above)
    return { lon: OTTAWA_CENTER_LON, lat: OTTAWA_CENTER_LAT, source: 'topic_mapping' };
  }
  
  if (topic.startsWith('airspace.') || topic.includes('airspace')) {
    // Airspace events -> Ottawa airport (YOW)
    return { lon: OTTAWA_AIRPORT_LON, lat: OTTAWA_AIRPORT_LAT, source: 'topic_mapping' };
  }
  
  
  // Strategy 4: Default to Ottawa center
  return { lon: OTTAWA_CENTER_LON, lat: OTTAWA_CENTER_LAT, source: 'default' };
}

