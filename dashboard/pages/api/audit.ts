import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

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

type ResponseData = {
  events: AuditEvent[];
  count: number;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const limit = parseInt(req.query.limit as string) || 100;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Fetch audit.decision events
    const events = await collection
      .find({ topic: 'chronos.events.audit.decision' })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();

    // Convert to response format
    const formattedEvents: AuditEvent[] = events.map((event: any) => ({
      _id: event._id.toString(),
      topic: event.topic,
      payload: event.payload,
      timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
    }));

    res.status(200).json({
      events: formattedEvents,
      count: formattedEvents.length,
    });
  } catch (error: any) {
    console.error('Error fetching audit events:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch audit events' });
  }
}

