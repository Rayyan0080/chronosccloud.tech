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

    // Build query for airspace events
    const airspaceTopics = [
      'chronos.events.airspace.flight.parsed',
      'chronos.events.airspace.conflict.detected',
      'chronos.events.airspace.hotspot.detected',
    ];

    const query: any = {
      topic: { $in: airspaceTopics },
    };

    // If plan_id provided, filter by correlation_id
    if (planId) {
      query['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    // Fetch relevant events
    const filteredEvents = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(1000)
      .toArray();

    // Extract trajectories from flight.parsed events
    const trajectories = filteredEvents
      .filter((e: any) => e.topic === 'chronos.events.airspace.flight.parsed')
      .map((e: any) => ({
        flight_id: e.payload?.details?.flight_id,
        route: e.payload?.details?.route || [],
        origin: e.payload?.details?.origin,
        destination: e.payload?.details?.destination,
        altitude: e.payload?.details?.altitude,
      }));

    // Extract conflicts
    const conflicts = filteredEvents
      .filter((e: any) => e.topic === 'chronos.events.airspace.conflict.detected')
      .map((e: any) => ({
        conflict_id: e.payload?.details?.conflict_id,
        conflict_location: e.payload?.details?.conflict_location,
        flight_ids: e.payload?.details?.flight_ids || [],
        severity_level: e.payload?.details?.severity_level,
      }));

    // Extract hotspots
    const hotspots = filteredEvents
      .filter((e: any) => e.topic === 'chronos.events.airspace.hotspot.detected')
      .map((e: any) => ({
        hotspot_id: e.payload?.details?.hotspot_id,
        location: e.payload?.details?.location,
        affected_flights: e.payload?.details?.affected_flights || [],
        severity: e.payload?.details?.severity,
      }));

    res.status(200).json({
      trajectories,
      conflicts,
      hotspots,
    });
  } catch (error: any) {
    console.error('Error fetching map data:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch map data' });
  }
}

