import { getClientBase } from '../app.js';

// ── Email Preview ─────────────────────────────────────────────

export function canHandle(sourceType, _suffix) {
    return sourceType === 'thunderbird' || _suffix === 'eml';
}

export async function render(body, partId, _path) {
  body.innerHTML = '<div class="preview-loading"><div class="spinner"></div></div>';

  const base = getClientBase();
  //const base = document.getElementById('apiBase')?.value.replace(/\/$/, '') || '';

  try {
    const data = await fetch(`${base}/documents/preview/${partId}`)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });

    const dateStr = data.date ? new Date(data.date).toLocaleString() : data.date;

    body.innerHTML = `
      <div class="email-preview">
        <div class="email-headers">
          <div class="email-header-row">
            <span class="email-header-key">From</span>
            <span class="email-header-val">${escHtml(data.from_ || '—')}</span>
          </div>
          <div class="email-header-row">
            <span class="email-header-key">To</span>
            <span class="email-header-val">${escHtml(data.to || '—')}</span>
          </div>
          <div class="email-header-row">
            <span class="email-header-key">Date</span>
            <span class="email-header-val">${escHtml(dateStr || '—')}</span>
          </div>
          <div class="email-header-row email-subject-row">
            <span class="email-header-key">Subject</span>
            <span class="email-header-val email-subject">${escHtml(data.subject || '—')}</span>
          </div>
        </div>
        <div class="email-body">
          ${data.body_html
            ? `<iframe class="email-iframe" srcdoc="${escAttr(data.body_html)}" sandbox="allow-same-origin"></iframe>`
            : `<pre class="email-plain">${escHtml(data.body_text || '')}</pre>`
          }
        </div>
      </div>`;
  } catch (e) {
    body.innerHTML = `
      <div class="preview-unsupported">
        <div style="font-size:32px;opacity:0.3;margin-bottom:12px">⚠️</div>
        <div>Failed to load email: ${e.message}</div>
      </div>`;
  }
}

// ── Helpers ───────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escAttr(str) {
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
