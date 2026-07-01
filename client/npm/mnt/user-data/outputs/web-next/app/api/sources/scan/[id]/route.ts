import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.LOSEME_API_URL || 'http://localhost:8000';
const API_KEY = process.env.LOSEME_API_KEY || '';
const DEVICE_ID = process.env.LOSEME_DEVICE_ID || '';
// Sidecar that still runs the Python ingest CLI logic (queue_filesystem_logic /
// queue_thunderbird_logic). Keeping ingestion in Python avoids reimplementing
// extractor/chunker wiring in Node — see migration plan §4.
const INGEST_SIDECAR_URL = process.env.LOSEME_INGEST_SIDECAR_URL || 'http://localhost:3001';

function headers(): HeadersInit {
  const h: HeadersInit = { 'Content-Type': 'application/json' };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return h;
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const forceReprocess = req.nextUrl.searchParams.get('force_reprocess') === 'true';

  const sourcesRes = await fetch(`${API_URL}/sources/get_all_sources`, { headers: headers() });
  if (!sourcesRes.ok) {
    return NextResponse.json({ detail: 'Failed to load sources' }, { status: 502 });
  }
  const { sources } = await sourcesRes.json();
  const source = sources.find((s: { id: string }) => s.id === id);

  if (!source) {
    return NextResponse.json({ detail: 'Source not found' }, { status: 404 });
  }

  if (DEVICE_ID && source.device_id && source.device_id !== DEVICE_ID) {
    return NextResponse.json(
      { detail: 'Cannot scan source that belongs to another device' },
      { status: 403 },
    );
  }

  // Fire-and-forget call into the ingest sidecar; mirrors the old
  // BackgroundTasks.add_task(queue_filesystem_logic / queue_thunderbird_logic).
  fetch(`${INGEST_SIDECAR_URL}/ingest/${source.source_type}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, force_reprocess: forceReprocess }),
  }).catch(() => {
    // Sidecar unreachable — surfaced via run status polling rather than blocking this response.
  });

  return NextResponse.json({ status: 'scanning' });
}
