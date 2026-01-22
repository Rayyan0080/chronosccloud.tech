import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../lib/mongodb';

type DefenseThreatEvent = {
  _id: string;
  topic: string;
  payload: {
    event_id: string;
    timestamp: string;
    severity: string;
    sector_id: string;
    summary: string;
    correlation_id: string;
    details: {
      threat_id: string;
      threat_type: string;
      confidence_score: number;
      severity: string;
      affected_area?: any;
      sources: string[];
      summary: string;
      detected_at: string;
      disclaimer: string;
    };
  };
  timestamp: string;
  assessment?: {
    threat_id: string;
    assessment_score?: number;
    risk_level?: string;
    assessment_notes?: string;
    assessed_by?: string;
    assessed_at?: string;
    _assessment_data?: {
      threat_type: string;
      likely_cause: string;
      recommended_posture: string;
      protective_actions: string[];
      escalation_needed: boolean;
    };
  };
  verification?: {
    threat_id: string;
    status: 'not_started' | 'in_progress' | 'resolved' | 'needs_attention';
    started_at?: string;
    completed_at?: string;
    resolved?: boolean;
    indicators?: any;
    escalation_suggestion?: string;
    timeline?: Array<{
      timestamp: string;
      status: string;
      message: string;
      data?: any;
    }>;
  };
};

type ResponseData = {
  threats: DefenseThreatEvent[];
  count: number;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' } as any);
  }

  try {
    const limit = parseInt(req.query.limit as string) || 100;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Fetch defense.threat.detected events
    const threatEvents = await collection
      .find({ 
        topic: 'chronos.events.defense.threat.detected',
      })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();

    // Get all threat IDs that have been resolved or dismissed
    const processedThreatIds = await collection
      .find({
        topic: { $in: ['chronos.events.defense.threat.resolved'] },
      })
      .toArray();
    
    const processedThreatIdSet = new Set(
      processedThreatIds.map((e: any) => e.payload?.details?.threat_id).filter(Boolean)
    );

    // Filter out threats that have been resolved
    const pendingThreats = threatEvents.filter((event: any) => {
      const threatId = event.payload?.details?.threat_id;
      return threatId && !processedThreatIdSet.has(threatId);
    });

    // Get assessment data for all threats
    const assessmentEvents = await collection
      .find({
        topic: 'chronos.events.defense.threat.assessed',
      })
      .toArray();
    
    const assessmentMap = new Map(
      assessmentEvents.map((e: any) => [
        e.payload?.details?.threat_id,
        {
          threat_id: e.payload?.details?.threat_id,
          assessment_score: e.payload?.details?.assessment_score,
          risk_level: e.payload?.details?.risk_level,
          assessment_notes: e.payload?.details?.assessment_notes,
          assessed_by: e.payload?.details?.assessed_by,
          assessed_at: e.payload?.details?.assessed_at,
          _assessment_data: e.payload?.details?._assessment_data,
        },
      ])
    );

    // Get verification statuses for all threats
    const verificationCollection = db.collection('defense_verifications');
    const threatIds = pendingThreats.map((e: any) => e.payload?.details?.threat_id).filter(Boolean);
    const verifications = await verificationCollection
      .find({ threat_id: { $in: threatIds } })
      .toArray();
    const verificationMap = new Map(
      verifications.map((v: any) => [
        v.threat_id,
        {
          threat_id: v.threat_id,
          status: v.status || 'not_started',
          started_at: v.started_at instanceof Date ? v.started_at.toISOString() : v.started_at,
          completed_at: v.completed_at instanceof Date ? v.completed_at.toISOString() : v.completed_at,
          resolved: v.resolved,
          indicators: v.indicators,
          escalation_suggestion: v.escalation_suggestion,
          timeline: v.timeline || [],
        },
      ])
    );

    // Convert to response format with assessment and verification data
    const formattedThreats: DefenseThreatEvent[] = pendingThreats.map((event: any) => {
      const threatId = event.payload?.details?.threat_id;
      const assessment = threatId ? assessmentMap.get(threatId) : undefined;
      const verification = threatId ? verificationMap.get(threatId) : undefined;
      
      return {
        _id: event._id.toString(),
        topic: event.topic,
        payload: event.payload,
        timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
        assessment,
        verification,
      };
    });

    res.status(200).json({
      threats: formattedThreats,
      count: formattedThreats.length,
    });
  } catch (error: any) {
    console.error('Error fetching defense threats:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch defense threats' } as { error: string });
  }
}

