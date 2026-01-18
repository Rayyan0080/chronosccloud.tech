import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

type TransitStop = {
  stop_id: string;
  name: string;
  lat: number;
  lon: number;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ stops: TransitStop[] } | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { bounds, zoom } = req.query;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const stopsCollection = db.collection('transit_stops');

    // Only show stops when zoomed in (zoom >= 14)
    const zoomLevel = zoom ? parseFloat(zoom as string) : 0;
    if (zoomLevel < 14) {
      return res.status(200).json({ stops: [] });
    }

    // Build query with optional bounds filter
    const query: any = {};
    
    if (bounds) {
      try {
        const boundsObj = JSON.parse(bounds as string);
        if (boundsObj.minLat && boundsObj.maxLat && boundsObj.minLon && boundsObj.maxLon) {
          query.lat = {
            $gte: boundsObj.minLat,
            $lte: boundsObj.maxLat,
          };
          query.lon = {
            $gte: boundsObj.minLon,
            $lte: boundsObj.maxLon,
          };
        }
      } catch (e) {
        // Invalid bounds format, ignore
      }
    }

    // Fetch stops
    const stops = await stopsCollection
      .find(query)
      .limit(1000) // Limit to prevent too many markers
      .toArray();

    const result = stops.map((stop: any) => ({
      stop_id: stop.stop_id,
      name: stop.name,
      lat: stop.lat,
      lon: stop.lon,
    }));

    console.log(`[Transit Stops API] Found ${result.length} stops (zoom: ${zoomLevel})`);

    res.status(200).json({ stops: result });
  } catch (error: any) {
    console.error('Error fetching transit stops:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch transit stops' });
  }
}

