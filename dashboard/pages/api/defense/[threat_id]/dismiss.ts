import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../../lib/mongodb';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ success: boolean; message?: string; error?: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { threat_id } = req.query;
    if (!threat_id || typeof threat_id !== 'string') {
      return res.status(400).json({ success: false, error: 'threat_id is required' });
    }

    const { reason } = req.body;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Fetch the threat.detected event
    const threatEvent = await collection.findOne({
      topic: 'chronos.events.defense.threat.detected',
      'payload.details.threat_id': threat_id,
    });

    if (!threatEvent) {
      return res.status(404).json({ success: false, error: 'Threat not found' });
    }

    // Create defense.threat.resolved event (marking as false positive/dismissed)
    const threatResolvedEvent = {
      event_id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      source: 'defense-threat-resolver',
      severity: 'info',
      sector_id: threatEvent.payload?.sector_id || 'unknown',
      summary: `Threat ${threat_id} dismissed`,
      correlation_id: threat_id,
      details: {
        threat_id: threat_id,
        resolution_status: 'false_positive',
        resolution_notes: reason || 'Threat dismissed by operator',
        resolved_by: 'operator',
        resolved_at: new Date().toISOString(),
      },
    };

    // Publish event to NATS via Python helper
    const scriptPath = path.join(process.cwd(), 'dashboard', 'scripts', 'publish_fix_event.py');
    const topic = 'chronos.events.defense.threat.resolved';
    const payload = Buffer.from(JSON.stringify(threatResolvedEvent)).toString('base64');

    try {
      await execAsync(`python "${scriptPath}" "${topic}" "${payload}"`, {
        cwd: process.cwd(),
        timeout: 10000,
      });
    } catch (natsError: any) {
      console.warn('Failed to publish to NATS, saving to MongoDB only:', natsError);
      // Continue to save to MongoDB even if NATS fails
    }

    // Save event to MongoDB
    await collection.insertOne({
      topic: topic,
      payload: threatResolvedEvent,
      timestamp: new Date(),
    });

    res.status(200).json({
      success: true,
      message: `Threat ${threat_id} dismissed successfully`,
    });
  } catch (error: any) {
    console.error('Error dismissing threat:', error);
    res.status(500).json({ success: false, error: error.message || 'Failed to dismiss threat' });
  }
}

