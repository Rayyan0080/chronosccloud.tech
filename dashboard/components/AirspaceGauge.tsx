type AirspaceGaugeProps = {
  congestion: number; // 0-100
};

export default function AirspaceGauge({ congestion }: AirspaceGaugeProps) {
  const getStatus = () => {
    if (congestion < 30) return { color: 'text-green-500', label: 'CLEAR' };
    if (congestion < 70) return { color: 'text-yellow-500', label: 'MODERATE' };
    return { color: 'text-red-500', label: 'CONGESTED' };
  };

  const status = getStatus();
  const percentage = Math.round(congestion);

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">Airspace Status</h3>
        <span className={`text-sm font-semibold ${status.color}`}>{status.label}</span>
      </div>
      
      <div className="relative">
        {/* Gauge background */}
        <div className="w-full h-8 bg-gray-800 rounded-full overflow-hidden">
          {/* Gauge fill */}
          <div
            className={`h-full transition-all duration-500 ${
              congestion < 30
                ? 'bg-green-600'
                : congestion < 70
                ? 'bg-yellow-600'
                : 'bg-red-600'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        
        {/* Percentage text */}
        <div className="text-center mt-3">
          <span className="text-3xl font-bold text-white">{percentage}%</span>
          <span className="text-sm text-gray-400 ml-2">Congestion</span>
        </div>
      </div>
    </div>
  );
}

