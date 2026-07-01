import type { RunStatus, SourceType } from './types';

/**
 * Single source of truth for status/type → color. Replaces:
 *  - runs.js STATUS_COLOR (duplicated logic)
 *  - storage.js / index.js nth-child color cycling (purely positional,
 *    not tied to any actual data — a real UX bug: tile #3 was always
 *    red no matter what it represented)
 *
 * Colors reference CSS vars so they automatically adapt between themes.
 */
export const RUN_STATUS_COLOR: Record<RunStatus, string> = {
  running: 'var(--accent-secondary)',
  starting: 'var(--accent-primary)',
  stop_requested: 'var(--warning)',
  failed: 'var(--error)',
  interrupted: 'var(--text-tertiary)',
  completed: 'var(--success)',
  pending: 'var(--text-tertiary)',
};

export const RUN_STATUS_ORDER: RunStatus[] = [
  'running',
  'starting',
  'stop_requested',
  'failed',
  'interrupted',
  'completed',
  'pending',
];

export const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  running: 'Running',
  starting: 'Starting',
  stop_requested: 'Stop requested',
  failed: 'Failed',
  interrupted: 'Interrupted',
  completed: 'Completed',
  pending: 'Pending',
};

export const SOURCE_TYPE_COLOR: Record<SourceType, string> = {
  filesystem: 'var(--accent-secondary)',
  thunderbird: 'var(--accent-quaternary)',
};

export const SOURCE_TYPE_ICON: Record<SourceType, string> = {
  filesystem: '📁',
  thunderbird: '📧',
};
