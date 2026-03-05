// ── Preview Registry ──────────────────────────────────────────
// This is the only file that knows about all preview types.
// To add a new preview: import it here and add it to RENDERERS
// (before fallback). search.js never needs to change.
//
// Each renderer module must export:
//   canHandle(sourceType: string, suffix: string) → boolean
//   render(body: HTMLElement, partId: string, path: string) → void | Promise<void>

import * as pdf      from './pdf.js';
import * as email    from './email.js';
import * as plaintext from './plaintext.js'; 
import * as fallback from './fallback.js';

// Order matters — first match wins. Keep fallback last.
const RENDERERS = [
  pdf,
  email,
  plaintext,
  fallback,
];

/**
 * Picks the correct renderer for the given file and calls render().
 * @param {HTMLElement} body       - The preview panel body element to render into
 * @param {string}      partId     - document_part_id
 * @param {string}      sourceType - e.g. 'filesystem', 'thunderbird'
 * @param {string}      path       - source path, used to determine file extension
 */
export function openPreview(body, partId, sourceType, path) {
  const suffix   = path.split('.').pop().toLowerCase();
  const renderer = RENDERERS.find(r => r.canHandle(sourceType, suffix));
  renderer.render(body, partId, path);
}
