'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

// Simple airport code to lat/lon mapping (for demo purposes)
const AIRPORT_COORDS: Record<string, { lat: number; lon: number }> = {
  KJFK: { lat: 40.6413, lon: -73.7781 }, // New York JFK
  KLAX: { lat: 33.9425, lon: -118.4081 }, // Los Angeles
  KORD: { lat: 41.9742, lon: -87.9073 }, // Chicago O'Hare
  KDFW: { lat: 32.8998, lon: -97.0403 }, // Dallas/Fort Worth
  KSEA: { lat: 47.4502, lon: -122.3088 }, // Seattle
  KDEN: { lat: 39.8561, lon: -104.6737 }, // Denver
  KATL: { lat: 33.6407, lon: -84.4277 }, // Atlanta
  KMIA: { lat: 25.7933, lon: -80.2906 }, // Miami
  KSFO: { lat: 37.6213, lon: -122.3790 }, // San Francisco
  PHX: { lat: 33.4342, lon: -112.0116 }, // Phoenix
  BOS: { lat: 42.3656, lon: -71.0096 }, // Boston
  PHL: { lat: 39.8719, lon: -75.2411 }, // Philadelphia
  STL: { lat: 38.7487, lon: -90.3700 }, // St. Louis
  MCI: { lat: 39.2976, lon: -94.7139 }, // Kansas City
  DEN: { lat: 39.8561, lon: -104.6737 }, // Denver
};

// Convert lat/lon to 3D coordinates (simple projection)
function latLonTo3D(lat: number, lon: number, altitude: number = 0): THREE.Vector3 {
  // Simple equirectangular projection scaled for visualization
  const scale = 0.1; // Scale factor for visualization
  const x = lon * scale;
  const y = altitude / 1000; // Convert feet to kilometers for visualization
  const z = -lat * scale; // Negative for correct orientation
  return new THREE.Vector3(x, y, z);
}

// Get airport coordinates or use default
function getAirportCoords(code: string): { lat: number; lon: number } {
  return AIRPORT_COORDS[code] || { lat: 40.0, lon: -100.0 }; // Default to center of US
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

type Airspace3DMapProps = {
  trajectories: Trajectory[];
  conflicts: Conflict[];
  hotspots: Hotspot[];
};

export default function Airspace3DMap({ trajectories, conflicts, hotspots }: Airspace3DMapProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<{ rotationX: number; rotationY: number; zoom: number }>({
    rotationX: 0,
    rotationY: 0,
    zoom: 50,
  });
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 30, 50);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 50, 50);
    scene.add(directionalLight);

    // Grid helper (ground plane)
    const gridHelper = new THREE.GridHelper(20, 20, 0x333333, 0x222222);
    scene.add(gridHelper);

    // Axes helper
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    // Create trajectory lines
    trajectories.forEach((traj) => {
      if (traj.route && traj.route.length >= 2) {
        const points: THREE.Vector3[] = [];
        
        traj.route.forEach((waypoint) => {
          const coords = getAirportCoords(waypoint);
          const point = latLonTo3D(coords.lat, coords.lon, traj.altitude || 35000);
          points.push(point);
        });

        if (points.length >= 2) {
          const geometry = new THREE.BufferGeometry().setFromPoints(points);
          const material = new THREE.LineBasicMaterial({
            color: 0x00ff00,
            linewidth: 2,
          });
          const line = new THREE.Line(geometry, material);
          scene.add(line);

          // Add flight ID label at start point
          const sprite = createTextSprite(traj.flight_id, 0x00ff00);
          sprite.position.copy(points[0]);
          sprite.position.y += 2;
          scene.add(sprite);
        }
      }
    });

    // Create conflict markers
    conflicts.forEach((conflict) => {
      const loc = conflict.conflict_location;
      const pos = latLonTo3D(loc.latitude, loc.longitude, loc.altitude);

      // Red sphere for conflict
      const geometry = new THREE.SphereGeometry(0.5, 16, 16);
      const material = new THREE.MeshBasicMaterial({
        color: conflict.severity_level === 'high' ? 0xff0000 : 0xff6600,
      });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.copy(pos);
      scene.add(sphere);

      // Pulsing animation
      const pulse = () => {
        const scale = 1 + Math.sin(Date.now() * 0.005) * 0.3;
        sphere.scale.set(scale, scale, scale);
      };
      setInterval(pulse, 16);
    });

    // Create hotspot spheres
    hotspots.forEach((hotspot) => {
      const loc = hotspot.location;
      const pos = latLonTo3D(loc.latitude, loc.longitude, 30000);

      // Semi-transparent sphere for hotspot
      const radius = (loc.radius_nm || 25) * 0.1; // Scale radius
      const geometry = new THREE.SphereGeometry(radius, 32, 32);
      const material = new THREE.MeshBasicMaterial({
        color: hotspot.severity === 'high' ? 0xffaa00 : 0xffff00,
        transparent: true,
        opacity: 0.3,
        wireframe: true,
      });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.copy(pos);
      scene.add(sphere);
    });

    // Mouse controls
    const handleMouseDown = (e: MouseEvent) => {
      isDraggingRef.current = true;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingRef.current) {
        const deltaX = e.clientX - lastMousePosRef.current.x;
        const deltaY = e.clientY - lastMousePosRef.current.y;

        controlsRef.current.rotationY += deltaX * 0.01;
        controlsRef.current.rotationX += deltaY * 0.01;

        // Update camera position based on rotation
        const radius = controlsRef.current.zoom;
        const x = radius * Math.sin(controlsRef.current.rotationY) * Math.cos(controlsRef.current.rotationX);
        const y = radius * Math.sin(controlsRef.current.rotationX);
        const z = radius * Math.cos(controlsRef.current.rotationY) * Math.cos(controlsRef.current.rotationX);

        camera.position.set(x, y, z);
        camera.lookAt(0, 0, 0);
        
        lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      }
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      controlsRef.current.zoom += e.deltaY * 0.01;
      controlsRef.current.zoom = Math.max(10, Math.min(100, controlsRef.current.zoom));

      const radius = controlsRef.current.zoom;
      const x = radius * Math.sin(controlsRef.current.rotationY) * Math.cos(controlsRef.current.rotationX);
      const y = radius * Math.sin(controlsRef.current.rotationX);
      const z = radius * Math.cos(controlsRef.current.rotationY) * Math.cos(controlsRef.current.rotationX);

      camera.position.set(x, y, z);
      camera.lookAt(0, 0, 0);
    };

    renderer.domElement.addEventListener('mousedown', handleMouseDown);
    renderer.domElement.addEventListener('mousemove', handleMouseMove);
    renderer.domElement.addEventListener('mouseup', handleMouseUp);
    renderer.domElement.addEventListener('wheel', handleWheel);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    // Handle resize
    const handleResize = () => {
      if (!mountRef.current || !camera || !renderer) return;
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('mousedown', handleMouseDown);
      renderer.domElement.removeEventListener('mousemove', handleMouseMove);
      renderer.domElement.removeEventListener('mouseup', handleMouseUp);
      renderer.domElement.removeEventListener('wheel', handleWheel);
      if (mountRef.current && renderer.domElement.parentNode) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [trajectories, conflicts, hotspots]);

  return (
    <div className="relative w-full h-full">
      <div ref={mountRef} className="w-full h-full" />
      <div className="absolute top-4 left-4 bg-black bg-opacity-70 text-white p-3 rounded-lg text-sm">
        <div className="space-y-1">
          <div>🖱️ Drag to rotate</div>
          <div>🔍 Scroll to zoom</div>
          <div className="mt-2 pt-2 border-t border-gray-600">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
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

// Helper function to create text sprites (simplified version)
function createTextSprite(text: string, color: number): THREE.Sprite {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d')!;
  canvas.width = 256;
  canvas.height = 64;

  context.fillStyle = '#000000';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
  context.font = '24px Arial';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
  const sprite = new THREE.Sprite(spriteMaterial);
  sprite.scale.set(2, 0.5, 1);

  return sprite;
}

