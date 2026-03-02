import { api, fmtDate, showError, clearError } from '../app.js';

// ── State ────────────────────────────────────────────────────
let groupedView   = false;
let lastResults   = [];
let lastEnriched  = {};
let lastMaxScore  = 1;
let activePartId  = null;   // currently previewed document_part_id

// ── HTML template ────────────────────────────────────────────
const TEMPLATE = `
  <div class="search-panel-box">
    <div class="search-input-row">
      <input
        class="search-big"
        type="text"
        id="searchQuery"
        placeholder="Ask anything — semantic search over your indexed documents…"
      >
      <div class="topk-wrap">
        <label>Top</label>
        <input type="number" id="topK" value="10" min="1" max="100">
      </div>
      <button class="btn" id="searchBtn">Search</button>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
      <div class="search-hint" id="searchHint">Press Enter or click Search to run a semantic query.</div>
      <div class="view-toggle" id="viewToggle" style="display:none;">
        <button class="view-btn active" id="btnFlat">Flat</button>
        <button class="view-btn" id="btnGrouped">Grouped</button>
      </div>
    </div>
  </div>

  <div class="search-split" id="searchSplit">
    <div class="search-results-col" id="searchResults"></div>
    <div class="preview-panel" id="previewPanel" style="display:none;">
      <div class="preview-header">
        <span class="preview-title" id="previewTitle">Preview</span>
        <button class="preview-close" id="previewClose" title="Close preview">✕</button>
      </div>
      <div class="preview-body" id="previewBody">
        <div class="preview-loading"><div class="spinner"></div></div>
      </div>
    </div>
  </div>
`;

// ── Mount / unmount ──────────────────────────────────────────
export function mount(container) {
  container.innerHTML = TEMPLATE;

  groupedView  = false;
  lastResults  = [];
  lastEnriched = {};
  lastMaxScore = 1;
  activePartId = null;

  document.getElementById('searchQuery').addEventListener('keydown', e => {
    if (e.key === 'Enter') runSearch();
  });
  document.getElementById('searchBtn').addEventListener('click', runSearch);
  document.getElementById('btnFlat').addEventListener('click', () => setView('flat'));
  document.getElementById('btnGrouped').addEventListener('click', () => setView('grouped'));
  document.getElementById('previewClose').addEventListener('click', closePreview);
}

export function unmount() {
  activePartId = null;
}

// ── View toggle ──────────────────────────────────────────────
function setView(mode) {
  groupedView = mode === 'grouped';
  document.getElementById('btnFlat').classList.toggle('active', !groupedView);
  document.getElementById('btnGrouped').classList.toggle('active', groupedView);
  if (lastResults.length) renderResults(lastResults, lastEnriched, lastMaxScore);
}

// ── Search ───────────────────────────────────────────────────
async function runSearch() {
  const query = document.getElementById('searchQuery').value.trim();
  if (!query) return;

  const topK      = parseInt(document.getElementById('topK').value) || 10;
  const btn       = document.getElementById('searchBtn');
  const hint      = document.getElementById('searchHint');
  const container = document.getElementById('searchResults');

  btn.disabled = true;
  btn.textContent = '…';
  hint.textContent = 'Searching…';
  document.getElementById('viewToggle').style.display = 'none';
  container.innerHTML = '<div class="loading"><div class="spinner"></div> Running query…</div>';
  clearError();
  closePreview();

  try {
    const data    = await api.post('/search', { query, top_k: topK });
    const results = data.results || [];

    hint.textContent = `${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`;

    if (!results.length) {
      container.innerHTML = '<div class="no-results-search"><div class="big">∅</div>No matching documents found.</div>';
    } else {
      const partIds = [...new Set(results.map(r => r.document_part_id).filter(Boolean))];
      const enriched = {};
      try {
        const bd = await api.post('/documents/batch_get', { document_part_ids: partIds });
        (bd.documents_parts || []).forEach(p => {
          const id = p.document_part_id || p.part?.document_part_id;
          if (id) enriched[id] = p;
        });
      } catch {}

      const maxScore = Math.max(...results.map(r => r.score), 1);

      lastResults  = results;
      lastEnriched = enriched;
      lastMaxScore = maxScore;

      document.getElementById('viewToggle').style.display = 'flex';
      renderResults(results, enriched, maxScore);
    }
  } catch(e) {
    showError('Search failed: ' + e.message);
    container.innerHTML = '';
    hint.textContent = 'Search failed.';
    console.error(e);
  }

  btn.disabled = false;
  btn.textContent = 'Search';
}

// ── Rendering ────────────────────────────────────────────────
function renderResults(results, enriched, maxScore) {
  const container = document.getElementById('searchResults');

  if (groupedView) {
    const groups = {};
    const groupOrder = [];
    results.forEach(r => {
      const ep   = enriched[r.document_part_id];
      const part = ep?.part || ep || {};
      const type = part.source_type || r.metadata?.source_type || 'unknown';
      if (!groups[type]) { groups[type] = []; groupOrder.push(type); }
      groups[type].push({ r, part });
    });

    container.innerHTML = groupOrder.map(type => {
      const items = groups[type];
      const cards = items.map(({ r, part }, i) => resultCard(r, part, maxScore, i)).join('');
      return `
        <div class="group-header">
          <span class="source-type-tag ${type}">${type}</span>
          <span class="group-title">${type}</span>
          <span class="badge">${items.length} result${items.length !== 1 ? 's' : ''}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:8px">${cards}</div>`;
    }).join('');
  } else {
    container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px">' +
      results.map((r, i) => {
        const ep   = enriched[r.document_part_id];
        const part = ep?.part || ep || {};
        return resultCard(r, part, maxScore, i);
      }).join('') +
      '</div>';
  }

  // Attach click handlers after render
  container.querySelectorAll('.result-card[data-part-id]').forEach(card => {
    card.addEventListener('click', (e) => {
      // Don't fire if they clicked the expand toggle inside the card
      if (e.target.closest('.result-body')) return;
      const partId     = card.dataset.partId;
      const sourceType = card.dataset.sourceType;
      const path       = card.dataset.path;
      openPreview(partId, sourceType, path);
    });
  });
}

function resultCard(r, part, maxScore, animIdx) {
  const path       = part.source_path || r.metadata?.source_path || r.document_part_id || '—';
  const type       = part.source_type || r.metadata?.source_type || '—';
  const pct        = (r.score / maxScore) * 100;
  const scoreStr   = r.score < 2 ? r.score.toFixed(3) : r.score.toFixed(1);
  const hue        = Math.round((r.score / maxScore) * 140);
  const metaEntries = Object.entries(r.metadata || {});
  const isActive   = r.document_part_id === activePartId;

  return `<div
    class="result-card${isActive ? ' result-card--active' : ''}"
    style="animation-delay:${animIdx * 0.04}s;cursor:pointer;"
    data-part-id="${r.document_part_id}"
    data-source-type="${type}"
    data-path="${path}"
  >
    <div class="result-header" onclick="window._openPreviewFromCard(this, event)">
      <div class="result-left">
        <div class="result-path" title="${path}">${path}</div>
        <div class="result-meta-row">
          <span class="source-type-tag ${type}">${type}</span>
          <span style="font-size:11px;font-family:'Space Mono',monospace;color:var(--muted)">chunk #${r.metadata?.index ?? '?'}</span>
          ${part.extractor_name ? `<span style="font-size:11px;font-family:'Space Mono',monospace;color:var(--muted)">${part.extractor_name}</span>` : ''}
        </div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-bar"><div class="score-fill" style="width:${pct.toFixed(1)}%"></div></div>
        <span class="score-label" style="color:hsl(${hue},70%,55%)">${scoreStr}</span>
      </div>
    </div>
    <div class="result-body">
      <div class="meta-grid">
        ${metaItem('Source Path', path)}
        ${metaItem('Chunk ID', r.chunk_id)}
        ${metaItem('Document Part ID', r.document_part_id)}
        ${metaItem('Device', r.device_id || '—')}
        ${metaItem('Score', scoreStr)}
        ${part.last_indexed_at ? metaItem('Last Indexed', fmtDate(part.last_indexed_at)) : ''}
        ${metaEntries.filter(([k]) => !['source_path', 'index'].includes(k)).map(([k, v]) =>
          metaItem(k, typeof v === 'object' ? JSON.stringify(v) : String(v))
        ).join('')}
      </div>
    </div>
  </div>`;
}

function metaItem(key, val) {
  return `<div class="meta-item"><div class="meta-key">${key}</div><div class="meta-val">${val}</div></div>`;
}

// ── Preview panel ─────────────────────────────────────────────
function openPreview(partId, sourceType, path) {
  activePartId = partId;

  // Highlight active card
  document.querySelectorAll('.result-card').forEach(c => {
    c.classList.toggle('result-card--active', c.dataset.partId === partId);
  });

  const panel     = document.getElementById('previewPanel');
  const body      = document.getElementById('previewBody');
  const titleEl   = document.getElementById('previewTitle');
  const split     = document.getElementById('searchSplit');

  // Show panel and activate split layout
  panel.style.display = 'flex';
  split.classList.add('search-split--open');

  // Set title to filename only
  const filename = path.split('/').pop() || path;
  titleEl.textContent = filename;
  titleEl.title = path;

  body.innerHTML = '<div class="preview-loading"><div class="spinner"></div></div>';

  const suffix = path.split('.').pop().toLowerCase();

    if (sourceType === 'filesystem') {
    const suffix = path.split('.').pop().toLowerCase();
    if (suffix === 'pdf') {
      renderPdfPreview(body, partId);
    } else {
      body.innerHTML = `<div class="preview-unsupported">
        <div style="font-size:32px;opacity:0.3;margin-bottom:12px">📄</div>
        <div>Preview not yet supported for <strong>.${suffix}</strong> files.</div>
      </div>`;
    }
  } else if (sourceType === 'thunderbird') {
    renderEmailPreview(body, partId);
  } else {
    body.innerHTML = `<div class="preview-unsupported">
      <div style="font-size:32px;opacity:0.3;margin-bottom:12px">📄</div>
      <div>Preview not yet supported for <strong>${sourceType}</strong> sources.</div>
    </div>`;
  }
}

function renderPdfPreview(body, partId) {
  const base = document.getElementById('apiBase')?.value.replace(/\/$/, '') || '';
  const url  = `${base}/documents/serve/${partId}`;

  // Use an object tag — more reliable cross-browser for PDFs than iframe
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

window._openPreviewFromCard = function(headerEl, event) {
  // If they clicked the expand arrow area (right side), toggle the body
  if (event.target.closest('.score-bar-wrap')) {
    headerEl.nextElementSibling.classList.toggle('open');
    return;
  }
  // Otherwise open the preview
  const card = headerEl.closest('.result-card');
  openPreview(card.dataset.partId, card.dataset.sourceType, card.dataset.path);
};

function closePreview() {
  activePartId = null;
  const panel = document.getElementById('previewPanel');
  const split = document.getElementById('searchSplit');
  if (!panel) return;
  panel.style.display = 'none';
  split?.classList.remove('search-split--open');
  document.querySelectorAll('.result-card').forEach(c => c.classList.remove('result-card--active'));
}

async function renderEmailPreview(body, partId) {
  const base = document.getElementById('apiBase')?.value.replace(/\/$/, '') || '';
  
  try {
    const data = await fetch(`${base}/documents/preview/${partId}`)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });

    const dateStr = data.date ? new Date(data.date).toLocaleString() : data.date;

    body.innerHTML = `
      <div class="email-preview">
        <div class="email-headers">
          <div class="email-header-row"><span class="email-header-key">From</span><span class="email-header-val">${escHtml(data.from || '—')}</span></div>
          <div class="email-header-row"><span class="email-header-key">To</span><span class="email-header-val">${escHtml(data.to || '—')}</span></div>
          <div class="email-header-row"><span class="email-header-key">Date</span><span class="email-header-val">${escHtml(dateStr || '—')}</span></div>
          <div class="email-header-row email-subject-row"><span class="email-header-key">Subject</span><span class="email-header-val email-subject">${escHtml(data.subject || '—')}</span></div>
        </div>
        <div class="email-body">
          ${data.body_html
            ? `<iframe class="email-iframe" srcdoc="${escAttr(data.body_html)}" sandbox="allow-same-origin"></iframe>`
            : `<pre class="email-plain">${escHtml(data.body_text || '')}</pre>`
          }
        </div>
      </div>`;
  } catch(e) {
    body.innerHTML = `<div class="preview-unsupported">
      <div style="font-size:32px;opacity:0.3;margin-bottom:12px">⚠️</div>
      <div>Failed to load email: ${e.message}</div>
    </div>`;
  }
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
