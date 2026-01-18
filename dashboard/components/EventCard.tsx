import StatusBadge from './StatusBadge';

type EventCardProps = {
  event: {
    _id: string;
    topic: string;
    payload: any;
    timestamp: string;
  };
};

export default function EventCard({ event }: EventCardProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getTopicName = (topic: string) => {
    return topic.split('.').pop()?.replace(/_/g, ' ').toUpperCase() || topic;
  };

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-dark-muted font-mono">{getTopicName(event.topic)}</span>
          <StatusBadge severity={event.payload?.severity || (event as any).severity || 'info'} size="sm" />
        </div>
        <span className="text-xs text-dark-muted">{formatTime(event.timestamp)}</span>
      </div>
      <h3 className="text-white font-medium mb-1">{event.payload?.summary || 'No summary'}</h3>
      <div className="text-sm text-dark-muted">
        <div>Sector: {event.payload?.sector_id || 'N/A'}</div>
        {event.payload?.details?.autonomy_level && (
          <div className="mt-1">
            Autonomy: <span className="text-white">{event.payload.details.autonomy_level}</span>
          </div>
        )}
      </div>
    </div>
  );
}

