// ── Fallback Preview ──────────────────────────────────────────
// Catch-all renderer shown when no other preview matches.
// Must always be last in the RENDERERS array in index.js.

export function canHandle(_sourceType, _suffix) {
  return true; // always matches
}

export function render(body, _partId, path) {
  const suffix = path.split('.').pop().toLowerCase();
  body.innerHTML = `
    <div class="preview-unsupported">
      <div style="font-size:32px;opacity:0.3;margin-bottom:12px">📄</div>
      <div>Preview not yet supported for <strong>.${suffix}</strong> files.</div>
    </div>`;
}
