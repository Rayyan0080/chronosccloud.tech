'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import DroppedPinPanel from './DroppedPinPanel';
import { eventToPingLocation } from '../lib/eventToPingLocation';

// Ottawa coordinates and bounds
const OTTAWA_LAT = 45.4215;
const OTTAWA_LON = -75.6972;
const OTTAWA_ZOOM = 10;

// Ottawa bounding box
const OTTAWA_BOUNDS: [[number, number], [number, number]] = [
  [-76.35, 44.95], // [west, south]
  [-75.00, 45.65], // [east, north]
];
const OTTAWA_MIN_ZOOM = 9;
const OTTAWA_MAX_ZOOM = 16;

type GeoIncident = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: 'low' | 'med' | 'high' | 'critical' | 'moderate' | 'error' | 'warning' | 'info';  // 'error' kept for backward compatibility
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
  source?: string;
  details?: any;
};

type GeoRiskArea = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: 'low' | 'med' | 'high' | 'critical' | 'moderate' | 'error' | 'warning' | 'info';  // 'error' kept for backward compatibility
  summary: string;
  geometry: {
    type: 'Circle' | 'Polygon';
    coordinates: [number, number] | number[][]; // Circle: [lon, lat], Polygon: [[lon, lat], ...]
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
  source?: string;
  details?: any;
};

type SelectedIncident = GeoIncident | null;

export default function OttawaMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mounted, setMounted] = useState(false);
  const [incidents, setIncidents] = useState<GeoIncident[]>([]);
  const [riskAreas, setRiskAreas] = useState<GeoRiskArea[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<SelectedIncident>(null);
  
  // Filters
  const [timeRange, setTimeRange] = useState<'15m' | '1h' | '6h' | '24h'>('1h');
  const [severity, setSeverity] = useState<'all' | 'low' | 'med' | 'high' | 'critical'>('all');
  const [source, setSource] = useState<'all' | 'transit' | 'traffic' | 'airspace' | 'power'>('all');
  
  // Real-time event streaming
  const [eventCount, setEventCount] = useState(0);
  const [pingEnabled, setPingEnabled] = useState(true);
  const [pingOnlyMedPlus, setPingOnlyMedPlus] = useState(false);
  const [sseConnected, setSseConnected] = useState(false);
  const [showPingLog, setShowPingLog] = useState(false);
  const [pingLog, setPingLog] = useState<Array<{ topic: string; lon: number; lat: number; timestamp: string; source: string }>>([]);
  const pingMarkersRef = useRef<Map<string, maplibregl.Marker>>(new Map());
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Ensure client-side only
  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch geo events from API
  useEffect(() => {
    if (!mounted) return;

    const fetchGeoEvents = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          timeRange,
          severity: severity !== 'all' ? severity : '',
          source: source !== 'all' ? source : 'all',
        });
        const res = await fetch(`/api/geo-events?${params}`);
        const data = await res.json();
        setIncidents(data.incidents || []);
        setRiskAreas(data.riskAreas || []);
      } catch (error) {
        console.error('Error fetching geo events:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchGeoEvents();
    // Fallback polling (only if SSE fails)
    if (!sseConnected) {
      pollingIntervalRef.current = setInterval(fetchGeoEvents, 30000);
    }
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [mounted, timeRange, severity, source, sseConnected]);

  // Initialize MapLibre map
  useEffect(() => {
    if (!mounted || !mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'osm-tiles-layer',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [OTTAWA_LON, OTTAWA_LAT],
      zoom: OTTAWA_ZOOM,
      minZoom: OTTAWA_MIN_ZOOM,
      maxZoom: OTTAWA_MAX_ZOOM,
      maxBounds: OTTAWA_BOUNDS,
      pitch: 0, // Disable pitch
      bearing: 0, // Disable rotation
      dragRotate: false, // Disable drag rotation
      touchPitch: false, // Disable touch pitch
      touchZoomRotate: {
        around: 'center',
      },
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Function to check if center is within bounds and recenter if needed
    const checkBoundsAndRecenter = () => {
      const center = map.getCenter();
      const [west, south] = OTTAWA_BOUNDS[0];
      const [east, north] = OTTAWA_BOUNDS[1];
      
      if (center.lng < west || center.lng > east || center.lat < south || center.lat > north) {
        // Center is outside bounds, smoothly fly back to Ottawa
        map.flyTo({
          center: [OTTAWA_LON, OTTAWA_LAT],
          zoom: OTTAWA_ZOOM,
          duration: 1000,
        });
      }
    };

    // Listen to dragend and zoomend to enforce bounds
    map.on('dragend', checkBoundsAndRecenter);
    map.on('zoomend', checkBoundsAndRecenter);

    // Add reset Ottawa view button
    const resetBtn = document.createElement('button');
    resetBtn.className = 'maplibregl-ctrl-icon maplibregl-ctrl-reset';
    resetBtn.innerHTML = '⌂';
    resetBtn.title = 'Reset Ottawa View';
    resetBtn.onclick = () => {
      map.flyTo({
        center: [OTTAWA_LON, OTTAWA_LAT],
        zoom: OTTAWA_ZOOM,
        duration: 1000,
      });
      setSelectedIncident(null);
    };
    const resetControl = document.createElement('div');
    resetControl.className = 'maplibregl-ctrl maplibregl-ctrl-group';
    resetControl.appendChild(resetBtn);
    map.addControl({ onAdd: () => resetControl, onRemove: () => {} } as any, 'top-right');

    mapRef.current = map;

    // Handle map clicks (deselect) - will be handled separately for incidents layer

    return () => {
      map.off('dragend', checkBoundsAndRecenter);
      map.off('zoomend', checkBoundsAndRecenter);
      map.remove();
      mapRef.current = null;
    };
  }, [mounted]);

  // Render risk areas (polygons/circles) - must be below markers
  useEffect(() => {
    if (!mapRef.current || !mounted) return;

    const map = mapRef.current;
    
    // Wait for map style to be loaded before adding sources
    const addRiskAreas = () => {
      if (!map.isStyleLoaded()) {
        map.once('load', addRiskAreas);
        return;
      }

      // Remove existing risk area layers
      if (map.getLayer('risk-areas-fill')) map.removeLayer('risk-areas-fill');
      if (map.getLayer('risk-areas-outline')) map.removeLayer('risk-areas-outline');
      if (map.getSource('risk-areas')) map.removeSource('risk-areas');

      if (riskAreas.length === 0) return;

      // Convert risk areas to GeoJSON
      const features: GeoJSON.Feature[] = riskAreas.map((area) => {
      const { geometry } = area;
      let coordinates: number[][];

      if (geometry.type === 'Circle') {
        const [lon, lat] = geometry.coordinates as [number, number];
        const radius = geometry.radius_meters || 1000;
        // Create circle approximation (64 points)
        coordinates = [];
        for (let i = 0; i < 64; i++) {
          const angle = (i / 64) * 2 * Math.PI;
          const dx = (radius / 111320) * Math.cos(angle); // Approximate meters to degrees
          const dy = (radius / 111320) * Math.sin(angle) / Math.cos(lat * Math.PI / 180);
          coordinates.push([lon + dx, lat + dy]);
        }
        coordinates.push(coordinates[0]); // Close the polygon
      } else {
        // Polygon
        coordinates = geometry.coordinates as number[][];
      }

      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [coordinates],
        },
        properties: {
          id: area.id,
          event_id: area.event_id,
          severity: area.severity,
          summary: area.summary,
          risk_type: area.risk_type,
          source: area.source,
          opacity: area.style.opacity || 0.3,
        },
      };
    });

      map.addSource('risk-areas', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features,
        },
      });

      // Add fill layer
      map.addLayer({
        id: 'risk-areas-fill',
        type: 'fill',
        source: 'risk-areas',
        paint: {
          'fill-color': '#ef4444', // red-500
          'fill-opacity': ['get', 'opacity'],
        },
      });

      // Add outline layer
      map.addLayer({
        id: 'risk-areas-outline',
        type: 'line',
        source: 'risk-areas',
        paint: {
          'line-color': '#dc2626', // red-600
          'line-width': 2,
          'line-opacity': 0.8,
        },
      });
    };

    addRiskAreas();
  }, [riskAreas, mounted]);

  // Render incident markers
  useEffect(() => {
    if (!mapRef.current || !mounted) return;

    const map = mapRef.current;
    
    // Wait for map style to be loaded before adding sources
    const addIncidents = () => {
      if (!map.isStyleLoaded()) {
        map.once('load', addIncidents);
        return;
      }

      // Remove existing incident layers
      if (map.getLayer('incidents-layer')) map.removeLayer('incidents-layer');
      if (map.getSource('incidents')) map.removeSource('incidents');

      if (incidents.length === 0) return;

      // Convert incidents to GeoJSON
      const features: GeoJSON.Feature[] = incidents.map((incident) => {
      const [lon, lat] = incident.geometry.coordinates;
      
      // Determine color by severity
      let color = '#eab308'; // yellow (low)
      if (incident.severity === 'high' || incident.severity === 'critical' || incident.severity === 'moderate' || incident.severity === 'error') {
        color = '#ef4444'; // red
      } else if (incident.severity === 'med' || incident.severity === 'warning') {
        color = '#f97316'; // orange
      }

      return {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [lon, lat],
        },
        properties: {
          id: incident.id,
          event_id: incident.event_id,
          severity: incident.severity,
          summary: incident.summary,
          incident_type: incident.incident_type,
          description: incident.description,
          source: incident.source,
          timestamp: incident.timestamp,
          color,
          details: incident.details,
        },
      };
    });

      map.addSource('incidents', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features,
        },
      });

      // Add circle markers
      map.addLayer({
        id: 'incidents-layer',
        type: 'circle',
        source: 'incidents',
        paint: {
          'circle-radius': [
            'case',
            ['==', ['get', 'id'], selectedIncident?.id || ''],
            12, // Selected marker is larger
            8,  // Default size
          ],
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
          'circle-opacity': 0.9,
        },
      });

      // Handle marker clicks
      map.on('click', 'incidents-layer', (e) => {
      if (e.features && e.features.length > 0) {
        const feature = e.features[0];
        const incident = incidents.find((inc) => inc.id === feature.properties?.id);
        if (incident) {
          setSelectedIncident(incident);
          // Center map on selected incident
          map.flyTo({
            center: [incident.geometry.coordinates[0], incident.geometry.coordinates[1]],
            zoom: Math.max(map.getZoom(), 14),
            duration: 500,
          });
        }
      }
    });

      // Change cursor on hover
      map.on('mouseenter', 'incidents-layer', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'incidents-layer', () => {
        map.getCanvas().style.cursor = '';
      });

      // Handle map clicks (deselect when clicking empty area)
      const handleMapClick = (e: maplibregl.MapMouseEvent) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ['incidents-layer'],
        });
        if (features.length === 0) {
          setSelectedIncident(null);
        }
      };
      map.on('click', handleMapClick);
    };

    addIncidents();

    // Cleanup
    return () => {
      if (mapRef.current) {
        const map = mapRef.current;
        // Remove layers to clean up event listeners
        try {
          if (map.getLayer('incidents-layer')) {
            map.removeLayer('incidents-layer');
          }
          if (map.getSource('incidents')) {
            map.removeSource('incidents');
          }
        } catch (e) {
          // Layers may already be removed
        }
      }
    };
  }, [incidents, mounted, selectedIncident]);

  // Update selected marker highlight
  useEffect(() => {
    if (!mapRef.current || !selectedIncident) return;

    const map = mapRef.current;
    
    // Force layer repaint to update circle size
    if (map.getLayer('incidents-layer')) {
      map.setPaintProperty('incidents-layer', 'circle-radius', [
        'case',
        ['==', ['get', 'id'], selectedIncident.id],
        12,
        8,
      ]);
    }
  }, [selectedIncident]);

  // SSE connection for real-time events
  useEffect(() => {
    if (!mounted || !mapRef.current) return;

    const connectSSE = () => {
      try {
        const since = new Date(Date.now() - 5 * 60 * 1000).toISOString();
        const eventSource = new EventSource(`/api/events/stream?since=${since}`);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setSseConnected(true);
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'connected' || data.type === 'heartbeat') {
              return; // Ignore connection/heartbeat messages
            }

            if (data.type === 'error') {
              console.error('SSE error:', data.message);
              eventSource.close();
              setSseConnected(false);
              // Fallback to polling
              pollingIntervalRef.current = setInterval(() => {
                fetch(`/api/geo-events?timeRange=1h&severity=&source=all`)
                  .then(res => res.json())
                  .then(data => {
                    setIncidents(data.incidents || []);
                    setRiskAreas(data.riskAreas || []);
                  })
                  .catch(err => console.error('Polling error:', err));
              }, 30000);
              return;
            }

            // Increment event counter
            setEventCount(prev => prev + 1);

            // Check if we should ping
            const shouldPing = pingEnabled && (
              !pingOnlyMedPlus || 
              ['med', 'high', 'critical', 'moderate', 'error', 'warning'].includes(data.severity?.toLowerCase() || '')
            );

            if (shouldPing && mapRef.current) {
              const pingLocation = eventToPingLocation(data);
              triggerPing(data, mapRef.current, pingLocation);
              
              // Add to ping log (keep last 10)
              setPingLog(prev => {
                const newLog = [
                  {
                    topic: data.topic || 'unknown',
                    lon: pingLocation.lon,
                    lat: pingLocation.lat,
                    timestamp: new Date().toLocaleTimeString(),
                    source: pingLocation.source,
                  },
                  ...prev,
                ];
                return newLog.slice(0, 10); // Keep only last 10
              });
            }

            // Update map data if event has geometry
            if (data.geometry) {
              // Trigger a refresh of geo events to include the new event
              fetch(`/api/geo-events?timeRange=${timeRange}&severity=${severity !== 'all' ? severity : ''}&source=${source !== 'all' ? source : 'all'}`)
                .then(res => res.json())
                .then(geoData => {
                  setIncidents(geoData.incidents || []);
                  setRiskAreas(geoData.riskAreas || []);
                })
                .catch(err => console.error('Error refreshing geo events:', err));
            }
          } catch (err) {
            console.error('Error parsing SSE message:', err);
          }
        };

        eventSource.onerror = () => {
          console.warn('SSE connection error, falling back to polling');
          eventSource.close();
          setSseConnected(false);
          // Fallback to polling
          pollingIntervalRef.current = setInterval(() => {
            fetch(`/api/geo-events?timeRange=1h&severity=&source=all`)
              .then(res => res.json())
              .then(data => {
                setIncidents(data.incidents || []);
                setRiskAreas(data.riskAreas || []);
              })
              .catch(err => console.error('Polling error:', err));
          }, 30000);
        };

      } catch (err) {
        console.error('Failed to create SSE connection:', err);
        setSseConnected(false);
      }
    };

    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      // Clean up ping markers
      pingMarkersRef.current.forEach(marker => marker.remove());
      pingMarkersRef.current.clear();
    };
  }, [mounted, pingEnabled, pingOnlyMedPlus, timeRange, severity, source]);

  // Function to trigger ping animation
  const triggerPing = (event: any, map: maplibregl.Map, pingLocation: { lon: number; lat: number; source: string }) => {
    const { lon: pingLon, lat: pingLat } = pingLocation;

    // Create ping marker element
    const pingId = `ping-${event.event_id || Date.now()}`;
    const pingEl = document.createElement('div');
    pingEl.className = 'ping-marker';
    pingEl.id = pingId;
    pingEl.style.width = '20px';
    pingEl.style.height = '20px';
    pingEl.style.borderRadius = '50%';
    pingEl.style.border = '3px solid #ef4444';
    pingEl.style.backgroundColor = 'rgba(239, 68, 68, 0.3)';
    pingEl.style.animation = 'ping-pulse 1.2s ease-out forwards';
    pingEl.style.pointerEvents = 'none';
    pingEl.style.zIndex = '1000';

    // Add animation keyframes if not already added
    if (!document.getElementById('ping-animation-style')) {
      const style = document.createElement('style');
      style.id = 'ping-animation-style';
      style.textContent = `
        @keyframes ping-pulse {
          0% {
            transform: scale(0.5);
            opacity: 1;
          }
          100% {
            transform: scale(4);
            opacity: 0;
          }
        }
      `;
      document.head.appendChild(style);
    }

    // Create marker
    const marker = new maplibregl.Marker({
      element: pingEl,
      anchor: 'center',
    })
      .setLngLat([pingLon, pingLat])
      .addTo(map);

    pingMarkersRef.current.set(pingId, marker);

    // Remove marker after animation
    setTimeout(() => {
      if (pingMarkersRef.current.has(pingId)) {
        pingMarkersRef.current.get(pingId)?.remove();
        pingMarkersRef.current.delete(pingId);
      }
    }, 1200);
  };

  if (!mounted) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading Map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-dark-surface bg-opacity-90 rounded-lg p-4 shadow-lg z-10 max-w-xs">
        <h3 className="text-sm font-semibold text-white mb-3">Legend</h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white"></div>
            <span className="text-gray-300">High/Critical</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-orange-500 border-2 border-white"></div>
            <span className="text-gray-300">Medium</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-yellow-500 border-2 border-white"></div>
            <span className="text-gray-300">Low</span>
          </div>
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-700">
            <div className="w-4 h-4 bg-red-500 bg-opacity-30 border border-red-600"></div>
            <span className="text-gray-300">Risk Area</span>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      <div className="absolute top-4 right-4 bg-dark-surface bg-opacity-90 rounded-lg p-4 shadow-lg z-10">
        <h3 className="text-sm font-semibold text-white mb-3">Filters</h3>
        <div className="space-y-3">
          {/* Time Range */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Time Window</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="w-full px-2 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600"
            >
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last hour</option>
              <option value="6h">Last 6 hours</option>
              <option value="24h">Last 24 hours</option>
            </select>
          </div>

          {/* Severity */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as any)}
              className="w-full px-2 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600"
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="med">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          {/* Source */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as any)}
              className="w-full px-2 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600"
            >
              <option value="all">All</option>
              <option value="transit">Transit</option>
              <option value="traffic">Traffic</option>
              <option value="airspace">Airspace</option>
              <option value="power">Power</option>
            </select>
          </div>
        </div>
      </div>

      {/* Real-time Event Counter & Controls */}
      <div className="absolute bottom-4 left-4 bg-dark-surface bg-opacity-90 rounded-lg p-3 shadow-lg z-10 space-y-2 max-w-xs">
        <div className="flex items-center gap-2 text-white text-xs">
          <div className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
          <span>Events received: {eventCount}</span>
        </div>
        
        {/* Ping Controls */}
        <div className="space-y-2 border-t border-gray-700 pt-2">
          <label className="flex items-center gap-2 text-white text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={pingEnabled}
              onChange={(e) => setPingEnabled(e.target.checked)}
              className="w-3 h-3 rounded"
            />
            <span>Ping on Events</span>
          </label>
          {pingEnabled && (
            <label className="flex items-center gap-2 text-white text-xs cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={pingOnlyMedPlus}
                onChange={(e) => setPingOnlyMedPlus(e.target.checked)}
                className="w-3 h-3 rounded"
              />
              <span>Ping only severity ≥ MED</span>
            </label>
          )}
          <label className="flex items-center gap-2 text-white text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={showPingLog}
              onChange={(e) => setShowPingLog(e.target.checked)}
              className="w-3 h-3 rounded"
            />
            <span>Show Ping Log</span>
          </label>
        </div>
      </div>

      {/* Ping Log Debug Panel */}
      {showPingLog && (
        <div className="absolute bottom-4 right-4 bg-dark-surface bg-opacity-95 rounded-lg p-4 shadow-lg z-10 max-w-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Ping Log (Last 10)</h3>
            <button
              onClick={() => setShowPingLog(false)}
              className="text-gray-400 hover:text-white text-lg"
            >
              ×
            </button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {pingLog.length === 0 ? (
              <p className="text-xs text-gray-400">No pings yet</p>
            ) : (
              pingLog.map((ping, idx) => (
                <div key={idx} className="text-xs bg-gray-800 rounded p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-medium">{ping.topic.split('.').pop()}</span>
                    <span className="text-gray-400">{ping.timestamp}</span>
                  </div>
                  <div className="text-gray-300">
                    {ping.lat.toFixed(4)}, {ping.lon.toFixed(4)}
                  </div>
                  <div className="text-gray-400 text-[10px] mt-1">
                    Source: {ping.source}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {loading && (
        <div className="absolute bottom-4 right-4 bg-dark-surface bg-opacity-90 rounded-lg px-4 py-2 shadow-lg z-10">
          <div className="flex items-center gap-2 text-white text-sm">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            <span>Loading events...</span>
          </div>
        </div>
      )}

      {/* Dropped Pin Panel */}
      {selectedIncident && (
        <DroppedPinPanel
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
          onFocus={() => {
            if (mapRef.current && selectedIncident) {
              mapRef.current.flyTo({
                center: [
                  selectedIncident.geometry.coordinates[0],
                  selectedIncident.geometry.coordinates[1],
                ],
                zoom: 16,
                duration: 500,
              });
            }
          }}
        />
      )}
    </div>
  );
}

