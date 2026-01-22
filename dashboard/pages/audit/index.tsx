import { useState, useEffect, useRef, useCallback } from 'react';
import StatusBadge from '../../components/StatusBadge';
import FixReviewPanel from '../../components/FixReviewPanel';
import DefenseThreatReviewPanel from '../../components/DefenseThreatReviewPanel';

type VerificationStatus = {
  fix_id: string;
  status: 'in_progress' | 'verified' | 'failed' | 'not_started';
  started_at?: string;
  completed_at?: string;
  passed?: boolean;
  metrics?: {
    total_actions: number;
    passed: number;
    failed: number;
    skipped: number;
  };
  timeline?: Array<{
    timestamp: string;
    status: string;
    message: string;
    data?: any;
  }>;
};

type FixEvent = {
  _id: string;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    correlation_id: string;
    details: {
      fix_id: string;
      correlation_id: string;
      source: string;
      title: string;
      summary: string;
      actions: Array<{
        type: string;
        target: any;
        params: any;
        verification: {
          metric_name: string;
          threshold: number;
          window_seconds: number;
        };
      }>;
      risk_level: string;
      expected_impact: {
        delay_reduction?: number;
        risk_score_delta?: number;
        area_affected?: string;
      };
      created_at: string;
      proposed_by: string;
      requires_human_approval: boolean;
    };
  };
  timestamp: string;
  verification?: VerificationStatus;
};

type DefenseThreatEvent = {
  _id: string;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    correlation_id: string;
    details: {
      threat_id: string;
      threat_type: string;
      confidence_score: number;
      severity: string;
      affected_area?: any;
      sources: string[];
      summary: string;
      detected_at: string;
      disclaimer: string;
    };
  };
  timestamp: string;
  assessment?: {
    threat_id: string;
    assessment_score?: number;
    risk_level?: string;
    assessment_notes?: string;
    assessed_by?: string;
    assessed_at?: string;
    _assessment_data?: {
      threat_type: string;
      likely_cause: string;
      recommended_posture: string;
      protective_actions: string[];
      escalation_needed: boolean;
    };
  };
};

export default function Audit() {
  const [activeTab, setActiveTab] = useState<'fixes' | 'defense'>('fixes');
  const [fixes, setFixes] = useState<FixEvent[]>([]);
  const [threats, setThreats] = useState<DefenseThreatEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFix, setSelectedFix] = useState<FixEvent | null>(null);
  const [selectedThreat, setSelectedThreat] = useState<DefenseThreatEvent | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const [updateKey, setUpdateKey] = useState(0); // Force re-render key
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch defense threats from API
  const fetchThreats = useCallback(async () => {
    try {
      const timestamp = Date.now();
      console.log('[Audit] Fetching defense threats...', timestamp);
      const res = await fetch(`/api/defense/threats?limit=100&_t=${timestamp}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
        },
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      const fetchedThreats = data.threats || [];
      console.log('[Audit] Fetched threats from API:', fetchedThreats.length);
      
      setThreats((prevThreats) => {
        const prevCount = prevThreats.length;
        const newCount = fetchedThreats.length;
        
        if (newCount !== prevCount) {
          console.log('[Audit] Threat count changed:', prevCount, '->', newCount);
          setUpdateKey(k => k + 1);
        }
        return fetchedThreats;
      });
    } catch (error) {
      console.error('[Audit] Error fetching threats:', error);
    }
  }, []);

  // Log when fixes count changes
  useEffect(() => {
    console.log('[Audit] Fixes count changed:', fixes.length);
  }, [fixes.length]);

  // Fetch fixes from API - use useCallback to ensure stable reference
  const fetchFixes = useCallback(async () => {
      try {
        // Add cache-busting parameter to ensure fresh data
        const timestamp = Date.now();
        console.log('[Audit] Fetching fixes...', timestamp);
        const res = await fetch(`/api/audit?limit=100&_t=${timestamp}`, {
          cache: 'no-store',
          headers: {
            'Cache-Control': 'no-cache',
          },
        });
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        const fetchedFixes = data.fixes || [];
        console.log('[Audit] Fetched fixes from API:', fetchedFixes.length);
        
        // Merge with existing fixes instead of replacing - prioritize fetched fixes but keep SSE-added ones
        setFixes((prevFixes) => {
          const prevCount = prevFixes.length;
          const newCount = fetchedFixes.length;
          
          // Create a map of fetched fixes by fix_id
          const fetchedMap = new Map(fetchedFixes.map(f => [f.payload?.details?.fix_id, f]));
          
          // Keep fixes that were added via SSE but aren't in the fetched list (they might be newer)
          const sseOnlyFixes = prevFixes.filter(f => {
            const fixId = f.payload?.details?.fix_id;
            return fixId && !fetchedMap.has(fixId);
          });
          
          // Combine: fetched fixes first, then SSE-only fixes
          const mergedFixes = [...fetchedFixes, ...sseOnlyFixes];
          const mergedCount = mergedFixes.length;
          
          if (mergedCount !== prevCount) {
            console.log('[Audit] Fix count changed after merge:', prevCount, '->', mergedCount, '(fetched:', newCount, ', SSE-only:', sseOnlyFixes.length, ')');
            setUpdateKey(k => k + 1);
          } else if (newCount !== prevCount) {
            console.log('[Audit] Fix count changed (fetched):', prevCount, '->', newCount);
            setUpdateKey(k => k + 1);
          } else {
            // Even if count is same, check if IDs changed
            const prevIds = new Set(prevFixes.map(f => f.payload?.details?.fix_id));
            const mergedIds = new Set(mergedFixes.map(f => f.payload?.details?.fix_id));
            const idsChanged = prevIds.size !== mergedIds.size || 
              [...prevIds].some(id => !mergedIds.has(id)) ||
              [...mergedIds].some(id => !prevIds.has(id));
            if (idsChanged) {
              console.log('[Audit] Fix IDs changed, forcing update');
              setUpdateKey(k => k + 1);
            } else {
              console.log('[Audit] Fix count and IDs unchanged:', mergedCount);
            }
          }
          return mergedFixes;
        });
      } catch (error) {
        console.error('[Audit] Error fetching fixes:', error);
        setMessage({ type: 'error', text: 'Failed to load fixes' });
      } finally {
        setLoading(false);
      }
    }, []);

  useEffect(() => {
    // Initial fetch
    fetchFixes();
    fetchThreats();

    let lastHeartbeat = Date.now();

    // Set up SSE connection for real-time updates
    const connectSSE = () => {
      try {
        const since = new Date(Date.now() - 5 * 60 * 1000); // Last 5 minutes
        const url = `/api/audit/stream?since=${since.toISOString()}`;
        console.log('[Audit] Connecting to SSE:', url);
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('[Audit] SSE connection opened');
          setSseConnected(true);
          lastHeartbeat = Date.now();
          
          // Check for heartbeats - if no heartbeat in 30 seconds, SSE isn't working
          if (heartbeatCheckIntervalRef.current) {
            clearInterval(heartbeatCheckIntervalRef.current);
          }
          heartbeatCheckIntervalRef.current = setInterval(() => {
            const timeSinceLastHeartbeat = Date.now() - lastHeartbeat;
            if (timeSinceLastHeartbeat > 30000) {
              console.warn('[Audit] No SSE heartbeat in 30s, SSE may not be working');
              setSseConnected(false);
              // Ensure polling is running
              if (!pollingIntervalRef.current) {
                pollingIntervalRef.current = setInterval(() => {
                  console.log('[Audit] Polling for updates...');
                  fetchFixes();
                }, 2000);
              }
            }
          }, 10000); // Check every 10 seconds
          
          // Slow down polling but don't stop it completely
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          // Use slower polling as backup (every 10 seconds) when SSE is connected
          pollingIntervalRef.current = setInterval(() => {
            console.log('[Audit] Backup polling (SSE connected)');
            fetchFixes();
            fetchThreats();
          }, 10000);
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[Audit] SSE message received:', data.type);
            
            if (data.type === 'connected') {
              console.log('[Audit] SSE connected successfully');
              return;
            }
            
            if (data.type === 'heartbeat') {
              // Update last heartbeat time
              lastHeartbeat = Date.now();
              return;
            }

            if (data.type === 'error') {
              console.error('[Audit] SSE error:', data.message);
              eventSource.close();
              setSseConnected(false);
              // Fallback to polling
              pollingIntervalRef.current = setInterval(() => {
                fetchFixes();
                fetchThreats();
              }, 2000);
              return;
            }

            if (data.type === 'fix_update') {
              console.log('[Audit] Fix update received:', data.payload?.details?.fix_id);
              // New or updated fix
              setFixes((prevFixes) => {
                const fixId = data.payload?.details?.fix_id;
                // Try to find by _id first, then by fix_id (for verification updates)
                const existingIndex = prevFixes.findIndex(f => 
                  f._id === data._id || f.payload?.details?.fix_id === fixId
                );
                if (existingIndex >= 0) {
                  // Update existing fix (preserve _id if it's different)
                  const updated = [...prevFixes];
                  updated[existingIndex] = {
                    ...data,
                    _id: updated[existingIndex]._id, // Preserve original _id
                  };
                  const newCount = updated.length;
                  console.log('[Audit] Updated existing fix, count:', newCount);
                  if (newCount !== prevFixes.length) {
                    setUpdateKey(k => k + 1);
                  }
                  return updated;
                } else {
                  // Add new fix at the beginning
                  const newFixes = [data, ...prevFixes];
                  const newCount = newFixes.length;
                  console.log('[Audit] Added new fix via SSE, count:', prevFixes.length, '->', newCount);
                  setUpdateKey(k => k + 1);
                  return newFixes;
                }
              });
            } else if (data.type === 'fix_verification_update') {
              console.log('[Audit] Verification update received:', data.fix_id, data.verification?.status);
              // Verification status update only
              setFixes((prevFixes) => {
                const fixId = data.fix_id;
                const existingIndex = prevFixes.findIndex(f => 
                  f.payload?.details?.fix_id === fixId
                );
                if (existingIndex >= 0) {
                  // Update only verification status
                  const updated = [...prevFixes];
                  updated[existingIndex] = {
                    ...updated[existingIndex],
                    verification: data.verification,
                  };
                  console.log('[Audit] Updated fix verification status');
                  return updated;
                }
                return prevFixes;
              });
            } else if (data.type === 'fix_removed') {
              console.log('[Audit] Fix removed:', data.fix_id);
              // Fix was approved/rejected, remove it
              setFixes((prevFixes) => {
                const filtered = prevFixes.filter(f => f.payload.details.fix_id !== data.fix_id);
                const newCount = filtered.length;
                console.log('[Audit] Removed fix, count:', prevFixes.length, '->', newCount);
                if (newCount !== prevFixes.length) {
                  setUpdateKey(k => k + 1);
                }
                return filtered;
              });
            }
          } catch (err) {
            console.error('Error parsing SSE message:', err);
          }
        };

        eventSource.onerror = (error) => {
          console.warn('[Audit] SSE connection error:', error);
          console.warn('[Audit] EventSource readyState:', eventSource.readyState);
          // EventSource.readyState: 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
          if (eventSource.readyState === EventSource.CLOSED) {
            console.warn('[Audit] SSE connection closed, falling back to polling');
            eventSource.close();
            setSseConnected(false);
            if (heartbeatCheckIntervalRef.current) {
              clearInterval(heartbeatCheckIntervalRef.current);
              heartbeatCheckIntervalRef.current = null;
            }
            // Ensure polling is running
            if (!pollingIntervalRef.current) {
              pollingIntervalRef.current = setInterval(() => {
                console.log('[Audit] Polling for updates...');
                fetchFixes();
                fetchThreats();
              }, 2000);
              console.log('[Audit] Started polling fallback');
            } else {
              // Speed up polling if SSE fails
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = setInterval(() => {
                console.log('[Audit] Polling for updates...');
                fetchFixes();
                fetchThreats();
              }, 2000);
            }
          }
        };

      } catch (err) {
        console.error('[Audit] Failed to create SSE connection:', err);
        setSseConnected(false);
        // Ensure polling is running
        if (!pollingIntervalRef.current) {
          pollingIntervalRef.current = setInterval(() => {
            console.log('[Audit] Polling for updates...');
            fetchFixes();
            fetchThreats();
          }, 2000);
        }
      }
    };

    // Always start with polling (fast updates)
    pollingIntervalRef.current = setInterval(() => {
      console.log('[Audit] Polling for updates...');
      fetchFixes();
      fetchThreats();
    }, 2000);

    // Then try to connect SSE
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
      if (heartbeatCheckIntervalRef.current) {
        clearInterval(heartbeatCheckIntervalRef.current);
      }
    };
  }, []);

  const handleApprove = async (fixId: string) => {
    // This is called after the API call succeeds in FixReviewPanel
    setMessage({ type: 'success', text: `Fix ${fixId} approved successfully` });
    
    // Immediately remove the fix from the list (SSE will also update, but this is instant)
    setFixes((prevFixes) => 
      prevFixes.filter(f => f.payload.details.fix_id !== fixId)
    );
    
    // Also refresh to ensure consistency
    setTimeout(() => {
      fetchFixes();
    }, 500);
  };

  const handleReject = async (fixId: string, reason: string) => {
    try {
      const res = await fetch(`/api/fix/${fixId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      const data = await res.json();
      
      if (data.success) {
        setMessage({ type: 'success', text: data.message || 'Fix rejected successfully' });
        
        // Immediately remove the fix from the list (SSE will also update, but this is instant)
        setFixes((prevFixes) => 
          prevFixes.filter(f => f.payload.details.fix_id !== fixId)
        );
        
        // Also refresh to ensure consistency
        setTimeout(() => {
          fetchFixes();
        }, 500);
      } else {
        throw new Error(data.error || 'Failed to reject fix');
      }
    } catch (error: any) {
      throw new Error(error.message || 'Failed to reject fix');
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'low':
        return 'bg-green-600';
      case 'med':
      case 'medium':
        return 'bg-yellow-600';
      case 'high':
        return 'bg-red-600';
      default:
        return 'bg-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-dark-muted">Loading fixes requiring review...</div>
      </div>
    );
  }

  const handleThreatApprove = async (threatId: string) => {
    setMessage({ type: 'success', text: `Defense action for threat ${threatId} approved successfully` });
    setThreats((prevThreats) => 
      prevThreats.filter(t => t.payload.details.threat_id !== threatId)
    );
    setTimeout(() => {
      fetchThreats();
    }, 500);
  };

  const handleThreatHold = async (threatId: string) => {
    setMessage({ type: 'success', text: `Threat ${threatId} placed on hold` });
    // Threat remains in queue when on hold
  };

  const handleThreatDismiss = async (threatId: string, reason: string) => {
    setMessage({ type: 'success', text: `Threat ${threatId} dismissed: ${reason}` });
    setThreats((prevThreats) => 
      prevThreats.filter(t => t.payload.details.threat_id !== threatId)
    );
    setTimeout(() => {
      fetchThreats();
    }, 500);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-white">Audit & Review</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            <span className="text-xs text-dark-muted">
              {sseConnected ? 'Live' : 'Polling'}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 mb-6 border-b border-dark-border">
        <button
          onClick={() => setActiveTab('fixes')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'fixes'
              ? 'text-white border-b-2 border-blue-500'
              : 'text-dark-muted hover:text-white'
          }`}
        >
          Fixes
          <span className="ml-2 text-xs" key={updateKey}>
            ({fixes.length})
          </span>
        </button>
        <button
          onClick={() => setActiveTab('defense')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'defense'
              ? 'text-white border-b-2 border-blue-500'
              : 'text-dark-muted hover:text-white'
          }`}
        >
          Defense Threats
          <span className="ml-2 text-xs" key={updateKey}>
            ({threats.length})
          </span>
        </button>
      </div>

      {/* Message Banner */}
      {message && (
        <div
          className={`mb-4 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-900 bg-opacity-50 border border-green-600 text-green-200'
              : 'bg-red-900 bg-opacity-50 border border-red-600 text-red-200'
          }`}
        >
          {message.text}
          <button
            onClick={() => setMessage(null)}
            className="float-right text-white hover:text-gray-300"
          >
            ✕
          </button>
        </div>
      )}

      <div className="space-y-4">
        {activeTab === 'fixes' ? (
          fixes.length === 0 ? (
            <div className="text-center py-12 text-dark-muted">
              <div className="text-lg mb-2">No fixes requiring review</div>
              <div className="text-sm">All fixes have been processed or no fixes are pending.</div>
            </div>
          ) : (
            fixes.map((fix) => (
            <div
              key={fix._id}
              className="bg-dark-surface border border-dark-border rounded-lg p-6 hover:border-gray-600 transition-colors cursor-pointer"
              onClick={() => setSelectedFix(fix)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3 flex-1">
                  <StatusBadge severity={fix.payload.severity} />
                  <div className="flex-1">
                    <h3 className="text-white font-semibold mb-1">
                      {fix.payload.details.title}
                    </h3>
                    <div className="text-sm text-dark-muted">
                      Fix ID: {fix.payload.details.fix_id} • Source: {fix.payload.details.source} • 
                      Correlation: {fix.payload.correlation_id}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getRiskLevelColor(
                      fix.payload.details.risk_level
                    )}`}
                  >
                    {fix.payload.details.risk_level.toUpperCase()}
                  </span>
                  <div className="text-xs text-dark-muted">
                    {formatDate(fix.timestamp)}
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <div className="text-sm text-white line-clamp-2">
                  {fix.payload.details.summary}
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <div className="text-dark-muted">
                    {fix.payload.details.actions.length} action{fix.payload.details.actions.length !== 1 ? 's' : ''} • 
                    Proposed by: {fix.payload.details.proposed_by}
                  </div>
                  {fix.verification && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-dark-muted">Verification:</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          fix.verification.status === 'verified'
                            ? 'bg-green-600 text-white'
                            : fix.verification.status === 'failed'
                            ? 'bg-red-600 text-white'
                            : fix.verification.status === 'in_progress'
                            ? 'bg-yellow-600 text-white'
                            : 'bg-gray-600 text-white'
                        }`}
                      >
                        {fix.verification.status === 'verified' && '✓ Verified'}
                        {fix.verification.status === 'failed' && '✗ Failed'}
                        {fix.verification.status === 'in_progress' && '⏳ In Progress'}
                        {fix.verification.status === 'not_started' && 'Not Started'}
                      </span>
                      {fix.verification.metrics && (
                        <span className="text-xs text-dark-muted">
                          ({fix.verification.metrics.passed}/{fix.verification.metrics.total_actions} passed)
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFix(fix);
                  }}
                  className="text-blue-400 hover:text-blue-300 font-semibold"
                >
                  Review →
                </button>
              </div>
            </div>
          ))
        )
        ) : (
          threats.length === 0 ? (
            <div className="text-center py-12 text-dark-muted">
              <div className="text-lg mb-2">No defense threats requiring review</div>
              <div className="text-sm">All threats have been processed or no threats are pending.</div>
            </div>
          ) : (
            threats.map((threat) => (
              <div
                key={threat._id}
                className="bg-dark-surface border border-dark-border rounded-lg p-6 hover:border-gray-600 transition-colors cursor-pointer"
                onClick={() => setSelectedThreat(threat)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3 flex-1">
                    <StatusBadge severity={threat.payload.severity} />
                    <div className="flex-1">
                      <h3 className="text-white font-semibold mb-1">
                        {threat.payload.details.summary}
                      </h3>
                      <div className="text-sm text-dark-muted">
                        Threat ID: {threat.payload.details.threat_id} • 
                        Type: {threat.payload.details.threat_type} • 
                        Sector: {threat.payload.sector_id}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${
                      threat.payload.details.confidence_score >= 0.8 ? 'bg-red-600' :
                      threat.payload.details.confidence_score >= 0.6 ? 'bg-yellow-600' :
                      'bg-green-600'
                    }`}>
                      {(threat.payload.details.confidence_score * 100).toFixed(0)}% confidence
                    </span>
                    <div className="text-xs text-dark-muted">
                      {formatDate(threat.timestamp)}
                    </div>
                  </div>
                </div>

                <div className="mb-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-dark-muted">Sources:</span>
                    {threat.payload.details.sources.map((source, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-blue-600 bg-opacity-30 border border-blue-500 rounded text-xs text-blue-200"
                      >
                        {source}
                      </span>
                    ))}
                  </div>
                  {threat.assessment && (
                    <div className="text-sm text-green-400">
                      ✓ AI Assessment Available
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-sm">
                  <div className="text-dark-muted">
                    {threat.assessment ? (
                      <span>Posture: {threat.assessment._assessment_data?.recommended_posture || 'N/A'}</span>
                    ) : (
                      <span className="text-yellow-400">Assessment pending...</span>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedThreat(threat);
                    }}
                    className="text-blue-400 hover:text-blue-300 font-semibold"
                  >
                    Review →
                  </button>
                </div>
              </div>
            ))
          )
        )}
      </div>

      {/* Review Panels */}
      {selectedFix && (
        <FixReviewPanel
          fix={selectedFix}
          onClose={() => setSelectedFix(null)}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
      {selectedThreat && (
        <DefenseThreatReviewPanel
          threat={selectedThreat}
          onClose={() => setSelectedThreat(null)}
          onApprove={handleThreatApprove}
          onHold={handleThreatHold}
          onDismiss={handleThreatDismiss}
        />
      )}
    </div>
  );
}

