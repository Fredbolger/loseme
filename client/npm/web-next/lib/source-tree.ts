import type { MonitoredSource, SourceType } from './types';

/**
 * Ported verbatim (logic-preserving) from
 * client/web/static/views/index.js — buildTree / longestCommonPrefix /
 * countLeaves / countDocs. Groups monitored sources into a tree based on
 * shared path prefixes so the dashboard can collapse deeply nested
 * filesystem sources instead of listing them flat.
 */

export interface EnrichedSource extends MonitoredSource {
  _loc: string;
  _type: SourceType;
  _docCount: number;
}

export type SourceTreeNode =
  | { type: 'leaf'; source: EnrichedSource }
  | { type: 'group'; label: string; children: SourceTreeNode[] };

function getSourceLoc(s: MonitoredSource): string {
  const scope = s.scope;
  const directories = (scope as { directories?: string[] }).directories;
  const mboxPath = (scope as { mbox_path?: string }).mbox_path;
  return s.locator || directories?.[0] || mboxPath || '';
}

export function getSourceType(s: MonitoredSource): SourceType {
  return s.source_type || (s.scope.type as SourceType) || ('unknown' as SourceType);
}

function pathParts(p: string): string[] {
  return p.replace(/\\/g, '/').split('/').filter(Boolean);
}

function longestCommonPrefix(locs: string[]): string[] {
  if (!locs.length) return [];
  const segs = locs.map(pathParts);
  const ref = segs[0]!;
  let i = 0;
  while (i < ref.length && segs.every((s) => s[i] === ref[i])) i++;
  return ref.slice(0, i);
}

export function enrichSources(
  sources: MonitoredSource[],
  docCountBySourceId: Record<string, number>,
): EnrichedSource[] {
  return sources.map((s) => ({
    ...s,
    _loc: getSourceLoc(s),
    _type: getSourceType(s),
    _docCount: docCountBySourceId[s.id] ?? 0,
  }));
}

export function buildSourceTree(sources: EnrichedSource[]): SourceTreeNode[] {
  if (sources.length === 0) return [];
  if (sources.length === 1) return [{ type: 'leaf', source: sources[0]! }];

  const locs = sources.map((s) => s._loc);
  const common = longestCommonPrefix(locs);

  const buckets: Record<string, EnrichedSource[]> = {};
  const order: string[] = [];

  sources.forEach((s) => {
    const parts = pathParts(s._loc);
    const next = parts[common.length];
    const key = next || s._loc;

    if (!buckets[key]) {
      buckets[key] = [];
      order.push(key);
    }
    buckets[key]!.push(s);
  });

  const nodes: SourceTreeNode[] = [];

  order.forEach((key) => {
    const members = buckets[key]!;

    if (members.length === 1) {
      nodes.push({ type: 'leaf', source: members[0]! });
    } else {
      const prefix = '/' + longestCommonPrefix(members.map((s) => s._loc)).join('/');
      nodes.push({
        type: 'group',
        label: prefix,
        children: buildSourceTree(members),
      });
    }
  });

  return nodes;
}

export function countLeaves(node: SourceTreeNode): number {
  if (node.type === 'leaf') return 1;
  return node.children.reduce((acc, c) => acc + countLeaves(c), 0);
}

export function countDocs(node: SourceTreeNode): number {
  if (node.type === 'leaf') return node.source._docCount || 0;
  return node.children.reduce((acc, c) => acc + countDocs(c), 0);
}
