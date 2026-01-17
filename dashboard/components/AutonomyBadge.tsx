type AutonomyBadgeProps = {
  level: string;
};

export default function AutonomyBadge({ level }: AutonomyBadgeProps) {
  const isHigh = level === 'HIGH';

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1.5 text-sm font-semibold ${
        isHigh
          ? 'bg-purple-600 text-white'
          : 'bg-gray-600 text-white'
      }`}
    >
      {isHigh ? '🔴 HIGH AUTONOMY' : '🟢 NORMAL AUTONOMY'}
    </span>
  );
}

