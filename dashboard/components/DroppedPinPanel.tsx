'use client';

import { useState } from 'react';

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
  incident_type?: string;
  description?: string;
  status?: string;
  source?: string;
  details?: any;
};

type DroppedPinPanelProps = {
  incident: GeoIncident;
  onClose: () => void;
  onFocus: () => void;
};

export default function DroppedPinPanel({ incident, onFocus, onClose }: DroppedPinPanelProps) {
  const [copied, setCopied] = useState(false);

  const [lon, lat] = incident.geometry.coordinates;
  const coordsString = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;

  const handleCopyCoords = () => {
    navigator.clipboard.writeText(coordsString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenInOSM = () => {
    window.open(`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=16`, '_blank');
  };

  // Determine severity color
  const getSeverityColor = () => {
    if (incident.severity === 'high' || incident.severity === 'critical' || incident.severity === 'moderate' || incident.severity === 'error') {
      return 'bg-red-500';
    } else if (incident.severity === 'med' || incident.severity === 'warning') {
      return 'bg-orange-500';
    }
    return 'bg-yellow-500';
  };

  const getSeverityLabel = () => {
    return incident.severity.charAt(0).toUpperCase() + incident.severity.slice(1);
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 md:bottom-4 md:left-4 md:right-auto md:w-96 z-20">
      <div className="bg-dark-surface rounded-t-2xl md:rounded-2xl shadow-2xl border border-dark-border overflow-hidden">
        {/* Header with rounded top */}
        <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-dark-border">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <h3 className="text-sm font-semibold text-white">Dropped pin</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Title/Summary */}
          <div>
            <h4 className="text-lg font-semibold text-white mb-1">{incident.summary}</h4>
            {incident.incident_type && (
              <p className="text-sm text-gray-400">{incident.incident_type}</p>
            )}
          </div>

          {/* Chips */}
          <div className="flex flex-wrap gap-2">
            {incident.source && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500 bg-opacity-20 text-blue-300 border border-blue-500 border-opacity-30">
                {incident.source}
              </span>
            )}
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor()} bg-opacity-20 text-white border border-opacity-30`}
            >
              {getSeverityLabel()}
            </span>
            {incident.status && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-500 bg-opacity-20 text-gray-300 border border-gray-500 border-opacity-30">
                {incident.status}
              </span>
            )}
          </div>

          {/* Description */}
          {incident.description && (
            <div>
              <p className="text-sm text-gray-300">{incident.description}</p>
            </div>
          )}

          {/* Coordinates */}
          <div className="pt-2 border-t border-dark-border">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Coordinates</span>
              <button
                onClick={handleCopyCoords}
                className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <p className="text-sm text-gray-300 font-mono mt-1">{coordsString}</p>
          </div>

          {/* Timestamp */}
          <div>
            <span className="text-xs text-gray-400">Time</span>
            <p className="text-sm text-gray-300 mt-1">
              {new Date(incident.timestamp).toLocaleString()}
            </p>
          </div>

          {/* Additional Details */}
          {incident.details && typeof incident.details === 'object' && (
            <div className="pt-2 border-t border-dark-border">
              <span className="text-xs text-gray-400">Details</span>
              <pre className="text-xs text-gray-300 mt-1 bg-gray-900 p-2 rounded overflow-x-auto">
                {JSON.stringify(incident.details, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-4 py-3 bg-gray-800 border-t border-dark-border flex gap-2">
          <button
            onClick={onFocus}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Focus
          </button>
          <button
            onClick={handleOpenInOSM}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Open in OSM
          </button>
        </div>
      </div>
    </div>
  );
}

