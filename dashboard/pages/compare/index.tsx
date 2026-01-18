import { useState, useEffect } from 'react';
import StatusBadge from '../../components/StatusBadge';

type CompareResult = {
  _id: string;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    details: {
      compare_id: string;
      framework_name: string;
      plan_output: any;
      execution_time_ms: number;
      number_of_actions: number;
      priority_violations: string[];
      confidence_score: number;
      metadata: any;
      selected?: boolean;
    };
  };
  timestamp: string;
};

type CompareEvent = {
  _id: string;
  payload: {
    details: {
      compare_id: string;
      frameworks_tested: string[];
      selected_framework: string;
      total_execution_time_ms: number;
    };
  };
  timestamp: string;
};

export default function Compare() {
  const [compareEvents, setCompareEvents] = useState<CompareEvent[]>([]);
  const [results, setResults] = useState<Record<string, CompareResult[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedCompareId, setSelectedCompareId] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch comparison events
        const compareRes = await fetch('/api/events?topic=chronos.events.agent.compare&limit=20');
        const compareData = await compareRes.json();
        setCompareEvents(compareData.events || []);

        // Fetch comparison results
        const resultsRes = await fetch('/api/events?topic=chronos.events.agent.compare.result&limit=100');
        const resultsData = await resultsRes.json();
        const resultsList = resultsData.events || [];

        // Group results by compare_id
        const grouped: Record<string, CompareResult[]> = {};
        resultsList.forEach((result: CompareResult) => {
          const compareId = result.payload.details.compare_id;
          if (!grouped[compareId]) {
            grouped[compareId] = [];
          }
          grouped[compareId].push(result);
        });
        setResults(grouped);

        // Select latest comparison if none selected
        if (!selectedCompareId && compareData.events?.length > 0) {
          setSelectedCompareId(compareData.events[0].payload.details.compare_id);
        }
      } catch (error) {
        console.error('Error fetching comparison data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [selectedCompareId]);

  const getFrameworkColor = (frameworkName: string) => {
    switch (frameworkName) {
      case 'RULES_ENGINE':
        return 'bg-blue-600';
      case 'SINGLE_LLM':
        return 'bg-purple-600';
      case 'AGENTIC_MESH':
        return 'bg-green-600';
      default:
        return 'bg-gray-600';
    }
  };

  const getFrameworkIcon = (frameworkName: string) => {
    switch (frameworkName) {
      case 'RULES_ENGINE':
        return '⚙️';
      case 'SINGLE_LLM':
        return '🤖';
      case 'AGENTIC_MESH':
        return '🕸️';
      default:
        return '📊';
    }
  };

  const currentResults = selectedCompareId ? results[selectedCompareId] || [] : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-dark-muted">Loading comparisons...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">Agentic Compare</h1>

      {/* Comparison Selector */}
      {compareEvents.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-dark-muted mb-2">
            Select Comparison Run:
          </label>
          <select
            value={selectedCompareId || ''}
            onChange={(e) => setSelectedCompareId(e.target.value)}
            className="bg-dark-surface border border-dark-border rounded px-4 py-2 text-white"
          >
            {compareEvents.map((event) => (
              <option key={event._id} value={event.payload.details.compare_id}>
                {new Date(event.timestamp).toLocaleString()} - {event.payload.details.frameworks_tested.join(', ')}
              </option>
            ))}
          </select>
        </div>
      )}

      {currentResults.length === 0 ? (
        <div className="text-center py-12 text-dark-muted">
          No comparison results found. Trigger a power failure to see framework comparisons.
        </div>
      ) : (
        <>
          {/* Comparison Summary */}
          {selectedCompareId && compareEvents.find(e => e.payload.details.compare_id === selectedCompareId) && (
            <div className="bg-dark-surface border border-dark-border rounded-lg p-4 mb-6">
              <h2 className="text-xl font-semibold text-white mb-2">Comparison Summary</h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-dark-muted">Total Time</div>
                  <div className="text-white font-semibold">
                    {compareEvents.find(e => e.payload.details.compare_id === selectedCompareId)?.payload.details.total_execution_time_ms.toFixed(2)}ms
                  </div>
                </div>
                <div>
                  <div className="text-dark-muted">Frameworks Tested</div>
                  <div className="text-white font-semibold">
                    {compareEvents.find(e => e.payload.details.compare_id === selectedCompareId)?.payload.details.frameworks_tested.length}
                  </div>
                </div>
                <div>
                  <div className="text-dark-muted">Selected Framework</div>
                  <div className="text-white font-semibold">
                    {compareEvents.find(e => e.payload.details.compare_id === selectedCompareId)?.payload.details.selected_framework}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Framework Results - Side by Side */}
          <div className="grid grid-cols-3 gap-6">
            {currentResults.map((result) => {
              const details = result.payload.details;
              const plan = details.plan_output || {};
              const isSelected = details.selected;

              return (
                <div
                  key={result._id}
                  className={`bg-dark-surface border-2 rounded-lg p-6 ${
                    isSelected
                      ? 'border-green-500'
                      : 'border-dark-border'
                  }`}
                >
                  {/* Framework Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{getFrameworkIcon(details.framework_name)}</span>
                      <div>
                        <h3 className="text-lg font-bold text-white">
                          {details.framework_name}
                        </h3>
                        {/* Show model/provider information prominently */}
                        {details.framework_name === 'RULES_ENGINE' ? (
                          <div className="text-xs text-gray-400 mt-0.5">
                            Deterministic Rules Engine
                          </div>
                        ) : details.metadata?.llm_provider ? (
                          <div className="text-xs text-blue-300 mt-0.5 font-medium">
                            {details.metadata.llm_provider}
                            {details.metadata.llm_model && details.metadata.llm_model !== 'N/A' && 
                              ` • ${details.metadata.llm_model}`}
                          </div>
                        ) : details.metadata?.provider ? (
                          <div className="text-xs text-blue-300 mt-0.5 font-medium">
                            {details.metadata.provider === 'gemini' ? 'Gemini' : 
                             details.metadata.provider === 'cerebras' ? 'Cerebras' : 
                             details.metadata.provider}
                            {details.metadata.model && ` • ${details.metadata.model}`}
                          </div>
                        ) : details.metadata?.llm_model && details.metadata.llm_model !== 'agent_consensus' ? (
                          <div className="text-xs text-blue-300 mt-0.5 font-medium">
                            {details.metadata.llm_model}
                          </div>
                        ) : details.framework_name === 'AGENTIC_MESH' && details.metadata?.llm_escalated === false ? (
                          <div className="text-xs text-gray-400 mt-0.5">
                            Agent Consensus (No LLM)
                          </div>
                        ) : null}
                      </div>
                    </div>
                    {isSelected && (
                      <span className="bg-green-600 text-white text-xs px-2 py-1 rounded">
                        SELECTED
                      </span>
                    )}
                  </div>

                  {/* Metrics */}
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-dark-muted">Latency:</span>
                      <span className="text-white font-semibold">
                        {details.execution_time_ms.toFixed(2)}ms
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-dark-muted">Actions:</span>
                      <span className="text-white font-semibold">
                        {details.number_of_actions}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-dark-muted">Confidence:</span>
                      <span className="text-white font-semibold">
                        {(details.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {details.priority_violations.length > 0 && (
                      <div className="flex justify-between text-sm">
                        <span className="text-dark-muted">Violations:</span>
                        <span className="text-red-400 font-semibold">
                          {details.priority_violations.length}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Plan Summary */}
                  <div className="border-t border-dark-border pt-4">
                    <div className="text-xs text-dark-muted mb-2">Plan:</div>
                    <div className="text-sm text-white mb-2">
                      {plan.plan_name || 'No plan name'}
                    </div>
                    <div className="text-xs text-dark-muted mb-2">Steps:</div>
                    <ul className="text-xs text-white space-y-1 max-h-40 overflow-y-auto">
                      {(plan.steps || []).slice(0, 5).map((step: string, idx: number) => (
                        <li key={idx} className="flex items-start">
                          <span className="mr-1">•</span>
                          <span>{step}</span>
                        </li>
                      ))}
                      {(plan.steps || []).length > 5 && (
                        <li className="text-dark-muted">
                          +{(plan.steps || []).length - 5} more steps
                        </li>
                      )}
                    </ul>
                  </div>

                  {/* Priority Violations */}
                  {details.priority_violations.length > 0 && (
                    <div className="border-t border-dark-border pt-4 mt-4">
                      <div className="text-xs text-red-400 font-semibold mb-2">
                        Priority Violations:
                      </div>
                      <ul className="text-xs text-red-300 space-y-1">
                        {details.priority_violations.map((violation: string, idx: number) => (
                          <li key={idx}>⚠️ {violation}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

