import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';
import { transitDisruptionRiskToGeo, enhanceGeoIncident, enhanceGeoRiskArea } from '../../lib/eventToGeo';

// Helper function to infer source from event payload
function inferSource(payload: any): string {
  const source = payload?.source;
  if (source) {
    // Map known sources
    if (source.includes('transit') || source.includes('oc_transpo') || source.includes('gtfs')) {
      return 'transit';
    }
    if (source.includes('traffic') || source.includes('ottawa_traffic')) {
      return 'traffic';
    }
    if (source.includes('airspace') || source.includes('opensky') || source.includes('flight')) {
      return 'airspace';
    }
    if (source.includes('power') || source.includes('crisis')) {
      return 'power';
    }
    return source;
  }
  
  // Infer from details
  const incidentType = payload?.details?.incident_type || '';
  const riskType = payload?.details?.risk_type || '';
  
  if (incidentType.includes('airspace') || riskType.includes('airspace') || incidentType.includes('aircraft')) {
    return 'airspace';
  }
  if (incidentType.includes('transit') || riskType.includes('transit') || incidentType.includes('stalled_vehicle')) {
    return 'transit';
  }
  if (incidentType.includes('traffic') || riskType.includes('traffic') || incidentType.includes('construction') || incidentType.includes('collision')) {
    return 'traffic';
  }
  if (incidentType.includes('power') || riskType.includes('power')) {
    return 'power';
  }
  
  return 'unknown';
}

type GeoEvent = {
  _id: string;
  topic: string;
  payload: any;
  timestamp: Date;
  logged_at: Date;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ incidents: any[]; riskAreas: any[] } | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { timeRange = '24h', severity, source = 'all' } = req.query; // Default: last 24h, all sources (changed from 1h to show more data)

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Calculate time threshold based on timeRange
    const now = new Date();
    let timeThreshold: Date;
    switch (timeRange) {
      case '15m':
        timeThreshold = new Date(now.getTime() - 15 * 60 * 1000);
        break;
      case '1h':
        timeThreshold = new Date(now.getTime() - 60 * 60 * 1000);
        break;
      case '6h':
        timeThreshold = new Date(now.getTime() - 6 * 60 * 60 * 1000);
        break;
      case '24h':
        timeThreshold = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      default:
        timeThreshold = new Date(now.getTime() - 60 * 60 * 1000); // Default: 1h
    }

    // Build query for geo events
    // When source is 'all', include all geo events
    // When source is specific, only include relevant topics
    const topics: string[] = [];
    
    if (source === 'all') {
      // Include all geo event types when showing all sources
      topics.push('chronos.events.geo.incident');
      topics.push('chronos.events.geo.risk_area');
      topics.push('chronos.events.transit.disruption.risk');
      topics.push('chronos.events.transit.hotspot');
      topics.push('chronos.events.transit.vehicle.position');
      topics.push('chronos.events.airspace.aircraft.position');
      topics.push('chronos.events.airspace.conflict.detected');
      topics.push('chronos.events.airspace.hotspot.detected');
      topics.push('chronos.events.ottawa_traffic.data');
      topics.push('chronos.events.ontario511.data');
      topics.push('chronos.events.power.failure');
    } else if (source === 'transit') {
      // Transit-specific topics
      topics.push('chronos.events.transit.disruption.risk');
      topics.push('chronos.events.transit.hotspot');
      topics.push('chronos.events.transit.vehicle.position');
      // Also include geo events that might be transit-related (will be filtered by source)
      topics.push('chronos.events.geo.incident');
      topics.push('chronos.events.geo.risk_area');
    } else if (source === 'airspace') {
      // Airspace-specific topics - focus on aircraft positions and conflicts
      topics.push('chronos.events.airspace.aircraft.position');
      topics.push('chronos.events.airspace.conflict.detected');
      topics.push('chronos.events.airspace.hotspot.detected');
      // Also include geo events that might be airspace-related (will be filtered by source)
      topics.push('chronos.events.geo.incident');
      topics.push('chronos.events.geo.risk_area');
    } else if (source === 'traffic') {
      topics.push('chronos.events.ottawa_traffic.data');
      topics.push('chronos.events.ontario511.data');
      topics.push('chronos.events.geo.incident');
      topics.push('chronos.events.geo.risk_area');
    } else if (source === 'power') {
      topics.push('chronos.events.power.failure');
      topics.push('chronos.events.geo.incident');
      topics.push('chronos.events.geo.risk_area');
    }
    
    // Build query - for now, don't filter by time to ensure we get results
    // TODO: Re-enable time filtering once we verify timestamp format
    const query: any = {
      topic: { $in: topics },
    };
    
    // Temporarily disable time filtering to debug
    // if (timeRange !== 'all') {
    //   query.timestamp = { $gte: timeThreshold };
    // }

    // Add severity filter if provided
    // Map user-friendly severity names to schema values
    const severityParam = severity as string;
    if (severityParam && severityParam !== 'all' && severityParam !== '') {
      const severityMap: Record<string, string> = {
        'low': 'info',
        'med': 'warning',
        'medium': 'warning',
        'moderate': 'moderate',
        'high': 'critical', // Map high to critical for display
        'critical': 'critical',
        'error': 'moderate', // Backward compatibility
      };
      const mappedSeverity = severityMap[severityParam.toLowerCase()] || severityParam;
      query['payload.severity'] = mappedSeverity;
    }

    // Fetch geo events
    const events = await collection
      .find(query)
      .sort({ timestamp: -1 })
      .limit(1000)
      .toArray();

    console.log(`[geo-events API] Request params:`, { timeRange, severity, source });
    console.log(`[geo-events API] Query:`, JSON.stringify(query, null, 2));
    console.log(`[geo-events API] Topics being queried:`, topics);
    console.log(`[geo-events API] Time threshold:`, timeThreshold ? timeThreshold.toISOString() : 'None (all time)');
    console.log(`[geo-events API] Found ${events.length} events matching query`);
    
    // Count events by topic
    const eventsByTopic: Record<string, number> = {};
    events.forEach((e: any) => {
      eventsByTopic[e.topic] = (eventsByTopic[e.topic] || 0) + 1;
    });
    console.log(`[geo-events API] Events by topic:`, eventsByTopic);
    
    if (events.length > 0) {
      console.log(`[geo-events API] Sample event topics:`, events.slice(0, 5).map((e: any) => e.topic));
      // Count aircraft position events specifically
      const aircraftEvents = events.filter((e: any) => e.topic === 'chronos.events.airspace.aircraft.position');
      console.log(`[geo-events API] Aircraft position events found: ${aircraftEvents.length}`);
      if (aircraftEvents.length > 0) {
        const sample = aircraftEvents[0];
        console.log(`[geo-events API] Sample aircraft event:`, {
          topic: sample.topic,
          hasDetails: !!sample.payload?.details,
          hasLat: !!sample.payload?.details?.latitude,
          hasLon: !!sample.payload?.details?.longitude,
          lat: sample.payload?.details?.latitude,
          lon: sample.payload?.details?.longitude,
          source: sample.payload?.source,
        });
      }
    } else {
      // Check if there are ANY events in the database
      const totalEvents = await collection.countDocuments({});
      const recentEvents = await collection.countDocuments({ timestamp: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) } });
      const aircraftCount = await collection.countDocuments({ topic: 'chronos.events.airspace.aircraft.position' });
      const aircraftCountRecent = await collection.countDocuments({ topic: 'chronos.events.airspace.aircraft.position', timestamp: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) } });
      console.log(`[geo-events API] Total events in DB: ${totalEvents}, Recent (24h): ${recentEvents}`);
      console.log(`[geo-events API] Aircraft events - Total: ${aircraftCount}, Recent (24h): ${aircraftCountRecent}`);
      if (totalEvents > 0) {
        const sampleTopics = await collection.distinct('topic');
        console.log(`[geo-events API] Available topics in DB:`, sampleTopics.slice(0, 20));
      }
    }

    // Process events: separate geo events and convert transit risks
    const incidents: any[] = [];
    const riskAreas: any[] = [];
    
    for (const e of events) {
      // Handle existing geo.incident events
      if (e.topic === 'chronos.events.geo.incident') {
        const geometry = e.payload?.details?.geometry || e.payload?.geometry || {};
        // Only include if geometry has valid coordinates
        const coords = geometry.coordinates;
        if (coords && Array.isArray(coords) && coords.length >= 2 && 
            typeof coords[0] === 'number' && typeof coords[1] === 'number') {
          const inferredSource = e.payload?.source || inferSource(e.payload);
          const incident = {
            event_id: e.payload?.event_id || e._id.toString(),
            id: e.payload?.details?.id || e.payload?.event_id || e._id.toString(),
            timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
            severity: e.payload?.severity || 'info',
            summary: e.payload?.summary || '',
            geometry: geometry,
            style: e.payload?.details?.style || { 
              color: inferredSource === 'traffic' ? '#10B981' : 'red', // Green for traffic
              opacity: 0.9, 
              outline: true 
            },
            incident_type: e.payload?.details?.incident_type,
            description: e.payload?.details?.description,
            status: e.payload?.details?.status,
            source: inferredSource,
            // Include full details for bearing, vehicle_id, etc. if available
            details: {
              ...e.payload?.details,
              ...(e.payload?.details?.bearing && { bearing: e.payload.details.bearing }),
              ...(e.payload?.details?.vehicle_id && { vehicle_id: e.payload.details.vehicle_id }),
            },
          };
          
          // Apply source filter
          // For airspace filter, also check if incident_type indicates airspace
          const isAirspaceIncident = inferredSource === 'airspace' || 
                                     inferredSource === 'trajectory-insight-agent' ||
                                     e.payload?.details?.incident_type === 'airspace_conflict' ||
                                     e.payload?.details?.incident_type === 'aircraft_position';
          
          if (source === 'all' || incident.source === source || (source === 'airspace' && isAirspaceIncident)) {
            incidents.push(incident);
          }
        }
      }
      
      // Handle existing geo.risk_area events
      if (e.topic === 'chronos.events.geo.risk_area') {
        const geometry = e.payload?.details?.geometry || e.payload?.geometry || {};
        // Only include if geometry is valid (Circle or Polygon)
        const isValid = (geometry.type === 'Circle' && geometry.coordinates && geometry.coordinates.length >= 2) ||
                       (geometry.type === 'Polygon' && geometry.coordinates && Array.isArray(geometry.coordinates));
        
        if (isValid) {
          const inferredSource = e.payload?.source || inferSource(e.payload);
          const riskArea = {
            event_id: e.payload?.event_id || e._id.toString(),
            id: e.payload?.details?.id || e.payload?.event_id || e._id.toString(),
            timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
            severity: e.payload?.severity || 'info',
            summary: e.payload?.summary || '',
            geometry: geometry,
            style: e.payload?.details?.style || { color: 'red', opacity: 0.5, outline: true },
            risk_level: e.payload?.details?.risk_level,
            risk_type: e.payload?.details?.risk_type,
            description: e.payload?.details?.description,
            source: inferredSource,
          };
          
          // Apply source filter
          // For airspace filter, also check if risk_type indicates airspace
          const isAirspaceRiskArea = inferredSource === 'airspace' || 
                                     inferredSource === 'trajectory-insight-agent' ||
                                     e.payload?.details?.risk_type === 'airspace_congestion';
          
          if (source === 'all' || riskArea.source === source || (source === 'airspace' && isAirspaceRiskArea)) {
            riskAreas.push(riskArea);
          }
        }
      }
      
      // Convert transit.disruption.risk events to geo events
      if (e.topic === 'chronos.events.transit.disruption.risk') {
        const geoEvent = transitDisruptionRiskToGeo(e.payload);
        
        if (geoEvent) {
          if ('incident_type' in geoEvent) {
            // It's a geo.incident
            if (source === 'all' || source === 'transit') {
              incidents.push(geoEvent);
            }
          } else {
            // It's a geo.risk_area
            if (source === 'all' || source === 'transit') {
              riskAreas.push(geoEvent);
            }
          }
        }
      }
      
      
      // Convert transit.vehicle.position to geo.incident (Point)
      if (e.topic === 'chronos.events.transit.vehicle.position') {
        const details = e.payload?.details || {};
        // Vehicle position events have latitude/longitude directly in details
        const lat = details.latitude || details.lat;
        const lon = details.longitude || details.lon;
        const bearing = details.bearing || null;
        const vehicleId = details.vehicle_id;
        const routeId = details.route_id;
        
        if (lat !== undefined && lon !== undefined && !isNaN(lat) && !isNaN(lon)) {
          if (source === 'all' || source === 'transit') {
            incidents.push({
              event_id: e.payload?.event_id || e._id.toString(),
              id: vehicleId || e._id.toString(),
              timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
              severity: e.payload?.severity || 'info',
              summary: e.payload?.summary || `Transit vehicle ${vehicleId || 'unknown'}`,
              geometry: { type: 'Point', coordinates: [lon, lat] },
              style: { color: '#3B82F6', opacity: 0.9, outline: true }, // Blue for transit vehicles
              source: 'transit',
              incident_type: 'vehicle_position',
              // Include full details for bearing, route_id, etc.
              details: {
                ...details,
                vehicle_id: vehicleId,
                route_id: routeId,
                bearing: bearing,
              },
            });
          }
        }
      }
      
      // Convert airspace.aircraft.position to geo.incident (Point)
      if (e.topic === 'chronos.events.airspace.aircraft.position') {
        const details = e.payload?.details || {};
        // Aircraft position events have latitude/longitude directly in details, not in location object
        const lat = details.latitude || details.lat;
        const lon = details.longitude || details.lon;
        
        // Debug logging for aircraft events
        if (events.length > 0 && events.indexOf(e) < 3) {
          console.log(`[geo-events API] Processing aircraft event ${events.indexOf(e)}:`, {
            hasDetails: !!details,
            hasLat: lat !== undefined,
            hasLon: lon !== undefined,
            lat,
            lon,
            isValid: lat !== undefined && lon !== undefined && !isNaN(lat) && !isNaN(lon),
            sourceFilter: source,
            willInclude: (source === 'all' || source === 'airspace') && lat !== undefined && lon !== undefined && !isNaN(lat) && !isNaN(lon),
          });
        }
        
        if (lat !== undefined && lon !== undefined && !isNaN(lat) && !isNaN(lon)) {
          if (source === 'all' || source === 'airspace') {
            const incident = {
              event_id: e.payload?.event_id || e._id.toString(),
              id: details.icao24 || e._id.toString(),
              timestamp: e.timestamp instanceof Date ? e.timestamp.toISOString() : e.timestamp,
              severity: e.payload?.severity || 'info',
              summary: e.payload?.summary || `Aircraft ${details.callsign || details.icao24 || 'unknown'}`,
              geometry: { type: 'Point', coordinates: [lon, lat] },
              style: { color: '#00FF00', opacity: 0.8, outline: true },
              source: 'airspace',
              incident_type: 'aircraft_position',
              description: `Aircraft ${details.callsign || details.icao24 || 'unknown'} at ${lat.toFixed(4)}, ${lon.toFixed(4)}${details.altitude ? ` (${Math.round(details.altitude)}m)` : ''}`,
              details: details, // Include full details for altitude, heading, etc.
            };
            incidents.push(incident);
          } else {
            console.log(`[geo-events API] Skipping aircraft event due to source filter: source=${source}, event source=${e.payload?.source}`);
          }
        } else {
          if (events.length > 0 && events.indexOf(e) < 3) {
            console.warn(`[geo-events API] Skipping aircraft event with invalid coordinates:`, {
              lat,
              lon,
              hasLat: lat !== undefined,
              hasLon: lon !== undefined,
            });
          }
        }
      }
    }

    console.log(`[Geo Events API] Processing complete:`);
    console.log(`  - Total events fetched: ${events.length}`);
    console.log(`  - Incidents created: ${incidents.length}`);
    console.log(`  - Risk areas created: ${riskAreas.length}`);
    console.log(`  - Filters: timeRange=${timeRange}, severity=${severity || 'all'}, source=${source}`);
    
    // Count incidents by source
    const incidentsBySource: Record<string, number> = {};
    incidents.forEach((inc: any) => {
      incidentsBySource[inc.source || 'unknown'] = (incidentsBySource[inc.source || 'unknown'] || 0) + 1;
    });
    console.log(`  - Incidents by source:`, incidentsBySource);
    
    if (incidents.length > 0) {
      console.log(`  - Sample incident:`, {
        id: incidents[0].id,
        source: incidents[0].source,
        geometry: incidents[0].geometry,
        hasCoords: !!incidents[0].geometry?.coordinates,
      });
    }

    res.status(200).json({ incidents, riskAreas });
  } catch (error: any) {
    console.error('Error fetching geo events:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch geo events' });
  }
}

