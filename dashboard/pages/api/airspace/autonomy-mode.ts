import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ autonomy_mode: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ autonomy_mode: 'RULES' });
  }

  try {
    // Get autonomy mode from environment variable
    // This should match the AUTONOMY_MODE set when running trajectory_insight_agent
    const autonomyMode = process.env.AUTONOMY_MODE || 'RULES';

    res.status(200).json({ autonomy_mode: autonomyMode });
  } catch (error: any) {
    // Default to RULES on error
    res.status(200).json({ autonomy_mode: 'RULES' });
  }
}

