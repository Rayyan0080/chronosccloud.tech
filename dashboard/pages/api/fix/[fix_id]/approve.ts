import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../../lib/mongodb';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

type ResponseData = {
  success: boolean;
  message?: string;
  error?: string;
};

// Helper to publish event to NATS via Python script
async function publishToNATS(topic: string, payload: any): Promise<void> {
  const scriptPath = path.join(process.cwd(), 'dashboard', 'scripts', 'publish_fix_event.py');
  const eventJson = JSON.stringify(payload);
  
  // Use base64 encoding to avoid shell escaping issues
  const eventJsonBase64 = Buffer.from(eventJson).toString('base64');
  
  try {
    const { stdout } = await execAsync(
      `python3 "${scriptPath}" "${topic}" "${eventJsonBase64}"`
    );
    
    const result = JSON.parse(stdout.trim());
    if (!result.success) {
      throw new Error(result.error || 'Failed to publish event');
    }
  } catch (error: any) {
    // Try with python instead of python3
    try {
      const { stdout } = await execAsync(
        `python "${scriptPath}" "${topic}" "${eventJsonBase64}"`
      );
      const result = JSON.parse(stdout.trim());
      if (!result.success) {
        throw new Error(result.error || 'Failed to publish event');
      }
    } catch (error2: any) {
      console.error('NATS publish error:', error2);
      throw new Error(`Failed to publish to NATS: ${error.message || error2.message}`);
    }
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { fix_id } = req.query;
    if (!fix_id || typeof fix_id !== 'string') {
      return res.status(400).json({ success: false, error: 'fix_id is required' });
    }

    // Get fix details from MongoDB
    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Find the fix.review_required event for this fix_id
    const reviewEvent = await collection.findOne({
      topic: 'chronos.events.fix.review_required',
      'payload.details.fix_id': fix_id,
    });

    if (!reviewEvent) {
      return res.status(404).json({ success: false, error: 'Fix not found or not in review' });
    }

    const fixDetails = reviewEvent.payload.details;
    const correlationId = reviewEvent.payload.correlation_id || fixDetails?.correlation_id || 'unknown';
    const sectorId = reviewEvent.payload.sector_id || 'unknown';

    // Create fix.approved event
    const approvedEvent = {
      event_id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      source: 'operator-dashboard',
      severity: 'info',
      sector_id: sectorId,
      summary: `Fix ${fix_id} approved for deployment`,
      correlation_id: correlationId,
      details: {
        ...fixDetails,
        approved_by: 'operator-001',
        approved_at: new Date().toISOString(),
      },
    };

    // Create fix.deploy_requested event
    const deployRequestedEvent = {
      event_id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      source: 'operator-dashboard',
      severity: 'warning',
      sector_id: sectorId,
      summary: `Deployment requested for fix ${fix_id}`,
      correlation_id: correlationId,
      details: {
        ...fixDetails,
        deploy_requested_by: 'operator-001',
        deploy_requested_at: new Date().toISOString(),
      },
    };

    // Save events to MongoDB first (so they're visible even if NATS fails)
    await collection.insertMany([
      {
        topic: 'chronos.events.fix.approved',
        payload: approvedEvent,
        timestamp: new Date(approvedEvent.timestamp),
        logged_at: new Date(),
      },
      {
        topic: 'chronos.events.fix.deploy_requested',
        payload: deployRequestedEvent,
        timestamp: new Date(deployRequestedEvent.timestamp),
        logged_at: new Date(),
      },
    ]);

    // Try to publish to NATS (non-blocking - events are already in MongoDB)
    try {
      await publishToNATS('chronos.events.fix.approved', approvedEvent);
      await publishToNATS('chronos.events.fix.deploy_requested', deployRequestedEvent);
    } catch (natsError: any) {
      // Log but don't fail - events are already saved to MongoDB
      console.warn('NATS publish failed (events saved to MongoDB):', natsError.message);
    }

    res.status(200).json({
      success: true,
      message: `Fix ${fix_id} approved and deployment requested (simulated actuation)`,
    });
  } catch (error: any) {
    console.error('Error approving fix:', error);
    console.error('Error stack:', error.stack);
    res.status(500).json({ 
      success: false,
      error: error.message || 'Failed to approve fix',
    });
  }
}

