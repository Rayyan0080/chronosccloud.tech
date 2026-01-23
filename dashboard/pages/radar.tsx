'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import RadarView, { RadarObject, RadarObjectType } from '../components/RadarView';
import DroppedPinPanel from '../components/DroppedPinPanel';
import { geoToRadar, OTTAWA_RADAR_CENTER, DEFAULT_RADAR_RANGE_KM, haversineDistance } from '../lib/radarUtils';

type Event = {
  event_id: string;
  timestamp: string;
  topic: string;
  severity?: string;
  summary?: string;
  geometry?: any;
  details?: any;
  source?: string;
  payload?: any; // For nested payload access
};

export default function Radar() {
  const [objects, setObjects] = useState<RadarObject[]>([]);
  const [sseConnected, setSseConnected] = useState(false);
  const [selectedObject, setSelectedObject] = useState<RadarObject | null>(null);
  const [showAircraft, setShowAircraft] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showThreats, setShowThreats] = useState(true);
  const [showRisks, setShowRisks] = useState(true);
  const [defenseMode, setDefenseMode] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [radarRange, setRadarRange] = useState(DEFAULT_RADAR_RANGE_KM);
  const [eventStats, setEventStats] = useState<{ [key: string]: number }>({});
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [updateCount, setUpdateCount] = useState(0);
  const [mounted, setMounted] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const objectsMapRef = useRef<Map<string, RadarObject>>(new Map());
  const cleanupIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Convert event to RadarObject
  const eventToRadarObject = useCallback((event: Event): RadarObject | null => {
    let lat: number | undefined;
    let lon: number | undefined;
    let type: RadarObjectType | null = null;
    let id: string;
    let callsign: string | undefined;
    let vehicle_id: string | undefined;
    let threat_id: string | undefined;

    // Extract coordinates based on topic
    if (event.topic === 'chronos.events.airspace.aircraft.position' || 
        event.topic?.includes('aircraft.position')) {
      type = 'aircraft';
      const details = event.details || event.payload?.details || {};
      lat = details.latitude || details.lat;
      lon = details.longitude || details.lon;
      id = details.icao24 || details.callsign || event.event_id;
      callsign = details.callsign;
      vehicle_id = details.icao24 || details.callsign;
    } else if (event.topic === 'chronos.events.geo.incident' ||
               event.topic?.includes('geo.incident')) {
      type = 'incident';
      if (event.geometry?.type === 'Point' && event.geometry.coordinates) {
        [lon, lat] = event.geometry.coordinates;
      } else if (event.details?.geometry?.type === 'Point' && event.details.geometry.coordinates) {
        [lon, lat] = event.details.geometry.coordinates;
      } else if (event.details?.location) {
        lat = event.details.location.latitude || event.details.location.lat;
        lon = event.details.location.longitude || event.details.location.lon;
      }
      id = event.event_id || `incident-${Date.now()}`;
    } else if (event.topic === 'chronos.events.geo.risk_area' ||
               event.topic?.includes('geo.risk_area') ||
               event.topic?.includes('transit.disruption.risk') ||
               event.topic?.includes('transit.hotspot')) {
      type = 'risk';
      // Try multiple locations for transit events
      const details = event.details || event.payload?.details || {};
      const payload = event.payload || {};
      
      // Check geometry first
      if (event.geometry?.type === 'Circle' && event.geometry.coordinates) {
        [lon, lat] = event.geometry.coordinates;
      } else if (event.geometry?.type === 'Point' && event.geometry.coordinates) {
        [lon, lat] = event.geometry.coordinates;
      } else if (event.geometry?.type === 'Polygon' && event.geometry.coordinates?.[0]?.[0]) {
        [lon, lat] = event.geometry.coordinates[0][0];
      } 
      // Check payload geometry
      else if (payload.geometry?.type === 'Circle' && payload.geometry.coordinates) {
        [lon, lat] = payload.geometry.coordinates;
      } else if (payload.geometry?.type === 'Point' && payload.geometry.coordinates) {
        [lon, lat] = payload.geometry.coordinates;
      }
      // Check details geometry
      else if (details.geometry) {
        const geom = details.geometry;
        if (geom.type === 'Circle' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        } else if (geom.type === 'Point' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        } else if (geom.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
          [lon, lat] = geom.coordinates[0][0];
        }
      }
      // Check location object (for transit events)
      else if (details.location) {
        lat = details.location.latitude || details.location.lat;
        lon = details.location.longitude || details.location.lon;
      }
      // Check position object (for transit vehicle positions)
      else if (details.position) {
        lat = details.position.latitude || details.position.lat;
        lon = details.position.longitude || details.position.lon;
      }
      // Use event_id, payload event_id, or generate unique ID with timestamp + random
      id = event.event_id || event.payload?.event_id || `risk-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    } else if (event.topic?.includes('defense.threat') || 
               event.topic?.includes('defense.action')) {
      // All defense events (threat.detected, threat.assessed, threat.escalated, threat.resolved, action.deployed)
      type = 'threat';
      const details = event.details || event.payload?.details || {};
      threat_id = details.threat_id || event.payload?.correlation_id || event.correlation_id;
      
      // Try to extract location from affected_area or geometry
      if (details.affected_area) {
        const area = details.affected_area;
        if (area.type === 'Point' && area.coordinates) {
          [lon, lat] = area.coordinates;
        } else if (area.type === 'Polygon' && area.coordinates?.[0]?.[0]) {
          [lon, lat] = area.coordinates[0][0];
        } else if (area.type === 'Circle' && area.coordinates) {
          [lon, lat] = area.coordinates;
        }
      } else if (event.geometry) {
        const geom = event.geometry;
        if (geom.type === 'Point' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        } else if (geom.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
          [lon, lat] = geom.coordinates[0][0];
        } else if (geom.type === 'Circle' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        }
      } else if (event.payload?.geometry) {
        const geom = event.payload.geometry;
        if (geom.type === 'Point' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        } else if (geom.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
          [lon, lat] = geom.coordinates[0][0];
        } else if (geom.type === 'Circle' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        }
      } else if (details.geometry) {
        const geom = details.geometry;
        if (geom.type === 'Point' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        } else if (geom.type === 'Polygon' && geom.coordinates?.[0]?.[0]) {
          [lon, lat] = geom.coordinates[0][0];
        } else if (geom.type === 'Circle' && geom.coordinates) {
          [lon, lat] = geom.coordinates;
        }
      }
      id = threat_id || event.event_id || event.payload?.event_id || `defense-${Date.now()}`;
    } else if (event.topic?.includes('transit.vehicle.position')) {
      // Transit vehicle positions - treat as incidents for now
      type = 'incident';
      const details = event.details || event.payload?.details || {};
      const position = details.position || {};
      lat = position.latitude || position.lat;
      lon = position.longitude || position.lon;
      id = details.vehicle_id || event.event_id || `transit-${Date.now()}`;
    } else {
      // Unknown event type - log for debugging (but skip if in defense mode to reduce noise)
      if (!defenseMode) {
        console.log('[Radar] Unknown event type:', event.topic, event);
      }
      return null;
    }
    
    // In defense mode, only show defense-related events
    if (defenseMode && type !== 'threat') {
      return null;
    }

    if (lat === undefined || lon === undefined || isNaN(lat) || isNaN(lon)) {
      console.log('[Radar] Event rejected - missing/invalid coordinates:', {
        topic: event.topic,
        lat,
        lon,
        hasGeometry: !!event.geometry,
        hasDetails: !!event.details,
      });
      return null;
    }

    // Convert to radar coordinates
    const radarCoords = geoToRadar(
      OTTAWA_RADAR_CENTER,
      { lat, lon },
      radarRange
    );

    if (!radarCoords) {
      console.log('[Radar] Event rejected - out of range:', {
        topic: event.topic,
        lat,
        lon,
        distance: haversineDistance(OTTAWA_RADAR_CENTER.lat, OTTAWA_RADAR_CENTER.lon, lat, lon),
        maxRange: radarRange,
      });
      return null; // Out of range
    }

    // Extract movement data for aircraft and vehicles
    const details = event.details || event.payload?.details || {};
    const velocity = details.velocity || details.speed; // m/s
    const heading = details.heading || details.bearing; // degrees
    
    return {
      id,
      type: type!,
      x: radarCoords.x,
      y: radarCoords.y,
      distance: radarCoords.distance,
      bearing: radarCoords.bearing,
      lat, // Store original coordinates
      lon, // Store original coordinates
      timestamp: event.timestamp || new Date().toISOString(),
      severity: event.severity || 'info',
      summary: event.summary || `${type} event`,
      source: event.source,
      details: event.details,
      callsign,
      vehicle_id,
      threat_id,
      eventData: event, // Store original event for DroppedPinPanel
      velocity: velocity, // For movement interpolation
      heading: heading, // For movement interpolation
    };
  }, [radarRange, defenseMode]);

  // Process new event
  const processEvent = useCallback((event: Event) => {
    // Update event stats
    const topic = event.topic || 'unknown';
    setEventStats(prev => ({
      ...prev,
      [topic]: (prev[topic] || 0) + 1,
    }));

    const obj = eventToRadarObject(event);
    if (!obj) {
      // Log why object wasn't created (for debugging) - but only for relevant topics
      if (event.topic && (
        event.topic.includes('airspace') || 
        event.topic.includes('geo') || 
        event.topic.includes('defense') ||
        event.topic.includes('transit')
      )) {
        console.log('[Radar] Event rejected - missing coordinates:', {
          topic: event.topic,
          hasGeometry: !!event.geometry,
          hasDetails: !!event.details,
          hasPayload: !!event.payload,
          geometry: event.geometry,
          details: event.details,
        });
      }
      return;
    }

    // Log successful object creation
    console.log('[Radar] New radar object:', obj.type, obj.id, 'at', obj.distance.toFixed(1), 'km', 'bearing', obj.bearing.toFixed(1) + '°');

    // Deduplicate based on type
    // For risk areas, use event_id to avoid duplicates, but allow multiple risk areas
    let dedupKey: string;
    if (obj.type === 'aircraft') {
      dedupKey = `aircraft-${obj.vehicle_id || obj.callsign || obj.id}`;
    } else if (obj.type === 'threat') {
      // For defense events, include event type in dedup key to show multiple states (detected, assessed, resolved, etc.)
      const eventType = obj.eventData?.topic?.split('.').pop() || 'threat';
      dedupKey = `threat-${obj.threat_id || obj.id}-${eventType}`;
    } else if (obj.type === 'risk') {
      // For risk areas, use a combination of coordinates and event_id to allow multiple nearby risk areas
      // but deduplicate the same event_id
      const coordKey = `${obj.lat.toFixed(4)}-${obj.lon.toFixed(4)}`;
      dedupKey = `risk-${obj.id}-${coordKey}`;
    } else {
      dedupKey = `${obj.type}-${obj.id}`;
    }

    // Update or add object
    const wasNew = !objectsMapRef.current.has(dedupKey);
    objectsMapRef.current.set(dedupKey, obj);

    // Limit to last 300 objects
    if (objectsMapRef.current.size > 300) {
      const entries = Array.from(objectsMapRef.current.entries());
      entries.sort((a, b) => 
        new Date(b[1].timestamp).getTime() - new Date(a[1].timestamp).getTime()
      );
      const toKeep = entries.slice(0, 300);
      objectsMapRef.current.clear();
      toKeep.forEach(([key, val]) => objectsMapRef.current.set(key, val));
    }

    // Force immediate state update to trigger re-render (real-time)
    const newObjects = Array.from(objectsMapRef.current.values());
    setObjects(newObjects);
    setLastUpdateTime(new Date());
    setUpdateCount(prev => prev + 1);
  }, [eventToRadarObject]);

  // Cleanup expired objects
  const cleanupExpired = useCallback(() => {
    const now = Date.now();
    const expired: string[] = [];

    objectsMapRef.current.forEach((obj, key) => {
      const age = now - new Date(obj.timestamp).getTime();
      let maxAge: number;

      switch (obj.type) {
        case 'aircraft':
          maxAge = 2 * 60 * 1000; // 2 minutes
          break;
        case 'incident':
          maxAge = 30 * 60 * 1000; // 30 minutes
          break;
        case 'threat':
          maxAge = 60 * 60 * 1000; // 60 minutes
          break;
        case 'risk':
          maxAge = 30 * 60 * 1000; // 30 minutes
          break;
        default:
          maxAge = 30 * 60 * 1000;
      }

      if (age > maxAge) {
        expired.push(key);
      }
    });

    expired.forEach((key) => objectsMapRef.current.delete(key));
    
    if (expired.length > 0) {
      setObjects(Array.from(objectsMapRef.current.values()));
    }
  }, []);

  // Set mounted flag to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  // Connect to SSE stream
  useEffect(() => {
    const connectSSE = () => {
      try {
        const since = new Date(Date.now() - 5 * 60 * 1000); // Last 5 minutes
        const eventSource = new EventSource(`/api/events/stream?since=${since.toISOString()}`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('[Radar] SSE connection opened - Real-time updates active');
          setSseConnected(true);
        };

        eventSource.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            
            if (data.type === 'connected') {
              console.log('[Radar] SSE connected');
              return;
            }
            
            if (data.type === 'heartbeat') {
              // Silently ignore heartbeats
              return;
            }

            if (data.type === 'error') {
              console.error('[Radar] SSE error:', data.message);
              return;
            }

            // Normalize event format (handle both direct events and payload-wrapped events)
            const normalizedEvent: Event = {
              event_id: data.event_id || data.payload?.event_id || data._id || '',
              timestamp: data.timestamp || data.payload?.timestamp || new Date().toISOString(),
              topic: data.topic || '',
              severity: data.severity || data.payload?.severity,
              summary: data.summary || data.payload?.summary,
              geometry: data.geometry || data.payload?.geometry,
              details: data.details || data.payload?.details,
              source: data.source || data.payload?.source,
              payload: data.payload, // Keep original payload for nested access
            };

            // Log incoming events for debugging (only for relevant events to reduce noise)
            if (normalizedEvent.topic && (
              normalizedEvent.topic.includes('defense') || 
              normalizedEvent.topic.includes('geo') ||
              normalizedEvent.topic.includes('airspace') ||
              normalizedEvent.topic.includes('transit')
            )) {
              console.log('[Radar] Real-time event:', {
                topic: normalizedEvent.topic,
                event_id: normalizedEvent.event_id,
                hasGeometry: !!normalizedEvent.geometry,
                hasDetails: !!normalizedEvent.details,
              });
            }

            // Process event immediately for real-time updates
            processEvent(normalizedEvent);
          } catch (err) {
            console.error('[Radar] Error parsing SSE message:', err, e.data);
          }
        };

        eventSource.onerror = (err) => {
          console.error('[Radar] SSE error:', err);
          setSseConnected(false);
          eventSource.close();
          
          // Reconnect quickly for real-time updates (1 second)
          setTimeout(connectSSE, 1000);
        };
      } catch (err) {
        console.error('[Radar] Error connecting to SSE:', err);
        setSseConnected(false);
      }
    };

    connectSSE();

    // Cleanup expired objects every 10 seconds
    cleanupIntervalRef.current = setInterval(cleanupExpired, 10000);

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (cleanupIntervalRef.current) {
        clearInterval(cleanupIntervalRef.current);
      }
    };
  }, [processEvent, cleanupExpired]);

  // Handle object click
  const handleObjectClick = useCallback((obj: RadarObject) => {
    setSelectedObject(obj);
  }, []);

  // Convert RadarObject to GeoIncident for DroppedPinPanel
  const radarObjectToGeoIncident = (obj: RadarObject) => {
    return {
      event_id: obj.id,
      id: obj.id,
      timestamp: obj.timestamp,
      severity: (obj.severity || 'info') as any,
      summary: obj.summary,
      geometry: {
        type: 'Point' as const,
        coordinates: [obj.lon, obj.lat] as [number, number],
      },
      source: obj.source,
      details: obj.details,
      incident_type: obj.type,
    };
  };

  return (
    <div className="min-h-screen bg-dark-bg">
      <div className="mb-1">
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-3xl font-bold text-white">
            {defenseMode ? '🛡️ Defense Radar - Ottawa' : 'Radar'}
          </h1>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
              <span className="text-xs text-dark-muted">
                {sseConnected ? '🔄 Real-time' : 'Connecting...'}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-dark-muted">
              <div>
                Objects: {objects.length} ({objects.filter(o => o.type === 'aircraft').length} aircraft, {objects.filter(o => o.type === 'incident').length} incidents, {objects.filter(o => o.type === 'threat').length} threats, {objects.filter(o => o.type === 'risk').length} risks)
              </div>
              <div className="flex items-center gap-1">
                <div className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`}></div>
                <span>Updates: {updateCount}</span>
              </div>
              {mounted && lastUpdateTime && (
                <div className="text-gray-500">
                  Last: {lastUpdateTime.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Event Stats (for debugging) */}
        {Object.keys(eventStats).length > 0 && (
          <div className="bg-dark-surface rounded-lg p-1 mb-1 border border-dark-border">
            <div className="text-xs text-dark-muted mb-2">Event Topics Received:</div>
            <div className="flex flex-wrap gap-2 text-xs">
              {Object.entries(eventStats)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([topic, count]) => (
                  <span key={topic} className="px-2 py-1 bg-gray-800 rounded text-gray-300">
                    {topic.split('.').pop()}: {count}
                  </span>
                ))}
            </div>
          </div>
        )}

        {/* Safety message */}
        <div className="bg-dark-surface border border-yellow-500 border-opacity-30 rounded-lg px-2 py-0.5 mb-1">
          <p className="text-xs text-yellow-300">
            ⚠️ Situational awareness radar (informational only).
          </p>
        </div>

        {/* Filters */}
        <div className="bg-dark-surface rounded-lg p-1.5 mb-1 border border-dark-border">
          <div className="flex flex-wrap items-center gap-4">
            {/* Defense Mode Toggle */}
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={defenseMode}
                  onChange={(e) => {
                    setDefenseMode(e.target.checked);
                    // When enabling defense mode, hide other types
                    if (e.target.checked) {
                      setShowAircraft(false);
                      setShowIncidents(false);
                      setShowRisks(false);
                      setShowThreats(true);
                    }
                  }}
                  className="w-4 h-4"
                />
                <span className="text-red-400 font-semibold">🛡️ Defense Mode (Ottawa Only)</span>
              </label>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-sm text-dark-muted">Show:</span>
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={showAircraft}
                  onChange={(e) => setShowAircraft(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-green-400">Aircraft</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={showIncidents}
                  onChange={(e) => setShowIncidents(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-orange-400">Incidents</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={showThreats}
                  onChange={(e) => setShowThreats(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-red-400">Threats</span>
              </label>
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={showRisks}
                  onChange={(e) => setShowRisks(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-yellow-400">Risks</span>
              </label>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-dark-muted">Range:</span>
              <select
                value={radarRange}
                onChange={(e) => setRadarRange(Number(e.target.value))}
                className="bg-dark-surface border border-dark-border rounded px-2 py-1 text-white text-sm"
              >
                <option value={30}>30 km</option>
                <option value={60}>60 km</option>
                <option value={100}>100 km</option>
              </select>
            </div>

            <button
              onClick={() => {
                // Reset filters to defaults
                setDefenseMode(false);
                setShowAircraft(true);
                setShowIncidents(true);
                setShowThreats(true);
                setShowRisks(true);
                setSeverityFilter([]);
                setRadarRange(DEFAULT_RADAR_RANGE_KM);
                setSelectedObject(null);
              }}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
            >
              Reset Filters
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-dark-surface rounded-lg p-1 mb-1 border border-dark-border">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-dark-muted">Aircraft</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span className="text-dark-muted">Incident</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-dark-muted">Threat (pulsing)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span className="text-dark-muted">Risk Area</span>
            </div>
          </div>
        </div>
      </div>

      {/* Radar View */}
      <div className="bg-dark-surface rounded-lg p-0 border border-dark-border" style={{ minHeight: 'calc(100vh - 150px)', height: 'calc(100vh - 150px)' }}>
        <div className="w-full h-full flex items-center justify-center">
          <RadarView
            objects={objects}
            showAircraft={showAircraft}
            showIncidents={showIncidents}
            showThreats={showThreats}
            showRisks={showRisks}
            severityFilter={severityFilter}
            onObjectClick={handleObjectClick}
          />
        </div>
      </div>

      {/* DroppedPinPanel */}
      {selectedObject && (
        <DroppedPinPanel
          incident={radarObjectToGeoIncident(selectedObject)}
          onClose={() => setSelectedObject(null)}
          onFocus={() => {
            // Focus is handled by DroppedPinPanel
          }}
        />
      )}
    </div>
  );
}


