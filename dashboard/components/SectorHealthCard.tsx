type SectorHealthCardProps = {
  sectorId: string;
  voltage: number;
  load: number;
  status: 'healthy' | 'warning' | 'critical';
};

export default function SectorHealthCard({ sectorId, voltage, load, status }: SectorHealthCardProps) {
  const statusColors = {
    healthy: 'bg-green-600',
    warning: 'bg-yellow-600',
    critical: 'bg-red-600',
  };

  const statusText = {
    healthy: 'HEALTHY',
    warning: 'WARNING',
    critical: 'CRITICAL',
  };

  const statusBg = {
    healthy: 'bg-green-600/10 border-green-600/30',
    warning: 'bg-yellow-600/10 border-yellow-600/30',
    critical: 'bg-red-600/10 border-red-600/30',
  };

  return (
    <div className={`${statusBg[status]} border-2 rounded-xl p-6`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-white">{sectorId.toUpperCase()}</h3>
        <span className={`${statusColors[status]} text-white text-xs font-bold px-3 py-1 rounded-full`}>
          {statusText[status]}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-sm text-gray-400 mb-1">Voltage</div>
          <div className="text-2xl font-bold text-white">{voltage.toFixed(1)}V</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Load</div>
          <div className="text-2xl font-bold text-white">{load.toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}

