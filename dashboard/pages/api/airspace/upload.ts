import type { NextApiRequest, NextApiResponse } from 'next';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import os from 'os';

const execAsync = promisify(exec);

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{ plan_id?: string; error?: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get JSON data from request body
    const planData = req.body;

    if (!planData || typeof planData !== 'object') {
      return res.status(400).json({ error: 'Invalid JSON data' });
    }

    // Validate basic structure
    if (!planData.flights || !Array.isArray(planData.flights)) {
      return res.status(400).json({ error: 'Invalid flight plan format: missing flights array' });
    }

    // Get project root (assuming this is in dashboard/pages/api/airspace/)
    // process.cwd() in Next.js API routes is the project root (dashboard/)
    // So we need to go up one level to get to Chronos-Cloud root
    const projectRoot = path.resolve(process.cwd(), '..');
    const ingestorPath = path.join(projectRoot, 'agents', 'flight_plan_ingestor.py');

    // Check if ingestor exists
    if (!fs.existsSync(ingestorPath)) {
      console.error(`Ingestor not found at: ${ingestorPath}`);
      return res.status(500).json({ error: `Ingestor script not found at ${ingestorPath}` });
    }

    // Create temp file
    const tempDir = os.tmpdir();
    const tempFilePath = path.join(tempDir, `plan_${Date.now()}_${Math.random().toString(36).substring(7)}.json`);

    try {
      // Write JSON to temp file
      fs.writeFileSync(tempFilePath, JSON.stringify(planData, null, 2));

      // Determine Python command (try python3 first, fallback to python)
      const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
      
      // Execute flight_plan_ingestor.py
      // Use absolute paths and handle Windows path separators
      const normalizedIngestorPath = ingestorPath.replace(/\\/g, '/');
      const normalizedTempPath = tempFilePath.replace(/\\/g, '/');
      
      const command = process.platform === 'win32' 
        ? `python "${ingestorPath}" "${tempFilePath}"`
        : `${pythonCmd} "${normalizedIngestorPath}" "${normalizedTempPath}"`;

      console.log(`Executing: ${command}`);
      console.log(`Working directory: ${projectRoot}`);
      
      const { stdout, stderr } = await execAsync(
        command,
        { 
          cwd: projectRoot, 
          maxBuffer: 10 * 1024 * 1024,
          env: { ...process.env, PYTHONUNBUFFERED: '1' }
        }
      );
      
      if (stderr) {
        console.warn('Ingestor stderr:', stderr);
      }
      console.log('Ingestor stdout:', stdout);

      // Extract plan_id from output if possible, or generate one
      const planIdMatch = stdout.match(/PLAN-[\w-]+/);
      const planId = planIdMatch ? planIdMatch[0] : `PLAN-${Date.now()}`;

      // Clean up temp file
      try {
        if (fs.existsSync(tempFilePath)) {
          fs.unlinkSync(tempFilePath);
        }
      } catch (e) {
        // Ignore cleanup errors
      }

      return res.status(200).json({ plan_id: planId });
    } catch (execError: any) {
      // Clean up temp file
      try {
        if (fs.existsSync(tempFilePath)) {
          fs.unlinkSync(tempFilePath);
        }
      } catch (e) {
        // Ignore cleanup errors
      }

      console.error('Ingestor error:', execError);
      const errorMessage = execError.message || 'Unknown error';
      const errorDetails = execError.stderr ? `\nStderr: ${execError.stderr}` : '';
      const errorOutput = execError.stdout ? `\nStdout: ${execError.stdout}` : '';
      return res.status(500).json({ 
        error: `Ingestor error: ${errorMessage}${errorDetails}${errorOutput}` 
      });
    }
  } catch (error: any) {
    console.error('Upload error:', error);
    return res.status(500).json({ error: error.message || 'Upload failed' });
  }
}

