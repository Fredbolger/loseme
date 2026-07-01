import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    api_url: process.env.LOSEME_API_URL || 'http://localhost:8000',
    api_key: process.env.LOSEME_API_KEY || '',
    client_url: process.env.LOSEME_CLIENT_URL || 'http://localhost:3000',
  });
}
