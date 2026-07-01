'use client';

import { useCallback, useRef, useState } from 'react';
import { getRuntimeConfig } from '@/lib/api-client';

interface StreamLLMParams {
  query: string;
  context: string;
  topK: number;
  model: string;
  resultIds: string[];
  sessionId: string | null;
}

/**
 * Replaces search-api.js's streamLLMFromServer(). Parses the
 * `data: {...}\n\n` SSE framing from POST /llm/generate and exposes
 * token-by-token updates via onToken, with abort support.
 */
export function useSSEStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setIsStreaming(false);
  }, []);

  const stream = useCallback(async (params: StreamLLMParams, onToken: (token: string) => void) => {
    // Cancel any in-flight stream first.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsStreaming(true);

    try {
      const cfg = await getRuntimeConfig();
      const headers: HeadersInit = { 'Content-Type': 'application/json', Accept: 'text/event-stream' };
      if (cfg.api_key) headers['X-API-Key'] = cfg.api_key;

      const res = await fetch(`${cfg.api_url}/llm/generate`, {
        method: 'POST',
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          query: params.query,
          context: params.context,
          topK: params.topK,
          model: params.model,
          result_ids: params.resultIds,
          session_id: params.sessionId,
          stream: true,
        }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`LLM server error: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const evt of events) {
          if (!evt.startsWith('data: ')) continue;
          const dataStr = evt.slice(6);
          if (dataStr === '[DONE]') continue;
          try {
            const data = JSON.parse(dataStr);
            if (data.token) onToken(data.token);
            else if (data.error) throw new Error(data.error);
          } catch {
            // Malformed SSE chunk — skip, matches legacy console.error-and-continue behavior.
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') throw e;
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setIsStreaming(false);
      }
    }
  }, []);

  return { stream, abort, isStreaming };
}
