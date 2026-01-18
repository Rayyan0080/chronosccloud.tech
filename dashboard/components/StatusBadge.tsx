type StatusBadgeProps = {
  severity: string;
  size?: 'sm' | 'md' | 'lg';
};

export default function StatusBadge({ severity, size = 'md' }: StatusBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  // Normalize severity to lowercase for consistent matching
  const normalizedSeverity = (severity || 'info').toLowerCase().trim();

  const colorClasses: Record<string, string> = {
    critical: 'bg-red-600 text-white',
    moderate: 'bg-orange-600 text-white',  // Renamed from 'error' for clarity
    error: 'bg-orange-600 text-white',     // Keep for backward compatibility - maps to moderate
    warning: 'bg-yellow-600 text-black',
    info: 'bg-blue-600 text-white',
  };

  // Map "error" to "moderate" for display, but keep color mapping
  const displaySeverity = normalizedSeverity === 'error' ? 'moderate' : normalizedSeverity;
  
  // Get the display text (capitalize first letter, rest uppercase)
  const displayText = displaySeverity.charAt(0).toUpperCase() + displaySeverity.slice(1).toUpperCase();

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold ${sizeClasses[size]} ${
        colorClasses[normalizedSeverity] || colorClasses.info
      }`}
    >
      {displayText}
    </span>
  );
}

