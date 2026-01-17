import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AutonomyBadge from '../../components/AutonomyBadge';
import AirspaceCesiumMap from '../../components/AirspaceCesiumMap';

type Tab = 'upload' | 'overview' | 'map' | 'conflicts' | 'hotspots' | 'validation';

export default function Airspace() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [autonomyMode, setAutonomyMode] = useState<string>('RULES');

  useEffect(() => {
    // Fetch autonomy mode from API
    const fetchAutonomyMode = async () => {
      try {
        const res = await fetch('/api/airspace/autonomy-mode');
        const data = await res.json();
        setAutonomyMode(data.autonomy_mode || 'RULES');
      } catch (error) {
        console.error('Error fetching autonomy mode:', error);
        setAutonomyMode('RULES');
      }
    };
    fetchAutonomyMode();
    // Refresh every 10 seconds
    const interval = setInterval(fetchAutonomyMode, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Set initial tab from query
    const tab = (router.query.tab as Tab) || 'upload';
    if (['upload', 'overview', 'map', 'conflicts', 'hotspots', 'validation'].includes(tab)) {
      setActiveTab(tab);
    }
  }, [router.query]);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'upload', label: 'Upload Plan' },
    { id: 'overview', label: 'Overview' },
    { id: 'map', label: 'Map' },
    { id: 'conflicts', label: 'Conflicts' },
    { id: 'hotspots', label: 'Hotspots' },
    { id: 'validation', label: 'Validation' },
  ];

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    router.push(`/airspace?tab=${tab}`, undefined, { shallow: true });
  };

  return (
    <div className="space-y-6">
      {/* Persistent Banner */}
      <div className="bg-yellow-900 border-l-4 border-yellow-500 p-4 rounded">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm font-medium text-yellow-200">
              <strong>SYNTHETIC DATA — NOT FOR OPERATIONAL USE</strong>
            </p>
            <p className="mt-1 text-sm text-yellow-300">
              This system processes synthetic flight plan data for demonstration purposes only.
              DO NOT use for operational air traffic control or real flight planning.
            </p>
          </div>
        </div>
      </div>

      {/* Header with Autonomy Mode */}
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold text-white">Airspace Management</h1>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-400">
            <span className="mr-2">Autonomy Mode:</span>
            <AutonomyBadge level={autonomyMode} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`
                whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'upload' && <UploadPlanTab />}
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'map' && <MapTab />}
        {activeTab === 'conflicts' && <ConflictsTab />}
        {activeTab === 'hotspots' && <HotspotsTab />}
        {activeTab === 'validation' && <ValidationTab />}
      </div>
    </div>
  );
}

// Upload Plan Tab Component
function UploadPlanTab() {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadStatus(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setUploadStatus({ type: 'error', message: 'Please select a file' });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      // Read file as text
      const fileContent = await file.text();
      let planData;
      try {
        planData = JSON.parse(fileContent);
      } catch (e) {
        setUploadStatus({ type: 'error', message: 'Invalid JSON file' });
        setUploading(false);
        return;
      }

      // Send JSON to API
      const response = await fetch('/api/airspace/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(planData),
      });

      const data = await response.json();

      if (response.ok) {
        setUploadStatus({ type: 'success', message: `Flight plan uploaded successfully! Plan ID: ${data.plan_id}` });
        setFile(null);
        // Reset file input
        const fileInput = document.getElementById('file-input') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      } else {
        setUploadStatus({ type: 'error', message: data.error || 'Upload failed' });
      }
    } catch (error: any) {
      setUploadStatus({ type: 'error', message: error.message || 'Upload failed' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <h2 className="text-2xl font-bold text-white mb-4">Upload Flight Plan</h2>
      <p className="text-gray-400 mb-6">
        Upload a JSON flight plan file to begin airspace analysis. The file will be processed and events will be published.
      </p>

      <div className="space-y-4">
        <div>
          <label htmlFor="file-input" className="block text-sm font-medium text-gray-300 mb-2">
            Select JSON File
          </label>
          <input
            id="file-input"
            type="file"
            accept=".json,application/json"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
        </div>

        {file && (
          <div className="bg-gray-800 rounded p-3">
            <p className="text-sm text-gray-300">
              <strong>Selected:</strong> {file.name} ({(file.size / 1024).toFixed(2)} KB)
            </p>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload Plan'}
        </button>

        {uploadStatus && (
          <div
            className={`p-4 rounded-lg ${
              uploadStatus.type === 'success' ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'
            }`}
          >
            {uploadStatus.message}
          </div>
        )}
      </div>
    </div>
  );
}

// Overview Tab Component
function OverviewTab() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [planId, setPlanId] = useState<string>('');

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 5000);
    return () => clearInterval(interval);
  }, [planId]);

  const fetchOverview = async () => {
    try {
      const url = planId ? `/api/airspace/overview?plan_id=${planId}` : '/api/airspace/overview';
      const res = await fetch(url);
      const result = await res.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching overview:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <h2 className="text-2xl font-bold text-white mb-4">Overview</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Filter by Plan ID (optional)</label>
          <input
            type="text"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            placeholder="Enter plan ID..."
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Flights" value={data?.flights_count || 0} color="blue" />
        <StatCard label="Conflicts" value={data?.conflicts_count || 0} color="red" />
        <StatCard label="Hotspots" value={data?.hotspots_count || 0} color="yellow" />
        <StatCard label="Violations" value={data?.violations_count || 0} color="orange" />
      </div>

      {data?.top_risk_score !== undefined && (
        <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
          <h3 className="text-xl font-bold text-white mb-2">Top Risk Score</h3>
          <div className="text-4xl font-bold text-red-400">{data.top_risk_score.toFixed(2)}</div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-900 text-blue-200',
    red: 'bg-red-900 text-red-200',
    yellow: 'bg-yellow-900 text-yellow-200',
    orange: 'bg-orange-900 text-orange-200',
  };

  return (
    <div className={`${colorClasses[color]} rounded-lg p-6`}>
      <div className="text-sm font-medium opacity-75">{label}</div>
      <div className="text-3xl font-bold mt-2">{value}</div>
    </div>
  );
}

// Map Tab Component
function MapTab() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [planId, setPlanId] = useState<string>('');

  useEffect(() => {
    fetchMapData();
    const interval = setInterval(fetchMapData, 5000);
    return () => clearInterval(interval);
  }, [planId]);

  const fetchMapData = async () => {
    try {
      const url = planId ? `/api/airspace/map?plan_id=${planId}` : '/api/airspace/map';
      const res = await fetch(url);
      const result = await res.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching map data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading map data...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <h2 className="text-2xl font-bold text-white mb-4">3D Airspace Map</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Filter by Plan ID (optional)</label>
          <input
            type="text"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            placeholder="Enter plan ID..."
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
        <div className="mt-4 text-sm text-gray-400">
          <p>
            {data?.trajectories?.length || 0} trajectories, {data?.conflicts?.length || 0} conflicts,{' '}
            {data?.hotspots?.length || 0} hotspots
          </p>
        </div>
      </div>

      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <div className="h-[600px] w-full rounded-lg overflow-hidden">
          {data && (data.trajectories?.length > 0 || data.conflicts?.length > 0 || data.hotspots?.length > 0) ? (
            <AirspaceCesiumMap
              trajectories={data.trajectories || []}
              conflicts={data.conflicts || []}
              hotspots={data.hotspots || []}
            />
          ) : (
            <div className="h-full bg-gray-900 rounded-lg flex items-center justify-center">
              <div className="text-center text-gray-400">
                <p className="text-lg mb-2">No data to display</p>
                <p className="text-sm">Upload a flight plan to see 3D visualization</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Conflicts Tab Component
function ConflictsTab() {
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [planId, setPlanId] = useState<string>('');

  useEffect(() => {
    fetchConflicts();
    const interval = setInterval(fetchConflicts, 5000);
    return () => clearInterval(interval);
  }, [planId]);

  const fetchConflicts = async () => {
    try {
      const url = planId ? `/api/airspace/conflicts?plan_id=${planId}` : '/api/airspace/conflicts';
      const res = await fetch(url);
      const result = await res.json();
      setConflicts(result.conflicts || []);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading conflicts...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <h2 className="text-2xl font-bold text-white mb-4">Conflicts</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Filter by Plan ID (optional)</label>
          <input
            type="text"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            placeholder="Enter plan ID..."
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
      </div>

      <div className="space-y-4">
        {conflicts.length === 0 ? (
          <div className="bg-dark-surface rounded-lg p-6 border border-dark-border text-center text-gray-400">
            No conflicts detected
          </div>
        ) : (
          conflicts.map((conflict) => (
            <ConflictCard key={conflict.conflict_id} conflict={conflict} />
          ))
        )}
      </div>
    </div>
  );
}

function ConflictCard({ conflict }: { conflict: any }) {
  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{conflict.conflict_id}</h3>
          <p className="text-sm text-gray-400 mt-1">Type: {conflict.conflict_type || 'separation'}</p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            conflict.severity_level === 'critical'
              ? 'bg-red-900 text-red-200'
              : conflict.severity_level === 'high'
              ? 'bg-orange-900 text-orange-200'
              : 'bg-yellow-900 text-yellow-200'
          }`}
        >
          {conflict.severity_level?.toUpperCase() || 'MEDIUM'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-400">Affected Flights</p>
          <p className="text-white font-medium">{conflict.flight_ids?.join(', ') || 'N/A'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-400">Minimum Separation</p>
          <p className="text-white font-medium">
            {conflict.minimum_separation?.toFixed(1) || 'N/A'} NM (required: {conflict.required_separation || 5.0} NM)
          </p>
        </div>
      </div>

      {conflict.recommended_solutions && conflict.recommended_solutions.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-sm font-medium text-gray-300 mb-2">Recommended Solutions</p>
          <div className="space-y-2">
            {conflict.recommended_solutions.map((solution: any, idx: number) => (
              <div key={idx} className="bg-gray-800 rounded p-3">
                <p className="text-sm text-white">{solution.description || JSON.stringify(solution)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Hotspots Tab Component
function HotspotsTab() {
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [planId, setPlanId] = useState<string>('');

  useEffect(() => {
    fetchHotspots();
    const interval = setInterval(fetchHotspots, 5000);
    return () => clearInterval(interval);
  }, [planId]);

  const fetchHotspots = async () => {
    try {
      const url = planId ? `/api/airspace/hotspots?plan_id=${planId}` : '/api/airspace/hotspots';
      const res = await fetch(url);
      const result = await res.json();
      setHotspots(result.hotspots || []);
    } catch (error) {
      console.error('Error fetching hotspots:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading hotspots...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <h2 className="text-2xl font-bold text-white mb-4">Hotspots</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Filter by Plan ID (optional)</label>
          <input
            type="text"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            placeholder="Enter plan ID..."
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
      </div>

      <div className="space-y-4">
        {hotspots.length === 0 ? (
          <div className="bg-dark-surface rounded-lg p-6 border border-dark-border text-center text-gray-400">
            No hotspots detected
          </div>
        ) : (
          hotspots.map((hotspot) => <HotspotCard key={hotspot.hotspot_id} hotspot={hotspot} />)
        )}
      </div>
    </div>
  );
}

function HotspotCard({ hotspot }: { hotspot: any }) {
  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{hotspot.hotspot_id}</h3>
          <p className="text-sm text-gray-400 mt-1">Type: {hotspot.hotspot_type || 'congestion'}</p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            hotspot.severity === 'high' ? 'bg-red-900 text-red-200' : 'bg-yellow-900 text-yellow-200'
          }`}
        >
          {hotspot.severity?.toUpperCase() || 'MEDIUM'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-400">Affected Flights</p>
          <p className="text-white font-medium">{hotspot.affected_flights?.length || 0}</p>
        </div>
        <div>
          <p className="text-sm text-gray-400">Density</p>
          <p className="text-white font-medium">{(hotspot.density * 100).toFixed(1)}%</p>
        </div>
      </div>

      {hotspot.mitigation_options && hotspot.mitigation_options.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-sm font-medium text-gray-300 mb-2">Mitigation Options</p>
          <div className="space-y-2">
            {hotspot.mitigation_options.map((option: any, idx: number) => (
              <div key={idx} className="bg-gray-800 rounded p-3">
                <p className="text-sm text-white">{option.description || JSON.stringify(option)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Validation Tab Component
function ValidationTab() {
  const [violations, setViolations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [planId, setPlanId] = useState<string>('');

  useEffect(() => {
    fetchViolations();
    const interval = setInterval(fetchViolations, 5000);
    return () => clearInterval(interval);
  }, [planId]);

  const fetchViolations = async () => {
    try {
      const url = planId ? `/api/airspace/validation?plan_id=${planId}` : '/api/airspace/validation';
      const res = await fetch(url);
      const result = await res.json();
      setViolations(result.violations || []);
    } catch (error) {
      console.error('Error fetching violations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-white">Loading violations...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <h2 className="text-2xl font-bold text-white mb-4">Validation</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">Filter by Plan ID (optional)</label>
          <input
            type="text"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            placeholder="Enter plan ID..."
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
      </div>

      <div className="space-y-4">
        {violations.length === 0 ? (
          <div className="bg-dark-surface rounded-lg p-6 border border-dark-border text-center text-gray-400">
            No violations detected
          </div>
        ) : (
          violations.map((violation) => <ViolationCard key={violation.violation_id} violation={violation} />)
        )}
      </div>
    </div>
  );
}

function ViolationCard({ violation }: { violation: any }) {
  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{violation.violation_id}</h3>
          <p className="text-sm text-gray-400 mt-1">Type: {violation.violation_type || 'unknown'}</p>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-orange-900 text-orange-200">
          {violation.severity?.toUpperCase() || 'WARNING'}
        </span>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-400">Flight ID</p>
        <p className="text-white font-medium">{violation.flight_id || 'N/A'}</p>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-400">Description</p>
        <p className="text-white">{violation.description || 'No description'}</p>
      </div>

      {violation.suggested_fixes && violation.suggested_fixes.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-sm font-medium text-gray-300 mb-2">Suggested Fixes</p>
          <div className="space-y-2">
            {violation.suggested_fixes.map((fix: any, idx: number) => (
              <div key={idx} className="bg-gray-800 rounded p-3">
                <p className="text-sm text-white">{fix.description || JSON.stringify(fix)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

