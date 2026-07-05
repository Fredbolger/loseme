import { NextResponse } from 'next/server';

/**
 * Proxy route for forwarding source scan requests to the ingest sidecar.
 * This maintains the same-origin browser call pattern while delegating the
 * actual filesystem walking/extractor logic to the Python sidecar container.
 * Must forward the force_reprocess query param and preserve the 403 "wrong device" response shape.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ sourceId: string }> }
) {
  const { sourceId } = await params;
  const sidecarUrl = process.env.LOSEME_INGEST_SIDECAR_URL || 'http://ingest-sidecar:3000';
  const apiKey = process.env.LOSEME_API_KEY || '';
  
  console.log(`[SERVER] Proxy route hit for sourceId: ${sourceId}`);
  console.log(`[SERVER] Sidecar URL: ${sidecarUrl}`);
  console.log(`[SERVER] API Key present: ${apiKey ? 'yes' : 'no'}`);
  
  // Extract the query parameters (particularly force_reprocess)
  const url = new URL(request.url);
  const forceReprocess = url.searchParams.get('force_reprocess');
  console.log(`[SERVER] force_reprocess: ${forceReprocess}`);
  
  // Forward the request to the ingest sidecar with proper authentication
  const targetUrl = new URL(`${sidecarUrl}/sources/scan/${sourceId}`);
  if (forceReprocess !== null) {
    targetUrl.searchParams.set('force_reprocess', forceReprocess);
  }
  
  console.log(`[SERVER] Forwarding to: ${targetUrl.toString()}`);
  
  // Build headers - include API key for authentication to ingest sidecar
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  // Add API key if available (ingest sidecar requires this)
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
    console.log(`[SERVER] Adding X-API-Key header for sidecar authentication`);
  } else {
    console.log(`[SERVER] WARNING: No API key found - sidecar may reject request`);
  }
  
  try {
    const startTime = Date.now();
    const response = await fetch(targetUrl.toString(), {
      method: 'POST',
      headers: headers,
    });
    const duration = Date.now() - startTime;
    
    console.log(`[SERVER] Sidecar response: ${response.status} (${duration}ms)`);
    
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
    console.error(`[SERVER] Sidecar unreachable: ${error}`);
    
    // If the sidecar is unreachable, return a 502 Bad Gateway
    return new NextResponse(JSON.stringify({
      detail: 'Ingest sidecar unreachable',
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