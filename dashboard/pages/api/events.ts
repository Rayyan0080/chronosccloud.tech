import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

type Event = {
  _id: string;
  topic: string;
  payload: any;
  timestamp: string;
  logged_at: string;
};

type ResponseData = {
  events: Event[];
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
    const limit = parseInt(req.query.limit as string) || 50;
    const topic = req.query.topic as string | undefined;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Build query
    const query: any = {};
    if (topic) {
      query.topic = topic;
    }

    // Fetch events
    const events = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();

    // Convert to response format
    const formattedEvents: Event[] = events.map((event: any) => ({
      _id: event._id.toString(),
      topic: event.topic,
      payload: event.payload,
      timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
      logged_at: event.logged_at instanceof Date ? event.logged_at.toISOString() : event.logged_at,
    }));

    res.status(200).json({
      events: formattedEvents,
      count: formattedEvents.length,
    });
  } catch (error: any) {
    console.error('Error fetching events:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch events' });
  }
}

