/**
 * Typed API client for the LoSeMe server (FastAPI on LOSEME_API_URL).
 * Replaces client/web/static/app.js's `api` object + `authHeaders()`.
 *
 * Base URL and key are resolved client-side via /api/config (a Next.js
 * route handler reading server env vars), mirroring the old /config
 * endpoint so the API key never gets baked into a static client bundle.
 */

export interface RuntimeConfig {
  api_url: string;
  api_key: string;
  client_url: string;
  ingest_sidecar_url: string;
  device_id: string;
}

let cachedConfig: RuntimeConfig | null = null;

export async function getRuntimeConfig(): Promise<RuntimeConfig> {
  if (cachedConfig) return cachedConfig;
  const res = await fetch('/api/config');
  if (!res.ok) {
    // Fall back to sane defaults if /config is unreachable, same as
    // the old app.js bootstrap() try/catch.
    cachedConfig = {
      api_url: 'http://localhost:8000',
      api_key: '',
      client_url: 'http://localhost:3000',
      ingest_sidecar_url: 'http://ingest-sidecar:3000',
      device_id: '',
    };
    return cachedConfig;
  }
  cachedConfig = await res.json();
  return cachedConfig as RuntimeConfig;
}

async function authHeaders(): Promise<HeadersInit> {
  const cfg = await getRuntimeConfig();
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (cfg.api_key) headers['X-API-Key'] = cfg.api_key;
  return headers;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const cfg = await getRuntimeConfig();
  const headers = await authHeaders();
  const res = await fetch(`${cfg.api_url}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers || {}) },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `HTTP ${res.status} on ${path}`);
  }
  // Some endpoints (delete) may return empty body
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/** Resolve the *client-local* base URL (this Next.js app), for preview/serve routes. */
export async function getClientBase(): Promise<string> {
  const cfg = await getRuntimeConfig();
  return cfg.client_url;
}

/** Resolve the ingest sidecar base URL for filesystem walking and extractor operations. */
export async function getIngestSidecarBase(): Promise<string> {
  const cfg = await getRuntimeConfig();
  return cfg.ingest_sidecar_url;
}
