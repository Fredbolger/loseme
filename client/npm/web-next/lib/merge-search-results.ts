import type { MergedSearchResult, SearchResultRaw } from './types';

/**
 * Ported verbatim (logic-preserving) from search.js's mergeByPart().
 * Groups raw chunk-level search hits by document_part_id, tracking the
 * chunk with the highest/lowest score and concatenating all matched
 * chunk texts for that document (used to build LLM context).
 */
export function mergeByPart(raw: SearchResultRaw[]): MergedSearchResult[] {
  const seen = new Map<string, MergedSearchResult>();
  const order: string[] = [];

  for (const r of raw) {
    const pid = r.document_part_id;
    const existing = seen.get(pid);
    if (!existing) {
      seen.set(pid, {
        ...r,
        chunks: [r],
        maxScore: r.score,
        minScore: r.score,
        chunkCount: 1,
        allChunkTexts: [],
      });
      order.push(pid);
    } else {
      existing.chunks.push(r);
      existing.maxScore = Math.max(existing.maxScore, r.score);
      existing.minScore = Math.min(existing.minScore, r.score);
      existing.chunkCount++;
      existing.score = existing.maxScore;
    }
  }

  return order.map((pid) => {
    const item = seen.get(pid)!;
    item.allChunkTexts = item.chunks.map((c) => c.chunk_text || '').filter(Boolean);
    return item;
  });
}

/** Ported from search.js's buildLLMContext(). */
export function buildLLMContext(
  mergedResults: MergedSearchResult[],
  enriched: Record<string, { source_path?: string } | undefined>,
  history: { role: string; content: string }[],
): string {
  const contextParts = mergedResults.slice(0, 8).map((doc, i) => {
    const ep = enriched[doc.document_part_id];
    const name = (ep?.source_path || doc.source_path || doc.document_part_id).split(/[/\\]/).pop() || 'Unknown';
    const allText = doc.allChunkTexts.join('\n\n');
    return `[Document ${i + 1}: ${name}]\n${allText}`;
  });

  let context = contextParts.join('\n\n---\n\n');

  if (history.length > 0) {
    const historyText = history
      .slice(-5)
      .map((msg) => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content.substring(0, 500)}`)
      .join('\n');
    context = `Previous conversation:\n${historyText}\n\nCurrent search results:\n${context}`;
  }

  return context;
}
