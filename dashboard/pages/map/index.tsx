import { useState, useEffect } from 'react';
import StatusBadge from '../../components/StatusBadge';
import AutonomyBadge from '../../components/AutonomyBadge';

type SectorStatus = {
  sector_id: string;
  latest_event: any;
  status: 'normal' | 'warning' | 'error' | 'critical';
  last_updated: string;
};

export default function Map() {
  const [sectors, setSectors] = useState<SectorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [autonomyLevel, setAutonomyLevel] = useState<string>('NORMAL');

  useEffect(() => {
    const fetchSectors = async () => {
      try {
        const [sectorsRes, eventsRes] = await Promise.all([
          fetch('/api/sectors'),
          fetch('/api/events?limit=10'),
        ]);

        const sectorsData = await sectorsRes.json();
        setSectors(sectorsData.sectors || []);

        // Find latest autonomy level
        const eventsData = await eventsRes.json();
        const operatorStatusEvents = eventsData.events?.filter(
          (e: any) => e.topic === 'chronos.events.operator.status'
        );
        if (operatorStatusEvents && operatorStatusEvents.length > 0) {
          const latest = operatorStatusEvents[0];
          const level = latest.payload?.details?.autonomy_level || 'NORMAL';
          setAutonomyLevel(level);
        }
      } catch (error) {
        console.error('Error fetching sectors:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSectors();
    const interval = setInterval(fetchSectors, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'bg-red-600';
      case 'error':
        return 'bg-orange-600';
      case 'warning':
        return 'bg-yellow-600';
      default:
        return 'bg-green-600';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'critical':
        return 'CRITICAL';
      case 'error':
        return 'ERROR';
      case 'warning':
        return 'WARNING';
      default:
        return 'NORMAL';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-dark-muted">Loading sectors...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-white">Sector Map</h1>
        <AutonomyBadge level={autonomyLevel} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {sectors.map((sector) => (
          <div
            key={sector.sector_id}
            className={`${getStatusColor(sector.status)} rounded-lg p-8 text-center`}
          >
            <h2 className="text-2xl font-bold text-white mb-4">
              {sector.sector_id.replace('-', ' ').toUpperCase()}
            </h2>
            <div className="text-4xl font-bold text-white mb-2">
              {getStatusText(sector.status)}
            </div>
            {sector.latest_event && (
              <div className="mt-4 text-sm text-white/80">
                <div>{sector.latest_event.summary}</div>
                <div className="mt-2 text-xs">
                  {new Date(sector.last_updated).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

