import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../lib/mongodb';

type FixEvent = {
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
      fix_id: string;
      correlation_id: string;
      source: string;
      title: string;
      summary: string;
      actions: Array<{
        type: string;
        target: any;
        params: any;
        verification: {
          metric_name: string;
          threshold: number;
          window_seconds: number;
        };
      }>;
      risk_level: string;
      expected_impact: {
        delay_reduction?: number;
        risk_score_delta?: number;
        area_affected?: string;
      };
      created_at: string;
      proposed_by: string;
      requires_human_approval: boolean;
    };
  };
  timestamp: string;
};

type VerificationStatus = {
  fix_id: string;
  status: 'in_progress' | 'verified' | 'failed' | 'not_started';
  started_at?: string;
  completed_at?: string;
  passed?: boolean;
  metrics?: {
    total_actions: number;
    passed: number;
    failed: number;
    skipped: number;
  };
  timeline?: Array<{
    timestamp: string;
    status: string;
    message: string;
    data?: any;
  }>;
};

type FixEventWithVerification = FixEvent & {
  verification?: VerificationStatus;
};

type ResponseData = {
  fixes: FixEventWithVerification[];
  count: number;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const limit = parseInt(req.query.limit as string) || 100;

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('events');

    // Fetch fix.review_required events that haven't been approved or rejected
    const reviewRequiredEvents = await collection
      .find({ 
        topic: 'chronos.events.fix.review_required',
      })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();

    // Get all fix IDs that have been approved or rejected
    const processedFixIds = await collection
      .find({
        topic: { $in: ['chronos.events.fix.approved', 'chronos.events.fix.rejected'] },
      })
      .toArray();
    
    const processedFixIdSet = new Set(
      processedFixIds.map((e: any) => e.payload?.details?.fix_id).filter(Boolean)
    );

    // Filter out fixes that have already been processed
    const pendingFixes = reviewRequiredEvents.filter((event: any) => {
      const fixId = event.payload?.details?.fix_id;
      return fixId && !processedFixIdSet.has(fixId);
    });

    // Get verification statuses for all fixes
    const verificationCollection = db.collection('fix_verifications');
    const fixIds = pendingFixes.map((e: any) => e.payload?.details?.fix_id).filter(Boolean);
    const verifications = await verificationCollection
      .find({ fix_id: { $in: fixIds } })
      .toArray();
    const verificationMap = new Map(
      verifications.map((v: any) => [
        v.fix_id,
        {
          fix_id: v.fix_id,
          status: v.status || 'not_started',
          started_at: v.started_at instanceof Date ? v.started_at.toISOString() : v.started_at,
          completed_at: v.completed_at instanceof Date ? v.completed_at.toISOString() : v.completed_at,
          passed: v.passed,
          metrics: v.metrics,
          timeline: v.timeline || [],
        },
      ])
    );

    // Convert to response format with verification status
    const formattedFixes: FixEventWithVerification[] = pendingFixes.map((event: any) => {
      const fixId = event.payload?.details?.fix_id;
      const verification = fixId ? verificationMap.get(fixId) : undefined;
      
      return {
        _id: event._id.toString(),
        topic: event.topic,
        payload: event.payload,
        timestamp: event.timestamp instanceof Date ? event.timestamp.toISOString() : event.timestamp,
        verification,
      };
    });

    res.status(200).json({
      fixes: formattedFixes,
      count: formattedFixes.length,
    });
  } catch (error: any) {
    console.error('Error fetching fix review events:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch fix review events' });
  }
}

