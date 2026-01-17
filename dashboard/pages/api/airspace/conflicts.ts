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

    // Build query for conflict events
    const query: any = {
      topic: 'chronos.events.airspace.conflict.detected',
    };
    
    // If plan_id provided, filter by correlation_id
    if (planId) {
      query['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    // Fetch conflict events
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

    // Map conflicts with solutions
    const conflicts = filteredEvents.map((e: any) => {
      const conflictDetails = e.payload?.details || {};
      const conflictId = conflictDetails.conflict_id;

      // Find solutions for this conflict
      const solutions = filteredSolutions
        .filter((s: any) => s.payload?.details?.problem_id === conflictId)
        .map((s: any) => ({
          solution_id: s.payload?.details?.solution_id,
          solution_type: s.payload?.details?.solution_type,
          proposed_actions: s.payload?.details?.proposed_actions || [],
          description: `Solution ${s.payload?.details?.solution_type || 'unknown'}`,
        }));

      return {
        conflict_id: conflictId,
        conflict_type: conflictDetails.conflict_type,
        severity_level: conflictDetails.severity_level,
        flight_ids: conflictDetails.flight_ids || [],
        conflict_location: conflictDetails.conflict_location,
        conflict_time: conflictDetails.conflict_time,
        minimum_separation: conflictDetails.minimum_separation,
        required_separation: conflictDetails.required_separation,
        conflict_duration: conflictDetails.conflict_duration,
        recommended_solutions: solutions,
      };
    });

    console.log(`[Conflicts API] Found ${filteredEvents.length} conflict events, ${conflicts.length} conflicts with solutions`);
    
    res.status(200).json({ conflicts });
  } catch (error: any) {
    console.error('Error fetching conflicts:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch conflicts' });
  }
}

