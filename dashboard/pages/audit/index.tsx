import { useState, useEffect, useRef } from 'react';
import StatusBadge from '../../components/StatusBadge';
import FixReviewPanel from '../../components/FixReviewPanel';

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

export default function Audit() {
  const [fixes, setFixes] = useState<FixEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFix, setSelectedFix] = useState<FixEvent | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch fixes from API
  const fetchFixes = async () => {
    try {
      const res = await fetch('/api/audit?limit=100');
      const data = await res.json();
      const fetchedFixes = data.fixes || [];
      setFixes(fetchedFixes);
    } catch (error) {
      console.error('Error fetching fixes:', error);
      setMessage({ type: 'error', text: 'Failed to load fixes' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchFixes();

    // Set up SSE connection for real-time updates
    const connectSSE = () => {
      try {
        const since = new Date(Date.now() - 5 * 60 * 1000); // Last 5 minutes
        const eventSource = new EventSource(`/api/audit/stream?since=${since.toISOString()}`);
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
              pollingIntervalRef.current = setInterval(fetchFixes, 2000);
              return;
            }

            if (data.type === 'fix_update') {
              // New or updated fix
              setFixes((prevFixes) => {
                const existingIndex = prevFixes.findIndex(f => f._id === data._id);
                if (existingIndex >= 0) {
                  // Update existing fix
                  const updated = [...prevFixes];
                  updated[existingIndex] = data;
                  return updated;
                } else {
                  // Add new fix at the beginning
                  return [data, ...prevFixes];
                }
              });
            } else if (data.type === 'fix_removed') {
              // Fix was approved/rejected, remove it
              setFixes((prevFixes) => 
                prevFixes.filter(f => f.payload.details.fix_id !== data.fix_id)
              );
            }
          } catch (err) {
            console.error('Error parsing SSE message:', err);
          }
        };

        eventSource.onerror = () => {
          console.warn('SSE connection error, falling back to polling');
          eventSource.close();
          setSseConnected(false);
          pollingIntervalRef.current = setInterval(fetchFixes, 2000);
        };

      } catch (err) {
        console.error('Failed to create SSE connection:', err);
        setSseConnected(false);
        pollingIntervalRef.current = setInterval(fetchFixes, 2000);
      }
    };

    connectSSE();

    // Set up initial polling fallback (will be cleared when SSE connects)
    pollingIntervalRef.current = setInterval(fetchFixes, 2000);

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-white">Fix Review & Approval</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            <span className="text-xs text-dark-muted">
              {sseConnected ? 'Live' : 'Polling'}
            </span>
          </div>
          <div className="text-sm text-dark-muted">
            {fixes.length} fix{fixes.length !== 1 ? 'es' : ''} requiring review
          </div>
        </div>
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
        {fixes.length === 0 ? (
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
        )}
      </div>

      {/* Review Panel */}
      {selectedFix && (
        <FixReviewPanel
          fix={selectedFix}
          onClose={() => setSelectedFix(null)}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  );
}

