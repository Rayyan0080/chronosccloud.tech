import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

type GeoEvent = {
  _id: string;
  topic: string;
  payload: any;
  timestamp: Date;
  logged_at: Date;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ incidents: any[]; riskAreas: any[] } | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { timeRange = '6h', severity } = req.query;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Calculate time threshold based on timeRange
    const now = new Date();
    let timeThreshold: Date;
    switch (timeRange) {
      case '1h':
        timeThreshold = new Date(now.getTime() - 60 * 60 * 1000);
        break;
      case '6h':
        timeThreshold = new Date(now.getTime() - 6 * 60 * 60 * 1000);
        break;
      case '24h':
        timeThreshold = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      default:
        timeThreshold = new Date(now.getTime() - 6 * 60 * 60 * 1000);
    }

    // Build query for geo events
    const query: any = {
      topic: { $in: ['chronos.events.geo.incident', 'chronos.events.geo.risk_area'] },
      timestamp: { $gte: timeThreshold },
    };

    // Add severity filter if provided
    // Map user-friendly severity names to schema values
    const severityParam = severity as string;
    if (severityParam && severityParam !== 'all' && severityParam !== '') {
      const severityMap: Record<string, string> = {
        'low': 'info',
        'med': 'warning',
        'medium': 'warning',
        'high': 'error',
        'critical': 'critical',
      };
      const mappedSeverity = severityMap[severityParam.toLowerCase()] || severityParam;
      query['payload.severity'] = mappedSeverity;
    }

    // Fetch geo events
    const events = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(1000)
      .toArray();

    // Separate incidents and risk areas
    const incidents = events
      .filter((e: GeoEvent) => e.topic === 'chronos.events.geo.incident')
      .map((e: GeoEvent) => ({
        event_id: e.payload?.event_id || e._id.toString(),
        id: e.payload?.details?.id,
        timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
        severity: e.payload?.severity || 'info',
        summary: e.payload?.summary || '',
        geometry: e.payload?.details?.geometry || {},
        style: e.payload?.details?.style || { color: 'red', opacity: 0.5, outline: true },
        incident_type: e.payload?.details?.incident_type,
        description: e.payload?.details?.description,
        status: e.payload?.details?.status,
      }));

    const riskAreas = events
      .filter((e: GeoEvent) => e.topic === 'chronos.events.geo.risk_area')
      .map((e: GeoEvent) => ({
        event_id: e.payload?.event_id || e._id.toString(),
        id: e.payload?.details?.id,
        timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
        severity: e.payload?.severity || 'info',
        summary: e.payload?.summary || '',
        geometry: e.payload?.details?.geometry || {},
        style: e.payload?.details?.style || { color: 'red', opacity: 0.5, outline: true },
        risk_level: e.payload?.details?.risk_level,
        risk_type: e.payload?.details?.risk_type,
        description: e.payload?.details?.description,
      }));

    console.log(`[Geo Events API] Found ${incidents.length} incidents, ${riskAreas.length} risk areas (timeRange: ${timeRange}, severity: ${severity || 'all'})`);

    res.status(200).json({ incidents, riskAreas });
  } catch (error: any) {
    console.error('Error fetching geo events:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch geo events' });
  }
}

