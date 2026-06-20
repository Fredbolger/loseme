import { api, fmtDate, showError, clearError, getClientBase } from '../app.js';

// ── HTML template ────────────────────────────────────────────
const TEMPLATE = `
  <!-- Stats Dashboard with Professional Tile Layout -->
  <div class="dashboard-stats">
    <div class="stats-grid">
      <div class="stat-tile">
        <div class="stat-tile-content">
          <div class="stat-label">Document Parts</div>
          <div class="stat-value accent" id="statDocs">—</div>
          <div class="stat-icon">📄</div>
        </div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-content">
          <div class="stat-label">Total Chunks</div>
          <div class="stat-value green" id="statChunks">—</div>
          <div class="stat-icon">🧩</div>
        </div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-content">
          <div class="stat-label">Source Instances</div>
          <div class="stat-value" id="statSources">—</div>
          <div class="stat-icon">📁</div>
        </div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-content">
          <div class="stat-label">Devices</div>
          <div class="stat-value" id="statDevices">—</div>
          <div class="stat-icon">📱</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Sources Section with Professional Tile Layout -->
  <div class="dashboard-section">
    <div class="section-header">
      <h2>Sources</h2>
      <span class="badge" id="sourcesBadge">—</span>
    </div>
    <div class="sources-tile-grid" id="sourcesGrid">
      <div class="loading-spinner"></div>
      <div class="loading-text">Loading sources...</div>
    </div>
  </div>
`;

// ── Mount / unmount ──────────────────────────────────────────
export function mount(container) {
  container.innerHTML = TEMPLATE;
  load();
}

export function unmount() {}

// ── Data loading ─────────────────────────────────────────────
async function load() {
  clearError();
  try {
    await Promise.all([loadStats(), loadSources()]);
  } catch (e) {
    showError('Could not reach API. Check the URL and ensure the server is running.');
    console.error(e);
  }
}

async function loadStats() {
  const [stats, chunks] = await Promise.all([
    api.get('/documents/stats'),
    api.get('/chunks/number_of_chunks'),
  ]);

  document.getElementById('statDocs').textContent =
    stats.total_document_parts ?? '—';
  document.getElementById('statSources').textContent =
    stats.total_sources ?? '—';
  document.getElementById('statDevices').textContent =
    stats.total_devices ?? '—';
  document.getElementById('statChunks').textContent =
    chunks.number_of_chunks ?? '—';
}

async function loadSources() {
  const grid = document.getElementById('sourcesGrid');

  try {
    const [sourcesResp, perSourceResp] = await Promise.all([
      api.get('/sources/get_all_sources'),
      api.get('/documents/stats/per_source'),
    ]);

    const sources = sourcesResp.sources || [];
    const stats = perSourceResp.stats_per_source || [];

    // Build lookup map: source_id -> document_part_count
    const statsMap = {};
    stats.forEach(s => {
      statsMap[s.source_id] = s.document_part_count ?? 0;
    });

    renderSources(sources, statsMap);

  } catch (e) {
    console.error(e);
    grid.innerHTML = '<div class="empty-state">Could not load sources.</div>';
  }
}

// ── Helpers ─────────────────────────────────────────────────
function getSourceLoc(s) {
  const scope = typeof s.scope === 'string'
    ? JSON.parse(s.scope)
    : (s.scope || {});
  return s.locator || scope.locator || scope.directories?.[0] || scope.mbox_path || '';
}

function getSourceType(s) {
  const scope = typeof s.scope === 'string'
    ? JSON.parse(s.scope)
    : (s.scope || {});
  return s.source_type || scope.type || 'unknown';
}

function getSourceId(s) {
  return s.source_instance_id || s.id;
}

function getSourceDeviceId(s) {
    return s.device_id || "-";
    }

function pathParts(p) {
  return p.replace(/\\/g, '/').split('/').filter(Boolean);
}

function longestCommonPrefix(locs) {
  if (!locs.length) return [];
  const segs = locs.map(pathParts);
  const ref = segs[0];
  let i = 0;
  while (i < ref.length && segs.every(s => s[i] === ref[i])) i++;
  return ref.slice(0, i);
}

// ── Tree building ───────────────────────────────────────────
function buildTree(sources) {
  if (sources.length === 0) return [];
  if (sources.length === 1)
    return [{ type: 'leaf', source: sources[0] }];

  const locs = sources.map(s => s._loc);
  const common = longestCommonPrefix(locs);

  const buckets = {};
  const order = [];

  sources.forEach(s => {
    const parts = pathParts(s._loc);
    const next = parts[common.length];

    const key = next || s._loc;

    if (!buckets[key]) {
      buckets[key] = [];
      order.push(key);
    }
    buckets[key].push(s);
  });

  const nodes = [];

  order.forEach(key => {
    const members = buckets[key];

    if (members.length === 1) {
      nodes.push({ type: 'leaf', source: members[0] });
    } else {
      const prefix =
        '/' + longestCommonPrefix(members.map(s => s._loc)).join('/');

      nodes.push({
        type: 'group',
        label: prefix,
        children: buildTree(members),
      });
    }
  });

  return nodes;
}

// ── Counting helpers ────────────────────────────────────────
function countLeaves(node) {
  if (node.type === 'leaf') return 1;
  return node.children.reduce((acc, c) => acc + countLeaves(c), 0);
}

function countDocs(node) {
  if (node.type === 'leaf') return node.source._docCount || 0;
  return node.children.reduce((acc, c) => acc + countDocs(c), 0);
}

// ── Rendering ───────────────────────────────────────────────
let _treeId = 0;

function renderNode(node, depth) {
  if (node.type === 'leaf') {
    const s = node.source;

    return `
      <div class="source-tile" style="margin-left:${depth * 20}px">
        <div class="source-tile-content">
          <div class="source-tile-header">
            <span class="source-type-tag ${s._type}">${s._type}</span>
            <span class="source-doc-count">${s._docCount} doc${s._docCount !== 1 ? 's' : ''}</span>
          </div>

          <div class="source-tile-body">
            <div class="source-path">${s._loc || '—'}</div>
            <div class="source-meta">
              <span class="source-id">${getSourceId(s)}</span>
              <span class="source-device">📱 ${getSourceDeviceId(s)}</span>
            </div>
          </div>

          <div class="source-tile-footer">
            <div class="source-status">
              <span class="dot ${s.enabled !== false ? 'green' : 'muted'}"></span>
              ${s.enabled !== false ? 'Active' : 'Disabled'}
            </div>
            ${s.last_ingested_at ? '<div class="source-updated">↺ ' + fmtDate(s.last_ingested_at) + '</div>' : ''}
          </div>

          <div class="source-tile-actions">
            <button class="btn btn-sm scan-source-btn" data-id="${s.id}">↺ Scan</button>
            <button class="btn btn-sm btn-delete" data-id="${s.id}">🗑 Delete</button>
          </div>
        </div>
      </div>
    `;
  }

  const id = 'grp' + (_treeId++);
  const leafCount = countLeaves(node);
  const docCount = countDocs(node);
  const childHtml = node.children.map(c => renderNode(c, depth + 1)).join('');

  return `
    <div class="source-tree-item">
      <div class="source-tile has-children"
           style="margin-left:${depth * 20}px"
           onclick="document.getElementById('children-${id}').classList.toggle('open');
                    document.getElementById('chevron-${id}').classList.toggle('open')">

        <div class="source-tile-content">
          <span class="source-chevron" id="chevron-${id}">▶</span>
          <div class="source-tile-header">
            <span class="source-group-badge">
              ${leafCount} source${leafCount !== 1 ? 's' : ''}
            </span>
          </div>

          <div class="source-tile-body">
            <div class="source-group-path">
              <span>${node.label}/</span>
              <span class="source-group-doc-count">
                ${docCount} doc${docCount !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="source-children"
           id="children-${id}"
           style="margin-left:${depth * 20 + 12}px">
        ${childHtml}
      </div>
    </div>
  `;
}

function renderSources(sources, statsMap = {}) {
  const grid = document.getElementById('sourcesGrid');

  document.getElementById('sourcesBadge').textContent =
    sources.length + ' source' + (sources.length !== 1 ? 's' : '');

  if (!sources.length) {
    grid.innerHTML =
      '<div class="empty-state">No monitored sources found.</div>';
    return;
  }

  _treeId = 0;

  const withLoc = sources.map(s => ({
    ...s,
    _loc: getSourceLoc(s),
    _type: getSourceType(s),
    _docCount: statsMap[getSourceId(s)] ?? 0,
  }));

  const tree = buildTree(withLoc);

  grid.innerHTML = tree.map(n => renderNode(n, 0)).join('');

  grid.querySelectorAll('.scan-source-btn').forEach(btn => {
    btn.addEventListener('click', () =>
      scanSource(btn.dataset.id, btn)
    );
  });
  
  grid.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () =>
      deleteSource(btn.dataset.id, btn)
    );
 });
}

function askForce() {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:9999';
    overlay.innerHTML = `
      <div style="background:white;padding:24px;border-radius:8px;max-width:360px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.2)">
        <p style="margin:0 0 20px;font-size:15px">Re-index already processed documents?</p>
        <div style="display:flex;gap:12px;justify-content:center">
          <button id="force-yes" style="padding:8px 20px;background:#e53e3e;color:white;border:none;border-radius:6px;cursor:pointer">Yes, force re-index</button>
          <button id="force-no" style="padding:8px 20px;background:#eee;border:none;border-radius:6px;cursor:pointer">No, skip unchanged</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('#force-yes').onclick = () => { document.body.removeChild(overlay); resolve(true); };
    overlay.querySelector('#force-no').onclick  = () => { document.body.removeChild(overlay); resolve(false); };
  });
}

async function scanSource(sourceId, btn) {
  const force = await askForce();

  btn.disabled = true;
  btn.textContent = '…';
  try {
    const res = await fetch(`${getClientBase()}/sources/scan/${sourceId}?force_reprocess=${force}`, { method: 'POST' });
    if (res.status === 403) {
      const data = await res.json();
      showError(data.detail || 'Cannot scan source that belongs to another device');
      btn.disabled = false;
      btn.textContent = '↺ Scan';
      return;
    }
    btn.textContent = force ? '✓ Queued (forced)' : '✓ Queued';
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = '↺ Scan';
    }, 3000);
  } catch (e) {
    showError('Could not start scan: ' + e.message);
    btn.disabled = false;
    btn.textContent = '↺ Scan';
  }
}

async function deleteSource(sourceId, btn) {
  if (!confirm('Are you sure you want to delete this source?...')) return;

  btn.disabled = true;
  btn.textContent = '…';

  try {
    await api.get(`/sources/delete/${sourceId}?dry_run=false&confirm=true`);
    load(); // refresh the sources list
  } catch (e) {
    showError('Could not delete source: ' + e.message);
    btn.disabled = false;
    btn.textContent = '🗑 Delete';
  }
}
