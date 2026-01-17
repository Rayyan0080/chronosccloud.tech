'use client';

import { useEffect, useRef, useState } from 'react';

// Dynamically import Cesium to avoid SSR issues
let Cesium: any = null;
if (typeof window !== 'undefined') {
  try {
    // @ts-ignore
    Cesium = require('cesium');
    
    // Configure Cesium base URL for static assets
    if (typeof window !== 'undefined') {
      (window as any).CESIUM_BASE_URL = '/cesium';
    }
  } catch (e) {
    console.error('Failed to load Cesium:', e);
  }
}

// Ottawa coordinates
const OTTAWA_LAT = 45.4215;
const OTTAWA_LON = -75.6972;
const OTTAWA_HEIGHT = 120000; // meters

type GeoIncident = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: string;
  summary: string;
  geometry: {
    type: 'Point' | 'Circle' | 'Polygon';
    coordinates: any;
    radius_meters?: number;
  };
  style: {
    color: string;
    opacity: number;
    outline: boolean;
  };
  incident_type?: string;
  description?: string;
  status?: string;
};

type GeoRiskArea = {
  event_id: string;
  id: string;
  timestamp: string;
  severity: string;
  summary: string;
  geometry: {
    type: 'Point' | 'Circle' | 'Polygon';
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
};

export default function OttawaCesiumMap() {
  const cesiumContainerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [cesiumLoaded, setCesiumLoaded] = useState(false);
  const [hasTerrain, setHasTerrain] = useState(false);
  const [ionToken, setIonToken] = useState<string | null>(null);
  
  // Layer manager state
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h'>('6h');
  const [severity, setSeverity] = useState<'all' | 'low' | 'med' | 'high' | 'critical'>('all');
  const [incidents, setIncidents] = useState<GeoIncident[]>([]);
  const [riskAreas, setRiskAreas] = useState<GeoRiskArea[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Entity references
  const incidentEntitiesRef = useRef<any[]>([]);
  const riskAreaEntitiesRef = useRef<any[]>([]);

  useEffect(() => {
    // Load Cesium dynamically
    if (typeof window !== 'undefined' && !Cesium) {
      import('cesium').then((cesiumModule) => {
        Cesium = cesiumModule;
        if (typeof window !== 'undefined') {
          (window as any).CESIUM_BASE_URL = '/cesium';
        }
        setCesiumLoaded(true);
      }).catch((err) => {
        console.error('Failed to load Cesium:', err);
      });
    } else if (Cesium) {
      setCesiumLoaded(true);
    }
  }, []);

  useEffect(() => {
    // Get Ion token from environment variable
    const token = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || null;
    setIonToken(token);
    
    if (token && Cesium) {
      Cesium.Ion.defaultAccessToken = token;
    }
  }, [cesiumLoaded]);

  // Fetch geo events from API
  useEffect(() => {
    const fetchGeoEvents = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          timeRange,
          severity: severity !== 'all' ? severity : '',
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
    // Refresh every 30 seconds
    const interval = setInterval(fetchGeoEvents, 30000);
    return () => clearInterval(interval);
  }, [timeRange, severity]);

  useEffect(() => {
    if (!cesiumContainerRef.current || !Cesium || !cesiumLoaded) return;

    // Clean up existing viewer if it exists
    if (viewerRef.current) {
      viewerRef.current.destroy();
      viewerRef.current = null;
    }

    // Store Cesium reference
    const cesiumInstance = Cesium;

    // Initialize terrain provider
    let terrainProvider;
    
    if (ionToken) {
      try {
        // Try to use Cesium World Terrain (requires Ion token)
        if (typeof cesiumInstance.createWorldTerrainAsync === 'function') {
          terrainProvider = new cesiumInstance.EllipsoidTerrainProvider();
          setHasTerrain(false);
          
          cesiumInstance.createWorldTerrainAsync()
            .then((worldTerrain: any) => {
              if (viewerRef.current) {
                viewerRef.current.terrainProvider = worldTerrain;
                setHasTerrain(true);
              }
            })
            .catch(() => {
              setHasTerrain(false);
            });
        } else {
          terrainProvider = new cesiumInstance.EllipsoidTerrainProvider();
          setHasTerrain(false);
        }
      } catch (e) {
        console.warn('Could not create world terrain, using ellipsoid:', e);
        terrainProvider = new cesiumInstance.EllipsoidTerrainProvider();
        setHasTerrain(false);
      }
    } else {
      terrainProvider = new cesiumInstance.EllipsoidTerrainProvider();
      setHasTerrain(false);
    }

    // Initialize imagery provider
    let imageryProvider;
    try {
      if (ionToken) {
        imageryProvider = new cesiumInstance.IonImageryProvider({ assetId: 2 });
      } else {
        imageryProvider = new cesiumInstance.OpenStreetMapImageryProvider({
          url: 'https://a.tile.openstreetmap.org/',
        });
      }
    } catch (e) {
      console.warn('Could not create imagery provider, using default');
      imageryProvider = undefined;
    }

    // Initialize Cesium Viewer
    const viewer = new cesiumInstance.Viewer(cesiumContainerRef.current, {
      terrainProvider: terrainProvider,
      imageryProvider: imageryProvider,
      baseLayerPicker: false,
      vrButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: true,
      sceneModePicker: true,
      selectionIndicator: true,
      timeline: false,
      animation: false,
      fullscreenButton: true,
      navigationHelpButton: false,
      navigationInstructionsInitiallyVisible: false,
    });

    viewerRef.current = viewer;

    // Center camera on Ottawa
    viewer.camera.setView({
      destination: cesiumInstance.Cartesian3.fromDegrees(
        OTTAWA_LON,
        OTTAWA_LAT,
        OTTAWA_HEIGHT
      ),
    });

    // Store reset view function
    const resetView = () => {
      viewer.camera.flyTo({
        destination: cesiumInstance.Cartesian3.fromDegrees(
          OTTAWA_LON,
          OTTAWA_LAT,
          OTTAWA_HEIGHT
        ),
        duration: 2.0,
      });
    };

    (viewer as any).resetView = resetView;

    // Cleanup
    return () => {
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, [cesiumLoaded, ionToken]);

  // Render incidents and risk areas when data changes
  useEffect(() => {
    if (!viewerRef.current || !Cesium) return;

    const viewer = viewerRef.current;
    const cesiumInstance = Cesium;

    // Clear existing entities
    incidentEntitiesRef.current.forEach((entity) => {
      viewer.entities.remove(entity);
    });
    incidentEntitiesRef.current = [];

    riskAreaEntitiesRef.current.forEach((entity) => {
      viewer.entities.remove(entity);
    });
    riskAreaEntitiesRef.current = [];

    // Render incidents
    incidents.forEach((incident) => {
      const geometry = incident.geometry;
      const style = incident.style;
      const color = parseColor(style.color, style.opacity, cesiumInstance);

      if (geometry.type === 'Point') {
        const [lon, lat] = geometry.coordinates;
        const position = cesiumInstance.Cartesian3.fromDegrees(lon, lat, 0);

        const entity = viewer.entities.add({
          position: position,
          point: {
            pixelSize: 12,
            color: color,
            outlineColor: cesiumInstance.Color.WHITE,
            outlineWidth: 2,
            heightReference: cesiumInstance.HeightReference.CLAMP_TO_GROUND,
          },
          billboard: {
            image: createIncidentIcon(color, cesiumInstance),
            scale: 1.5,
            verticalOrigin: cesiumInstance.VerticalOrigin.BOTTOM,
          },
          label: {
            text: incident.id || incident.summary,
            font: '12pt sans-serif',
            fillColor: color,
            outlineColor: cesiumInstance.Color.BLACK,
            outlineWidth: 2,
            style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new cesiumInstance.Cartesian2(0, -30),
          },
          description: `
            <div style="padding: 10px;">
              <h3>Incident: ${incident.id || 'Unknown'}</h3>
              <p><strong>Severity:</strong> ${incident.severity}</p>
              <p><strong>Type:</strong> ${incident.incident_type || 'N/A'}</p>
              <p><strong>Status:</strong> ${incident.status || 'N/A'}</p>
              <p><strong>Summary:</strong> ${incident.summary}</p>
              ${incident.description ? `<p><strong>Description:</strong> ${incident.description}</p>` : ''}
              <p><strong>Time:</strong> ${new Date(incident.timestamp).toLocaleString()}</p>
            </div>
          `,
        });

        incidentEntitiesRef.current.push(entity);
      }
    });

    // Render risk areas
    riskAreas.forEach((riskArea) => {
      const geometry = riskArea.geometry;
      const style = riskArea.style;
      const color = parseColor(style.color, style.opacity, cesiumInstance);

      if (geometry.type === 'Circle') {
        const [lon, lat] = geometry.coordinates;
        const center = cesiumInstance.Cartesian3.fromDegrees(lon, lat, 0);
        const radius = geometry.radius_meters || 1000;

        const entity = viewer.entities.add({
          position: center,
          ellipse: {
            semiMajorAxis: radius,
            semiMinorAxis: radius,
            material: color,
            outline: style.outline,
            outlineColor: color.withAlpha(1.0),
            outlineWidth: 2,
            heightReference: cesiumInstance.HeightReference.CLAMP_TO_GROUND,
          },
          label: {
            text: riskArea.id || riskArea.summary,
            font: '11pt sans-serif',
            fillColor: cesiumInstance.Color.WHITE,
            outlineColor: cesiumInstance.Color.BLACK,
            outlineWidth: 2,
            style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new cesiumInstance.Cartesian2(0, -40),
          },
          description: `
            <div style="padding: 10px;">
              <h3>Risk Area: ${riskArea.id || 'Unknown'}</h3>
              <p><strong>Severity:</strong> ${riskArea.severity}</p>
              <p><strong>Risk Level:</strong> ${riskArea.risk_level || 'N/A'}</p>
              <p><strong>Type:</strong> ${riskArea.risk_type || 'N/A'}</p>
              <p><strong>Summary:</strong> ${riskArea.summary}</p>
              ${riskArea.description ? `<p><strong>Description:</strong> ${riskArea.description}</p>` : ''}
              <p><strong>Time:</strong> ${new Date(riskArea.timestamp).toLocaleString()}</p>
            </div>
          `,
        });

        riskAreaEntitiesRef.current.push(entity);
      } else if (geometry.type === 'Polygon') {
        const positions = geometry.coordinates.map((coord: number[]) => {
          const [lon, lat] = coord;
          return cesiumInstance.Cartesian3.fromDegrees(lon, lat, 0);
        });

        const entity = viewer.entities.add({
          polygon: {
            hierarchy: positions,
            material: color,
            outline: style.outline,
            outlineColor: color.withAlpha(1.0),
            outlineWidth: 2,
            heightReference: cesiumInstance.HeightReference.CLAMP_TO_GROUND,
          },
          label: {
            text: riskArea.id || riskArea.summary,
            font: '11pt sans-serif',
            fillColor: cesiumInstance.Color.WHITE,
            outlineColor: cesiumInstance.Color.BLACK,
            outlineWidth: 2,
            style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new cesiumInstance.Cartesian2(0, -40),
          },
          description: `
            <div style="padding: 10px;">
              <h3>Risk Area: ${riskArea.id || 'Unknown'}</h3>
              <p><strong>Severity:</strong> ${riskArea.severity}</p>
              <p><strong>Risk Level:</strong> ${riskArea.risk_level || 'N/A'}</p>
              <p><strong>Type:</strong> ${riskArea.risk_type || 'N/A'}</p>
              <p><strong>Summary:</strong> ${riskArea.summary}</p>
              ${riskArea.description ? `<p><strong>Description:</strong> ${riskArea.description}</p>` : ''}
              <p><strong>Time:</strong> ${new Date(riskArea.timestamp).toLocaleString()}</p>
            </div>
          `,
        });

        riskAreaEntitiesRef.current.push(entity);
      }
    });
  }, [incidents, riskAreas, cesiumLoaded]);

  const handleResetView = () => {
    if (viewerRef.current && (viewerRef.current as any).resetView) {
      (viewerRef.current as any).resetView();
    }
  };

  if (!cesiumLoaded) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading 3D Globe...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={cesiumContainerRef} className="w-full h-full" />
      
      {/* Warning badge if no terrain */}
      {!hasTerrain && (
        <div className="absolute top-4 right-4 bg-yellow-600 bg-opacity-90 text-white px-4 py-2 rounded-lg text-sm z-10">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>Terrain unavailable - using ellipsoid</span>
          </div>
        </div>
      )}

      {/* Layer Manager */}
      <div className="absolute top-4 left-4 bg-black bg-opacity-80 text-white p-4 rounded-lg text-sm z-10 min-w-[280px]">
        <h3 className="text-lg font-bold mb-3">Layer Manager</h3>
        
        {/* Time Range Filter */}
        <div className="mb-4">
          <label className="block text-xs font-medium mb-2">Time Range</label>
          <div className="flex gap-2">
            {(['1h', '6h', '24h'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 rounded text-xs transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Severity Filter */}
        <div className="mb-4">
          <label className="block text-xs font-medium mb-2">Severity</label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as any)}
            className="w-full px-3 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600"
          >
            <option value="all">All</option>
            <option value="low">Low</option>
            <option value="med">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        {/* Stats */}
        <div className="mb-4 text-xs text-gray-300">
          <div>Incidents: {incidents.length}</div>
          <div>Risk Areas: {riskAreas.length}</div>
        </div>

        {/* Controls */}
        <div className="space-y-2">
          <button
            onClick={handleResetView}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded transition-colors text-xs"
          >
            Reset View
          </button>
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t border-gray-600">
          <h4 className="text-xs font-medium mb-2">Legend</h4>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white"></div>
              <span>Incident (marker)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 bg-opacity-50 rounded border border-red-500"></div>
              <span>Risk Area (filled region)</span>
            </div>
          </div>
        </div>

        {loading && (
          <div className="mt-2 text-xs text-gray-400">Loading...</div>
        )}
      </div>
    </div>
  );
}

// Helper function to parse color
function parseColor(colorStr: string, opacity: number, cesiumInstance: any): any {
  if (!cesiumInstance) return null;
  
  // Handle hex colors
  if (colorStr.startsWith('#')) {
    const hex = colorStr.slice(1);
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    return cesiumInstance.Color.fromBytes(r, g, b, Math.round(opacity * 255));
  }
  
  // Handle named colors
  const colorMap: Record<string, any> = {
    red: cesiumInstance.Color.RED,
    orange: cesiumInstance.Color.ORANGE,
    yellow: cesiumInstance.Color.YELLOW,
    green: cesiumInstance.Color.GREEN,
    blue: cesiumInstance.Color.BLUE,
    purple: cesiumInstance.Color.PURPLE,
    pink: cesiumInstance.Color.PINK,
    cyan: cesiumInstance.Color.CYAN,
    white: cesiumInstance.Color.WHITE,
    black: cesiumInstance.Color.BLACK,
  };
  
  const baseColor = colorMap[colorStr.toLowerCase()] || cesiumInstance.Color.RED;
  return baseColor.withAlpha(opacity);
}

// Helper function to create incident icon
function createIncidentIcon(color: any, cesiumInstance: any): string {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;

  // Draw warning triangle
  let cssColor = '#FF0000'; // Default red
  if (color && cesiumInstance && typeof color.toCssColorString === 'function') {
    cssColor = color.toCssColorString();
  }
  
  ctx.fillStyle = cssColor;
  ctx.beginPath();
  ctx.moveTo(32, 8);
  ctx.lineTo(56, 56);
  ctx.lineTo(8, 56);
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Draw exclamation mark
  ctx.fillStyle = '#FFFFFF';
  ctx.font = 'bold 32px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('!', 32, 36);

  return canvas.toDataURL();
}
