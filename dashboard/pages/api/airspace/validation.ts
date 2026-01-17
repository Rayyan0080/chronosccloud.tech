import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../lib/mongodb';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<any>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const planId = req.query.plan_id as string | undefined;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Build query for flight.parsed events (violations are detected from these)
    const query: any = {
      topic: 'chronos.events.airspace.flight.parsed',
    };
    
    // If plan_id provided, filter by correlation_id
    if (planId) {
      query['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    // Fetch flight.parsed events
    const filteredEvents = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(1000)
      .toArray();

    // Extract violations from flight.parsed events (check for parse_errors)
    // Or from trajectory analysis if available
    const violations: any[] = [];

    // Check flight.parsed events for parse errors
    filteredEvents
      .filter((e: any) => e.topic === 'chronos.events.airspace.flight.parsed')
      .forEach((e: any) => {
        const parseErrors = e.payload?.details?.parse_errors || [];
        if (parseErrors.length > 0) {
          parseErrors.forEach((error: string, idx: number) => {
            violations.push({
              violation_id: `VIOL-PARSE-${e.payload?.details?.flight_id}-${idx}`,
              violation_type: 'parse_error',
              flight_id: e.payload?.details?.flight_id,
              severity: 'warning',
              description: error,
              suggested_fixes: [
                { description: 'Review flight plan JSON format' },
                { description: 'Check required fields are present' },
              ],
            });
          });
        }
      });

    // Check for altitude/speed violations (synthetic - would come from trajectory analysis)
    // For demo, we'll create some based on flight data
    filteredEvents
      .filter((e: any) => e.topic === 'chronos.events.airspace.flight.parsed')
      .forEach((e: any) => {
        const details = e.payload?.details || {};
        const altitude = details.altitude;
        const speed = details.speed;

        // Altitude violations
        if (altitude && (altitude < 10000 || altitude > 50000)) {
          violations.push({
            violation_id: `VIOL-ALT-${details.flight_id}`,
            violation_type: 'altitude',
            flight_id: details.flight_id,
            severity: altitude < 10000 ? 'critical' : 'warning',
            description: `Flight ${details.flight_id} has altitude ${altitude}ft (valid range: 10,000-50,000ft)`,
            value: altitude,
            threshold: altitude < 10000 ? 10000 : 50000,
            suggested_fixes: [
              {
                description: altitude < 10000
                  ? `Increase altitude to at least 10,000ft (recommended: 25,000ft)`
                  : `Decrease altitude to at most 50,000ft (recommended: 40,000ft)`,
              },
            ],
          });
        }

        // Speed violations
        if (speed && (speed < 200 || speed > 600)) {
          violations.push({
            violation_id: `VIOL-SPEED-${details.flight_id}`,
            violation_type: 'speed',
            flight_id: details.flight_id,
            severity: 'warning',
            description: `Flight ${details.flight_id} has speed ${speed}kts (valid range: 200-600kts)`,
            value: speed,
            threshold: speed < 200 ? 200 : 600,
            suggested_fixes: [
              {
                description: speed < 200
                  ? `Increase speed to at least 200kts (recommended: 400kts)`
                  : `Decrease speed to at most 600kts (recommended: 450kts)`,
              },
            ],
          });
        }
      });

    console.log(`[Validation API] Found ${filteredEvents.length} flight events, ${violations.length} violations`);
    
    res.status(200).json({ violations });
  } catch (error: any) {
    console.error('Error fetching violations:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch violations' });
  }
}

