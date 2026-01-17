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

  const colorClasses: Record<string, string> = {
    critical: 'bg-red-600 text-white',
    error: 'bg-orange-600 text-white',
    warning: 'bg-yellow-600 text-black',
    info: 'bg-blue-600 text-white',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold ${sizeClasses[size]} ${
        colorClasses[severity] || colorClasses.info
      }`}
    >
      {severity.toUpperCase()}
    </span>
  );
}

