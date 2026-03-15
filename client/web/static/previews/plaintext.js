import  { getClientBase } from '../app.js';

// ── Plaintext / Code / Markdown Preview ──────────────────────
// Handles filesystem files served by PlaintextPreviewGenerator.
// Markdown files are rendered as HTML via marked.js (loaded from CDN).
// All other text files are shown as a plain scrollable code block.

const SUPPORTED_SUFFIXES = new Set([
  'txt', 'md', 'rst', 'py', 'js', 'ts', 'css', 'html', 'htm',
  'json', 'yaml', 'yml', 'toml', 'ini', 'sh', 'bash',
]);

const MARKDOWN_SUFFIXES = new Set(['md', 'rst']);

export function canHandle(sourceType, suffix) {
  return sourceType === 'filesystem' && SUPPORTED_SUFFIXES.has(suffix);
}

export async function render(body, partId, path) {
  body.innerHTML = '<div class="preview-loading"><div class="spinner"></div></div>';

  const base   = getClientBase();

  const suffix = path.split('.').pop().toLowerCase();

  try {
    const data = await fetch(`${base}/documents/preview/${partId}`)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });

    if (MARKDOWN_SUFFIXES.has(suffix)) {
      await renderMarkdown(body, data.text || '', data.language || 'markdown');
    } else {
      renderPlaintext(body, data.text || '', data.language || 'plaintext');
    }
  } catch (e) {
    body.innerHTML = `
      <div class="preview-unsupported">
        <div style="font-size:32px;opacity:0.3;margin-bottom:12px">⚠️</div>
        <div>Failed to load file: ${e.message}</div>
      </div>`;
  }
}

// ── Markdown renderer ─────────────────────────────────────────
async function renderMarkdown(body, text, language) {
  // Load marked.js from CDN on first use, then cache it on window
  if (!window._marked) {
    await loadScript('https://cdn.jsdelivr.net/npm/marked/marked.min.js');
    window._marked = window.marked;
    // Configure: GitHub-flavoured markdown, line breaks on single newline
    window._marked.setOptions({ breaks: true, gfm: true });
  }

  const html = window._marked.parse(text);

  body.innerHTML = `
    <div class="plaintext-preview">
      <div class="plaintext-toolbar">
        <span class="plaintext-language">${escHtml(language)}</span>
        <span class="plaintext-lines">${text.split('\n').length} lines</span>
      </div>
      <div class="markdown-body">${html}</div>
    </div>`;
}

// ── Plain text / code renderer ────────────────────────────────
function renderPlaintext(body, text, language) {
  body.innerHTML = `
    <div class="plaintext-preview">
      <div class="plaintext-toolbar">
        <span class="plaintext-language">${escHtml(language)}</span>
        <span class="plaintext-lines">${text.split('\n').length} lines</span>
      </div>
      <pre class="plaintext-body"><code>${escHtml(text)}</code></pre>
    </div>`;
}

// ── Helpers ───────────────────────────────────────────────────

// Dynamically load a <script> tag once and resolve when ready
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script   = document.createElement('script');
    script.src     = src;
    script.onload  = resolve;
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
