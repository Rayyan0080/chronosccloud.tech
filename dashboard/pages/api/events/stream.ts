import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../lib/mongodb';

// Disable default body parser for SSE
export const config = {
  api: {
    bodyParser: false,
  },
};

type EventDocument = {
  _id?: any;
  event_id: string;
  timestamp: Date;
  topic: string;
  payload: {
    event_id?: string;
    timestamp?: string;
    severity?: string;
    summary?: string;
    geometry?: any;
    details?: any;
    [key: string]: any;
  };
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Set up SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering

  // Get since parameter for replay
  const sinceParam = req.query.since as string;
  const since = sinceParam ? new Date(sinceParam) : new Date(Date.now() - 5 * 60 * 1000); // Default: last 5 minutes

  try {
    // Connect to MongoDB
    const client = await clientPromise;
    const db = client.db(process.env.MONGODB_DB || 'chronos');
    const collection = db.collection('events');

    // Send initial connection message
    res.write(`data: ${JSON.stringify({ type: 'connected', timestamp: new Date().toISOString() })}\n\n`);

    // Send any events since the 'since' timestamp (replay)
    if (sinceParam) {
      const replayEvents = await collection
        .find({
          timestamp: { $gte: since },
        })
        .sort({ timestamp: 1 })
        .limit(100)
        .toArray();

      for (const event of replayEvents) {
        const eventData = formatEvent(event as EventDocument);
        res.write(`data: ${JSON.stringify(eventData)}\n\n`);
      }
    }

    // Set up change stream to watch for new events
    const changeStream = collection.watch(
      [
        {
          $match: {
            'operationType': 'insert',
          },
        },
      ],
      {
        fullDocument: 'updateLookup',
      }
    );

    // Send heartbeat every 15 seconds
    const heartbeatInterval = setInterval(() => {
      try {
        res.write(`data: ${JSON.stringify({ type: 'heartbeat', timestamp: new Date().toISOString() })}\n\n`);
      } catch (err) {
        // Client disconnected
        clearInterval(heartbeatInterval);
        changeStream.close();
      }
    }, 15000);

    // Handle new events from change stream
    changeStream.on('change', (change) => {
      try {
        if ('fullDocument' in change && change.fullDocument) {
          const eventData = formatEvent(change.fullDocument as EventDocument);
          res.write(`data: ${JSON.stringify(eventData)}\n\n`);
        }
      } catch (err) {
        console.error('Error sending event:', err);
      }
    });

    // Handle client disconnect
    req.on('close', () => {
      clearInterval(heartbeatInterval);
      changeStream.close();
      res.end();
    });

    // Keep connection alive
    req.on('aborted', () => {
      clearInterval(heartbeatInterval);
      changeStream.close();
      res.end();
    });

  } catch (error: any) {
    console.error('SSE stream error:', error);
    res.write(`data: ${JSON.stringify({ type: 'error', message: error.message })}\n\n`);
    res.end();
  }
}

function formatEvent(doc: EventDocument) {
  const payload = doc.payload || {};
  const geometry = payload.geometry || payload.details?.geometry;
  
  return {
    event_id: payload.event_id || doc.event_id || doc._id?.toString(),
    timestamp: doc.timestamp?.toISOString() || payload.timestamp || new Date().toISOString(),
    topic: doc.topic,
    severity: payload.severity || 'info',
    summary: payload.summary || 'Event',
    geometry: geometry,
    details: payload.details,
    source: payload.source,
  };
}

