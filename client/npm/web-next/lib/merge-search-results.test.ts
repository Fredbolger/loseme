import { describe, it, expect } from 'vitest';
import { mergeByPart } from '../merge-search-results';
import type { SearchResultRaw } from '../types';

function chunk(overrides: Partial<SearchResultRaw>): SearchResultRaw {
  return {
    chunk_id: 'c1',
    document_part_id: 'doc1',
    device_id: 'dev1',
    score: 0.5,
    metadata: {},
    source_path: '/a.txt',
    source_type: 'filesystem',
    unit_locator: 'filesystem:/a.txt',
    chunk_text: 'hello',
    ...overrides,
  };
}

describe('mergeByPart', () => {
  it('groups multiple chunks from the same document', () => {
    const raw = [
      chunk({ chunk_id: 'c1', score: 0.6, chunk_text: 'part one' }),
      chunk({ chunk_id: 'c2', score: 0.9, chunk_text: 'part two' }),
    ];
    const merged = mergeByPart(raw);
    expect(merged).toHaveLength(1);
    expect(merged[0]!.chunkCount).toBe(2);
    expect(merged[0]!.maxScore).toBe(0.9);
    expect(merged[0]!.minScore).toBe(0.6);
    expect(merged[0]!.score).toBe(0.9); // score reflects max
    expect(merged[0]!.allChunkTexts).toEqual(['part one', 'part two']);
  });

  it('keeps separate documents separate, preserving first-seen order', () => {
    const raw = [
      chunk({ document_part_id: 'docB', chunk_id: 'b1' }),
      chunk({ document_part_id: 'docA', chunk_id: 'a1' }),
    ];
    const merged = mergeByPart(raw);
    expect(merged.map((m) => m.document_part_id)).toEqual(['docB', 'docA']);
  });

  it('handles empty input', () => {
    expect(mergeByPart([])).toEqual([]);
  });
});
