import { NextRequest, NextResponse } from 'next/server';
import fs from 'node:fs';
import { hostPathToContainer } from '@/lib/docker-path-translation';

const API_URL = process.env.LOSEME_API_URL || 'http://localhost:8000';
const API_KEY = process.env.LOSEME_API_KEY || '';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ partId: string }> }) {
  const { partId } = await params;
  const headers: HeadersInit = {};
  if (API_KEY) headers['X-API-Key'] = API_KEY;

  const metaRes = await fetch(`${API_URL}/documents/${partId}`, { headers });
  if (metaRes.status === 404) {
    return NextResponse.json({ detail: 'Document not found' }, { status: 404 });
  }
  if (!metaRes.ok) {
    return NextResponse.json({ detail: `Upstream error ${metaRes.status}` }, { status: 502 });
  }
  const body = await metaRes.json();
  const docPart = body.document_part ?? body;
  const sourcePath: string = docPart.source_path;

  let containerPath: string;
  try {
    containerPath = hostPathToContainer(sourcePath);
  } catch (e) {
    return NextResponse.json({ detail: (e as Error).message }, { status: 400 });
  }

  if (!fs.existsSync(containerPath)) {
    return NextResponse.json(
      { detail: `File not found on this device: ${sourcePath}` },
      { status: 404 },
    );
  }

  const fileBuffer = fs.readFileSync(containerPath);
  const contentType = containerPath.toLowerCase().endsWith('.pdf')
    ? 'application/pdf'
    : 'application/octet-stream';

  return new NextResponse(fileBuffer, {
    headers: { 'Content-Type': contentType },
  });
}
