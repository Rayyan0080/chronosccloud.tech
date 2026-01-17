type AutonomyBadgeProps = {
  level: string;
};

export default function AutonomyBadge({ level }: AutonomyBadgeProps) {
  const upperLevel = level.toUpperCase();
  
  // Airspace autonomy modes
  if (upperLevel === 'RULES') {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl px-6 py-3 font-bold text-lg bg-gradient-to-r from-blue-600 to-blue-700 text-white">
        <span className="text-2xl">⚙️</span>
        <span>RULES</span>
      </div>
    );
  }
  
  if (upperLevel === 'LLM') {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl px-6 py-3 font-bold text-lg bg-gradient-to-r from-green-600 to-green-700 text-white">
        <span className="text-2xl">🤖</span>
        <span>LLM</span>
      </div>
    );
  }
  
  if (upperLevel === 'AGENTIC') {
    return (
      <div className="inline-flex items-center gap-2 rounded-xl px-6 py-3 font-bold text-lg bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-600/50">
        <span className="text-2xl">🔴</span>
        <span>AGENTIC</span>
      </div>
    );
  }

  // Power domain autonomy modes
  const isHigh = upperLevel === 'HIGH';

  return (
    <div className={`inline-flex items-center gap-2 rounded-xl px-6 py-3 font-bold text-lg ${
      isHigh
        ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-600/50'
        : 'bg-gradient-to-r from-gray-600 to-gray-700 text-white'
    }`}>
      <span className="text-2xl">{isHigh ? '🔴' : '🟢'}</span>
      <span>{isHigh ? 'HIGH AUTONOMY' : 'NORMAL AUTONOMY'}</span>
    </div>
  );
}

