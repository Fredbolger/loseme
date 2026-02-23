import { api, fmtDate, showError, clearError } from '../app.js';

// ── HTML template ────────────────────────────────────────────
const TEMPLATE = `
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">Document Parts</div>
      <div class="stat-value accent" id="statDocs">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total Chunks</div>
      <div class="stat-value green" id="statChunks">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Source Instances</div>
      <div class="stat-value" id="statSources">—</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Devices</div>
      <div class="stat-value" id="statDevices">—</div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2>Sources</h2>
      <span class="badge" id="sourcesBadge">—</span>
    </div>
    <div class="sources-grid" id="sourcesGrid">
      <div class="loading"><div class="spinner"></div> Loading…</div>
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
  } catch(e) {
    showError('Could not reach API. Check the URL and ensure the server is running.');
    console.error(e);
  }
}

async function loadStats() {
  const [stats, chunks] = await Promise.all([
    api.get('/documents/stats'),
    api.get('/chunks/number_of_chunks'),
  ]);
  document.getElementById('statDocs').textContent    = stats.total_document_parts   ?? '—';
  document.getElementById('statSources').textContent = stats.total_sources  ?? '—';
  document.getElementById('statDevices').textContent = stats.total_devices  ?? '—';
  document.getElementById('statChunks').textContent  = chunks.number_of_chunks ?? '—';
}

async function loadSources() {
  const grid = document.getElementById('sourcesGrid');
  try {
    const d = await api.get('/sources/get_all_sources');
    renderSources(d.sources || []);
  } catch {
    grid.innerHTML = '<div class="empty-state">Could not load sources.</div>';
  }
}

// ── Sources tree ─────────────────────────────────────────────
function getSourceLoc(s) {
  const scope = typeof s.scope === 'string' ? JSON.parse(s.scope) : (s.scope || {});
  return scope.locator || scope.directories?.[0] || scope.mbox_path || '';
}

function getSourceType(s) {
  const scope = typeof s.scope === 'string' ? JSON.parse(s.scope) : (s.scope || {});
  return s.source_type || scope.type || 'unknown';
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

function buildTree(sources) {
  if (sources.length === 0) return [];
  if (sources.length === 1) return [{ type: 'leaf', source: sources[0] }];

  const locs = sources.map(s => s._loc);
  const common = longestCommonPrefix(locs);

  const buckets = {};
  const bucketOrder = [];
  sources.forEach(s => {
    const parts = pathParts(s._loc);
    const next = parts[common.length];
    if (!next) {
      const key = s._loc;
      if (!buckets[key]) { buckets[key] = []; bucketOrder.push(key); }
      buckets[key].push(s);
    } else {
      if (!buckets[next]) { buckets[next] = []; bucketOrder.push(next); }
      buckets[next].push(s);
    }
  });

  const nodes = [];
  bucketOrder.forEach(key => {
    const members = buckets[key];
    if (members.length === 1) {
      nodes.push({ type: 'leaf', source: members[0] });
    } else {
      const prefix = '/' + longestCommonPrefix(members.map(s => s._loc)).join('/');
      nodes.push({ type: 'group', label: prefix, children: buildTree(members) });
    }
  });
  return nodes;
}

function countLeaves(node) {
  if (node.type === 'leaf') return 1;
  return node.children.reduce((acc, c) => acc + countLeaves(c), 0);
}

let _treeId = 0;

function renderNode(node, depth) {
  if (node.type === 'leaf') {
    const s = node.source;
    return `<div class="source-card" style="margin-left:${depth * 20}px">
      <div class="source-card-inner">
        <span style="width:12px;flex-shrink:0"></span>
        <div class="source-card-body">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
            <span class="source-type-tag ${s._type}">${s._type}</span>
          </div>
          <div class="source-path" style="margin-bottom:8px">${s._loc || '—'}</div>
          <div class="source-meta">
            <span><span class="dot ${s.enabled !== false ? 'green' : 'muted'}"></span>${s.enabled !== false ? 'Active' : 'Disabled'}</span>
            ${s.last_ingested_at ? '<span>↺ ' + fmtDate(s.last_ingested_at) + '</span>' : ''}
          </div>
        </div>
      </div>
    </div>`;
  }

  const id = 'grp' + (_treeId++);
  const leafCount = countLeaves(node);
  const childHtml = node.children.map(c => renderNode(c, 0)).join('');

  return `<div class="source-tree-item">
    <div class="source-card has-children" style="margin-left:${depth * 20}px"
         onclick="document.getElementById('children-${id}').classList.toggle('open');document.getElementById('chevron-${id}').classList.toggle('open')">
      <div class="source-card-inner">
        <span class="source-chevron" id="chevron-${id}">▶</span>
        <div class="source-card-body">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span class="badge">${leafCount} source${leafCount !== 1 ? 's' : ''}</span>
          </div>
          <div class="source-path">${node.label}/</div>
        </div>
      </div>
    </div>
    <div class="source-children" id="children-${id}" style="margin-left:${depth * 20 + 12}px">
      ${childHtml}
    </div>
  </div>`;
}

function renderSources(sources) {
  const grid = document.getElementById('sourcesGrid');
  document.getElementById('sourcesBadge').textContent =
    sources.length + ' source' + (sources.length !== 1 ? 's' : '');

  if (!sources.length) {
    grid.innerHTML = '<div class="empty-state">No monitored sources found.</div>';
    return;
  }

  _treeId = 0;
  const withLoc = sources.map(s => ({ ...s, _loc: getSourceLoc(s), _type: getSourceType(s) }));
  const tree = buildTree(withLoc);
  grid.innerHTML = tree.map(n => renderNode(n, 0)).join('');
}
