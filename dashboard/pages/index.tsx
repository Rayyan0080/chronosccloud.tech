import { useState, useEffect } from 'react';
import EventCard from '../components/EventCard';
import AutonomyBadge from '../components/AutonomyBadge';

type Event = {
  _id: string;
  topic: string;
  payload: any;
  timestamp: string;
};

export default function Home() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [autonomyLevel, setAutonomyLevel] = useState<string>('NORMAL');

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('/api/events?limit=50');
        const data = await res.json();
        setEvents(data.events || []);

        // Find latest autonomy level
        const operatorStatusEvents = data.events.filter(
          (e: Event) => e.topic === 'chronos.events.operator.status'
        );
        if (operatorStatusEvents.length > 0) {
          const latest = operatorStatusEvents[0];
          const level = latest.payload?.details?.autonomy_level || 'NORMAL';
          setAutonomyLevel(level);
        }
      } catch (error) {
        console.error('Error fetching events:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
    const interval = setInterval(fetchEvents, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-dark-muted">Loading events...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-white">Live Event Feed</h1>
        <AutonomyBadge level={autonomyLevel} />
      </div>

      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="text-center py-12 text-dark-muted">
            No events found. Start the crisis generator to see events.
          </div>
        ) : (
          events.map((event) => (
            <EventCard key={event._id} event={event} />
          ))
        )}
      </div>
    </div>
  );
}

