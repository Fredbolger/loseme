import { NextResponse } from 'next/server';

/**
 * Proxy route for forwarding source scan requests to the ingest sidecar.
 * This maintains the same-origin browser call pattern while delegating the
 * actual filesystem walking/extractor logic to the Python sidecar container.
 * Must forward the force_reprocess query param and preserve the 403 "wrong device" response shape.
 *
 * For paperless sources, forwards to the FastAPI server's paperless endpoint instead.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ sourceId: string }> }
) {
  const { sourceId } = await params;
  const sidecarUrl = process.env.LOSEME_INGEST_SIDECAR_URL || 'http://ingest-sidecar:3000';
  const apiUrl = process.env.LOSEME_API_URL || 'http://localhost:8000';
  const apiKey = process.env.LOSEME_API_KEY || '';

  console.log(`[SERVER] Proxy route hit for sourceId: ${sourceId}`);
  console.log(`[SERVER] Sidecar URL: ${sidecarUrl}`);
  console.log(`[SERVER] API URL: ${apiUrl}`);
  console.log(`[SERVER] API Key present: ${apiKey ? 'yes' : 'no'}`);

  // Extract the query parameters (particularly force_reprocess)
  const url = new URL(request.url);
  const forceReprocess = url.searchParams.get('force_reprocess');
  console.log(`[SERVER] force_reprocess: ${forceReprocess}`);

  // First, fetch the source to check its type
  let sourceType: string | null = null;
  try {
    const sourceRes = await fetch(`${apiUrl}/sources/get_all_sources`, {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
    });
    if (sourceRes.ok) {
      const sourcesData = await sourceRes.json();
      const source = sourcesData.sources?.find((s: any) => s.id === sourceId);
      if (source) {
        sourceType = source.source_type;
        console.log(`[SERVER] Source type: ${sourceType}`);
      }
    }
  } catch (error) {
    console.log(`[SERVER] Could not fetch source type: ${error}`);
  }

  // Determine target URL based on source type
  let targetUrl: URL;

  if (sourceType === 'paperless') {
    // Paperless sources use the FastAPI server's dedicated endpoint
    targetUrl = new URL(`${apiUrl}/paperless/sources/${sourceId}/scan`);
    if (forceReprocess !== null) {
      // The paperless endpoint uses 'force' instead of 'force_reprocess'
      targetUrl.searchParams.set('force', forceReprocess);
    }
    console.log(`[SERVER] Paperless source detected, forwarding to FastAPI endpoint: ${targetUrl.toString()}`);
  } else {
    // Filesystem and Thunderbird sources use the ingest sidecar
    targetUrl = new URL(`${sidecarUrl}/sources/scan/${sourceId}`);
    if (forceReprocess !== null) {
      targetUrl.searchParams.set('force_reprocess', forceReprocess);
    }
    console.log(`[SERVER] Forwarding to ingest sidecar: ${targetUrl.toString()}`);
  }

  // Build headers - include API key for authentication
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add API key if available
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
    console.log(`[SERVER] Adding X-API-Key header for authentication`);
  } else {
    console.log(`[SERVER] WARNING: No API key found - server may reject request`);
  }

  try {
    const startTime = Date.now();
    const response = await fetch(targetUrl.toString(), {
      method: 'POST',
      headers: headers,
    });
    const duration = Date.now() - startTime;

    console.log(`[SERVER] Target response: ${response.status} (${duration}ms)`);

    // Forward the response status and body exactly as-is (especially 403 responses)
    const text = await response.text();
    console.log(`[SERVER] Response body: ${text}`);

    return new NextResponse(text, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
      },
    });
  } catch (error) {
    console.error(`[SERVER] Target server unreachable: ${error}`);

    // If the target server is unreachable, return a 502 Bad Gateway
    return new NextResponse(JSON.stringify({
      detail: 'Target server unreachable',
      error: error instanceof Error ? error.message : 'Unknown error',
    }), {
      status: 502,
      statusText: 'Bad Gateway',
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
      },
    });
  }
}
