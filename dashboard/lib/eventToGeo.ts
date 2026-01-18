/**
 * Event to Geo Mapping Utilities
 * 
 * Converts various event types to geo.incident and geo.risk_area formats
 * for rendering on the Cesium 3D map.
 */

export type GeoIncident = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: string;
  summary: string;
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [lon, lat]
  };
  style: {
    color: string;
    opacity: number;
    outline: boolean;
  };
  incident_type?: string;
  description?: string;
  status?: string;
  source?: string; // 'flights' | 'power' | 'transit'
};

export type GeoRiskArea = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: string;
  summary: string;
  geometry: {
    type: 'Circle' | 'Polygon';
    coordinates: any;
    radius_meters?: number;
  };
  style: {
    color: string;
    opacity: number;
    outline: boolean;
  };
  risk_level?: string;
  risk_type?: string;
  description?: string;
  source?: string; // 'flights' | 'power' | 'transit'
};

/**
 * Convert transit.disruption.risk event to geo.risk_area or geo.incident
 * 
 * - stalled_vehicle -> geo.incident (Point)
 * - delay_cluster, headway_gap -> geo.risk_area (Circle)
 */
export function transitDisruptionRiskToGeo(event: any): GeoIncident | GeoRiskArea | null {
  const details = event.details || {};
  const location = details.location || {};
  const cause = details.cause || '';
  const riskScore = details.risk_score || details.confidence_score || 0.5;
  
  // Determine severity from risk score
  let severity = 'info';
  if (riskScore >= 0.8) {
    severity = 'critical';
  } else if (riskScore >= 0.6) {
    severity = 'moderate';  // Renamed from 'error' for clarity
  } else if (riskScore >= 0.4) {
    severity = 'warning';
  }
  
  // Stalled vehicle -> geo.incident (Point)
  if (cause === 'stalled_vehicle') {
    const lat = location.latitude;
    const lon = location.longitude;
    
    if (!lat || !lon) {
      return null; // Missing location data
    }
    
    return {
      event_id: event.event_id || event.id || '',
      id: details.risk_id || `transit-${cause}-${event.event_id?.slice(0, 8) || 'unknown'}`,
      timestamp: event.timestamp || new Date().toISOString(),
      severity: severity,
      summary: event.summary || details.description || `Stalled vehicle: ${cause}`,
      geometry: {
        type: 'Point',
        coordinates: [lon, lat],
      },
      style: {
        color: '#FF0000', // Red
        opacity: 0.9,
        outline: true,
      },
      incident_type: 'stalled_vehicle',
      description: details.description || `Vehicle stalled for extended period`,
      source: 'transit',
    };
  }
  
  // Delay cluster or headway gap -> geo.risk_area (Circle)
  if (cause === 'delay_cluster' || cause === 'headway_gap') {
    const lat = location.latitude || location.center_lat || location.location_lat;
    const lon = location.longitude || location.center_lon || location.location_lon;
    const radiusMeters = location.radius_meters || 2000; // Default 2km
    
    if (!lat || !lon) {
      return null; // Missing location data
    }
    
    return {
      event_id: event.event_id || event.id || '',
      id: details.risk_id || `transit-${cause}-${event.event_id?.slice(0, 8) || 'unknown'}`,
      timestamp: event.timestamp || new Date().toISOString(),
      severity: severity,
      summary: event.summary || details.description || `Transit disruption: ${cause}`,
      geometry: {
        type: 'Circle',
        coordinates: [lon, lat],
        radius_meters: radiusMeters,
      },
      style: {
        color: '#FF0000', // Red
        opacity: 0.35, // Translucent
        outline: true,
      },
      risk_level: details.severity_level || 'medium',
      risk_type: cause,
      description: details.description || `Transit disruption risk: ${cause}`,
      source: 'transit',
    };
  }
  
  return null; // Unknown cause type
}

/**
 * Convert existing geo.incident event (add source if missing)
 */
export function enhanceGeoIncident(incident: any, source?: string): GeoIncident {
  return {
    ...incident,
    source: incident.source || source || 'unknown',
  };
}

/**
 * Convert existing geo.risk_area event (add source if missing)
 */
export function enhanceGeoRiskArea(riskArea: any, source?: string): GeoRiskArea {
  return {
    ...riskArea,
    source: riskArea.source || source || 'unknown',
  };
}

