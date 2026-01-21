import { useState } from 'react';
import StatusBadge from './StatusBadge';

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

type FixReviewPanelProps = {
  fix: {
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
  onClose: () => void;
  onApprove: (fixId: string) => Promise<void>;
  onReject: (fixId: string, reason: string) => Promise<void>;
};

export default function FixReviewPanel({
  fix,
  onClose,
  onApprove,
  onReject,
}: FixReviewPanelProps) {
  const [rejectReason, setRejectReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    console.log('[FixReviewPanel] handleApprove called');
    setIsProcessing(true);
    setError(null);
    
    const fixId = fix.payload.details.fix_id;
    console.log(`[FixReviewPanel] Approving fix: ${fixId}`);
    
    try {
      const url = `/api/fix/${fixId}/approve`;
      console.log(`[FixReviewPanel] Making POST request to: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log(`[FixReviewPanel] Response status: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[FixReviewPanel] Response error: ${errorText}`);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
        }
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('[FixReviewPanel] Approve response:', data);
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to approve fix');
      }
      
      console.log('[FixReviewPanel] Approval successful!');
      
      // Show success message
      setError(null);
      
      // Call the parent handler for UI updates (refresh list, show message)
      console.log('[FixReviewPanel] Calling parent onApprove handler');
      try {
        await onApprove(fixId);
        console.log('[FixReviewPanel] Parent handler completed');
      } catch (parentError: any) {
        // Parent handler might throw, but we already succeeded
        console.warn('[FixReviewPanel] Parent handler error (non-fatal):', parentError);
      }
      
      // Close panel after showing success
      console.log('[FixReviewPanel] Scheduling panel close in 1.5s');
      setTimeout(() => {
        console.log('[FixReviewPanel] Closing panel now');
        onClose();
      }, 1500);
    } catch (err: any) {
      console.error('[FixReviewPanel] Approve error:', err);
      console.error('[FixReviewPanel] Error stack:', err.stack);
      setError(err.message || 'Failed to approve fix. Check browser console (F12) for details.');
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setError('Please provide a reason for rejection');
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      await onReject(fix.payload.details.fix_id, rejectReason);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to reject fix');
    } finally {
      setIsProcessing(false);
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

  const getActionTypeLabel = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .replace(/SIM/g, '')
      .trim()
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface border border-dark-border rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-dark-surface border-b border-dark-border p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Review Fix Proposal</h2>
          <button
            onClick={onClose}
            className="text-dark-muted hover:text-white transition-colors"
            disabled={isProcessing}
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-red-900 bg-opacity-50 border border-red-600 rounded-lg p-4 text-red-200">
              <div className="font-semibold mb-1">Error</div>
              {error}
            </div>
          )}
          
          {/* Success/Processing Message */}
          {isProcessing && !error && (
            <div className="bg-blue-900 bg-opacity-50 border border-blue-600 rounded-lg p-4 text-blue-200">
              <div className="font-semibold">Processing approval...</div>
              <div className="text-sm mt-1">Saving to database and publishing events...</div>
            </div>
          )}

          {/* Fix Header */}
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">
                {fix.payload.details.title}
              </h3>
              <div className="flex items-center gap-3 text-sm text-dark-muted">
                <span>Fix ID: {fix.payload.details.fix_id}</span>
                <span>•</span>
                <span>Source: {fix.payload.details.source}</span>
                <span>•</span>
                <span>Proposed by: {fix.payload.details.proposed_by}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getRiskLevelColor(
                  fix.payload.details.risk_level
                )}`}
              >
                {fix.payload.details.risk_level.toUpperCase()} RISK
              </span>
              <StatusBadge severity={fix.payload.severity} />
            </div>
          </div>

          {/* What Happened */}
          <div>
            <h4 className="text-lg font-semibold text-white mb-2">What Happened</h4>
            <div className="bg-dark-bg rounded-lg p-4">
              <div className="text-sm text-dark-muted mb-2">
                Correlation ID: {fix.payload.correlation_id}
              </div>
              <div className="text-white">
                This fix addresses: {fix.payload.correlation_id}
              </div>
              <div className="text-sm text-dark-muted mt-2">
                Sector: {fix.payload.sector_id}
              </div>
            </div>
          </div>

          {/* Proposed Fix Summary */}
          <div>
            <h4 className="text-lg font-semibold text-white mb-2">Proposed Fix Summary</h4>
            <div className="bg-dark-bg rounded-lg p-4 text-white">
              {fix.payload.details.summary}
            </div>
          </div>

          {/* Actions */}
          <div>
            <h4 className="text-lg font-semibold text-white mb-2">
              Actions ({fix.payload.details.actions.length})
            </h4>
            <div className="space-y-3">
              {fix.payload.details.actions.map((action, idx) => (
                <div key={idx} className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-white font-semibold mb-1">
                        Action {idx + 1}: {getActionTypeLabel(action.type)}
                      </div>
                      <div className="text-sm text-dark-muted">
                        Type: {action.type}
                      </div>
                    </div>
                  </div>
                  
                  {/* Target */}
                  <div className="mb-3">
                    <div className="text-xs text-dark-muted mb-1">Target</div>
                    <div className="text-sm text-white font-mono bg-dark-surface p-2 rounded">
                      {JSON.stringify(action.target, null, 2)}
                    </div>
                  </div>

                  {/* Parameters */}
                  {Object.keys(action.params || {}).length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs text-dark-muted mb-1">Parameters</div>
                      <div className="text-sm text-white font-mono bg-dark-surface p-2 rounded">
                        {JSON.stringify(action.params, null, 2)}
                      </div>
                    </div>
                  )}

                  {/* Verification */}
                  {action.verification && (
                    <div>
                      <div className="text-xs text-dark-muted mb-1">Verification</div>
                      <div className="text-sm text-white">
                        <div>
                          Metric: <span className="font-semibold">{action.verification.metric_name}</span>
                        </div>
                        <div>
                          Threshold: <span className="font-semibold">{action.verification.threshold}</span>
                        </div>
                        <div>
                          Window: <span className="font-semibold">{action.verification.window_seconds}s</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Risk Level & Expected Impact */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-lg font-semibold text-white mb-2">Risk Level</h4>
              <div className="bg-dark-bg rounded-lg p-4">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-sm font-semibold text-white ${getRiskLevelColor(
                    fix.payload.details.risk_level
                  )}`}
                >
                  {fix.payload.details.risk_level.toUpperCase()}
                </span>
              </div>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white mb-2">Expected Impact</h4>
              <div className="bg-dark-bg rounded-lg p-4 space-y-2 text-sm">
                {fix.payload.details.expected_impact.delay_reduction !== undefined && (
                  <div className="text-white">
                    Delay Reduction: <span className="font-semibold text-green-400">
                      {fix.payload.details.expected_impact.delay_reduction} min
                    </span>
                  </div>
                )}
                {fix.payload.details.expected_impact.risk_score_delta !== undefined && (
                  <div className="text-white">
                    Risk Score Delta: <span className="font-semibold text-green-400">
                      {fix.payload.details.expected_impact.risk_score_delta > 0 ? '+' : ''}
                      {fix.payload.details.expected_impact.risk_score_delta}
                    </span>
                  </div>
                )}
                {fix.payload.details.expected_impact.area_affected && (
                  <div className="text-white">
                    Area Affected: <span className="font-semibold">
                      {typeof fix.payload.details.expected_impact.area_affected === 'string'
                        ? fix.payload.details.expected_impact.area_affected
                        : JSON.stringify(fix.payload.details.expected_impact.area_affected)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Verification Plan */}
          <div>
            <h4 className="text-lg font-semibold text-white mb-2">Verification Plan</h4>
            <div className="bg-dark-bg rounded-lg p-4">
              {fix.payload.details.actions.length > 0 && fix.payload.details.actions[0].verification ? (
                <div className="text-sm text-white space-y-1">
                  <div>
                    After deployment into the live operations loop (simulated actuation), monitor{' '}
                    <span className="font-semibold">
                      {fix.payload.details.actions[0].verification.metric_name}
                    </span>{' '}
                    for{' '}
                    <span className="font-semibold">
                      {fix.payload.details.actions[0].verification.window_seconds}s
                    </span>
                  </div>
                  <div>
                    Success threshold: <span className="font-semibold text-green-400">
                      {fix.payload.details.actions[0].verification.threshold}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-dark-muted">No verification plan specified</div>
              )}
            </div>
          </div>

          {/* Verification Status */}
          {fix.verification && (
            <div>
              <h4 className="text-lg font-semibold text-white mb-2">Verification Status</h4>
              <div className="bg-dark-bg rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-muted">Status</span>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${
                      fix.verification.status === 'verified'
                        ? 'bg-green-600'
                        : fix.verification.status === 'failed'
                        ? 'bg-red-600'
                        : fix.verification.status === 'in_progress'
                        ? 'bg-yellow-600'
                        : 'bg-gray-600'
                    }`}
                  >
                    {fix.verification.status === 'verified' && '✓ Verified'}
                    {fix.verification.status === 'failed' && '✗ Failed'}
                    {fix.verification.status === 'in_progress' && '⏳ In Progress'}
                    {fix.verification.status === 'not_started' && 'Not Started'}
                  </span>
                </div>
                {fix.verification.metrics && (
                  <div className="grid grid-cols-4 gap-2 text-sm">
                    <div>
                      <div className="text-dark-muted">Total</div>
                      <div className="text-white font-semibold">{fix.verification.metrics.total_actions}</div>
                    </div>
                    <div>
                      <div className="text-dark-muted">Passed</div>
                      <div className="text-green-400 font-semibold">{fix.verification.metrics.passed}</div>
                    </div>
                    <div>
                      <div className="text-dark-muted">Failed</div>
                      <div className="text-red-400 font-semibold">{fix.verification.metrics.failed}</div>
                    </div>
                    <div>
                      <div className="text-dark-muted">Skipped</div>
                      <div className="text-gray-400 font-semibold">{fix.verification.metrics.skipped}</div>
                    </div>
                  </div>
                )}
                {fix.verification.timeline && fix.verification.timeline.length > 0 && (
                  <div>
                    <div className="text-sm text-dark-muted mb-2">Timeline</div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {fix.verification.timeline.map((entry, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-xs">
                          <span className="text-dark-muted min-w-[120px]">
                            {formatDate(entry.timestamp)}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-xs ${
                              entry.status === 'verified' || entry.status === 'passed'
                                ? 'bg-green-900 text-green-200'
                                : entry.status === 'failed' || entry.status === 'verification_failed'
                                ? 'bg-red-900 text-red-200'
                                : entry.status === 'in_progress' || entry.status === 'verifying'
                                ? 'bg-yellow-900 text-yellow-200'
                                : 'bg-gray-800 text-gray-300'
                            }`}
                          >
                            {entry.status}
                          </span>
                          <span className="text-white flex-1">{entry.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {fix.verification.started_at && (
                  <div className="text-xs text-dark-muted">
                    Started: {formatDate(fix.verification.started_at)}
                  </div>
                )}
                {fix.verification.completed_at && (
                  <div className="text-xs text-dark-muted">
                    Completed: {formatDate(fix.verification.completed_at)}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="text-xs text-dark-muted">
            <div>Created: {formatDate(fix.payload.details.created_at)}</div>
            <div>Requires Human Approval: {fix.payload.details.requires_human_approval ? 'Yes' : 'No'}</div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-4 pt-4 border-t border-dark-border">
            <div className="flex-1 relative group">
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  console.log('[FixReviewPanel] Approve button clicked');
                  handleApprove();
                }}
                disabled={isProcessing}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                title="Deployed into the live operations loop (simulated actuation). We do not control public infrastructure. Deploy triggers a safe actuation sandbox + verifies impact using live telemetry."
              >
                {isProcessing ? 'Processing...' : 'Approve'}
              </button>
              {/* Tooltip on hover */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-50 pointer-events-none">
                <div className="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 shadow-lg max-w-xs border border-gray-700 whitespace-normal">
                  <div className="font-semibold mb-1">Deployed into the live operations loop (simulated actuation)</div>
                  <div className="text-gray-300">
                    We do not control public infrastructure. Deploy triggers a safe actuation sandbox + verifies impact using live telemetry.
                  </div>
                  {/* Tooltip arrow */}
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Enter rejection reason..."
                className="w-full bg-dark-bg border border-dark-border rounded-lg p-3 text-white text-sm resize-none"
                rows={2}
                disabled={isProcessing}
              />
              <button
                onClick={handleReject}
                disabled={isProcessing || !rejectReason.trim()}
                className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg transition-colors"
              >
                {isProcessing ? 'Processing...' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

