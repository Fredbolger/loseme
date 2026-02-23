import { api, fmtDate, showError, clearError } from '../app.js';

// ── HTML template ────────────────────────────────────────────
const TEMPLATE = `
  <div class="section">
    <div class="section-header">
      <h2>Indexing Runs</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span class="badge" id="runsBadge">—</span>
        <button class="btn btn-danger" id="stopAllBtn" style="display:none;">⏹ Stop All</button>
      </div>
    </div>
    <div id="runsContainer">
      <div class="loading"><div class="spinner"></div> Loading…</div>
    </div>
  </div>
`;

// ── Status helpers ───────────────────────────────────────────
const STATUS_COLOR = {
  running:         'var(--accent2)',
  completed:       '#6ee7b7',
  interrupted:     'var(--muted)',
  failed:          'var(--danger)',
  stop_requested:  '#f59e0b',
  starting:        'var(--accent)',
};

function statusDot(status) {
  const color = STATUS_COLOR[status] ?? 'var(--muted)';
  const glow  = status === 'running' ? `box-shadow:0 0 6px ${color};` : '';
  return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};${glow};margin-right:6px;vertical-align:middle;"></span>`;
}

function progressBar(discovered, indexed) {
  if (!discovered || discovered === 0) return '';
  const pct = Math.min(100, (indexed / discovered) * 100).toFixed(1);
  return `
    <div style="margin-top:10px;">
      <div style="display:flex;justify-content:space-between;font-size:11px;font-family:'Space Mono',monospace;color:var(--muted);margin-bottom:4px;">
        <span>Progress</span>
        <span>${indexed} / ${discovered} (${pct}%)</span>
      </div>
      <div style="background:var(--tag-bg);border-radius:4px;height:6px;overflow:hidden;">
        <div style="background:var(--accent2);height:100%;width:${pct}%;transition:width 0.4s ease;border-radius:4px;"></div>
      </div>
    </div>`;
}

function renderRun(run) {
  const canStop = run.status === 'running' || run.status === 'starting';
  const stopBtn = canStop
    ? `<button class="btn btn-sm btn-danger stop-run-btn" data-id="${run.run_id}" style="margin-top:12px;">⏹ Stop</button>`
    : '';

  return `
    <div class="run-card" style="animation-delay:${Math.random() * 0.15}s">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div>
          <div style="font-size:12px;font-family:'Space Mono',monospace;color:var(--muted);margin-bottom:4px;">${run.run_id}</div>
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span class="source-type-tag ${run.source_type}">${run.source_type}</span>
            <span style="font-size:13px;">${statusDot(run.status)}<strong>${run.status}</strong></span>
          </div>
        </div>
        <div style="text-align:right;font-size:12px;font-family:'Space Mono',monospace;color:var(--muted);">
          <div>Started ${fmtDate(run.started_at)}</div>
          ${run.updated_at ? `<div>Updated ${fmtDate(run.updated_at)}</div>` : ''}
        </div>
      </div>

      <div style="display:flex;gap:24px;margin-top:12px;flex-wrap:wrap;">
        <div>
          <div class="stat-label">Discovered</div>
          <div style="font-size:20px;font-weight:700;color:var(--accent);">${run.discovered_document_count ?? '—'}</div>
        </div>
        <div>
          <div class="stat-label">Indexed</div>
          <div style="font-size:20px;font-weight:700;color:var(--accent2);">${run.indexed_document_count ?? '—'}</div>
        </div>
      </div>

      ${progressBar(run.discovered_document_count, run.indexed_document_count)}
      ${stopBtn}
    </div>`;
}

// ── Mount / unmount ──────────────────────────────────────────
let _pollTimer = null;

export function mount(container) {
  container.innerHTML = TEMPLATE;
  load();

  // Auto-refresh every 60 s while the tab is visible
  _pollTimer = setInterval(load, 60000);
}

export function unmount() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

// ── Data loading ─────────────────────────────────────────────
async function load() {
  clearError();
  try {
    const data = await api.get('/runs/list');
    render(data.runs || []);
  } catch(e) {
    showError('Could not load runs: ' + e.message);
    document.getElementById('runsContainer').innerHTML =
      '<div class="empty-state">Could not load runs.</div>';
  }
}

function render(runs) {
  const container = document.getElementById('runsContainer');
  if (!container) return;                       // tab was unmounted while fetching

  const badge      = document.getElementById('runsBadge');
  const stopAllBtn = document.getElementById('stopAllBtn');

  badge.textContent = runs.length + ' run' + (runs.length !== 1 ? 's' : '');

  const activeRuns = runs.filter(r => r.status === 'running' || r.status === 'starting');
  stopAllBtn.style.display = activeRuns.length ? '' : 'none';

  if (!runs.length) {
    container.innerHTML = '<div class="empty-state">No indexing runs found.</div>';
    return;
  }

  // Sort: running first, then by updated_at desc
  const sorted = [...runs].sort((a, b) => {
    const aActive = a.status === 'running' || a.status === 'starting' ? 1 : 0;
    const bActive = b.status === 'running' || b.status === 'starting' ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    return new Date(b.updated_at) - new Date(a.updated_at);
  });

  container.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px;">${sorted.map(renderRun).join('')}</div>`;

  // Wire stop buttons
  container.querySelectorAll('.stop-run-btn').forEach(btn => {
    btn.addEventListener('click', () => stopRun(btn.dataset.id, btn));
  });

  stopAllBtn.onclick = stopAll;
}

// ── Actions ──────────────────────────────────────────────────
async function stopRun(runId, btn) {
  btn.disabled = true;
  btn.textContent = '…';
  try {
    await api.post(`/runs/request_stop/${runId}`);
    await load();
  } catch(e) {
    showError('Could not stop run: ' + e.message);
    btn.disabled = false;
    btn.textContent = '⏹ Stop';
  }
}

async function stopAll() {
  const btn = document.getElementById('stopAllBtn');
  btn.disabled = true;
  btn.textContent = '…';
  try {
    await api.post('/runs/stop_all');
    await load();
  } catch(e) {
    showError('Could not stop all runs: ' + e.message);
  }
  btn.disabled = false;
  btn.textContent = '⏹ Stop All';
}
