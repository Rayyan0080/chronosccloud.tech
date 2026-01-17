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
    
    // Set Cesium Ion access token (optional - uses default if not set)
    // You can get a free token at https://cesium.com/ion/
    // Cesium.Ion.defaultAccessToken = 'YOUR_TOKEN_HERE';
  } catch (e) {
    console.error('Failed to load Cesium:', e);
  }
}

// Airport code to lat/lon mapping
const AIRPORT_COORDS: Record<string, { lat: number; lon: number }> = {
  KJFK: { lat: 40.6413, lon: -73.7781 },
  KLAX: { lat: 33.9425, lon: -118.4081 },
  KORD: { lat: 41.9742, lon: -87.9073 },
  KDFW: { lat: 32.8998, lon: -97.0403 },
  KSEA: { lat: 47.4502, lon: -122.3088 },
  KDEN: { lat: 39.8561, lon: -104.6737 },
  KATL: { lat: 33.6407, lon: -84.4277 },
  KMIA: { lat: 25.7933, lon: -80.2906 },
  KSFO: { lat: 37.6213, lon: -122.3790 },
  PHX: { lat: 33.4342, lon: -112.0116 },
  BOS: { lat: 42.3656, lon: -71.0096 },
  PHL: { lat: 39.8719, lon: -75.2411 },
  STL: { lat: 38.7487, lon: -90.3700 },
  MCI: { lat: 39.2976, lon: -94.7139 },
  DEN: { lat: 39.8561, lon: -104.6737 },
};

function getAirportCoords(code: string): { lat: number; lon: number } {
  return AIRPORT_COORDS[code] || { lat: 40.0, lon: -100.0 };
}

type Trajectory = {
  flight_id: string;
  route: string[];
  origin: string;
  destination: string;
  altitude: number;
};

type Conflict = {
  conflict_id: string;
  conflict_location: { latitude: number; longitude: number; altitude: number };
  flight_ids: string[];
  severity_level: string;
};

type Hotspot = {
  hotspot_id: string;
  location: { latitude: number; longitude: number; radius_nm: number };
  affected_flights: string[];
  severity: string;
};

type AirspaceCesiumMapProps = {
  trajectories: Trajectory[];
  conflicts: Conflict[];
  hotspots: Hotspot[];
};

export default function AirspaceCesiumMap({ trajectories, conflicts, hotspots }: AirspaceCesiumMapProps) {
  const cesiumContainerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [cesiumLoaded, setCesiumLoaded] = useState(false);

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
    if (!cesiumContainerRef.current || !Cesium || !cesiumLoaded) return;

    // Clean up existing viewer if it exists
    if (viewerRef.current) {
      viewerRef.current.destroy();
      viewerRef.current = null;
    }

    // Store Cesium reference
    const cesiumInstance = Cesium;

    // Initialize Cesium Viewer
    // Use default terrain provider (works without Ion token)
    let terrainProvider;
    try {
      // Use EllipsoidTerrainProvider (default, no external dependencies)
      terrainProvider = new cesiumInstance.EllipsoidTerrainProvider();
    } catch (e) {
      console.warn('Could not create terrain provider, using default');
      terrainProvider = undefined; // Will use Viewer default
    }

    // Use OpenStreetMap imagery (works without Ion token)
    let imageryProvider;
    try {
      imageryProvider = new cesiumInstance.OpenStreetMapImageryProvider({
        url: 'https://a.tile.openstreetmap.org/',
      });
    } catch (e) {
      console.warn('Could not create imagery provider, using default');
      imageryProvider = undefined; // Will use Viewer default
    }

    const viewer = new cesiumInstance.Viewer(cesiumContainerRef.current, {
      terrainProvider: terrainProvider,
      imageryProvider: imageryProvider,
      baseLayerPicker: false,
      vrButton: false,
      geocoder: true,
      homeButton: true,
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

    // Set initial camera position (center of US, zoomed to show flights)
    viewer.camera.setView({
      destination: cesiumInstance.Cartesian3.fromDegrees(-100.0, 40.0, 5000000),
    });

    // Add flight trajectories
    trajectories.forEach((traj) => {
      if (traj.route && traj.route.length >= 2) {
        const positions: any[] = [];
        
        traj.route.forEach((waypoint) => {
          const coords = getAirportCoords(waypoint);
          const position = cesiumInstance.Cartesian3.fromDegrees(
            coords.lon,
            coords.lat,
            (traj.altitude || 35000) * 0.3048 // Convert feet to meters
          );
          positions.push(position);
        });

        if (positions.length >= 2) {
          // Create polyline for trajectory
          viewer.entities.add({
            polyline: {
              positions: positions,
              width: 3,
              material: cesiumInstance.Color.CYAN,
              clampToGround: false,
              arcType: cesiumInstance.ArcType.GEODESIC,
            },
            label: {
              text: traj.flight_id,
              font: '14pt sans-serif',
              fillColor: cesiumInstance.Color.CYAN,
              outlineColor: cesiumInstance.Color.BLACK,
              outlineWidth: 2,
              style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
              pixelOffset: new cesiumInstance.Cartesian2(0, -40),
            },
          });

          // Add waypoint markers
          positions.forEach((pos, index) => {
            viewer.entities.add({
              position: pos,
              point: {
                pixelSize: 8,
                color: cesiumInstance.Color.YELLOW,
                outlineColor: cesiumInstance.Color.BLACK,
                outlineWidth: 2,
                heightReference: cesiumInstance.HeightReference.NONE,
              },
              label: {
                text: traj.route[index] || '',
                font: '10pt sans-serif',
                fillColor: cesiumInstance.Color.WHITE,
                outlineColor: cesiumInstance.Color.BLACK,
                outlineWidth: 2,
                style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
                pixelOffset: new cesiumInstance.Cartesian2(0, -25),
              },
            });
          });
        }
      }
    });

    // Add conflict markers
    conflicts.forEach((conflict) => {
      const loc = conflict.conflict_location;
      const position = cesiumInstance.Cartesian3.fromDegrees(
        loc.longitude,
        loc.latitude,
        loc.altitude * 0.3048 // Convert feet to meters
      );

      const color = conflict.severity_level === 'high' 
        ? cesiumInstance.Color.RED 
        : conflict.severity_level === 'critical'
        ? cesiumInstance.Color.MAGENTA
        : cesiumInstance.Color.ORANGE;

      viewer.entities.add({
        position: position,
        point: {
          pixelSize: 15,
          color: color,
          outlineColor: cesiumInstance.Color.WHITE,
          outlineWidth: 2,
          heightReference: cesiumInstance.HeightReference.NONE,
        },
        billboard: {
          image: createConflictIcon(color),
          scale: 1.5,
          verticalOrigin: cesiumInstance.VerticalOrigin.BOTTOM,
        },
        label: {
          text: conflict.conflict_id,
          font: '12pt sans-serif',
          fillColor: color,
          outlineColor: cesiumInstance.Color.BLACK,
          outlineWidth: 2,
          style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new cesiumInstance.Cartesian2(0, -30),
        },
        description: `
          <div style="padding: 10px;">
            <h3>Conflict: ${conflict.conflict_id}</h3>
            <p><strong>Severity:</strong> ${conflict.severity_level}</p>
            <p><strong>Affected Flights:</strong> ${conflict.flight_ids.join(', ')}</p>
            <p><strong>Location:</strong> ${loc.latitude.toFixed(4)}, ${loc.longitude.toFixed(4)}</p>
            <p><strong>Altitude:</strong> ${loc.altitude.toLocaleString()} ft</p>
          </div>
        `,
      });
    });

    // Add hotspot areas
    hotspots.forEach((hotspot) => {
      const loc = hotspot.location;
      const center = cesiumInstance.Cartesian3.fromDegrees(
        loc.longitude,
        loc.latitude,
        (loc.altitude || 30000) * 0.3048
      );

      const radius = (loc.radius_nm || 25) * 1852; // Convert nautical miles to meters
      const color = hotspot.severity === 'high' 
        ? cesiumInstance.Color.RED.withAlpha(0.3)
        : cesiumInstance.Color.YELLOW.withAlpha(0.3);

      viewer.entities.add({
        position: center,
        ellipse: {
          semiMajorAxis: radius,
          semiMinorAxis: radius,
          material: color,
          outline: true,
          outlineColor: hotspot.severity === 'high' ? cesiumInstance.Color.RED : cesiumInstance.Color.YELLOW,
          outlineWidth: 2,
          heightReference: cesiumInstance.HeightReference.NONE,
        },
        label: {
          text: hotspot.hotspot_id,
          font: '12pt sans-serif',
          fillColor: cesiumInstance.Color.YELLOW,
          outlineColor: cesiumInstance.Color.BLACK,
          outlineWidth: 2,
          style: cesiumInstance.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new cesiumInstance.Cartesian2(0, -40),
        },
        description: `
          <div style="padding: 10px;">
            <h3>Hotspot: ${hotspot.hotspot_id}</h3>
            <p><strong>Severity:</strong> ${hotspot.severity}</p>
            <p><strong>Affected Flights:</strong> ${hotspot.affected_flights.length}</p>
            <p><strong>Location:</strong> ${loc.latitude.toFixed(4)}, ${loc.longitude.toFixed(4)}</p>
            <p><strong>Radius:</strong> ${loc.radius_nm} nm</p>
          </div>
        `,
      });
    });

    // Cleanup
    return () => {
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, [trajectories, conflicts, hotspots, cesiumLoaded]);

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
      <div className="absolute top-4 left-4 bg-black bg-opacity-70 text-white p-3 rounded-lg text-sm z-10">
        <div className="space-y-1">
          <div>🖱️ Drag to rotate</div>
          <div>🔍 Scroll to zoom</div>
          <div>🔄 Right-click + drag to pan</div>
          <div className="mt-2 pt-2 border-t border-gray-600">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-cyan-500 rounded"></div>
              <span>Trajectories</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Conflicts</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded opacity-30"></div>
              <span>Hotspots</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper function to create conflict icon
function createConflictIcon(color: any): string {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;

  // Draw warning triangle
  ctx.fillStyle = color.toCssColorString();
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

