import { useState, useEffect } from 'react';
import StatusBadge from '../../components/StatusBadge';

type AuditEvent = {
  _id: string;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    details: {
      decision_id: string;
      decision_type: string;
      decision_maker: string;
      action: string;
      reasoning?: string;
      outcome?: string;
      related_events?: string[];
    };
  };
  timestamp: string;
};

async function computeHash(payload: any): Promise<string> {
  // Compute SHA-256 hash (same as backend)
  const json = JSON.stringify(payload, Object.keys(payload).sort());
  const encoder = new TextEncoder();
  const data = encoder.encode(json);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function Audit() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [hashes, setHashes] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchAuditEvents = async () => {
      try {
        const res = await fetch('/api/audit?limit=100');
        const data = await res.json();
        const fetchedEvents = data.events || [];
        setEvents(fetchedEvents);

        // Compute hashes for all events
        const hashPromises = fetchedEvents.map(async (event: AuditEvent) => {
          const hash = await computeHash(event.payload);
          return [event._id, hash];
        });
        const hashResults = await Promise.all(hashPromises);
        setHashes(Object.fromEntries(hashResults));
      } catch (error) {
        console.error('Error fetching audit events:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAuditEvents();
    const interval = setInterval(fetchAuditEvents, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-dark-muted">Loading audit decisions...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-6">Audit Decisions</h1>

      <div className="space-y-4">
        {events.length === 0 ? (
          <div className="text-center py-12 text-dark-muted">
            No audit decisions found.
          </div>
        ) : (
          events.map((event) => {
            const hash = hashes[event._id] || 'computing...';
            return (
              <div
                key={event._id}
                className="bg-dark-surface border border-dark-border rounded-lg p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <StatusBadge severity={event.payload.severity} />
                    <div>
                      <h3 className="text-white font-semibold">
                        {event.payload.summary}
                      </h3>
                      <div className="text-sm text-dark-muted mt-1">
                        Decision ID: {event.payload.details.decision_id}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-dark-muted">
                    {new Date(event.timestamp).toLocaleString()}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-dark-muted mb-1">Decision Type</div>
                    <div className="text-white">{event.payload.details.decision_type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-muted mb-1">Decision Maker</div>
                    <div className="text-white">{event.payload.details.decision_maker}</div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-muted mb-1">Action</div>
                    <div className="text-white">{event.payload.details.action}</div>
                  </div>
                  <div>
                    <div className="text-xs text-dark-muted mb-1">Outcome</div>
                    <div className="text-white">
                      {event.payload.details.outcome || 'N/A'}
                    </div>
                  </div>
                </div>

                {event.payload.details.reasoning && (
                  <div className="mb-4">
                    <div className="text-xs text-dark-muted mb-1">Reasoning</div>
                    <div className="text-white text-sm">{event.payload.details.reasoning}</div>
                  </div>
                )}

                <div className="border-t border-dark-border pt-4">
                  <div className="text-xs text-dark-muted mb-1">Solana Hash</div>
                  <div className="font-mono text-sm text-blue-400 break-all">
                    {hash}
                  </div>
                  <div className="text-xs text-dark-muted mt-2">
                    [SOLANA] would log hash: {hash}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

