import type { NextApiRequest, NextApiResponse } from 'next';

type AdapterStatus = {
  name: string;
  mode: 'live' | 'mock' | 'unknown';
  enabled: boolean;
  degraded: boolean;
  last_fetch?: string;
  last_error?: string;
};

type SystemStatus = {
  live_mode: 'on' | 'off';
  transit_mode: 'live' | 'mock';
  adapters: AdapterStatus[];
  degraded_adapters: string[];
  [key: string]: any;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<SystemStatus | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get LIVE_MODE from environment variable
    const liveMode = process.env.LIVE_MODE?.toLowerCase().trim();
    const isLiveMode = liveMode === 'on';
    
    // Get transit mode from environment variable
    // In Next.js, server-side env vars are available via process.env
    // Match Python logic: check TRANSIT_MODE first, then auto-detect based on API key
    let transitMode = process.env.TRANSIT_MODE?.toLowerCase().trim();
    
    if (transitMode !== 'live' && transitMode !== 'mock') {
      // Auto-detect: if API key exists, use live mode
      transitMode = process.env.OCTRANSPO_API_KEY ? 'live' : 'mock';
    }

    // For now, return basic status. In a real implementation, you might want to:
    // 1. Query a status endpoint from the Python runner
    // 2. Read from a shared status file
    // 3. Use a message broker to get status
    // For this demo, we'll infer adapter status from environment variables
    
    const adapters: AdapterStatus[] = [];
    const degraded: string[] = [];
    
    // Check which adapters are enabled
    const enabledAdapters = process.env.LIVE_ADAPTERS?.split(',').map(a => a.trim()) || [];
    
    for (const adapterName of enabledAdapters) {
      let mode: 'live' | 'mock' = 'mock';
      let degraded_adapter = false;
      
      if (isLiveMode) {
        // Check if adapter has required credentials/config
        if (adapterName === 'oc_transpo_gtfsrt' || adapterName === 'oc_transpo') {
          mode = process.env.OCTRANSPO_SUBSCRIPTION_KEY || process.env.OCTRANSPO_API_KEY ? 'live' : 'mock';
          if (mode === 'mock' && isLiveMode) {
            degraded_adapter = true;
          }
        } else if (adapterName === 'ottawa_traffic') {
          mode = 'live'; // Public API, no key needed
        } else if (adapterName === 'ontario511') {
          mode = 'live'; // Public API, no key needed
        } else if (adapterName === 'opensky_airspace') {
          mode = (process.env.OPENSKY_USER && process.env.OPENSKY_PASS) ? 'live' : 'live'; // Can work without auth
        } else {
          mode = 'live'; // Default to live if LIVE_MODE=on
        }
      } else {
        mode = 'mock'; // Force mock if LIVE_MODE=off
      }
      
      adapters.push({
        name: adapterName,
        mode: mode,
        enabled: true,
        degraded: degraded_adapter,
      });
      
      if (degraded_adapter) {
        degraded.push(adapterName);
      }
    }

    const status: SystemStatus = {
      live_mode: isLiveMode ? 'on' : 'off',
      transit_mode: transitMode === 'live' ? 'live' : 'mock',
      adapters: adapters,
      degraded_adapters: degraded,
    };

    res.status(200).json(status);
  } catch (error: any) {
    console.error('Error fetching system status:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch system status' });
  }
}

