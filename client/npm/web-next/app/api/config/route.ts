import { NextResponse } from 'next/server';
import os from 'node:os';

export async function GET() {
  return NextResponse.json({
    api_url: process.env.LOSEME_API_URL || 'http://localhost:8000',
    api_key: process.env.LOSEME_API_KEY || '',
    client_url: process.env.LOSEME_CLIENT_URL || 'http://localhost:3000',
    ingest_sidecar_url: process.env.LOSEME_INGEST_SIDECAR_URL || 'http://ingest-sidecar:3000',
    device_id: process.env.LOSEME_DEVICE_ID || os.hostname(),
  });
}
