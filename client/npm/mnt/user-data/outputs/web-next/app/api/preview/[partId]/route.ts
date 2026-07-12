import { NextRequest, NextResponse } from 'next/server';
import fs from 'node:fs';
import path from 'node:path';
import { simpleParser } from 'mailparser';
import { hostPathToContainer } from '@/lib/docker-path-translation';

const API_URL = process.env.LOSEME_API_URL || 'http://localhost:8000';
const API_KEY = process.env.LOSEME_API_KEY || '';

const SUFFIX_TO_LANGUAGE: Record<string, string> = {
  '.md': 'markdown',
  '.rst': 'restructuredtext',
  '.txt': 'plaintext',
  '.py': 'python',
  '.js': 'javascript',
  '.ts': 'typescript',
  '.css': 'css',
  '.html': 'html',
};

async function getPartMeta(partId: string) {
  const headers: HeadersInit = {};
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  const res = await fetch(`${API_URL}/documents/${partId}`, { headers });
  if (!res.ok) throw new Error(`Upstream ${res.status}`);
  const body = await res.json();
  return body.document_part ?? body;
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ partId: string }> }) {
  const { partId } = await params;
  let meta: { source_type: string; source_path: string };
  try {
    meta = await getPartMeta(partId);
  } catch (e) {
    return NextResponse.json({ detail: (e as Error).message }, { status: 502 });
  }

  // ── Thunderbird (and .eml on filesystem, which mailparser handles too) ──
  if (meta.source_type === 'thunderbird') {
    const parts = meta.source_path.split('::Message-ID:');
    if (parts.length !== 2) {
      return NextResponse.json({ detail: 'Cannot parse thunderbird source_path' }, { status: 400 });
    }
    // NOTE: full mbox scanning needs a Node mbox parser; for a production
    // build wire this to the same mbox-reading routine as the eml branch
    // below via a shared parsing utility. Left as a follow-up task — the
    // EML path below demonstrates the full pattern with mailparser.
    return NextResponse.json(
      { detail: 'Thunderbird preview: implement mbox extraction using a Node mbox reader (see TODO).' },
      { status: 501 },
    );
  }

  // ── Paperless ──
  if (meta.source_type === 'paperless') {
    // Paperless documents need to be fetched from the server's paperless proxy endpoint
    // The source_path format is: paperless:{document_id}:{title}
    const parts = meta.source_path.split(':');
    if (parts.length < 2) {
      return NextResponse.json({ detail: 'Cannot parse paperless source_path' }, { status: 400 });
    }
    
    const paperlessDocumentId = parts[1];
    
    // Get the document metadata to find the connection_id
    let connectionId: string | null = null;
    try {
      const docMeta = await getPartMeta(partId);
      const scopeJson = docMeta.scope_json;
      if (scopeJson) {
        const scope = typeof scopeJson === 'string' ? JSON.parse(scopeJson) : scopeJson;
        connectionId = scope.connection_id;
      }
    } catch (e) {
      return NextResponse.json({ detail: 'Failed to get paperless document metadata' }, { status: 500 });
    }
    
    if (!connectionId) {
      return NextResponse.json({ detail: 'Paperless connection ID not found' }, { status: 404 });
    }
    
    // Return a paperless preview result that the client can use to fetch the document
    return NextResponse.json({
      source_type: 'paperless',
      preview_type: 'paperless_document',
      paperless_document_id: paperlessDocumentId,
      connection_id: connectionId,
      source_path: meta.source_path,
      document_part_id: partId,
    });
  }

  // ── Filesystem ──
  let containerPath: string;
  try {
    containerPath = hostPathToContainer(meta.source_path);
  } catch (e) {
    return NextResponse.json({ detail: (e as Error).message }, { status: 400 });
  }
  if (!fs.existsSync(containerPath)) {
    return NextResponse.json({ detail: `File not found on this device: ${meta.source_path}` }, { status: 404 });
  }

  const suffix = path.extname(containerPath).toLowerCase();

  if (suffix === '.eml') {
    const raw = fs.readFileSync(containerPath);
    const parsed = await simpleParser(raw);
    return NextResponse.json({
      source_type: 'filesystem',
      preview_type: 'email',
      subject: parsed.subject || '',
      from_: parsed.from?.text || '',
      to: Array.isArray(parsed.to) ? parsed.to.map((t) => t.text).join(', ') : parsed.to?.text || '',
      date: parsed.date?.toISOString() || '',
      body_html: typeof parsed.html === 'string' ? parsed.html : undefined,
      body_text: parsed.text,
    });
  }

  if (suffix in SUFFIX_TO_LANGUAGE) {
    return NextResponse.json({
      source_type: 'filesystem',
      preview_type: 'plaintext',
      text: fs.readFileSync(containerPath, 'utf-8'),
      language: SUFFIX_TO_LANGUAGE[suffix],
    });
  }

  return NextResponse.json({ detail: `Preview not supported for ${suffix} files on this client.` }, { status: 400 });
}
