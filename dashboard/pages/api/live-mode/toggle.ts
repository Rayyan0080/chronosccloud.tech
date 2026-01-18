import type { NextApiRequest, NextApiResponse } from 'next';
import { writeFile, readFile } from 'fs/promises';
import { join } from 'path';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ success: boolean; live_mode: 'on' | 'off'; message?: string } | { error: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { live_mode } = req.body;
    
    if (live_mode !== 'on' && live_mode !== 'off') {
      return res.status(400).json({ error: 'Invalid live_mode. Must be "on" or "off"' });
    }

    // Get project root (assuming .env is in project root)
    // In Next.js, we need to go up from .next directory
    const projectRoot = process.cwd();
    const envPath = join(projectRoot, '.env');

    // Read current .env file
    let envContent = '';
    try {
      envContent = await readFile(envPath, 'utf-8');
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        // .env file doesn't exist, create it
        envContent = '';
      } else {
        throw error;
      }
    }

    // Update or add LIVE_MODE line
    const lines = envContent.split('\n');
    let found = false;
    const newLines = lines.map(line => {
      if (line.trim().startsWith('LIVE_MODE=')) {
        found = true;
        return `LIVE_MODE=${live_mode}`;
      }
      return line;
    });

    // If LIVE_MODE wasn't found, add it
    if (!found) {
      newLines.push(`LIVE_MODE=${live_mode}`);
    }

    // Write back to .env file
    await writeFile(envPath, newLines.join('\n'), 'utf-8');

    res.status(200).json({
      success: true,
      live_mode,
      message: `LIVE_MODE set to ${live_mode}. Please restart the live_data runner for changes to take effect.`,
    });
  } catch (error: any) {
    console.error('Error updating LIVE_MODE:', error);
    res.status(500).json({ error: error.message || 'Failed to update LIVE_MODE' });
  }
}

