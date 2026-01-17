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
      'chronos.events.airspace.plan.uploaded',
    ];

    const query: any = {
      topic: { $in: airspaceTopics },
    };

    // If plan_id provided, filter by correlation_id
    if (planId) {
      query['payload.correlation_id'] = { $regex: planId, $options: 'i' };
    }

    // Fetch relevant events
    const events = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(1000)
      .toArray();

    // Count different event types
    const flights = events.filter(
      (e: any) => e.topic === 'chronos.events.airspace.flight.parsed'
    );
    const conflicts = events.filter(
      (e: any) => e.topic === 'chronos.events.airspace.conflict.detected'
    );
    const hotspots = events.filter(
      (e: any) => e.topic === 'chronos.events.airspace.hotspot.detected'
    );
    
    // Violations are detected from flight.parsed events with parse_errors or from analysis
    // For now, check flight.parsed events for parse_errors
    const violations: any[] = [];
    flights.forEach((f: any) => {
      const parseErrors = f.payload?.details?.parse_errors || [];
      if (parseErrors.length > 0) {
        violations.push(...parseErrors);
      }
    });
    
    // Also check for altitude/speed violations in flight details
    flights.forEach((f: any) => {
      const details = f.payload?.details || {};
      const altitude = details.altitude;
      const speed = details.speed;
      if (altitude && (altitude < 10000 || altitude > 50000)) {
        violations.push({ type: 'altitude', flight_id: details.flight_id });
      }
      if (speed && (speed < 200 || speed > 600)) {
        violations.push({ type: 'speed', flight_id: details.flight_id });
      }
    });

    // Calculate top risk score (simplified - use conflict severity)
    let topRiskScore = 0;
    conflicts.forEach((c: any) => {
      const severity = c.payload?.details?.severity_level || 'medium';
      const score = severity === 'critical' ? 10 : severity === 'high' ? 7 : severity === 'medium' ? 4 : 1;
      topRiskScore = Math.max(topRiskScore, score);
    });

    console.log(`[Overview API] Found ${events.length} total events, ${flights.length} flights, ${conflicts.length} conflicts, ${hotspots.length} hotspots, ${violations.length} violations`);
    
    res.status(200).json({
      flights_count: flights.length,
      conflicts_count: conflicts.length,
      hotspots_count: hotspots.length,
      violations_count: violations.length,
      top_risk_score: topRiskScore,
    });
  } catch (error: any) {
    console.error('Error fetching overview:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch overview' });
  }
}

