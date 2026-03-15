import { api, fmtDate, showError, clearError, getClientBase } from '../app.js';
import { openPreview }                          from '../previews/index.js';

// ── State ────────────────────────────────────────────────────
let lastResults  = [];
let lastEnriched = {};
let lastMaxScore = 1;
let activePartId = null;
let currentQuery = '';

// ── HTML template ────────────────────────────────────────────
// Three-column layout that fills the viewport.
// Columns: [result list | document viewer | LLM answer]
// Search bar is pinned to the bottom.
const TEMPLATE = `
<div class="sw-layout">

  <!-- ── Left: result cards ── -->
  <aside class="sw-sidebar" id="swSidebar">
    <div class="sw-sidebar-header">
      <span class="sw-sidebar-label">Results</span>
      <span class="sw-sidebar-count" id="swResultCount"></span>
    </div>
    <div class="sw-sidebar-list" id="swResultList">
      <div class="sw-empty-state">
        <div class="sw-empty-icon">⬡</div>
        <div class="sw-empty-text">Run a search to see results</div>
      </div>
    </div>
  </aside>

  <!-- ── Centre: document viewer ── -->
  <main class="sw-doc-panel" id="swDocPanel">
    <div class="sw-doc-header" id="swDocHeader" style="display:none;">
      <div class="sw-doc-header-left">
        <span class="sw-doc-icon">◈</span>
        <span class="sw-doc-filename" id="swDocFilename"></span>
        <span class="sw-doc-path" id="swDocPath"></span>
      </div>
      <div class="sw-doc-header-right">
        <span class="sw-chunk-badge" id="swChunkBadge" style="display:none;">✦ chunk highlighted</span>
      </div>
    </div>
    <div class="sw-doc-body" id="swDocBody">
      <div class="sw-empty-state">
        <div class="sw-empty-icon" style="font-size:48px;opacity:0.12;">◈</div>
        <div class="sw-empty-title">No document selected</div>
        <div class="sw-empty-text">Run a search</div>
      </div>
    </div>
  </main>

  <!-- ── Right: LLM answer ── -->
  <aside class="sw-answer-panel" id="swAnswerPanel">
    <div class="sw-answer-header">
      <span class="sw-answer-label">LLM Answer</span>
      <span class="sw-spinner" id="swAnswerSpinner" style="display:none;"></span>
    </div>
    <div class="sw-answer-body" id="swAnswerBody">
      <div class="sw-answer-placeholder">
        Ask a question to get a synthesised answer drawn from your documents.
      </div>
    </div>
  </aside>

</div>

<!-- ── Bottom: search bar ── -->
<div class="sw-searchbar" id="swSearchBar">
  <div class="sw-searchbar-inner">
    <div class="sw-search-box" id="swSearchBox">
      <span class="sw-search-icon">⌕</span>
      <input
        class="sw-search-input"
        type="text"
        id="swQuery"
        placeholder="Search your knowledge base…"
        autocomplete="off"
        spellcheck="false"
      >
      <div class="sw-topk-wrap">
        <label for="swTopK">Top</label>
        <input type="number" id="swTopK" value="10" min="1" max="100">
      </div>
    </div>
    <button class="btn sw-search-btn" id="swSearchBtn">Search</button>
  </div>
  <div class="sw-searchbar-hint" id="swSearchHint">Press Enter or click Search</div>
</div>
`;

// ── Mount / Unmount ───────────────────────────────────────────
export function mount(container) {
  container.innerHTML = TEMPLATE;

  lastResults  = [];
  lastEnriched = {};
  lastMaxScore = 1;
  activePartId = null;
  currentQuery = '';

  document.getElementById('swQuery').addEventListener('keydown', e => {
    if (e.key === 'Enter') runSearch();
  });
  document.getElementById('swSearchBtn').addEventListener('click', runSearch);
}

export function unmount() {}

// ── Search ────────────────────────────────────────────────────
async function runSearch() {
  const query = document.getElementById('swQuery').value.trim();
  if (!query) return;

  currentQuery = query;

  const topK    = parseInt(document.getElementById('swTopK').value) || 10;
  const btn     = document.getElementById('swSearchBtn');
  const hint    = document.getElementById('swSearchHint');
  const list    = document.getElementById('swResultList');

  btn.disabled      = true;
  btn.textContent   = '…';
  hint.textContent  = 'Searching…';
  list.innerHTML    = '<div class="sw-loading"><span class="sw-spinner"></span> Searching…</div>';

  clearError();
  clearDocPanel();
  clearAnswerPanel();

  try {
    // 1. Vector search
    const data    = await api.post('/search', { query, top_k: topK });
    const rawResults = data.results || [];

    // 2. Merge chunks by document part
    const merged = mergeByPart(rawResults);

    // 3. Enrich with document metadata
    const partIds  = [...new Set(rawResults.map(r => r.document_part_id).filter(Boolean))];
    const enriched = {};
    try {
      const bd = await api.post('/documents/batch_get', { document_part_ids: partIds });
      (bd.documents_parts || []).forEach(p => {
        const id = p.document_part_id || p.part?.document_part_id;
        if (id) enriched[id] = p;
      });
    } catch {}

    lastResults  = merged;
    lastEnriched = enriched;
    lastMaxScore = Math.max(...rawResults.map(r => r.score), 0.001);

    const count = document.getElementById('swResultCount');
    count.textContent = merged.length ? `${merged.length}` : '';

    hint.textContent = merged.length
      ? `${merged.length} document${merged.length !== 1 ? 's' : ''} for "${query}"`
      : `No results for "${query}"`;

    renderResultList(merged, enriched);

    // 4. Auto-open highest-ranking result
    if (merged.length > 0) {
      openDocument(merged[0], enriched);
    }

    // 5. Stream LLM answer
    streamLLMAnswer(query, merged, enriched);

  } catch (e) {
    showError('Search failed: ' + e.message);
    list.innerHTML = '';
    hint.textContent = 'Search failed.';
  }

  btn.disabled    = false;
  btn.textContent = 'Search';
}

// ── Result list ───────────────────────────────────────────────
function renderResultList(results, enriched) {
  const list = document.getElementById('swResultList');

  if (!results.length) {
    list.innerHTML = `
      <div class="sw-empty-state">
        <div class="sw-empty-icon">∅</div>
        <div class="sw-empty-text">No matching documents</div>
      </div>`;
    return;
  }

  list.innerHTML = results.map((r, i) => {
    const ep      = enriched[r.document_part_id];
    const part    = ep?.part || ep || {};
    const path    = part.source_path || r.metadata?.source_path || r.document_part_id || '—';
    const name    = basename(path);
    const pct     = (r.score / lastMaxScore) * 100;
    const hue     = Math.round((r.score / lastMaxScore) * 130);
    const isActive = r.document_part_id === activePartId;

    return `
    <div
      class="sw-result-card${isActive ? ' sw-result-card--active' : ''}"
      data-part-id="${r.document_part_id}"
      data-idx="${i}"
      style="animation-delay:${i * 0.035}s"
      title="${escHtml(path)}"
    >
      <div class="sw-card-name">${escHtml(name)}</div>
      <div class="sw-card-meta">
        <div class="sw-score-bar">
          <div class="sw-score-fill" style="width:${pct.toFixed(1)}%;background:hsl(${hue},65%,55%)"></div>
        </div>
        <span class="sw-score-label" style="color:hsl(${hue},65%,55%)">${r.score < 2 ? r.score.toFixed(3) : r.score.toFixed(1)}</span>
      </div>
      ${r.chunks?.length > 1
        ? `<div class="sw-chunk-count">✦ ${r.chunks.length} chunks</div>`
        : ''}
    </div>`;
  }).join('');

  // Click handlers
  list.querySelectorAll('.sw-result-card').forEach(card => {
    card.addEventListener('click', () => {
      const idx = parseInt(card.dataset.idx);
      openDocument(lastResults[idx], lastEnriched);
    });
  });
}

function setActiveCard(partId) {
  document.querySelectorAll('.sw-result-card').forEach(c => {
    c.classList.toggle('sw-result-card--active', c.dataset.partId === partId);
  });
}

// ── Document viewer ───────────────────────────────────────────
async function openDocument(r, enriched) {
  activePartId = r.document_part_id;
  setActiveCard(activePartId);

  const ep   = enriched[r.document_part_id];
  const part = ep?.part || ep || {};
  const path = part.source_path || r.metadata?.source_path || '';
  const type = part.source_type || r.metadata?.source_type || 'filesystem';

  // Header
  const header   = document.getElementById('swDocHeader');
  const filename = document.getElementById('swDocFilename');
  const pathEl   = document.getElementById('swDocPath');
  const badge    = document.getElementById('swChunkBadge');
  const body     = document.getElementById('swDocBody');

  header.style.display = 'flex';
  filename.textContent = basename(path) || r.document_part_id;
  filename.title       = path;
  pathEl.textContent   = path;
  pathEl.title         = path;
  badge.style.display  = 'none';

  body.innerHTML = '<div class="sw-loading"><span class="sw-spinner"></span> Loading…</div>';

  // Delegate to the existing preview registry — it handles plaintext, PDF, email, etc.
  // We wrap its output so we can inject chunk highlighting afterwards.
  openPreview(body, r.document_part_id, type, path);

  // After the preview renderer has populated `body`, inject chunk highlights.
  // We use a short poll because some renderers (markdown, PDF) are async.
  injectChunkHighlight(body, r, badge);
}

function clearDocPanel() {
  activePartId = null;
  const header = document.getElementById('swDocHeader');
  const body   = document.getElementById('swDocBody');
  if (header) header.style.display = 'none';
  if (body) body.innerHTML = `
    <div class="sw-empty-state">
      <div class="sw-empty-icon" style="font-size:48px;opacity:0.12;">◈</div>
      <div class="sw-empty-title">No document selected</div>
      <div class="sw-empty-text">Run a search — the top result opens here automatically</div>
    </div>`;
}

// ── Chunk highlight injection ─────────────────────────────────
// After the preview renderer fills the body, find all text nodes and
// wrap matches of the chunk text in <mark class="sw-highlight">.
function injectChunkHighlight(bodyEl, r, badgeEl) {
  // Collect chunk texts from all chunks of this merged result.
  // Use the chunk's metadata text if stored, otherwise fall back to nothing —
  // the preview renderer already has the full document text.
  const ep         = lastEnriched[r.document_part_id];
  const part       = ep?.part || ep || {};
  const chunkTexts = (r.chunks || [r])
    .map(c => c.metadata?.text || c.text || '')
    .filter(t => t.length >= 30);   // ignore trivially short chunks

  if (!chunkTexts.length) return;

  // Poll until the preview renderer has rendered something real (max 2 s)
  let attempts = 0;
  const maxAttempts = 20;

  const tryHighlight = () => {
    attempts++;
    const hasContent = bodyEl.querySelector('pre, .plaintext-body, .markdown-body, .email-plain, p');
    if (!hasContent && attempts < maxAttempts) {
      setTimeout(tryHighlight, 100);
      return;
    }

    let highlighted = false;
    for (const chunkText of chunkTexts) {
      if (highlightTextInElement(bodyEl, chunkText)) {
        highlighted = true;
        break;   // highlight only the first / best chunk
      }
    }

    if (highlighted) {
      badgeEl.style.display = 'inline-flex';
      // Scroll the first highlight into view
      const mark = bodyEl.querySelector('mark.sw-highlight');
      if (mark) mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  setTimeout(tryHighlight, 150);
}

/**
 * Walk text nodes inside `root` and wrap occurrences of `needle`
 * in <mark class="sw-highlight">.
 * Returns true if at least one match was found.
 */
function highlightTextInElement(root, needle) {
  if (!needle || needle.length < 30) return false;

  // Use the first 120 chars of the chunk as the search needle —
  // long needles are less likely to match due to whitespace normalisation.
  const searchStr = needle.substring(0, 120).trim();
  if (!searchStr) return false;

  // Normalise whitespace for comparison
  const normalise = s => s.replace(/\s+/g, ' ');

  let found = false;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  const textNodes = [];
  let node;
  while ((node = walker.nextNode())) textNodes.push(node);

  for (const tn of textNodes) {
    const content    = tn.nodeValue || '';
    const normContent = normalise(content);
    const normNeedle  = normalise(searchStr);
    const idx = normContent.toLowerCase().indexOf(normNeedle.toLowerCase());
    if (idx === -1) continue;

    // Find the actual char offset in the original string corresponding to idx
    // (they differ if whitespace normalisation changed char counts, but for
    //  simple cases it's a direct index)
    const before = document.createTextNode(content.substring(0, idx));
    const mark   = document.createElement('mark');
    mark.className = 'sw-highlight';
    mark.textContent = content.substring(idx, idx + normNeedle.length);
    const after  = document.createTextNode(content.substring(idx + normNeedle.length));

    tn.parentNode.replaceChild(after, tn);
    tn.parentNode.insertBefore(mark, after);
    tn.parentNode.insertBefore(before, mark);

    found = true;
    break;   // one highlight per document is enough
  }

  return found;
}

// ── LLM Answer streaming ──────────────────────────────────────
async function streamLLMAnswer(query, results, enriched) {
  const panel   = document.getElementById('swAnswerBody');
  const spinner = document.getElementById('swAnswerSpinner');
  spinner.style.display = 'inline-block';
  panel.innerHTML = '<div class="sw-answer-streaming" id="swAnswerText"></div>';

  // Build context from top-10 results
  const contextParts = await Promise.all(results.slice(0, 10).map(async (r, i) => {
    const ep   = lastEnriched[r.document_part_id];
    const part = ep?.part || ep || {};
    const name = basename(part.source_path || r.document_part_id);
    try {
      const prev = await fetch(`${getClientBase()}/documents/preview/${r.document_part_id}`)
        .then(res => { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); });

      let text = '';
      if (prev.preview_type === 'email') {
        text = [
          prev.subject ? `Subject: ${prev.subject}` : '',
          prev.from_   ? `From: ${prev.from_}`       : '',
          prev.to      ? `To: ${prev.to}`             : '',
          prev.date    ? `Date: ${prev.date}`         : '',
          '',
          prev.body_text || prev.body_html?.replace(/<[^>]+>/g, '') || '',
        ].filter(Boolean).join('\n');
      } else {
        text = prev.text || prev.body_text || '';
      }

      return `[Source ${i + 1}: ${name}]\n${text.substring(0, 2000)}`;
    } catch {
      return `[Source ${i + 1}: ${name}]\n(preview unavailable)`;
    }
  }));

  const context = contextParts.join('\n\n---\n\n');

  let fullText = '';
  const textEl = document.getElementById('swAnswerText');

  try {
    await fetchLLMStream(query, context, (token) => {
      fullText += token;
      if (textEl) textEl.innerHTML = renderAnswerMarkdown(fullText) + '<span class="sw-cursor">▌</span>';
      panel.scrollTop = panel.scrollHeight;
    });

    // Final render without cursor
    if (textEl) textEl.innerHTML = renderAnswerMarkdown(fullText);

    // Source pills
    appendSourcePills(panel, results, enriched);

  } catch (e) {
    if (textEl) textEl.innerHTML = '<em style="opacity:0.5">LLM answer unavailable — check API connection.</em>';
  }

  spinner.style.display = 'none';
}


function clearAnswerPanel() {
  const panel   = document.getElementById('swAnswerBody');
  const spinner = document.getElementById('swAnswerSpinner');
  if (panel)   panel.innerHTML = '<div class="sw-answer-placeholder">Ask a question to get a synthesised answer drawn from your documents.</div>';
  if (spinner) spinner.style.display = 'none';
}

async function fetchLLMStream(query, context, onToken) {
  const ollamaBase = document.getElementById('apiBase').value.replace(/\/$/, '').replace(':8000', ':11434');
  
  const prompt = `You are a precise knowledge assistant. Answer the user's question using ONLY the provided document excerpts. Cite sources inline using [Source N] notation. Be concise and accurate. If the answer is not found in the sources, say so clearly.\n\nQuestion: ${query}\n\nDocument excerpts:\n\n${context}`;
  console.log('LLM Prompt:', prompt);

  const response = await fetch(`${ollamaBase}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        model:  'mistral:7b',   // change to whichever model you have pulled
      prompt: prompt,
      stream: true,
    }),
  });

  if (!response.ok) throw new Error(`Ollama API ${response.status}`);

  const reader  = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value, { stream: true }).split('\n').filter(Boolean);
    for (const line of lines) {
      try {
        const parsed = JSON.parse(line);
        if (parsed.response) onToken(parsed.response);
      } catch {}
    }
  }
}

function appendSourcePills(panel, results, enriched) {
  if (!results.length) return;

  const pillsHtml = results.slice(0, 5).map((r, i) => {
    const ep   = enriched[r.document_part_id];
    const part = ep?.part || ep || {};
    const name = basename(part.source_path || r.document_part_id);
    return `<div class="sw-source-pill" data-idx="${i}" title="${escHtml(part.source_path || '')}">
      <span class="sw-source-num">${i + 1}</span>
      <span class="sw-source-name">${escHtml(name)}</span>
    </div>`;
  }).join('');

  const sources = document.createElement('div');
  sources.className = 'sw-sources-block';
  sources.innerHTML = `<div class="sw-sources-label">Sources</div>${pillsHtml}`;
  panel.appendChild(sources);

  sources.querySelectorAll('.sw-source-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const idx = parseInt(pill.dataset.idx);
      openDocument(lastResults[idx], lastEnriched);
    });
  });
}

// ── Simple markdown renderer for the answer panel ─────────────
function renderAnswerMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // [Source N] citation chips
    .replace(/\[Source (\d+)\]/g, '<span class="sw-citation">Source $1</span>')
    // Headings
    .replace(/^### (.+)$/gm, '<h3 class="sw-answer-h">$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2 class="sw-answer-h">$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1 class="sw-answer-h">$1</h1>')
    // Bullet lists
    .replace(/^[*-] (.+)$/gm, '<div class="sw-answer-li"><span>·</span>$1</div>')
    // Blank lines → paragraph breaks
    .replace(/\n{2,}/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

// ── Utilities ─────────────────────────────────────────────────
function mergeByPart(raw) {
  const seen  = new Map();
  const order = [];
  for (const r of raw) {
    const pid = r.document_part_id;
    if (!seen.has(pid)) {
      seen.set(pid, { ...r, score: r.score, chunks: [r] });
      order.push(pid);
    } else {
      const ex = seen.get(pid);
      ex.chunks.push(r);
      ex.score = Math.max(ex.score, r.score);
    }
  }
  return order.map(pid => seen.get(pid));
}

function basename(path) {
  if (!path) return '—';
  return path.split(/[/\\]/).pop() || path;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
