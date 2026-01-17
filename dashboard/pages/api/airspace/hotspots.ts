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

    // Build query for hotspot events
    const query: any = {
      topic: 'chronos.events.airspace.hotspot.detected',
    };
    
    // If plan_id provided, filter by correlation_id
    if (planId) {
      query['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    // Fetch hotspot events
    const filteredEvents = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(100)
      .toArray();

    // Get corresponding solutions
    const solutionQuery: any = {
      topic: 'chronos.events.airspace.solution.proposed',
    };
    
    if (planId) {
      solutionQuery['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    const filteredSolutions = await collection
      .find(solutionQuery)
      .sort({ timestamp: -1 })
      .limit(200)
      .toArray();

    // Map hotspots with mitigation options
    const hotspots = filteredEvents.map((e: any) => {
      const hotspotDetails = e.payload?.details || {};
      const hotspotId = hotspotDetails.hotspot_id;

      // Find solutions for this hotspot
      const solutions = filteredSolutions
        .filter((s: any) => s.payload?.details?.problem_id === hotspotId)
        .map((s: any) => ({
          solution_id: s.payload?.details?.solution_id,
          solution_type: s.payload?.details?.solution_type,
          proposed_actions: s.payload?.details?.proposed_actions || [],
          description: `Mitigation: ${s.payload?.details?.solution_type || 'unknown'}`,
        }));

      return {
        hotspot_id: hotspotId,
        hotspot_type: hotspotDetails.hotspot_type,
        location: hotspotDetails.location,
        affected_flights: hotspotDetails.affected_flights || [],
        severity: hotspotDetails.severity,
        density: hotspotDetails.density,
        capacity_limit: hotspotDetails.capacity_limit,
        current_count: hotspotDetails.current_count,
        description: hotspotDetails.description,
        mitigation_options: solutions,
      };
    });

    console.log(`[Hotspots API] Found ${filteredEvents.length} hotspot events, ${hotspots.length} hotspots with mitigations`);
    
    res.status(200).json({ hotspots });
  } catch (error: any) {
    console.error('Error fetching hotspots:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch hotspots' });
  }
}

