import { api, fmtDate, showError, clearError } from '../app.js';

// ── State ────────────────────────────────────────────────────
let groupedView = false;
let lastResults  = [];
let lastEnriched = {};
let lastMaxScore = 1;

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
  <div id="searchResults"></div>
`;

// ── Mount / unmount ──────────────────────────────────────────
export function mount(container) {
  container.innerHTML = TEMPLATE;

  // Reset state on mount so stale results don't show if you switch tabs
  groupedView  = false;
  lastResults  = [];
  lastEnriched = {};
  lastMaxScore = 1;

  document.getElementById('searchQuery').addEventListener('keydown', e => {
    if (e.key === 'Enter') runSearch();
  });
  document.getElementById('searchBtn').addEventListener('click', runSearch);
  document.getElementById('btnFlat').addEventListener('click', () => setView('flat'));
  document.getElementById('btnGrouped').addEventListener('click', () => setView('grouped'));
}

export function unmount() {}

// ── View toggle ──────────────────────────────────────────────
function setView(mode) {
  groupedView = mode === 'grouped';
  document.getElementById('btnFlat').classList.toggle('active', !groupedView);
  document.getElementById('btnGrouped').classList.toggle('active', groupedView);
  if (lastResults.length) renderResults(lastResults, lastEnriched, lastMaxScore);
}

// Escape HTML
function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

  try {
    const data    = await api.post('/search', { query, top_k: topK });
    const results = data.results || [];

    hint.textContent = `${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`;

    if (!results.length) {
      container.innerHTML = '<div class="no-results-search"><div class="big">∅</div>No matching documents found.</div>';
    } else {
      // Enrich via batch_get
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
}

function resultCard(r, part, maxScore, animIdx) {
  console.log('resultCard r:', r);
  const path     = part.source_path || r.metadata?.source_path || r.document_part_id || '—';
  const safePath = escHtml(path);
  const displayPath = path.includes('::Message-ID:')
        ? safePath.split('/').pop()
        : safePath.split('/').slice(-2).join('/');
  const basePath = path.includes('::Message-ID:')
  ? path.split('::Message-ID:')[0].split('/').pop()  // e.g. "Sent"
  : path.split('/').pop();
  const type     = part.source_type || r.metadata?.source_type || '—';
  const pct      = (r.score / maxScore) * 100;
  const scoreStr = r.score < 2 ? r.score.toFixed(3) : r.score.toFixed(1);
  const hue      = Math.round((r.score / maxScore) * 140);
  const metaEntries = Object.entries(r.metadata || {});

  return `<div class="result-card" style="animation-delay:${animIdx * 0.04}s">
    <div class="result-header" onclick="this.nextElementSibling.classList.toggle('open')">
      <div class="result-left">
        <div class="result-path" title="${safePath}">${displayPath}</div>
        <div class="result-meta-row">
          <span class="source-type-tag ${type}">${type}</span>
          <span style="font-size:11px;font-family:'Space Mono',monospace;color:var(--muted)">Source: ${basePath}</span>
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
        ${metaItem('Source Path', safePath)}
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
