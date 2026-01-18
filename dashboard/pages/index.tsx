import { useState, useEffect, useRef } from 'react';
import AutonomyBadge from '../components/AutonomyBadge';
import SectorHealthCard from '../components/SectorHealthCard';
import AirspaceGauge from '../components/AirspaceGauge';
import RecoveryPlanPanel from '../components/RecoveryPlanPanel';
import TimelineEvent from '../components/TimelineEvent';
import { announceNewEvents, setVoiceEnabled as setGlobalVoiceEnabled, isVoiceEnabled } from '../lib/voiceAnnouncements';

type Event = {
  _id: string;
  topic: string;
  payload: any;
  timestamp: string;
};

type SectorStatus = {
  sectorId: string;
  voltage: number;
  load: number;
  status: 'healthy' | 'warning' | 'critical';
};

export default function Home() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [autonomyLevel, setAutonomyLevel] = useState<string>('NORMAL');
  const [sectors, setSectors] = useState<SectorStatus[]>([]);
  const [airspaceCongestion, setAirspaceCongestion] = useState<number>(0);
  const [latestPlan, setLatestPlan] = useState<any>(null);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);
  const previousEventsRef = useRef<Event[]>([]);

  // Load voices when component mounts
  useEffect(() => {
    if ('speechSynthesis' in window) {
      // Load voices (some browsers need this)
      const loadVoices = () => {
        speechSynthesis.getVoices();
      };
      loadVoices();
      if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = loadVoices;
      }
    }
  }, []);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('/api/events?limit=50');
        const data = await res.json();
        const newEvents = data.events || [];
        
        // CRITICAL: Don't overwrite global state if user just toggled it off
        // Only sync if React state matches what we expect
        // Check current global state first
        const currentGlobalState = isVoiceEnabled();
        
        // Only sync if states are different AND React state is true
        // If React state is false, respect it (user clicked off)
        // If React state is true but global is false, don't overwrite (user just turned off)
        if (voiceEnabled && currentGlobalState) {
          // Both are true, safe to sync
          setGlobalVoiceEnabled(voiceEnabled);
        } else if (!voiceEnabled) {
          // React state is false (user wants it off), respect that
          setGlobalVoiceEnabled(false);
        }
        // If React is true but global is false, don't change global (user just turned off)
        
        // Announce new events - compare with previous to find truly new ones
        if (voiceEnabled && currentGlobalState) {
          if (previousEventsRef.current.length > 0) {
            // Compare to find new events
            announceNewEvents(previousEventsRef.current, newEvents, voiceEnabled);
          } else {
            // First load - announce all events (but only if we have events)
            if (newEvents.length > 0) {
              // Announce all events on first load
              announceNewEvents([], newEvents, voiceEnabled);
            }
          }
        } else if (!voiceEnabled || !currentGlobalState) {
          // If voice is disabled, make sure nothing is queued
          console.log('[VOICE] Voice disabled (React:', voiceEnabled, 'Global:', currentGlobalState, '), skipping announcement check');
        }
        
        // Update previous events reference
        previousEventsRef.current = [...newEvents];
        setEvents(newEvents);

        // Find latest autonomy level
        const operatorStatusEvents = data.events.filter(
          (e: Event) => e.topic === 'chronos.events.operator.status'
        );
        if (operatorStatusEvents.length > 0) {
          const sorted = operatorStatusEvents.sort((a: any, b: any) => 
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          );
          const latest = sorted[0];
          const level = latest.payload?.details?.autonomy_level || 'NORMAL';
          setAutonomyLevel(level);
        }

        // Extract sector statuses from power.failure events
        const sectorMap = new Map<string, { voltage: number; load: number; timestamp: string }>();
        data.events
          .filter((e: Event) => e.topic === 'chronos.events.power.failure')
          .forEach((e: Event) => {
            const sectorId = e.payload?.sector_id;
            const voltage = e.payload?.details?.voltage || 0;
            const load = e.payload?.details?.load || 0;
            const timestamp = e.timestamp;

            if (sectorId) {
              const existing = sectorMap.get(sectorId);
              if (!existing || new Date(timestamp) > new Date(existing.timestamp)) {
                sectorMap.set(sectorId, { voltage, load, timestamp });
              }
            }
          });

        // Convert to sector status array
        const sectorStatuses: SectorStatus[] = ['sector-1', 'sector-2', 'sector-3'].map(sectorId => {
          const data = sectorMap.get(sectorId) || { voltage: 120, load: 50, timestamp: '' };
          let status: 'healthy' | 'warning' | 'critical' = 'healthy';
          
          if (data.voltage < 10 || data.load > 90) {
            status = 'critical';
          } else if (data.voltage < 90 || data.load > 70) {
            status = 'warning';
          }

          return {
            sectorId,
            voltage: data.voltage,
            load: data.load,
            status,
          };
        });
        setSectors(sectorStatuses);

        // Calculate airspace congestion from aircraft position events and hotspot events
        const aircraftEvents = data.events.filter(
          (e: Event) => e.topic === 'chronos.events.airspace.aircraft.position' || 
                       e.topic === 'chronos.events.airspace.hotspot.detected' ||
                       e.topic === 'chronos.events.geo.risk_area'
        );
        
        // Count unique aircraft in last 5 minutes
        const recentAircraftEvents = aircraftEvents.filter(
          (e: Event) => {
            const eventTime = new Date(e.timestamp).getTime();
            return eventTime > Date.now() - 5 * 60 * 1000;
          }
        );
        
        // Count unique aircraft by icao24 (from aircraft.position events)
        const aircraftPositionEvents = recentAircraftEvents.filter(
          (e: Event) => e.topic === 'chronos.events.airspace.aircraft.position'
        );
        const uniqueAircraft = new Set(
          aircraftPositionEvents.map((e: Event) => {
            // Try multiple paths for icao24
            return e.payload?.details?.icao24 || 
                   e.payload?.icao24 || 
                   e.payload?.details?.location?.icao24;
          }).filter(Boolean)
        );
        
        // Also check for congestion hotspots
        const hotspotEvents = recentAircraftEvents.filter(
          (e: Event) => e.topic === 'chronos.events.airspace.hotspot.detected' ||
                       (e.topic === 'chronos.events.geo.risk_area' && 
                        e.payload?.details?.risk_type === 'airspace_congestion')
        );
        
        // Calculate congestion: base on aircraft count, boost if hotspots detected
        const aircraftCount = uniqueAircraft.size;
        const hotspotCount = hotspotEvents.length;
        let congestion = Math.min(100, (aircraftCount / 15) * 100);
        
        // If hotspots detected, increase congestion
        if (hotspotCount > 0) {
          congestion = Math.min(100, congestion + (hotspotCount * 20));
        }
        
        // Also check payload details for aircraft_count if available
        hotspotEvents.forEach((e: Event) => {
          const aircraftCountInHotspot = e.payload?.details?.aircraft_count || 
                                        e.payload?.details?.aircraftCount;
          if (aircraftCountInHotspot) {
            congestion = Math.min(100, Math.max(congestion, (aircraftCountInHotspot / 15) * 100));
          }
        });
        
        setAirspaceCongestion(congestion);

        // Find latest recovery plan
        const recoveryPlans = data.events.filter(
          (e: Event) => e.topic === 'chronos.events.recovery.plan'
        );
        if (recoveryPlans.length > 0) {
          const sorted = recoveryPlans.sort((a: any, b: any) => 
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          );
          setLatestPlan(sorted[0].payload?.details || null);
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
        <div className="text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold text-white">Chronos Control Center</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const newState = !voiceEnabled;
              console.log('[VOICE] ============================================');
              console.log('[VOICE] Button clicked! Toggling voice:', newState ? 'ON' : 'OFF');
              console.log('[VOICE] ============================================');
              
              // CRITICAL: Update global state FIRST (before React state)
              // This ensures the module-level check happens immediately
              setGlobalVoiceEnabled(newState);
              
              // Then update React state (for UI feedback)
              setVoiceEnabled(newState);
              
              // Force cancel speech synthesis immediately (extra safety)
              if (!newState && 'speechSynthesis' in window) {
                console.log('[VOICE] Force canceling speech synthesis from button');
                // Very aggressive cancellation - try to interrupt with silent utterance
                const interrupt = () => {
                  try {
                    speechSynthesis.pause();
                    speechSynthesis.cancel();
                    // Try to interrupt with a silent utterance
                    const silent = new SpeechSynthesisUtterance('');
                    silent.volume = 0;
                    speechSynthesis.speak(silent);
                    speechSynthesis.cancel();
                  } catch (e) {
                    // Ignore errors, just try to cancel
                    speechSynthesis.cancel();
                  }
                };
                
                // Immediate
                interrupt();
                
                // Try multiple times with different methods
                const cancelAttempts = [10, 50, 100, 200, 500, 1000];
                cancelAttempts.forEach(delay => {
                  setTimeout(() => {
                    interrupt();
                    console.log(`[VOICE] Cancel attempt at ${delay}ms`);
                  }, delay);
                });
              }
            }}
            className={`px-4 py-2 rounded-lg border transition-colors ${
              voiceEnabled
                ? 'bg-green-600 border-green-500 text-white'
                : 'bg-gray-700 border-gray-600 text-gray-300'
            }`}
            title={voiceEnabled ? 'Voice announcements enabled' : 'Voice announcements disabled'}
          >
            {voiceEnabled ? '🔊 Voice On' : '🔇 Voice Off'}
          </button>
          <AutonomyBadge level={autonomyLevel} />
        </div>
      </div>

      {/* Status Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {sectors.map((sector) => (
          <SectorHealthCard
            key={sector.sectorId}
            sectorId={sector.sectorId}
            voltage={sector.voltage}
            load={sector.load}
            status={sector.status}
          />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Airspace & Recovery Plan */}
        <div className="lg:col-span-1 space-y-6">
          <AirspaceGauge congestion={airspaceCongestion} />
          <RecoveryPlanPanel plan={latestPlan} />
        </div>

        {/* Right Column - Timeline Feed */}
        <div className="lg:col-span-2">
          <div className="bg-dark-surface border border-dark-border rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-6">Event Timeline</h2>
            <div className="space-y-0">
              {events.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  No events found. Start the crisis generator to see events.
                </div>
              ) : (
                events.slice(0, 20).map((event) => (
                  <TimelineEvent key={event._id} event={event} />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
