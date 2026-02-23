import { api, fmtDate, showError, clearError } from '../app.js';

// ── State ────────────────────────────────────────────────────
let allRuns      = [];
let groupMode    = 'source';   // 'source' | 'status' | 'none'
let filterStatus = 'all';
let filterSource = 'all';
let searchQuery  = '';

// ── Constants ────────────────────────────────────────────────
const STATUS_COLOR = {
  running:        'var(--accent2)',
  completed:      '#6ee7b7',
  interrupted:    'var(--muted)',
  failed:         'var(--danger)',
  stop_requested: '#f59e0b',
  starting:       'var(--accent)',
};

const STATUS_ORDER = ['running', 'starting', 'stop_requested', 'failed', 'interrupted', 'completed'];

// ── Template ─────────────────────────────────────────────────
const TEMPLATE = `
<div class="runs-toolbar">
  <div class="runs-search-wrap">
    <span class="runs-search-icon">⌕</span>
    <input class="runs-search" id="runsSearch" type="text" placeholder="Filter by run ID…">
  </div>

  <div class="runs-toolbar-group">
    <label class="runs-toolbar-label">Status</label>
    <select class="filter-select" id="filterStatus">
      <option value="all">All statuses</option>
      <option value="running">Running</option>
      <option value="starting">Starting</option>
      <option value="stop_requested">Stop requested</option>
      <option value="completed">Completed</option>
      <option value="interrupted">Interrupted</option>
      <option value="failed">Failed</option>
    </select>
  </div>

  <div class="runs-toolbar-group">
    <label class="runs-toolbar-label">Source</label>
    <select class="filter-select" id="filterSource">
      <option value="all">All sources</option>
    </select>
  </div>

  <div class="runs-toolbar-group">
    <label class="runs-toolbar-label">Group by</label>
    <div class="view-toggle">
      <button class="view-btn active" data-group="source">Source</button>
      <button class="view-btn"        data-group="status">Status</button>
      <button class="view-btn"        data-group="none">None</button>
    </div>
  </div>

  <button class="btn btn-danger" id="stopAllBtn" style="display:none;margin-left:auto;">⏹ Stop All</button>
</div>

<div class="runs-summary" id="runsSummary"></div>
<div id="runsContainer">
  <div class="loading"><div class="spinner"></div> Loading…</div>
</div>
`;

// ── Mount / unmount ──────────────────────────────────────────
let _pollTimer = null;

export function mount(container) {
  container.innerHTML = TEMPLATE;

  // Group buttons
  container.querySelectorAll('[data-group]').forEach(btn => {
    btn.addEventListener('click', () => {
      groupMode = btn.dataset.group;
      container.querySelectorAll('[data-group]').forEach(b =>
        b.classList.toggle('active', b.dataset.group === groupMode));
      render();
    });
  });

  document.getElementById('filterStatus').addEventListener('change', e => {
    filterStatus = e.target.value;
    render();
  });
  document.getElementById('filterSource').addEventListener('change', e => {
    filterSource = e.target.value;
    render();
  });
  document.getElementById('runsSearch').addEventListener('input', e => {
    searchQuery = e.target.value.trim().toLowerCase();
    render();
  });
  document.getElementById('stopAllBtn').addEventListener('click', stopAll);

  load();
  _pollTimer = setInterval(load, 60000);
}

export function unmount() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
  allRuns = []; groupMode = 'source'; filterStatus = 'all';
  filterSource = 'all'; searchQuery = '';
}

// ── Data ─────────────────────────────────────────────────────
async function load() {
  clearError();
  try {
    const data = await api.get('/runs/list');
    allRuns = data.runs || [];
    populateSourceFilter();
    render();
  } catch(e) {
    showError('Could not load runs: ' + e.message);
    const c = document.getElementById('runsContainer');
    if (c) c.innerHTML = '<div class="empty-state">Could not load runs.</div>';
  }
}

function populateSourceFilter() {
  const sel = document.getElementById('filterSource');
  if (!sel) return;
  const sources  = [...new Set(allRuns.map(r => r.source_type))].sort();
  const current  = sel.value;
  sel.innerHTML  = '<option value="all">All sources</option>' +
    sources.map(s => `<option value="${s}"${s === current ? ' selected' : ''}>${s}</option>`).join('');
}

// ── Filtering ────────────────────────────────────────────────
function filtered() {
  return allRuns.filter(r => {
    if (filterStatus !== 'all' && r.status     !== filterStatus) return false;
    if (filterSource !== 'all' && r.source_type !== filterSource) return false;
    if (searchQuery  && !r.run_id.toLowerCase().includes(searchQuery)) return false;
    return true;
  });
}

// ── Render ───────────────────────────────────────────────────
function render() {
  const container  = document.getElementById('runsContainer');
  const summary    = document.getElementById('runsSummary');
  const stopAllBtn = document.getElementById('stopAllBtn');
  if (!container) return;

  const runs   = filtered();
  const active = allRuns.filter(r => r.status === 'running' || r.status === 'starting');
  stopAllBtn.style.display = active.length ? '' : 'none';

  // Summary chips — counts across ALL runs (not filtered)
  const counts = {};
  allRuns.forEach(r => { counts[r.status] = (counts[r.status] || 0) + 1; });
  summary.innerHTML = STATUS_ORDER
    .filter(s => counts[s])
    .map(s => `<span class="run-chip" style="--chip-color:${STATUS_COLOR[s] ?? 'var(--muted)'}">
      <span class="run-chip-dot"></span>${s} <strong>${counts[s]}</strong>
    </span>`).join('');

  if (!runs.length) {
    container.innerHTML = '<div class="empty-state">No runs match the current filters.</div>';
    return;
  }

  // Sort: by status priority first, then updated_at desc
  const sorted = [...runs].sort((a, b) => {
    const ao = STATUS_ORDER.indexOf(a.status);
    const bo = STATUS_ORDER.indexOf(b.status);
    if (ao !== bo) return ao - bo;
    return new Date(b.updated_at) - new Date(a.updated_at);
  });

  if (groupMode === 'none') {
    container.innerHTML = `<div class="runs-list">${sorted.map(runCard).join('')}</div>`;
  } else {
    const key = groupMode === 'source' ? 'source_type' : 'status';
    const groups = {};
    const order  = [];
    sorted.forEach(r => {
      if (!groups[r[key]]) { groups[r[key]] = []; order.push(r[key]); }
      groups[r[key]].push(r);
    });

    container.innerHTML = order.map(k => `
      <div class="runs-group">
        <div class="runs-group-header">
          ${groupMode === 'status'
            ? `<span class="run-status-dot" style="background:${STATUS_COLOR[k] ?? 'var(--muted)'}"></span>`
            : ''}
          <span class="source-type-tag ${k}">${k}</span>
          <span class="badge">${groups[k].length} run${groups[k].length !== 1 ? 's' : ''}</span>
        </div>
        <div class="runs-list">${groups[k].map(runCard).join('')}</div>
      </div>`).join('');
  }

  // Wire stop buttons after DOM update
  container.querySelectorAll('.stop-run-btn').forEach(btn => {
    btn.addEventListener('click', () => stopRun(btn.dataset.id, btn));
  });
}

// ── Card ─────────────────────────────────────────────────────
function runCard(run) {
  const color   = STATUS_COLOR[run.status] ?? 'var(--muted)';
  const canStop = run.status === 'running' || run.status === 'starting';
  const disc    = run.discovered_document_count ?? 0;
  const idx     = run.indexed_document_count    ?? 0;
  const pct     = disc > 0 ? Math.min(100, (idx / disc) * 100) : 0;

  return `
  <div class="run-card">
    <div class="run-card-top">
      <div class="run-card-left">
        <div class="run-id">${run.run_id}</div>
        <div class="run-meta-row">
          <span class="source-type-tag ${run.source_type}">${run.source_type}</span>
          <span class="run-status-pill" style="--sc:${color}">
            <span class="run-status-dot${run.status === 'running' ? ' pulse' : ''}"></span>
            ${run.status}
          </span>
        </div>
      </div>
      <div class="run-card-right">
        <div class="run-time">Started ${fmtDate(run.started_at)}</div>
        ${run.updated_at ? `<div class="run-time">Updated ${fmtDate(run.updated_at)}</div>` : ''}
      </div>
    </div>

    <div class="run-counts">
      <div class="run-count-item">
        <div class="stat-label">Discovered</div>
        <div class="run-count-val accent">${disc > 0 ? disc : '—'}</div>
      </div>
      <div class="run-count-item">
        <div class="stat-label">Indexed</div>
        <div class="run-count-val green">${idx > 0 ? idx : '—'}</div>
      </div>
      ${disc > 0 ? `
      <div class="run-count-item" style="flex:1;min-width:140px;">
        <div class="stat-label">Progress &nbsp;<span style="color:var(--text);font-family:'Syne',sans-serif">${pct.toFixed(0)}%</span></div>
        <div class="run-progress-track">
          <div class="run-progress-fill" style="width:${pct}%"></div>
        </div>
      </div>` : ''}
    </div>

    ${canStop ? `<button class="btn btn-sm btn-danger stop-run-btn" data-id="${run.run_id}" style="margin-top:12px;">⏹ Stop</button>` : ''}
  </div>`;
}

// ── Actions ──────────────────────────────────────────────────
async function stopRun(runId, btn) {
  btn.disabled = true; btn.textContent = '…';
  try {
    await api.post(`/runs/request_stop/${runId}`);
    await load();
  } catch(e) {
    showError('Could not stop run: ' + e.message);
    btn.disabled = false; btn.textContent = '⏹ Stop';
  }
}

async function stopAll() {
  const btn = document.getElementById('stopAllBtn');
  btn.disabled = true; btn.textContent = '…';
  try {
    await api.post('/runs/stop_all');
    await load();
  } catch(e) {
    showError('Could not stop all runs: ' + e.message);
  }
  btn.disabled = false; btn.textContent = '⏹ Stop All';
}
