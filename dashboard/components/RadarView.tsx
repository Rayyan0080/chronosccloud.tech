'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { geoToRadar, radarToCanvas, OTTAWA_RADAR_CENTER, DEFAULT_RADAR_RANGE_KM } from '../lib/radarUtils';

export type RadarObjectType = 'aircraft' | 'incident' | 'risk' | 'threat';

export type RadarObject = {
  id: string;
  type: RadarObjectType;
  x: number; // kilometers from center (East)
  y: number; // kilometers from center (North)
  distance: number; // kilometers from center
  bearing: number; // degrees (0° = North)
  lat: number; // Original latitude
  lon: number; // Original longitude
  timestamp: string;
  severity?: string;
  summary: string;
  source?: string;
  details?: any;
  // For aircraft
  callsign?: string;
  vehicle_id?: string;
  // For threats
  threat_id?: string;
  // Original event data for DroppedPinPanel
  eventData?: any;
  // Animation state
  firstSeenAt?: number; // Timestamp when first rendered
  sweepHighlightUntil?: number; // Timestamp until which sweep highlight is active
  // Movement tracking
  velocity?: number; // m/s
  heading?: number; // degrees (0° = North)
  lastUpdateTime?: number; // Timestamp of last position update
  positionHistory?: Array<{x: number; y: number; time: number}>; // Trail history
  interpolatedX?: number; // Current interpolated X position
  interpolatedY?: number; // Current interpolated Y position
};

type RadarViewProps = {
  objects: RadarObject[];
  showAircraft: boolean;
  showIncidents: boolean;
  showThreats: boolean;
  showRisks: boolean;
  severityFilter?: string[];
  onObjectClick?: (obj: RadarObject) => void;
  onObjectHover?: (obj: RadarObject | null) => void;
};

export default function RadarView({
  objects,
  showAircraft,
  showIncidents,
  showThreats,
  showRisks,
  severityFilter = [],
  onObjectClick,
  onObjectHover,
}: RadarViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const sweepAngleRef = useRef<number>(0);
  const hoveredObjectRef = useRef<RadarObject | null>(null);
  const [hoveredObject, setHoveredObject] = useState<RadarObject | null>(null);
  const noiseTextureRef = useRef<ImageData | null>(null);
  const objectsWithStateRef = useRef<Map<string, RadarObject>>(new Map());
  const previousSweepAngleRef = useRef<number>(0);
  const lastUpdateTimeRef = useRef<number>(Date.now());

  // Track object state and update animation timestamps
  const updateObjectStates = useCallback(() => {
    const now = Date.now();
    const currentSweepAngle = sweepAngleRef.current;
    const previousSweepAngle = previousSweepAngleRef.current;
    
    // Create a set of current object IDs
    const currentObjectIds = new Set(objects.map(obj => obj.id));
    
    // Remove objects that are no longer in the list
    objectsWithStateRef.current.forEach((obj, id) => {
      if (!currentObjectIds.has(id)) {
        objectsWithStateRef.current.delete(id);
      }
    });
    
    // Update or add objects
    objects.forEach((obj) => {
      const existing = objectsWithStateRef.current.get(obj.id);
      const angleDiff = Math.abs(((currentSweepAngle - obj.bearing + 180) % 360) - 180);
      
      // Check if sweep is passing over this object (within 3 degrees)
      const isSweepOver = angleDiff < 3;
      
      // Check if sweep just passed over (wasn't over before, but is now)
      let wasSweepOver = false;
      if (existing) {
        const prevAngleDiff = Math.abs(((previousSweepAngle - obj.bearing + 180) % 360) - 180);
        wasSweepOver = prevAngleDiff < 3;
      }
      
      if (isSweepOver && !wasSweepOver) {
        // Sweep just passed over - trigger highlight
        objectsWithStateRef.current.set(obj.id, {
          ...obj,
          firstSeenAt: existing?.firstSeenAt || now,
          sweepHighlightUntil: now + 300, // 300ms highlight
        });
      } else if (existing) {
        // Update object but preserve state
        objectsWithStateRef.current.set(obj.id, {
          ...obj,
          firstSeenAt: existing.firstSeenAt,
          sweepHighlightUntil: existing.sweepHighlightUntil,
        });
      } else {
        // New object - mark as first seen
        objectsWithStateRef.current.set(obj.id, {
          ...obj,
          firstSeenAt: now,
        });
      }
    });
    
    previousSweepAngleRef.current = currentSweepAngle;
  }, [objects]);

  // Calculate movement interpolation for an object
  const interpolatePosition = useCallback((obj: RadarObject, now: number): {x: number; y: number} => {
    if (!obj.velocity || !obj.heading || !obj.lastUpdateTime) {
      // No movement data, return current position
      return { x: obj.x, y: obj.y };
    }

    // Calculate time since last update (in seconds)
    const timeSinceUpdate = (now - obj.lastUpdateTime) / 1000;
    
    // If update is too old (>30 seconds), don't interpolate
    if (timeSinceUpdate > 30) {
      return { x: obj.x, y: obj.y };
    }

    // Convert velocity from m/s to km/s, then to km per frame (assuming ~60fps)
    const velocityKmPerS = obj.velocity / 1000; // m/s to km/s
    const distanceKm = velocityKmPerS * timeSinceUpdate;

    // Convert heading to radians (0° = North, clockwise)
    const headingRad = ((obj.heading - 90) * Math.PI) / 180; // -90 because canvas 0° is right

    // Calculate movement in radar coordinates (x = East, y = North)
    const dx = distanceKm * Math.cos(headingRad);
    const dy = distanceKm * Math.sin(headingRad);

    return {
      x: obj.x + dx,
      y: obj.y + dy,
    };
  }, []);

  // Sync objects prop to ref and filter, with movement tracking
  useEffect(() => {
    const now = Date.now();
    lastUpdateTimeRef.current = now;

    // Update ref with latest objects from props
    objects.forEach((obj) => {
      const existing = objectsWithStateRef.current.get(obj.id);
      
      // Extract movement data from details
      const details = obj.details || obj.eventData?.details || {};
      const velocity = details.velocity || details.speed; // m/s
      const heading = details.heading || details.bearing; // degrees
      
      // Update position history for trail
      let positionHistory = existing?.positionHistory || [];
      if (existing && (existing.x !== obj.x || existing.y !== obj.y)) {
        // Position changed, add to history
        positionHistory.push({ x: existing.x, y: existing.y, time: existing.lastUpdateTime || now });
        // Keep only last 20 positions (for trail)
        if (positionHistory.length > 20) {
          positionHistory = positionHistory.slice(-20);
        }
      }

      if (existing) {
        // Update existing but preserve animation state and movement
        const updatedObj: RadarObject = {
          ...obj,
          firstSeenAt: existing.firstSeenAt,
          sweepHighlightUntil: existing.sweepHighlightUntil,
          velocity: velocity !== undefined ? velocity : existing.velocity,
          heading: heading !== undefined ? heading : existing.heading,
          lastUpdateTime: now,
          positionHistory: positionHistory,
        };
        
        // Calculate interpolated position
        const interpolated = interpolatePosition(updatedObj, now);
        updatedObj.interpolatedX = interpolated.x;
        updatedObj.interpolatedY = interpolated.y;
        
        objectsWithStateRef.current.set(obj.id, updatedObj);
      } else {
        // New object
        const newObj: RadarObject = {
          ...obj,
          firstSeenAt: now,
          velocity: velocity,
          heading: heading,
          lastUpdateTime: now,
          positionHistory: [],
          interpolatedX: obj.x,
          interpolatedY: obj.y,
        };
        objectsWithStateRef.current.set(obj.id, newObj);
      }
    });
    
    // Remove objects not in props
    const currentIds = new Set(objects.map(o => o.id));
    objectsWithStateRef.current.forEach((obj, id) => {
      if (!currentIds.has(id)) {
        objectsWithStateRef.current.delete(id);
      }
    });
  }, [objects, interpolatePosition]);

  // Filter objects based on visibility and severity
  const filteredObjects = Array.from(objectsWithStateRef.current.values()).filter((obj) => {
    // Type filter
    if (obj.type === 'aircraft' && !showAircraft) return false;
    if (obj.type === 'incident' && !showIncidents) return false;
    if (obj.type === 'threat' && !showThreats) return false;
    if (obj.type === 'risk' && !showRisks) return false;
    
    // Severity filter
    if (severityFilter.length > 0 && obj.severity) {
      if (!severityFilter.includes(obj.severity)) return false;
    }
    
    return true;
  });

  // Generate procedural noise texture (cached)
  const generateNoiseTexture = useCallback((width: number, height: number, ctx: CanvasRenderingContext2D): ImageData => {
    const imageData = ctx.createImageData(width, height);
    const data = imageData.data;
    
    // Simple noise pattern - subtle random pixels
    for (let i = 0; i < data.length; i += 4) {
      const noise = Math.random() * 0.15; // Subtle noise (0-15% opacity)
      data[i] = 0; // R
      data[i + 1] = Math.floor(255 * noise); // G (green radar)
      data[i + 2] = 0; // B
      data[i + 3] = Math.floor(255 * noise * 0.3); // A (very subtle)
    }
    
    return imageData;
  }, []);

  // Calculate movement interpolation for an object (used in draw)
  const interpolatePositionForDraw = useCallback((obj: RadarObject, now: number): {x: number; y: number} => {
    if (!obj.velocity || !obj.heading || !obj.lastUpdateTime) {
      return { x: obj.x, y: obj.y };
    }
    const timeSinceUpdate = (now - obj.lastUpdateTime) / 1000;
    if (timeSinceUpdate > 30) {
      return { x: obj.x, y: obj.y };
    }
    const velocityKmPerS = obj.velocity / 1000;
    const distanceKm = velocityKmPerS * timeSinceUpdate;
    const headingRad = ((obj.heading - 90) * Math.PI) / 180;
    const dx = distanceKm * Math.cos(headingRad);
    const dy = distanceKm * Math.sin(headingRad);
    return { x: obj.x + dx, y: obj.y + dy };
  }, []);

  // Draw radar screen
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxKm = DEFAULT_RADAR_RANGE_KM;

    // Update object states
    updateObjectStates();

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Dark green radar background
    ctx.fillStyle = '#0a1a0a';
    ctx.fillRect(0, 0, width, height);

    // Draw noise texture overlay (cached, regenerated on resize)
    if (!noiseTextureRef.current || 
        noiseTextureRef.current.width !== width || 
        noiseTextureRef.current.height !== height) {
      noiseTextureRef.current = generateNoiseTexture(width, height, ctx);
    }
    ctx.putImageData(noiseTextureRef.current, 0, 0);

    // Draw grid circles (5, 10, 25, 50, 60 km)
    ctx.strokeStyle = '#00ff0020'; // Dark green, semi-transparent
    ctx.lineWidth = 1;
    const rings = [5, 10, 25, 50, 60];
    const scale = Math.min(width, height) / (2 * maxKm);

    rings.forEach((radiusKm) => {
      const radiusPx = radiusKm * scale;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radiusPx, 0, 2 * Math.PI);
      ctx.stroke();
    });

    // Draw cardinal directions
    ctx.strokeStyle = '#00ff0040';
    ctx.lineWidth = 1;
    const directions = [
      { angle: 0, label: 'N' },
      { angle: 90, label: 'E' },
      { angle: 180, label: 'S' },
      { angle: 270, label: 'W' },
    ];

    directions.forEach((dir) => {
      const angleRad = ((dir.angle - 90) * Math.PI) / 180; // -90 because canvas 0° is right
      const endX = centerX + Math.cos(angleRad) * (Math.min(width, height) / 2);
      const endY = centerY + Math.sin(angleRad) * (Math.min(width, height) / 2);
      
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      // Draw labels
      const labelX = centerX + Math.cos(angleRad) * (Math.min(width, height) / 2 + 20);
      const labelY = centerY + Math.sin(angleRad) * (Math.min(width, height) / 2 + 20);
      ctx.fillStyle = '#00ff0080';
      ctx.font = '12px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(dir.label, labelX, labelY);
    });

    // Draw range labels
    ctx.fillStyle = '#00ff0060';
    ctx.font = '10px monospace';
    ctx.textAlign = 'left';
    rings.forEach((radiusKm) => {
      const radiusPx = radiusKm * scale;
      ctx.fillText(`${radiusKm}km`, centerX + radiusPx + 5, centerY - 5);
    });

    // Draw sweep line (rotating)
    const sweepAngle = sweepAngleRef.current;
    const sweepAngleRad = ((sweepAngle - 90) * Math.PI) / 180; // -90 because canvas 0° is right
    const sweepLength = Math.min(width, height) / 2;
    const sweepEndX = centerX + Math.cos(sweepAngleRad) * sweepLength;
    const sweepEndY = centerY + Math.sin(sweepAngleRad) * sweepLength;

    // Sweep gradient
    const gradient = ctx.createLinearGradient(centerX, centerY, sweepEndX, sweepEndY);
    gradient.addColorStop(0, '#00ff0080');
    gradient.addColorStop(0.5, '#00ff0040');
    gradient.addColorStop(1, '#00ff0000');

    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(sweepEndX, sweepEndY);
    ctx.stroke();

    // Draw sweep arc (fading wedge)
    const sweepArcStart = sweepAngle - 2; // 2 degree wedge
    const sweepArcEnd = sweepAngle + 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(
      centerX,
      centerY,
      sweepLength,
      ((sweepArcStart - 90) * Math.PI) / 180,
      ((sweepArcEnd - 90) * Math.PI) / 180
    );
    ctx.closePath();
    ctx.fillStyle = '#00ff0010';
    ctx.fill();

    // Draw blips with movement interpolation
    const now = Date.now();
    filteredObjects.forEach((obj) => {
      // Update interpolation in real-time for smooth movement
      if (obj.velocity && obj.heading && obj.lastUpdateTime) {
        const interpolated = interpolatePositionForDraw(obj, now);
        obj.interpolatedX = interpolated.x;
        obj.interpolatedY = interpolated.y;
      }
      
      // Use interpolated position if available, otherwise use actual position
      const displayX = obj.interpolatedX !== undefined ? obj.interpolatedX : obj.x;
      const displayY = obj.interpolatedY !== undefined ? obj.interpolatedY : obj.y;
      
      const { canvasX, canvasY } = radarToCanvas(displayX, displayY, width, height, maxKm);
      
      // Draw movement trail for moving objects
      if (obj.positionHistory && obj.positionHistory.length > 1 && obj.velocity && obj.velocity > 0) {
        ctx.strokeStyle = obj.type === 'aircraft' ? '#00ff0040' : obj.type === 'threat' ? '#ff000040' : '#ffff0040';
        ctx.lineWidth = 1;
        ctx.beginPath();
        
        // Draw trail from history
        let firstPoint = true;
        obj.positionHistory.forEach((point, idx) => {
          const trailAge = now - point.time;
          const fadeAlpha = Math.max(0, 1 - trailAge / 10000); // Fade over 10 seconds
          
          if (fadeAlpha > 0) {
            const { canvasX: trailX, canvasY: trailY } = radarToCanvas(point.x, point.y, width, height, maxKm);
            if (firstPoint) {
              ctx.moveTo(trailX, trailY);
              firstPoint = false;
            } else {
              ctx.lineTo(trailX, trailY);
            }
          }
        });
        
          // Draw line to current position
          if (!firstPoint) {
            ctx.lineTo(canvasX, canvasY);
            ctx.stroke();
          }
      }
      
      const isHovered = hoveredObject?.id === obj.id;
      const isThreat = obj.type === 'threat';
      
      // Calculate brightness based on animation state
      let brightness = 1.0;
      let glowRadius = 0;
      
      // Blip persistence: brighten when first seen (fade over 1 second)
      if (obj.firstSeenAt) {
        const age = now - obj.firstSeenAt;
        if (age < 1000) {
          brightness = 1.0 + (1.0 - age / 1000) * 0.5; // Up to 50% brighter, fading over 1s
        }
      }
      
      // Sweep highlight: glow brighter when sweep passes over (300ms)
      if (obj.sweepHighlightUntil && now < obj.sweepHighlightUntil) {
        const timeLeft = obj.sweepHighlightUntil - now;
        const highlightIntensity = timeLeft / 300; // Fade from 1.0 to 0.0 over 300ms
        brightness = Math.max(brightness, 1.0 + highlightIntensity * 0.8); // Up to 80% brighter
        glowRadius = highlightIntensity * 8; // Glow radius up to 8px
      }
      
      // Draw threat pulse (red pulsing ring)
      if (isThreat) {
        const pulseTime = Date.now() / 1000;
        const pulseRadius = 8 + Math.sin(pulseTime * 3) * 4; // Pulsing between 4-12px
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(canvasX, canvasY, pulseRadius, 0, 2 * Math.PI);
        ctx.stroke();
      }

      // Draw glow effect for sweep highlight
      if (glowRadius > 0) {
        const gradient = ctx.createRadialGradient(canvasX, canvasY, 0, canvasX, canvasY, glowRadius);
        gradient.addColorStop(0, 'rgba(0, 255, 0, 0.6)');
        gradient.addColorStop(0.5, 'rgba(0, 255, 0, 0.2)');
        gradient.addColorStop(1, 'rgba(0, 255, 0, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(canvasX, canvasY, glowRadius, 0, 2 * Math.PI);
        ctx.fill();
      }

      // Draw blip based on type
      const baseRadius = isHovered ? 5 : 3;
      const radius = baseRadius * (1 + (brightness - 1.0) * 0.3); // Slightly larger when bright
      
      ctx.beginPath();
      ctx.arc(canvasX, canvasY, radius, 0, 2 * Math.PI);
      
      // Apply brightness to colors
      let baseColor: string;
      switch (obj.type) {
        case 'aircraft':
          baseColor = isHovered ? '#00ffff' : '#00ff00';
          break;
        case 'incident':
          baseColor = isHovered ? '#ff8800' : '#ff6600';
          break;
        case 'threat':
          baseColor = '#ff0000';
          break;
        case 'risk':
          baseColor = '#ffaa00';
          break;
        default:
          baseColor = '#ffffff';
      }
      
      // Brighten color
      if (brightness > 1.0) {
        // Parse hex color
        const hex = baseColor.replace('#', '');
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        const brightR = Math.min(255, Math.floor(r * brightness));
        const brightG = Math.min(255, Math.floor(g * brightness));
        const brightB = Math.min(255, Math.floor(b * brightness));
        ctx.fillStyle = `rgb(${brightR}, ${brightG}, ${brightB})`;
      } else {
        ctx.fillStyle = baseColor;
      }
      
      ctx.fill();
      
      // Draw hover highlight
      if (isHovered) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

    // Update sweep angle (360° rotation every 4 seconds)
    sweepAngleRef.current = (sweepAngleRef.current + 0.5) % 360;

    // Continue animation loop for smooth real-time updates
    animationFrameRef.current = requestAnimationFrame(draw);
  }, [objects, filteredObjects, hoveredObject, updateObjectStates, generateNoiseTexture, showAircraft, showIncidents, showThreats, showRisks, severityFilter, interpolatePositionForDraw]);

  // Handle mouse move for hover
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const maxKm = DEFAULT_RADAR_RANGE_KM;
    const scale = Math.min(width, height) / (2 * maxKm);

    // Convert canvas coordinates back to radar coordinates
    const radarX = (x - centerX) / scale;
    const radarY = (centerY - y) / scale; // Invert y

    // Find nearest object within 5km
    let nearest: RadarObject | null = null;
    let minDist = 5; // 5km threshold

    filteredObjects.forEach((obj) => {
      const dx = obj.x - radarX;
      const dy = obj.y - radarY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < minDist) {
        minDist = dist;
        nearest = obj;
      }
    });

    if (nearest !== hoveredObjectRef.current) {
      hoveredObjectRef.current = nearest;
      setHoveredObject(nearest);
      if (onObjectHover) {
        onObjectHover(nearest);
      }
    }
  }, [filteredObjects, onObjectHover]);

  // Handle click
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hoveredObjectRef.current && onObjectClick) {
      onObjectClick(hoveredObjectRef.current);
    }
  }, [onObjectClick]);

  // Start animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Set canvas size - use maximum available space
    const resizeCanvas = () => {
      const container = canvas.parentElement;
      if (container) {
        // Use 100% of the smaller dimension, with a very large minimum size
        const availableWidth = container.clientWidth - 4; // Minimal padding
        const availableHeight = container.clientHeight - 4; // Minimal padding
        // Use the full available space, minimum 1200px
        const size = Math.max(1200, Math.min(availableWidth, availableHeight));
        canvas.width = size;
        canvas.height = size;
      }
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Start animation loop
    animationFrameRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [draw]);

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <canvas
        ref={canvasRef}
        className="border border-green-500 border-opacity-30 rounded-lg"
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        style={{ 
          cursor: hoveredObject ? 'pointer' : 'default',
          maxWidth: '100%',
          maxHeight: '100%',
        }}
      />
      
      {/* Tooltip */}
      {hoveredObject && (
        <div
          className="absolute bg-dark-surface border border-green-500 border-opacity-50 rounded-lg px-3 py-2 text-white text-xs pointer-events-none z-10"
          style={{
            left: '50%',
            top: '20px',
            transform: 'translateX(-50%)',
            maxWidth: '300px',
          }}
        >
          <div className="font-semibold">{hoveredObject.summary}</div>
          <div className="text-gray-400 mt-1">
            Type: {hoveredObject.type} | Distance: {hoveredObject.distance.toFixed(1)}km | Bearing: {hoveredObject.bearing.toFixed(0)}°
          </div>
          {hoveredObject.source && (
            <div className="text-gray-500 mt-1">Source: {hoveredObject.source}</div>
          )}
        </div>
      )}
    </div>
  );
}

