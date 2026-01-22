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

    // Fetch the threat.assessed event to get assessment data
    const assessedEvent = await collection.findOne({
      topic: 'chronos.events.defense.threat.assessed',
      'payload.details.threat_id': threat_id,
    });

    if (!assessedEvent) {
      return res.status(404).json({ success: false, error: 'Threat assessment not found. Threat must be assessed before approval.' });
    }

    const assessmentData = assessedEvent.payload?.details?._assessment_data;
    if (!assessmentData || !assessmentData.protective_actions || assessmentData.protective_actions.length === 0) {
      return res.status(400).json({ success: false, error: 'No protective actions available to approve' });
    }

    // Get recommended posture from assessment
    const recommendedPosture = assessmentData.recommended_posture || 'heightened_alert';

    // Create defense.action.approved event
    const actionApprovedEvent = {
      event_id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      source: 'defense-action-approver',
      severity: 'info',
      sector_id: threatEvent.payload?.sector_id || 'unknown',
      summary: `Defense action approved for threat ${threat_id}`,
      correlation_id: threat_id,
      details: {
        action_id: `ACTION-${Date.now()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`,
        threat_id: threat_id,
        approved_by: 'operator',
        approved_at: new Date().toISOString(),
        approval_notes: 'Protective actions approved for deployment',
        protective_actions: assessmentData.protective_actions,
      },
    };

    // Create defense.posture.changed event
    const postureChangedEvent = {
      event_id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      source: 'defense-posture-manager',
      severity: 'warning',
      sector_id: threatEvent.payload?.sector_id || 'unknown',
      summary: `Defense posture changed to ${recommendedPosture}`,
      correlation_id: threat_id,
      details: {
        posture_id: `POSTURE-${Date.now()}`,
        previous_posture: 'normal', // TODO: Get actual current posture
        new_posture: recommendedPosture,
        change_reason: `Threat ${threat_id} approved for protective actions`,
        changed_by: 'operator',
        changed_at: new Date().toISOString(),
      },
    };

    // Publish events to NATS via Python helper
    const scriptPath = path.join(process.cwd(), 'dashboard', 'scripts', 'publish_fix_event.py');
    const topic1 = 'chronos.events.defense.action.approved';
    const topic2 = 'chronos.events.defense.posture.changed';
    
    const payload1 = Buffer.from(JSON.stringify(actionApprovedEvent)).toString('base64');
    const payload2 = Buffer.from(JSON.stringify(postureChangedEvent)).toString('base64');

    try {
      // Publish action.approved
      await execAsync(`python "${scriptPath}" "${topic1}" "${payload1}"`, {
        cwd: process.cwd(),
        timeout: 10000,
      });

      // Publish posture.changed
      await execAsync(`python "${scriptPath}" "${topic2}" "${payload2}"`, {
        cwd: process.cwd(),
        timeout: 10000,
      });
    } catch (natsError: any) {
      console.warn('Failed to publish to NATS, saving to MongoDB only:', natsError);
      // Continue to save to MongoDB even if NATS fails
    }

    // Save events to MongoDB
    await collection.insertOne({
      topic: topic1,
      payload: actionApprovedEvent,
      timestamp: new Date(),
    });

    await collection.insertOne({
      topic: topic2,
      payload: postureChangedEvent,
      timestamp: new Date(),
    });

    res.status(200).json({
      success: true,
      message: `Defense action approved and posture changed to ${recommendedPosture}`,
    });
  } catch (error: any) {
    console.error('Error approving defense action:', error);
    res.status(500).json({ success: false, error: error.message || 'Failed to approve defense action' });
  }
}

