import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../lib/mongodb';

// Disable default body parser for SSE
export const config = {
  api: {
    bodyParser: false,
  },
};

type FixEventDocument = {
  _id?: any;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    correlation_id: string;
    details: {
      fix_id: string;
      correlation_id: string;
      source: string;
      title: string;
      summary: string;
      actions: Array<any>;
      risk_level: string;
      expected_impact: any;
      created_at: string;
      proposed_by: string;
      requires_human_approval: boolean;
    };
  };
  timestamp: Date;
  logged_at: Date;
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
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');
    const verificationCollection = db.collection('fix_verifications');

    // Send initial connection message
    res.write(`data: ${JSON.stringify({ type: 'connected', timestamp: new Date().toISOString() })}\n\n`);

    // Helper function to get processed fix IDs
    const getProcessedFixIds = async () => {
      const processedFixIds = await collection
        .find({
          topic: { $in: ['chronos.events.fix.approved', 'chronos.events.fix.rejected'] },
        })
        .toArray();
      
      return new Set(
        processedFixIds.map((e: any) => e.payload?.details?.fix_id).filter(Boolean)
      );
    };

    // Helper function to format fix event
    const formatFixEvent = async (event: FixEventDocument) => {
      const fixId = event.payload?.details?.fix_id;
      if (!fixId) return null;

      // Check if already processed
      const processedIds = await getProcessedFixIds();
      if (processedIds.has(fixId)) return null;

      // Get verification status
      const verification = await verificationCollection.findOne({ fix_id: fixId });
      const verificationStatus = verification ? {
        fix_id: verification.fix_id,
        status: verification.status || 'not_started',
        started_at: verification.started_at instanceof Date ? verification.started_at.toISOString() : verification.started_at,
        completed_at: verification.completed_at instanceof Date ? verification.completed_at.toISOString() : verification.completed_at,
        passed: verification.passed,
        metrics: verification.metrics,
        timeline: verification.timeline || [],
      } : undefined;

      return {
        type: 'fix_update',
        _id: event._id.toString(),
        topic: event.topic,
        payload: event.payload,
        timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
        verification: verificationStatus,
      };
    };

    // Send any fix events since the 'since' timestamp (replay)
    if (sinceParam) {
      const replayEvents = await collection
        .find({
          topic: { $in: ['chronos.events.fix.review_required', 'chronos.events.fix.approved', 'chronos.events.fix.rejected'] },
          timestamp: { $gte: since },
        })
        .sort({ timestamp: 1 })
        .limit(100)
        .toArray();

      for (const event of replayEvents) {
        const formatted = await formatFixEvent(event as FixEventDocument);
        if (formatted) {
          res.write(`data: ${JSON.stringify(formatted)}\n\n`);
        }
      }
    }

    // Set up change stream to watch for new fix events
    const changeStream = collection.watch(
      [
        {
          $match: {
            'operationType': 'insert',
            'fullDocument.topic': {
              $in: [
                'chronos.events.fix.review_required',
                'chronos.events.fix.approved',
                'chronos.events.fix.rejected',
                'chronos.events.fix.deploy_started',
                'chronos.events.fix.deploy_succeeded',
                'chronos.events.fix.deploy_failed',
                'chronos.events.fix.verified',
              ],
            },
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
    changeStream.on('change', async (change) => {
      try {
        if ('fullDocument' in change && change.fullDocument) {
          const formatted = await formatFixEvent(change.fullDocument as FixEventDocument);
          if (formatted) {
            res.write(`data: ${JSON.stringify(formatted)}\n\n`);
          } else {
            // Fix was processed (approved/rejected), send removal event
            const fixId = (change.fullDocument as any).payload?.details?.fix_id;
            if (fixId) {
              res.write(`data: ${JSON.stringify({ type: 'fix_removed', fix_id: fixId })}\n\n`);
            }
          }
        }
      } catch (err) {
        console.error('Error sending fix event:', err);
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

