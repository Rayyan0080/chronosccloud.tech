import type { NextApiRequest, NextApiResponse } from 'next';
import clientPromise from '../../../../lib/mongodb';

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
  error?: string;
};

type ResponseData = {
  verification: VerificationStatus | null;
  error?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { fix_id } = req.query;
    if (!fix_id || typeof fix_id !== 'string') {
      return res.status(400).json({ error: 'fix_id is required' });
    }

    const client = await clientPromise;
    const db = client.db(process.env.MONGO_DB || 'chronos');
    const collection = db.collection('fix_verifications');

    // Find verification status
    const verification = await collection.findOne({ fix_id });

    if (!verification) {
      return res.status(200).json({
        verification: {
          fix_id,
          status: 'not_started',
        },
      });
    }

    // Format verification status
    const verificationStatus: VerificationStatus = {
      fix_id: verification.fix_id,
      status: verification.status || 'not_started',
      started_at: verification.started_at instanceof Date
        ? verification.started_at.toISOString()
        : verification.started_at,
      completed_at: verification.completed_at instanceof Date
        ? verification.completed_at.toISOString()
        : verification.completed_at,
      passed: verification.passed,
      metrics: verification.metrics,
      timeline: verification.timeline || [],
      error: verification.error,
    };

    res.status(200).json({ verification: verificationStatus });
  } catch (error: any) {
    console.error('Error fetching verification status:', error);
    res.status(500).json({ error: error.message || 'Failed to fetch verification status' });
  }
}

