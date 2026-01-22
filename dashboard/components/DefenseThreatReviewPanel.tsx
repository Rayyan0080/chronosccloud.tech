import { useState } from 'react';
import StatusBadge from './StatusBadge';

type DefenseThreatReviewPanelProps = {
  threat: {
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
  onClose: () => void;
  onApprove: (threatId: string) => Promise<void>;
  onHold: (threatId: string) => Promise<void>;
  onDismiss: (threatId: string, reason: string) => Promise<void>;
};

export default function DefenseThreatReviewPanel({
  threat,
  onClose,
  onApprove,
  onHold,
  onDismiss,
}: DefenseThreatReviewPanelProps) {
  const [dismissReason, setDismissReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'hold' | 'dismiss' | null>(null);

  const handleApprove = async () => {
    console.log('[DefenseThreatReviewPanel] handleApprove called');
    setIsProcessing(true);
    setError(null);
    setActionType('approve');
    
    const threatId = threat.payload.details.threat_id;
    console.log(`[DefenseThreatReviewPanel] Approving threat: ${threatId}`);
    
    try {
      const url = `/api/defense/${threatId}/approve`;
      console.log(`[DefenseThreatReviewPanel] Making POST request to: ${url}`);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log(`[DefenseThreatReviewPanel] Response status: ${response.status} ${response.statusText}`);
      
      const data = await response.json();
      console.log('[DefenseThreatReviewPanel] Response data:', data);
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }
      
      console.log('[DefenseThreatReviewPanel] Approval successful, calling onApprove callback');
      await onApprove(threatId);
      onClose();
    } catch (err: any) {
      console.error('[DefenseThreatReviewPanel] Approval error:', err);
      setError(err.message || 'Failed to approve defense action');
    } finally {
      setIsProcessing(false);
      setActionType(null);
    }
  };

  const handleHold = async () => {
    console.log('[DefenseThreatReviewPanel] handleHold called');
    setIsProcessing(true);
    setError(null);
    setActionType('hold');
    
    const threatId = threat.payload.details.threat_id;
    
    try {
      const response = await fetch(`/api/defense/${threatId}/hold`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to hold threat');
      }
      
      await onHold(threatId);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to hold threat');
    } finally {
      setIsProcessing(false);
      setActionType(null);
    }
  };

  const handleDismiss = async () => {
    if (!dismissReason.trim()) {
      setError('Please provide a reason for dismissing the threat');
      return;
    }

    console.log('[DefenseThreatReviewPanel] handleDismiss called');
    setIsProcessing(true);
    setError(null);
    setActionType('dismiss');
    
    const threatId = threat.payload.details.threat_id;
    
    try {
      const response = await fetch(`/api/defense/${threatId}/dismiss`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason: dismissReason }),
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to dismiss threat');
      }
      
      await onDismiss(threatId, dismissReason);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to dismiss threat');
    } finally {
      setIsProcessing(false);
      setActionType(null);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'bg-red-600';
    if (score >= 0.6) return 'bg-yellow-600';
    return 'bg-green-600';
  };

  const getThreatTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'airspace':
        return 'bg-blue-600';
      case 'cyber_physical':
        return 'bg-purple-600';
      case 'environmental':
        return 'bg-orange-600';
      case 'civil':
        return 'bg-gray-600';
      default:
        return 'bg-gray-600';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface border border-dark-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white">Defense Threat Review</h2>
            <button
              onClick={onClose}
              className="text-dark-muted hover:text-white text-2xl"
              disabled={isProcessing}
            >
              ×
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-900 bg-opacity-50 border border-red-600 text-red-200 rounded">
              {error}
            </div>
          )}

          {/* Threat Details */}
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Threat Information</h3>
              <div className="bg-dark-bg rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <StatusBadge severity={threat.payload.severity} />
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getThreatTypeColor(threat.payload.details.threat_type)}`}>
                    {threat.payload.details.threat_type.toUpperCase()}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getConfidenceColor(threat.payload.details.confidence_score)}`}>
                    Confidence: {(threat.payload.details.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm text-dark-muted">
                  Threat ID: {threat.payload.details.threat_id} • 
                  Sector: {threat.payload.sector_id} • 
                  Detected: {formatDate(threat.payload.details.detected_at)}
                </div>
                <div className="text-white">
                  {threat.payload.details.summary}
                </div>
              </div>
            </div>

            {/* Sources */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Data Sources</h3>
              <div className="bg-dark-bg rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {threat.payload.details.sources.map((source, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-blue-600 bg-opacity-30 border border-blue-500 rounded text-sm text-blue-200"
                    >
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Affected Area */}
            {threat.payload.details.affected_area && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Affected Area</h3>
                <div className="bg-dark-bg rounded-lg p-4">
                  <pre className="text-xs text-dark-muted overflow-auto">
                    {JSON.stringify(threat.payload.details.affected_area, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* AI Assessment */}
            {threat.assessment && threat.assessment._assessment_data ? (
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">AI Assessment</h3>
                <div className="bg-dark-bg rounded-lg p-4 space-y-3">
                  <div>
                    <span className="text-sm text-dark-muted">Likely Cause:</span>
                    <div className="text-white mt-1">{threat.assessment._assessment_data.likely_cause}</div>
                  </div>
                  <div>
                    <span className="text-sm text-dark-muted">Recommended Posture:</span>
                    <div className="text-white mt-1 font-semibold">
                      {threat.assessment._assessment_data.recommended_posture}
                    </div>
                  </div>
                  <div>
                    <span className="text-sm text-dark-muted">Protective Actions:</span>
                    <ul className="list-disc list-inside text-white mt-1 space-y-1">
                      {threat.assessment._assessment_data.protective_actions.map((action, idx) => (
                        <li key={idx}>{action}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span className="text-sm text-dark-muted">Escalation Needed:</span>
                    <div className="text-white mt-1">
                      {threat.assessment._assessment_data.escalation_needed ? (
                        <span className="text-red-400 font-semibold">Yes</span>
                      ) : (
                        <span className="text-green-400">No</span>
                      )}
                    </div>
                  </div>
                  {threat.assessment.assessment_notes && (
                    <div>
                      <span className="text-sm text-dark-muted">Assessment Notes:</span>
                      <div className="text-white mt-1">{threat.assessment.assessment_notes}</div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-yellow-900 bg-opacity-30 border border-yellow-600 rounded-lg p-4">
                <div className="text-yellow-200">
                  ⚠️ Threat assessment pending. Waiting for AI assessment...
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div className="bg-gray-900 bg-opacity-50 border border-gray-700 rounded-lg p-3">
              <div className="text-xs text-gray-400 italic">
                {threat.payload.details.disclaimer}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex items-center justify-between gap-4 pt-6 border-t border-dark-border">
            <div className="flex-1">
              {actionType === 'dismiss' && (
                <div className="mb-4">
                  <label className="block text-sm text-dark-muted mb-2">
                    Reason for dismissal:
                  </label>
                  <textarea
                    value={dismissReason}
                    onChange={(e) => setDismissReason(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded text-white text-sm"
                    placeholder="Enter reason for dismissing this threat..."
                    rows={3}
                    disabled={isProcessing}
                  />
                </div>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleHold}
                disabled={isProcessing || actionType !== null}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded font-semibold"
              >
                {isProcessing && actionType === 'hold' ? 'Holding...' : 'Hold'}
              </button>
              <button
                onClick={handleDismiss}
                disabled={isProcessing || actionType !== null || !threat.assessment}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded font-semibold"
              >
                {isProcessing && actionType === 'dismiss' ? 'Dismissing...' : 'Dismiss'}
              </button>
              <button
                onClick={handleApprove}
                disabled={isProcessing || actionType !== null || !threat.assessment}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded font-semibold"
                title={!threat.assessment ? "Threat must be assessed before approval" : "Approve protective actions and change posture"}
              >
                {isProcessing && actionType === 'approve' ? 'Approving...' : 'Approve Protective Actions'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

