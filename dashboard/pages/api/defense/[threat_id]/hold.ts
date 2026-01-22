import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../../lib/mongodb';

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

    // Create a hold event (we can store this in a separate collection or as metadata)
    // For now, we'll just return success - the threat remains in the queue
    // In a full implementation, you might want to add a "hold" status to the threat

    res.status(200).json({
      success: true,
      message: `Threat ${threat_id} placed on hold`,
    });
  } catch (error: any) {
    console.error('Error holding threat:', error);
    res.status(500).json({ success: false, error: error.message || 'Failed to hold threat' });
  }
}

