type RecoveryPlanPanelProps = {
  plan: {
    plan_id: string;
    plan_name: string;
    status: string;
    steps: string[];
    estimated_completion: string;
    assigned_agents: string[];
  } | null;
};

export default function RecoveryPlanPanel({ plan }: RecoveryPlanPanelProps) {
  if (!plan) {
    return (
      <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
        <h3 className="text-lg font-bold text-white mb-4">Latest Recovery Plan</h3>
        <div className="text-center py-8 text-gray-400">
          No active recovery plan
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Latest Recovery Plan</h3>
        <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          {plan.status.toUpperCase()}
        </span>
      </div>

      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-1">Plan ID</div>
        <div className="text-white font-mono text-sm">{plan.plan_id}</div>
      </div>

      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-1">Plan Name</div>
        <div className="text-white font-medium">{plan.plan_name}</div>
      </div>

      {plan.estimated_completion && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-1">Estimated Completion</div>
          <div className="text-white">{formatDate(plan.estimated_completion)}</div>
        </div>
      )}

      {plan.steps && plan.steps.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Steps ({plan.steps.length})</div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {plan.steps.slice(0, 5).map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm text-white">
                <span className="text-blue-500 font-bold">{idx + 1}.</span>
                <span>{step}</span>
              </div>
            ))}
            {plan.steps.length > 5 && (
              <div className="text-xs text-gray-400">
                +{plan.steps.length - 5} more steps
              </div>
            )}
          </div>
        </div>
      )}

      {plan.assigned_agents && plan.assigned_agents.length > 0 && (
        <div>
          <div className="text-sm text-gray-400 mb-2">Assigned Agents</div>
          <div className="flex flex-wrap gap-2">
            {plan.assigned_agents.map((agent, idx) => (
              <span
                key={idx}
                className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded"
              >
                {agent}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

