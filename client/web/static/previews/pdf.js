import { getClientBase } from '../app.js';

// ── PDF Preview ──────────────────────────────────────────────
// Handles filesystem files with a .pdf extension.

export function canHandle(sourceType, _suffix) {
  return sourceType === 'filesystem' && _suffix === 'pdf';
}

export function render(body, partId, _path) {
  const base = getClientBase();
  const url  = `${base}/documents/serve/${partId}`;

  body.innerHTML = `
    <object
      data="${url}"
      type="application/pdf"
      class="preview-pdf-object"
    >
      <div class="preview-unsupported">
        <div style="font-size:32px;opacity:0.3;margin-bottom:12px">⚠️</div>
        <div>Your browser cannot display this PDF inline.</div>
        <a class="btn" style="margin-top:16px;display:inline-block;" href="${url}" target="_blank">Open in new tab</a>
      </div>
    </object>`;
}
