import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

type SectorStatus = {
  sector_id: string;
  latest_event: any;
  status: 'normal' | 'warning' | 'error' | 'critical';
  last_updated: string;
};

type ResponseData = {
  sectors: SectorStatus[];
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    const sectors = ['sector-1', 'sector-2', 'sector-3'];
    const sectorStatuses: SectorStatus[] = [];

    for (const sectorId of sectors) {
      // Find latest event for this sector
      const latestEvent = await collection
        .find({
          'payload.sector_id': sectorId,
        })
        .sort({ timestamp: -1 })
        .limit(1)
        .toArray();

      if (latestEvent.length > 0) {
        const event = latestEvent[0];
        const severity = event.payload?.severity || 'info';
        
        let status: 'normal' | 'warning' | 'error' | 'critical' = 'normal';
        if (severity === 'critical') status = 'critical';
        else if (severity === 'moderate' || severity === 'error') status = 'error';  // 'error' for backward compatibility
        else if (severity === 'warning') status = 'warning';

        sectorStatuses.push({
          sector_id: sectorId,
          latest_event: event.payload,
          status,
          last_updated: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
        });
      } else {
        // No events found, default to normal
        sectorStatuses.push({
          sector_id: sectorId,
          latest_event: null,
          status: 'normal',
          last_updated: new Date().toISOString(),
        });
      }
    }

    res.status(200).json({ sectors: sectorStatuses });
  } catch (error: any) {
    console.error('Error fetching sector statuses:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch sector statuses' });
  }
}

