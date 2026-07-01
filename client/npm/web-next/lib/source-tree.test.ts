import { describe, it, expect } from 'vitest';
import { buildSourceTree, enrichSources, countLeaves, countDocs } from '../source-tree';
import type { MonitoredSource } from '../types';

function mockSource(id: string, dir: string): MonitoredSource {
  return {
    id,
    source_type: 'filesystem',
    locator: dir,
    scope: { type: 'filesystem', directories: [dir], recursive: true, include_patterns: [], exclude_patterns: [] },
    enabled: true,
    created_at: '2024-01-01T00:00:00Z',
  };
}

describe('source-tree', () => {
  it('returns a single leaf for one source', () => {
    const sources = enrichSources([mockSource('a', '/data/docs')], {});
    const tree = buildSourceTree(sources);
    expect(tree).toHaveLength(1);
    expect(tree[0]!.type).toBe('leaf');
  });

  it('groups sources sharing a common prefix', () => {
    const raw = [
      mockSource('a', '/data/projects/alpha'),
      mockSource('b', '/data/projects/beta'),
      mockSource('c', '/data/notes'),
    ];
    const sources = enrichSources(raw, { a: 2, b: 3, c: 1 });
    const tree = buildSourceTree(sources);

    // /data/projects/{alpha,beta} should collapse into one group,
    // /data/notes stays a leaf.
    const group = tree.find((n) => n.type === 'group');
    const leaf = tree.find((n) => n.type === 'leaf');
    expect(group).toBeDefined();
    expect(leaf).toBeDefined();

    if (group?.type === 'group') {
      expect(countLeaves(group)).toBe(2);
      expect(countDocs(group)).toBe(5);
    }
  });
});
