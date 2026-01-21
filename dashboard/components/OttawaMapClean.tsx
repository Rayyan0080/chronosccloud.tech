'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import DroppedPinPanel from './DroppedPinPanel';
import { eventToPingLocation } from '../lib/eventToPingLocation';
import { transitDisruptionRiskToGeo, enhanceGeoIncident, enhanceGeoRiskArea } from '../lib/eventToGeo';

// Ottawa coordinates and bounds
const OTTAWA_LAT = 45.4215;
const OTTAWA_LON = -75.6972;
const OTTAWA_ZOOM = 10;
const OTTAWA_BOUNDS: [[number, number], [number, number]] = [
  [-76.35, 44.95], // [west, south]
  [-75.00, 45.65], // [east, north]
];
const OTTAWA_MIN_ZOOM = 9;
const OTTAWA_MAX_ZOOM = 16;

// Performance limits
const MAX_INCIDENTS = 2000;
const MAX_RISK_AREAS = 200;
const PING_TTL_MS = 1500;
const PING_CLEANUP_INTERVAL = 250;
const MAX_PINGS_PER_SECOND = 5;

type GeoIncident = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: 'low' | 'med' | 'high' | 'critical' | 'moderate' | 'error' | 'warning' | 'info';  // 'error' kept for backward compatibility
  summary: string;
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  source?: string;
  topic?: string;
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
    coordinates: [number, number] | number[][];
    radius_meters?: number;
  };
  source?: string;
  topic?: string;
  details?: any;
};

type PingRing = {
  id: string;
  lon: number;
  lat: number;
  createdAt: number;
  severity: string;
  radius: number;
};

type SelectedIncident = GeoIncident | null;

type OttawaMapCleanProps = {
  defaultSource?: 'all' | 'transit' | 'traffic' | 'airspace' | 'power';
  defaultTimeRange?: '15m' | '1h' | '6h' | '24h';
  showFilters?: boolean;
};

export default function OttawaMapClean(props: OttawaMapCleanProps = {}) {
  const {
    defaultSource = 'all',
    defaultTimeRange = '24h',
    showFilters = true,
  } = props;
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mounted, setMounted] = useState(false);
  const [incidents, setIncidents] = useState<GeoIncident[]>([]);
  const [riskAreas, setRiskAreas] = useState<GeoRiskArea[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<SelectedIncident>(null);
  
  // Filters
  const [timeRange, setTimeRange] = useState<'15m' | '1h' | '6h' | '24h'>(defaultTimeRange);
  const [severity, setSeverity] = useState<'all' | 'high' | 'med' | 'low'>('all');
  const [source, setSource] = useState<'all' | 'transit' | 'traffic' | 'airspace' | 'power'>(defaultSource);
  
  // Real-time event streaming
  const [eventCount, setEventCount] = useState(0);
  const [pingEnabled, setPingEnabled] = useState(true);
  const [pingOnlyMedPlus, setPingOnlyMedPlus] = useState(false);
  const [pingOnlyWithLocation, setPingOnlyWithLocation] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);
  const [showPingLog, setShowPingLog] = useState(false);
  const [pingLog, setPingLog] = useState<Array<{ topic: string; lon: number; lat: number; timestamp: string; source: string }>>([]);
  
  // Ping rings state (temporary, client-only)
  const [pingRings, setPingRings] = useState<PingRing[]>([]);
  const pingRingsRef = useRef<PingRing[]>([]);
  const pingAnimationFrameRef = useRef<number | null>(null);
  const lastPingTimesRef = useRef<number[]>([]);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const filterDebounceRef = useRef<NodeJS.Timeout | null>(null);
  const lastMapUpdateRef = useRef<number>(0);
  const mapUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ensure client-side only
  useEffect(() => {
    setMounted(true);
  }, []);

  // Debounced filter handler
  const applyFilters = useCallback(async () => {
    if (!mounted) return;

    setLoading(true);
    try {
      // Use the geo-events API which has comprehensive conversion logic
      const params = new URLSearchParams({
        timeRange: timeRange,
        severity: severity !== 'all' ? severity : '',
        source: source !== 'all' ? source : 'all',
      });
      const res = await fetch(`/api/geo-events?${params}`);
      const data = await res.json();
      
      console.log('[Map] API response:', { 
        incidentsCount: data.incidents?.length || 0, 
        riskAreasCount: data.riskAreas?.length || 0,
      });
      if (data.incidents?.[0]) {
        console.log('[Map] Sample incident from API:', JSON.stringify(data.incidents[0], null, 2));
      }
      if (data.riskAreas?.[0]) {
        console.log('[Map] Sample risk area from API:', JSON.stringify(data.riskAreas[0], null, 2));
      }
      
      // The API returns incidents and riskAreas already converted
      let apiIncidents = data.incidents || [];
      let apiRiskAreas = data.riskAreas || [];
      
      
      // Convert to our internal format
      const geoIncidents: GeoIncident[] = apiIncidents.map((inc: any) => ({
        event_id: inc.event_id || inc.id || '',
        id: inc.id || inc.event_id || '',
        timestamp: inc.timestamp || new Date().toISOString(),
        severity: inc.severity || 'info',
        summary: inc.summary || 'Incident',
        geometry: inc.geometry || { type: 'Point', coordinates: [0, 0] },
        source: inc.source,
        topic: inc.topic || 'geo.incident',
        details: inc,
      })).filter((inc: GeoIncident) => {
        // Only include if geometry is valid
        const coords = inc.geometry?.coordinates;
        const isValid = coords && coords.length === 2 && !isNaN(coords[0]) && !isNaN(coords[1]);
        if (!isValid && inc.geometry) {
          console.warn('[Map] Filtered out incident with invalid geometry:', {
            id: inc.id,
            geometry: inc.geometry,
            coords: coords,
            coordsType: typeof coords,
            coordsLength: coords?.length,
          });
        }
        return isValid;
      });
      
      const geoRiskAreas: GeoRiskArea[] = apiRiskAreas.map((area: any) => ({
        event_id: area.event_id || area.id || '',
        id: area.id || area.event_id || '',
        timestamp: area.timestamp || new Date().toISOString(),
        severity: area.severity || 'info',
        summary: area.summary || 'Risk Area',
        geometry: area.geometry || {},
        source: area.source,
        topic: area.topic || 'geo.risk_area',
        details: area,
      })).filter((area: GeoRiskArea) => {
        // Only include if geometry is valid
        const geom = area.geometry;
        if (geom?.type === 'Circle') {
          return geom.coordinates && geom.coordinates.length === 2;
        } else if (geom?.type === 'Polygon') {
          return geom.coordinates && Array.isArray(geom.coordinates);
        }
        return false;
      });
      
      // Apply performance limits (keep newest)
      const sortedIncidents = geoIncidents.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      const sortedRiskAreas = geoRiskAreas.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      
      const finalIncidents = sortedIncidents.slice(0, MAX_INCIDENTS);
      const finalRiskAreas = sortedRiskAreas.slice(0, MAX_RISK_AREAS);
      
      setIncidents(finalIncidents);
      setRiskAreas(finalRiskAreas);
      
      console.log(`[Map] Loaded ${finalIncidents.length} incidents, ${finalRiskAreas.length} risk areas`);
      if (finalIncidents.length > 0) {
        const sample = finalIncidents[0];
        const coords = sample.geometry?.coordinates;
        console.log('[Map] Sample incident after processing:', {
          id: sample.id,
          geometryType: sample.geometry?.type,
          hasGeometry: !!sample.geometry,
          hasCoords: !!coords,
          coordsLength: coords?.length,
          coords: coords,
          coord0: coords?.[0],
          coord1: coords?.[1],
          isValidNumber: typeof coords?.[0] === 'number' && typeof coords?.[1] === 'number',
        });
      }
      if (finalRiskAreas.length > 0) {
        console.log('[Map] Sample risk area after processing:', JSON.stringify({
          id: finalRiskAreas[0].id,
          geometry: finalRiskAreas[0].geometry,
        }, null, 2));
      }
    } catch (error) {
      console.error('Error fetching events:', error);
    } finally {
      setLoading(false);
    }
  }, [mounted, timeRange, severity, source]);

  // Initial load and debounced filter changes
  useEffect(() => {
    if (!mounted) return;
    
    // Initial load immediately
    applyFilters();
    
    // Debounced updates on filter change
    if (filterDebounceRef.current) {
      clearTimeout(filterDebounceRef.current);
    }
    filterDebounceRef.current = setTimeout(() => {
      applyFilters();
    }, 300);
    
    return () => {
      if (filterDebounceRef.current) {
        clearTimeout(filterDebounceRef.current);
      }
    };
  }, [mounted, timeRange, severity, source, applyFilters]);

  // Helper to get since timestamp
  const getSinceTimestamp = (range: string): Date => {
    const now = Date.now();
    const ms = {
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
    }[range] || 60 * 60 * 1000;
    return new Date(now - ms);
  };

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
      pitch: 0,
      bearing: 0,
      dragRotate: false,
      touchPitch: false,
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Function to check bounds and recenter
    const checkBoundsAndRecenter = () => {
      const center = map.getCenter();
      const [west, south] = OTTAWA_BOUNDS[0];
      const [east, north] = OTTAWA_BOUNDS[1];
      
      if (center.lng < west || center.lng > east || center.lat < south || center.lat > north) {
        map.flyTo({
          center: [OTTAWA_LON, OTTAWA_LAT],
          zoom: OTTAWA_ZOOM,
          duration: 1000,
        });
      }
    };

    map.on('dragend', checkBoundsAndRecenter);
    map.on('zoomend', checkBoundsAndRecenter);

    // Add reset button
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

    // Wait for map to load
    map.on('load', () => {
      console.log('[Map] Map loaded successfully');
      // Trigger initial render of incidents and risk areas
      if (incidents.length > 0 || riskAreas.length > 0) {
        // Force re-render by triggering state update
        setTimeout(() => {
          if (mapRef.current) {
            mapRef.current.triggerRepaint();
          }
        }, 100);
      }
    });
    
    // Also listen for style load
    map.on('styledata', () => {
      console.log('[Map] Style data loaded');
    });

    return () => {
      map.off('dragend', checkBoundsAndRecenter);
      map.off('zoomend', checkBoundsAndRecenter);
      map.remove();
      mapRef.current = null;
    };
  }, [mounted]);

  // Render risk areas (polygons/circles) - ONLY true geo.risk_area events
  useEffect(() => {
    if (!mapRef.current || !mounted) return;

    const map = mapRef.current;
    
    const addRiskAreas = () => {
      if (!map.isStyleLoaded()) {
        // Use setTimeout as fallback if 'load' event doesn't fire
        const timeoutId = setTimeout(() => {
          if (map.isStyleLoaded()) {
            addRiskAreas();
          } else {
            setTimeout(addRiskAreas, 500);
          }
        }, 1000);
        map.once('load', () => {
          clearTimeout(timeoutId);
          addRiskAreas();
        });
        return;
      }

      // Remove existing layers
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
          // Create 64-point circle approximation
          coordinates = [];
          for (let i = 0; i < 64; i++) {
            const angle = (i / 64) * 2 * Math.PI;
            const dx = (radius / 111320) * Math.cos(angle);
            const dy = (radius / 111320) * Math.sin(angle) / Math.cos(lat * Math.PI / 180);
            coordinates.push([lon + dx, lat + dy]);
          }
          coordinates.push(coordinates[0]);
        } else {
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
            source: area.source,
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
          'fill-color': '#ef4444',
          'fill-opacity': 0.25,
        },
      });

      // Add outline layer
      map.addLayer({
        id: 'risk-areas-outline',
        type: 'line',
        source: 'risk-areas',
        paint: {
          'line-color': '#ef4444',
          'line-width': 2,
          'line-opacity': 0.6,
        },
      });
    };

    addRiskAreas();
  }, [riskAreas, mounted]);

  // Render incident points with clustering
  useEffect(() => {
    if (!mapRef.current || !mounted) {
      console.log('[Map] Rendering effect skipped: map not ready or not mounted');
      return;
    }

    // Early return if no incidents (but log why)
    if (incidents.length === 0) {
      console.log('[Map] Rendering effect: incidents array is empty, skipping render');
      return;
    }

    const map = mapRef.current;
    
    const addIncidents = async () => {
      // Check if map is loaded and ready
      // For inline styles, we check if the map has been loaded
      if (!map.loaded() || !map.getSource('osm-tiles')) {
        console.log('[Map] Map not ready, waiting for load event...');
        // Wait for map to load
        const loadHandler = () => {
          console.log('[Map] Map loaded, proceeding with incident rendering');
          addIncidents();
        };
        map.once('load', loadHandler);
        // Fallback timeout
        setTimeout(() => {
          map.off('load', loadHandler);
          if (map.loaded() && map.getSource('osm-tiles')) {
            console.log('[Map] Map ready after timeout, proceeding');
            addIncidents();
          } else {
            console.warn('[Map] Map still not ready after timeout, will retry on next render');
          }
        }, 2000);
        return;
      }

      // Remove existing layers
      if (map.getLayer('incidents-clusters')) map.removeLayer('incidents-clusters');
      if (map.getLayer('incidents-cluster-count')) map.removeLayer('incidents-cluster-count');
      if (map.getLayer('incidents-unclustered')) map.removeLayer('incidents-unclustered');
      if (map.getLayer('vehicles-layer')) map.removeLayer('vehicles-layer');
      if (map.getSource('incidents')) map.removeSource('incidents');
      if (map.getSource('vehicles')) map.removeSource('vehicles');

      // Double-check incidents still exist (state might have changed)
      if (incidents.length === 0) {
        console.log('[Map] No incidents to render (incidents array became empty during render)');
        return;
      }

      console.log(`[Map] Rendering ${incidents.length} incidents`);
      console.log('[Map] First incident sample:', {
        id: incidents[0].id,
        geometry: incidents[0].geometry,
        coords: incidents[0].geometry?.coordinates,
      });

      // Convert incidents to GeoJSON
      const features: GeoJSON.Feature[] = incidents
        .map((incident): GeoJSON.Feature | null => {
          const coords = incident.geometry?.coordinates;
          if (!coords || coords.length !== 2) {
            console.warn('[Map] Invalid coordinates for incident:', incident.id, coords);
            return null;
          }
          const [lon, lat] = coords;
          
          if (isNaN(lon) || isNaN(lat)) {
            console.warn('[Map] NaN coordinates for incident:', incident.id, { lon, lat });
            return null;
          }
        
        // Determine color by severity and source
        let color = '#eab308'; // yellow (low)
        // Special styling for aircraft/flights
        const incidentType = (incident.details as any)?.incident_type;
        if (incident.source === 'airspace' || incidentType === 'aircraft_position') {
          color = '#00FF00'; // bright green for aircraft
        } else if (incident.source === 'transit' || incidentType === 'vehicle_position') {
          color = '#3B82F6'; // blue for transit vehicles - more visible and distinctive
        } else if (incident.source === 'traffic' || incidentType?.includes('traffic') || incidentType?.includes('collision')) {
          color = '#10B981'; // green for traffic vehicles
        } else if (incident.severity === 'high' || incident.severity === 'critical' || incident.severity === 'moderate' || incident.severity === 'error') {
          color = '#ef4444'; // red
        } else if (incident.severity === 'med' || incident.severity === 'warning') {
          color = '#f97316'; // orange
        }

        // Determine icon type based on source, topic, and incident type
        let iconType = 'incident'; // default
        const topic = incident.topic || '';
        const source = incident.source || '';
        
        if (source === 'airspace' || incidentType === 'aircraft_position' || topic.includes('airspace.aircraft')) {
          iconType = 'aircraft';
        } else if (source === 'transit' || topic.includes('transit.vehicle') || incidentType === 'vehicle_position') {
          iconType = 'transit';
        } else if (source === 'traffic' || topic.includes('traffic') || incidentType?.includes('traffic') || incidentType?.includes('collision') || incidentType?.includes('vehicle')) {
          iconType = 'traffic'; // Car icon for traffic vehicles
        } else if (topic.includes('power') || incidentType?.includes('power')) {
          iconType = 'power';
        } else if (incident.severity === 'critical' || incident.severity === 'error') {
          iconType = 'alert';
        }
        
        // Debug logging for vehicle detection (will log during feature creation)
        if (iconType === 'transit' || iconType === 'traffic') {
          console.log('[Map] Vehicle detected:', {
            id: incident.id,
            source,
            topic,
            incidentType,
            iconType,
            hasBearing: !!((incident.details as any)?.details || incident.details)?.bearing,
          });
        }

        // Extract bearing from vehicle details for rotation
        const vehicleDetails = (incident.details as any)?.details || incident.details;
        const bearing = vehicleDetails?.bearing || null;

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
            source: incident.source,
            topic: incident.topic,
            timestamp: incident.timestamp,
            color,
            iconType, // Add icon type for rendering
            bearing: bearing !== null ? bearing : undefined, // Add bearing for vehicle rotation
            details: incident.details,
          },
        };
      }).filter((f): f is GeoJSON.Feature => f !== null);

      if (features.length === 0) {
        console.warn('[Map] No valid features after filtering');
        console.warn('[Map] Incidents that were filtered:', incidents.map(inc => ({
          id: inc.id,
          hasGeometry: !!inc.geometry,
          coords: inc.geometry?.coordinates,
          coordsType: typeof inc.geometry?.coordinates,
        })));
        return;
      }

      console.log(`[Map] Adding ${features.length} features to map`);
      console.log('[Map] First feature sample:', {
        type: features[0].type,
        geometry: features[0].geometry,
        properties: features[0].properties,
      });

      // Separate vehicles from other incidents - vehicles should never cluster
      const vehicleFeatures = features.filter(f => {
        const iconType = f.properties?.iconType;
        return iconType === 'transit' || iconType === 'traffic' || iconType === 'aircraft';
      });
      const otherFeatures = features.filter(f => {
        const iconType = f.properties?.iconType;
        return iconType !== 'transit' && iconType !== 'traffic' && iconType !== 'aircraft';
      });

      console.log(`[Map] Separated: ${vehicleFeatures.length} vehicles, ${otherFeatures.length} other incidents`);

      // Remove existing vehicle source if it exists
      if (map.getSource('vehicles')) {
        if (map.getLayer('vehicles-layer')) map.removeLayer('vehicles-layer');
        map.removeSource('vehicles');
      }

      // Add vehicles as a separate non-clustered source
      if (vehicleFeatures.length > 0) {
        map.addSource('vehicles', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: vehicleFeatures,
          },
          cluster: false, // Never cluster vehicles - always show individual icons
        });
      }

      // Add other incidents with clustering
      map.addSource('incidents', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: otherFeatures,
        },
        cluster: true,
        clusterRadius: 55,
        clusterMaxZoom: 13,
      });

      // Cluster circles
      map.addLayer({
        id: 'incidents-clusters',
        type: 'circle',
        source: 'incidents',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#ef4444',
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            20, // radius for 1 point
            10, 30, // radius for 10 points
            50, 40, // radius for 50 points
            100, 50, // radius for 100+ points
          ],
          'circle-opacity': 0.6,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      });

      // Cluster count labels - using circles with text instead of symbol layer (avoids glyphs requirement)
      // We'll use a circle layer with larger radius and add text via HTML overlay if needed
      // For now, just show cluster circles without text labels to avoid glyphs error

      // Add icon images for different event types
      const iconImages: Record<string, string> = {
        aircraft: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="currentColor"/>
          </svg>
        `),
        transit: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Bus body -->
            <rect x="4" y="8" width="24" height="14" rx="2" fill="currentColor" stroke="#fff" stroke-width="1.5"/>
            <!-- Windows -->
            <rect x="7" y="10" width="4" height="3" rx="0.5" fill="#fff" opacity="0.9"/>
            <rect x="13" y="10" width="4" height="3" rx="0.5" fill="#fff" opacity="0.9"/>
            <rect x="19" y="10" width="4" height="3" rx="0.5" fill="#fff" opacity="0.9"/>
            <!-- Front window -->
            <rect x="25" y="10" width="2" height="3" rx="0.5" fill="#fff" opacity="0.9"/>
            <!-- Wheels -->
            <circle cx="9" cy="24" r="3" fill="#1a1a1a" stroke="#fff" stroke-width="1"/>
            <circle cx="9" cy="24" r="1.5" fill="#fff"/>
            <circle cx="23" cy="24" r="3" fill="#1a1a1a" stroke="#fff" stroke-width="1"/>
            <circle cx="23" cy="24" r="1.5" fill="#fff"/>
            <!-- Door -->
            <rect x="7" y="15" width="2.5" height="6" rx="0.5" fill="#fff" opacity="0.8"/>
            <!-- Route number indicator (optional) -->
            <circle cx="26" cy="12" r="3" fill="#fff" opacity="0.3"/>
          </svg>
        `),
        traffic: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Car body -->
            <rect x="6" y="10" width="20" height="12" rx="2" fill="currentColor" stroke="#fff" stroke-width="1.5"/>
            <!-- Windshield -->
            <rect x="8" y="12" width="6" height="4" rx="0.5" fill="#fff" opacity="0.9"/>
            <!-- Rear window -->
            <rect x="18" y="12" width="6" height="4" rx="0.5" fill="#fff" opacity="0.9"/>
            <!-- Front wheel -->
            <circle cx="11" cy="24" r="2.5" fill="#1a1a1a" stroke="#fff" stroke-width="1"/>
            <circle cx="11" cy="24" r="1.2" fill="#fff"/>
            <!-- Rear wheel -->
            <circle cx="21" cy="24" r="2.5" fill="#1a1a1a" stroke="#fff" stroke-width="1"/>
            <circle cx="21" cy="24" r="1.2" fill="#fff"/>
            <!-- Headlights -->
            <circle cx="6" cy="16" r="1.5" fill="#fff" opacity="0.8"/>
            <!-- Taillights -->
            <circle cx="26" cy="16" r="1.5" fill="#ff0000" opacity="0.8"/>
          </svg>
        `),
        power: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 2L3 14h8v8l10-12h-8V2z" fill="currentColor"/>
          </svg>
        `),
        alert: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 22h20L12 2zm0 3.99L19.53 20H4.47L12 5.99zM11 16v-4h2v4h-2zm0 2v-2h2v2h-2z" fill="currentColor"/>
          </svg>
        `),
        incident: 'data:image/svg+xml;base64,' + btoa(`
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="8" fill="currentColor"/>
          </svg>
        `),
      };

      // Load icon images
      const loadIcon = (name: string, svgData: string): Promise<void> => {
        return new Promise((resolve, reject) => {
          if (map.hasImage(name)) {
            resolve();
            return;
          }
          const img = new Image();
          img.onload = () => {
            map.addImage(name, img);
            resolve();
          };
          img.onerror = reject;
          img.src = svgData;
        });
      };

      // Load all icons
      await Promise.all(
        Object.entries(iconImages).map(([name, svg]) => loadIcon(name, svg))
      );

      // Add vehicle layer (always visible, never clustered)
      if (vehicleFeatures.length > 0 && map.getSource('vehicles')) {
        map.addLayer({
          id: 'vehicles-layer',
          type: 'symbol',
          source: 'vehicles',
          layout: {
          'icon-image': [
            'case',
            ['==', ['get', 'iconType'], 'aircraft'], 'aircraft',
            ['==', ['get', 'iconType'], 'transit'], 'transit',
            ['==', ['get', 'iconType'], 'traffic'], 'traffic',
            ['==', ['get', 'iconType'], 'power'], 'power',
            ['==', ['get', 'iconType'], 'alert'], 'alert',
            'incident', // default
          ],
          'icon-size': [
            'case',
            ['==', ['get', 'id'], selectedIncident?.id || ''], 1.5, // Selected is larger
            ['==', ['get', 'source'], 'airspace'], 1.2, // Aircraft are larger
            ['==', ['get', 'source'], 'transit'], 1.3, // Transit vehicles - larger and more visible
            ['==', ['get', 'source'], 'traffic'], 1.2, // Traffic vehicles - visible size
            0.8, // Default size
          ],
          'icon-rotation-alignment': 'map', // Rotate with map (for vehicles)
          'icon-rotate': [
            'case',
            ['has', 'bearing'], ['get', 'bearing'], // Use bearing if available
            0, // Default no rotation
          ],
          'icon-allow-overlap': true,
          'icon-ignore-placement': true, // Allow vehicles to overlap so they're always visible
        },
        paint: {
          'icon-color': ['get', 'color'],
          'icon-opacity': [
            'case',
            ['==', ['get', 'source'], 'airspace'], 0.95, // Brighter for aircraft
            ['==', ['get', 'source'], 'transit'], 0.95, // Brighter for transit vehicles
            ['==', ['get', 'source'], 'traffic'], 0.95, // Brighter for traffic vehicles
            0.9, // Default
          ],
        },
      });

      // Add click handler for vehicles
      map.on('click', 'vehicles-layer', (e) => {
        if (e.features && e.features.length > 0) {
          const feature = e.features[0];
          const incident = incidents.find((inc) => inc.id === feature.properties?.id);
          if (incident) {
            setSelectedIncident(incident);
          }
        }
      });

      // Change cursor on hover for vehicles
      map.on('mouseenter', 'vehicles-layer', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'vehicles-layer', () => {
        map.getCanvas().style.cursor = '';
      });
      }

      // Unclustered points with icons (for non-vehicle incidents)
      map.addLayer({
        id: 'incidents-unclustered',
        type: 'symbol',
        source: 'incidents',
        filter: ['!', ['has', 'point_count']], // Only unclustered points
        layout: {
          'icon-image': [
            'case',
            ['==', ['get', 'iconType'], 'aircraft'], 'aircraft',
            ['==', ['get', 'iconType'], 'transit'], 'transit',
            ['==', ['get', 'iconType'], 'traffic'], 'traffic',
            ['==', ['get', 'iconType'], 'power'], 'power',
            ['==', ['get', 'iconType'], 'alert'], 'alert',
            'incident', // default
          ],
          'icon-size': [
            'case',
            ['==', ['get', 'id'], selectedIncident?.id || ''], 1.5, // Selected is larger
            0.8, // Default size
          ],
          'icon-allow-overlap': true,
          'icon-ignore-placement': false,
        },
        paint: {
          'icon-color': ['get', 'color'],
          'icon-opacity': 0.9,
        },
      });

      // Handle cluster clicks (zoom in)
      map.on('click', 'incidents-clusters', (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ['incidents-clusters'],
        });
        const clusterId = features[0].properties?.cluster_id;
        if (clusterId !== undefined) {
          const source = map.getSource('incidents') as maplibregl.GeoJSONSource;
          source.getClusterExpansionZoom(clusterId).then((zoom) => {
            map.easeTo({
              center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
              zoom: zoom || map.getZoom() + 1,
            });
          }).catch((err) => {
            console.error('Error getting cluster expansion zoom:', err);
          });
        }
      });

      // Handle incident point clicks
      map.on('click', 'incidents-unclustered', (e) => {
        if (e.features && e.features.length > 0) {
          const feature = e.features[0];
          const incident = incidents.find((inc) => inc.id === feature.properties?.id);
          if (incident) {
            setSelectedIncident(incident);
          }
        }
      });

      // Change cursor on hover
      map.on('mouseenter', 'incidents-clusters', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'incidents-clusters', () => {
        map.getCanvas().style.cursor = '';
      });
      map.on('mouseenter', 'incidents-unclustered', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'incidents-unclustered', () => {
        map.getCanvas().style.cursor = '';
      });

      // Handle map clicks (deselect) - attach to map container, not a layer
      const handleMapClick = (e: maplibregl.MapMouseEvent) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ['incidents-unclustered', 'incidents-clusters'],
        });
        if (features.length === 0) {
          setSelectedIncident(null);
        }
      };
      map.on('click', handleMapClick);
    };

    addIncidents();

    return () => {
      if (mapRef.current) {
        const map = mapRef.current;
        // Remove all event listeners - MapLibre requires handler function
        // Since we can't store handlers easily, we'll just remove the layers
        // The handlers will be cleaned up when layers are removed
        try {
          if (map.getLayer('incidents-clusters')) {
            map.removeLayer('incidents-clusters');
          }
          if (map.getLayer('incidents-unclustered')) {
            map.removeLayer('incidents-unclustered');
          }
          if (map.getSource('incidents')) {
            map.removeSource('incidents');
          }
        } catch (e) {
          // Layers may already be removed
        }
      }
    };
  }, [incidents, mounted]); // Removed selectedIncident - it shouldn't trigger re-render of incidents

  // Ping rings animation and cleanup
  useEffect(() => {
    if (!mapRef.current || !mounted || pingRings.length === 0) return;

    const map = mapRef.current;
    
    const animatePings = () => {
      if (!map.isStyleLoaded()) {
        pingAnimationFrameRef.current = requestAnimationFrame(animatePings);
        return;
      }

      const now = Date.now();
      const updatedRings = pingRingsRef.current
        .filter(ring => now - ring.createdAt < PING_TTL_MS)
        .map(ring => ({
          ...ring,
          radius: Math.min(ring.radius + 2, 100), // Expand radius
        }));

      pingRingsRef.current = updatedRings;
      setPingRings([...updatedRings]);

      // Update ping source data
      if (map.getSource('pings')) {
        const source = map.getSource('pings') as maplibregl.GeoJSONSource;
        source.setData({
          type: 'FeatureCollection',
          features: updatedRings.map(ring => ({
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [ring.lon, ring.lat],
            },
            properties: {
              id: ring.id,
              radius: ring.radius,
            },
          })),
        });
      }

      if (updatedRings.length > 0) {
        pingAnimationFrameRef.current = requestAnimationFrame(animatePings);
      }
    };

    pingAnimationFrameRef.current = requestAnimationFrame(animatePings);

    return () => {
      if (pingAnimationFrameRef.current) {
        cancelAnimationFrame(pingAnimationFrameRef.current);
      }
    };
  }, [pingRings.length, mounted]);

  // Ping cleanup interval
  useEffect(() => {
    if (!mounted) return;

    const cleanupInterval = setInterval(() => {
      const now = Date.now();
      setPingRings(prev => {
        const filtered = prev.filter(ring => now - ring.createdAt < PING_TTL_MS);
        pingRingsRef.current = filtered;
        return filtered;
      });
    }, PING_CLEANUP_INTERVAL);

    return () => clearInterval(cleanupInterval);
  }, [mounted]);

  // Render ping rings layer
  useEffect(() => {
    if (!mapRef.current || !mounted) return;

    const map = mapRef.current;
    
    const addPings = () => {
      if (!map.isStyleLoaded()) {
        map.once('load', addPings);
        return;
      }

      if (map.getLayer('pings')) map.removeLayer('pings');
      if (map.getSource('pings')) map.removeSource('pings');

      if (pingRings.length === 0) return;

      map.addSource('pings', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: pingRings.map(ring => ({
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [ring.lon, ring.lat],
            },
            properties: {
              id: ring.id,
              radius: ring.radius,
            },
          })),
        },
      });

      // Render as expanding circles
      map.addLayer({
        id: 'pings',
        type: 'circle',
        source: 'pings',
        paint: {
          'circle-radius': ['get', 'radius'],
          'circle-color': '#ef4444',
          'circle-opacity': [
            'interpolate',
            ['linear'],
            ['get', 'radius'],
            0, 0.8,
            100, 0,
          ],
          'circle-stroke-color': '#ef4444',
          'circle-stroke-width': 2,
          'circle-stroke-opacity': [
            'interpolate',
            ['linear'],
            ['get', 'radius'],
            0, 0.6,
            100, 0,
          ],
        },
      });
    };

    addPings();
  }, [pingRings, mounted]);

  // SSE connection for real-time events
  useEffect(() => {
    if (!mounted || !mapRef.current) return;

    const connectSSE = () => {
      try {
        const since = getSinceTimestamp(timeRange);
        const eventSource = new EventSource(`/api/events/stream?since=${since.toISOString()}`);
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
              return;
            }

            if (data.type === 'error') {
              console.error('SSE error:', data.message);
              eventSource.close();
              setSseConnected(false);
              // Fallback to polling
              pollingIntervalRef.current = setInterval(applyFilters, 5000);
              return;
            }

            // Apply filters to incoming event
            const eventSeverity = (data.severity || 'info').toLowerCase();
            const eventSourceName = (data.source || '').toLowerCase();
            
            const severityMatch = severity === 'all' || 
              (severity === 'high' && ['high', 'critical', 'moderate', 'error'].includes(eventSeverity)) ||
              (severity === 'med' && ['med', 'medium', 'warning'].includes(eventSeverity)) ||
              (severity === 'low' && ['low', 'info'].includes(eventSeverity));
            
            const sourceMatch = source === 'all' || 
              eventSourceName.includes(source);
            
            
            if (!severityMatch || !sourceMatch) {
              return; // Skip event that doesn't match filters
            }

            setEventCount(prev => prev + 1);

            // Check if event has geometry (Point, Circle, Polygon) or location data in details
            const hasExplicitGeometry = data.geometry && (
              data.geometry.type === 'Point' ||
              data.geometry.type === 'Circle' ||
              data.geometry.type === 'Polygon'
            );
            
            // Check if event has location data in details (for transit, airspace, etc.)
            const hasLocationInDetails = data.details && (
              (data.details.location && (data.details.location.latitude || data.details.location.lat)) ||
              (data.details.position && (data.details.position.latitude || data.details.position.lat)) ||
              (typeof data.details.latitude === 'number' && typeof data.details.longitude === 'number')
            );
            
            const hasGeometryForRendering = hasExplicitGeometry || hasLocationInDetails;

            // Handle ping (only if enabled and conditions met)
            if (pingEnabled) {
              const shouldPing = (
                (!pingOnlyMedPlus || ['med', 'high', 'critical', 'moderate', 'error', 'warning'].includes(eventSeverity)) &&
                (!pingOnlyWithLocation || hasGeometryForRendering)
              );

              if (shouldPing) {
                // Throttle pings
                const now = Date.now();
                lastPingTimesRef.current = lastPingTimesRef.current.filter(t => now - t < 1000);
                
                if (lastPingTimesRef.current.length < MAX_PINGS_PER_SECOND) {
                  lastPingTimesRef.current.push(now);
                  
                  // Always get ping location (even if no geometry, uses fallback)
                  const pingLocation = eventToPingLocation(data);
                  const pingId = `ping-${data.event_id || Date.now()}`;
                  
                  setPingRings(prev => {
                    const newRings = [
                      {
                        id: pingId,
                        lon: pingLocation.lon,
                        lat: pingLocation.lat,
                        createdAt: now,
                        severity: eventSeverity,
                        radius: 5,
                      },
                      ...prev,
                    ];
                    pingRingsRef.current = newRings;
                    return newRings;
                  });

                  // Add to ping log
                  setPingLog(prev => [
                    {
                      topic: data.topic || 'unknown',
                      lon: pingLocation.lon,
                      lat: pingLocation.lat,
                      timestamp: new Date().toLocaleTimeString(),
                      source: pingLocation.source,
                    },
                    ...prev.slice(0, 9),
                  ]);
                }
              }
            }

            // Update map data if event has geometry or location data
            // Throttle map updates to avoid too many refreshes
            if (hasGeometryForRendering) {
              const now = Date.now();
              const lastUpdate = lastMapUpdateRef.current || 0;
              
              // Only refresh map if it's been at least 2 seconds since last update
              if (now - lastUpdate > 2000) {
                lastMapUpdateRef.current = now;
                // Trigger refresh
                applyFilters();
              } else {
                // Schedule a debounced update
                if (mapUpdateTimeoutRef.current) {
                  clearTimeout(mapUpdateTimeoutRef.current);
                }
                mapUpdateTimeoutRef.current = setTimeout(() => {
                  lastMapUpdateRef.current = Date.now();
                  applyFilters();
                }, 2000);
              }
            }
          } catch (err) {
            console.error('Error parsing SSE message:', err);
          }
        };

        eventSource.onerror = () => {
          console.warn('SSE connection error, falling back to polling');
          eventSource.close();
          setSseConnected(false);
          pollingIntervalRef.current = setInterval(applyFilters, 5000);
        };

      } catch (err) {
        console.error('Failed to create SSE connection:', err);
        setSseConnected(false);
        pollingIntervalRef.current = setInterval(applyFilters, 5000);
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
      if (mapUpdateTimeoutRef.current) {
        clearTimeout(mapUpdateTimeoutRef.current);
        mapUpdateTimeoutRef.current = null;
      }
    };
  }, [mounted, pingEnabled, pingOnlyMedPlus, pingOnlyWithLocation, timeRange, severity, source, applyFilters]);

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
            <div className="w-3 h-3 rounded-full bg-red-500 border border-white"></div>
            <span className="text-gray-300">High/Critical</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500 border border-white"></div>
            <span className="text-gray-300">Medium</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500 border border-white"></div>
            <span className="text-gray-300">Low</span>
          </div>
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-700">
            <div className="w-4 h-4 bg-red-500 bg-opacity-25 border border-red-600"></div>
            <span className="text-gray-300">Risk Area</span>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
      <div className="absolute top-4 right-4 bg-dark-surface bg-opacity-90 rounded-lg p-4 shadow-lg z-10">
        <h3 className="text-sm font-semibold text-white mb-3">Filters</h3>
        <div className="space-y-3">
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

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as any)}
              className="w-full px-2 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600"
            >
              <option value="all">All</option>
              <option value="high">High+Critical</option>
              <option value="med">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

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
      )}

      {/* Real-time Event Counter & Controls */}
      <div className="absolute bottom-4 left-4 bg-dark-surface bg-opacity-90 rounded-lg p-3 shadow-lg z-10 space-y-2 max-w-xs">
        <div className="flex items-center gap-2 text-white text-xs">
          <div className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
          <span>Events: {eventCount}</span>
        </div>
        
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
            <>
              <label className="flex items-center gap-2 text-white text-xs cursor-pointer ml-4">
                <input
                  type="checkbox"
                  checked={pingOnlyMedPlus}
                  onChange={(e) => setPingOnlyMedPlus(e.target.checked)}
                  className="w-3 h-3 rounded"
                />
                <span>Ping only severity ≥ MED</span>
              </label>
              <label className="flex items-center gap-2 text-white text-xs cursor-pointer ml-4">
                <input
                  type="checkbox"
                  checked={pingOnlyWithLocation}
                  onChange={(e) => setPingOnlyWithLocation(e.target.checked)}
                  className="w-3 h-3 rounded"
                />
                <span>Ping only events with location</span>
              </label>
            </>
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
        <div className="absolute top-20 right-4 bg-dark-surface bg-opacity-90 rounded-lg px-4 py-2 shadow-lg z-10">
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

