import StatusBadge from './StatusBadge';

type TimelineEventProps = {
  event: {
    _id: string;
    topic: string;
    payload: any;
    timestamp: string;
  };
};

const getEventIcon = (topic: string) => {
  if (topic.includes('power.failure')) return '⚡';
  if (topic.includes('recovery.plan')) return '📋';
  if (topic.includes('operator.status')) return '👤';
  if (topic.includes('audit.decision')) return '🔍';
  if (topic.includes('system.action')) return '⚙️';
  if (topic.includes('approval.required')) return '✋';
  if (topic.includes('agent.compare')) return '🔬';
  return '📌';
};

const getEventColor = (topic: string) => {
  if (topic.includes('power.failure')) return 'bg-red-500';
  if (topic.includes('recovery.plan')) return 'bg-blue-500';
  if (topic.includes('operator.status')) return 'bg-purple-500';
  if (topic.includes('audit.decision')) return 'bg-yellow-500';
  if (topic.includes('system.action')) return 'bg-green-500';
  if (topic.includes('approval.required')) return 'bg-orange-500';
  if (topic.includes('agent.compare')) return 'bg-cyan-500';
  return 'bg-gray-500';
};

export default function TimelineEvent({ event }: TimelineEventProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    return date.toLocaleString();
  };

  const getTopicName = (topic: string) => {
    return topic.split('.').pop()?.replace(/_/g, ' ').toUpperCase() || topic;
  };

  // Debug: Log severity for power failure events to help diagnose issues
  if (event.topic?.includes('power.failure')) {
    const severity = event.payload?.severity || (event as any).severity || 'info';
    // Log all power failure events to see what severities are actually being received
    console.log('[TimelineEvent] Power failure event:', {
      topic: event.topic,
      payload_severity: event.payload?.severity,
      event_severity: (event as any).severity,
      final_severity: severity,
      summary: event.payload?.summary,
    });
  }

  return (
    <div className="flex gap-4 pb-4 border-l-2 border-gray-800 pl-4 relative">
      {/* Icon */}
      <div className={`${getEventColor(event.topic)} w-10 h-10 rounded-full flex items-center justify-center text-white text-lg flex-shrink-0 relative z-10`}>
        {getEventIcon(event.topic)}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between mb-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white">{getTopicName(event.topic)}</span>
            <StatusBadge 
              severity={
                event.payload?.severity || 
                (event as any).severity || 
                'info'
              } 
              size="sm" 
            />
          </div>
          <span className="text-xs text-gray-400 flex-shrink-0 ml-2">{formatTime(event.timestamp)}</span>
        </div>
        
        <div className="text-sm text-white mb-1">{event.payload?.summary || 'No summary'}</div>
        
        {event.payload?.sector_id && (
          <div className="text-xs text-gray-400">
            Sector: <span className="text-gray-300">{event.payload.sector_id}</span>
          </div>
        )}
      </div>
    </div>
  );
}

