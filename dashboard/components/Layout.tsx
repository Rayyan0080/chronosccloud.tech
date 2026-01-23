import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState, useEffect } from 'react';

type SystemStatus = {
  live_mode: 'on' | 'off';
  transit_mode: 'live' | 'mock';
  adapters: Array<{
    name: string;
    mode: 'live' | 'mock' | 'unknown';
    enabled: boolean;
    degraded: boolean;
  }>;
  degraded_adapters: string[];
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const navItems = [
    { href: '/', label: 'Event Feed' },
    { href: '/map', label: 'Map' },
    { href: '/radar', label: 'Radar' },
    { href: '/airspace', label: 'Airspace' },
    { href: '/compare', label: 'Agentic Compare' },
    { href: '/audit', label: 'Audit' },
  ];

  // Fetch system status to check LIVE_MODE and adapter status
  const fetchSystemStatus = async () => {
    try {
      const res = await fetch('/api/system-status');
      const data = await res.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Error fetching system status:', error);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    // Refresh every 30 seconds
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-dark-bg">
      <nav className="border-b border-dark-border bg-dark-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-white">Chronos Dashboard</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                      router.pathname === item.href
                        ? 'border-blue-500 text-white'
                        : 'border-transparent text-dark-muted hover:text-white hover:border-gray-300'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
            {/* Status Badges */}
            <div className="flex items-center gap-2">
              {/* LIVE_MODE Badge - Toggle Button */}
              {systemStatus && (
                <button
                  onClick={async () => {
                    const newMode = systemStatus.live_mode === 'on' ? 'off' : 'on';
                    try {
                      const response = await fetch('/api/live-mode/toggle', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ live_mode: newMode }),
                      });
                      const data = await response.json();
                      if (data.success) {
                        // Update local state immediately
                        setSystemStatus({ ...systemStatus, live_mode: newMode });
                        // Show notification
                        alert(data.message || `LIVE_MODE set to ${newMode}. Please restart the live_data runner.`);
                        // Refresh status after a short delay
                        setTimeout(() => {
                          fetchSystemStatus();
                        }, 1000);
                      } else {
                        alert(`Error: ${data.error || 'Failed to update LIVE_MODE'}`);
                      }
                    } catch (error: any) {
                      console.error('Error toggling LIVE_MODE:', error);
                      alert(`Error: ${error.message || 'Failed to update LIVE_MODE'}`);
                    }
                  }}
                  className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-white text-xs font-semibold transition-all hover:opacity-80 cursor-pointer ${
                    systemStatus.live_mode === 'on' 
                      ? 'bg-green-600 bg-opacity-90 hover:bg-green-700' 
                      : 'bg-gray-600 bg-opacity-90 hover:bg-gray-700'
                  }`}
                  title={`Click to toggle LIVE_MODE (currently ${systemStatus.live_mode}). Restart live_data runner after toggling.`}
                >
                  <span>LIVE: {systemStatus.live_mode.toUpperCase()}</span>
                </button>
              )}
              
              {/* Adapter Degradation Badge */}
              {systemStatus && systemStatus.degraded_adapters.length > 0 && (
                <div className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 bg-yellow-600 bg-opacity-90 text-white text-xs font-semibold">
                  <span>⚠️</span>
                  <span>Adapter degraded (falling back to mock)</span>
                </div>
              )}
              
              {/* Transit Mode Badge (only show if transit is mock and LIVE_MODE is on) */}
              {systemStatus && systemStatus.live_mode === 'on' && systemStatus.transit_mode === 'mock' && (
                <div className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 bg-yellow-600 bg-opacity-90 text-white text-xs font-semibold">
                  <span>⚠️</span>
                  <span>Transit: MOCK</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main className={`${router.pathname === '/map' ? 'px-0' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8'} py-8`}>
        {children}
      </main>
    </div>
  );
}

