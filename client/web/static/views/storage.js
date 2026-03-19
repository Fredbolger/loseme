import { api, showError, clearError } from '../app.js';

let activeChunker = 'all';
let allStats = [];

const TEMPLATE = `
  <div class="section">
    <div class="section-header"><h2>Storage Overview</h2></div>
    <div class="stats-row" id="storageStatCards"></div>

    <div class="section-header" style="margin-top:24px;"><h2>By Chunker</h2></div>
    <div class="runs-toolbar" style="margin-bottom:20px;">
      <div class="runs-toolbar-group">
        <label class="runs-toolbar-label">Filter</label>
        <div class="view-toggle" id="chunkerFilter"></div>
      </div>
    </div>
    <div id="chunkerTable"><div class="loading"><div class="spinner"></div> Loading…</div></div>

    <div class="section-header" style="margin-top:32px;"><h2>Distributions</h2></div>
    <div id="histogramsSection"><div class="loading"><div class="spinner"></div> Loading…</div></div>
  </div>
`;

export function mount(container) {
  container.innerHTML = TEMPLATE;
  activeChunker = 'all';
  load();
}

export function unmount() {}

async function load() {
  clearError();
  try {
    const [chunkerResp, totalResp] = await Promise.all([
      api.get('/documents/stats/chunker'),
      api.get('/chunks/number_of_chunks'),
    ]);

    allStats = chunkerResp.stats || [];
    const totalChunks = totalResp.number_of_chunks ?? '—';
    const totalParts = allStats.reduce((s, r) => s + (r.document_part_count ?? 0), 0);

    renderStatCards(totalParts, totalChunks, allStats.length);
    renderChunkerFilter(allStats);
    renderTable(allStats);
    await loadHistograms();
  } catch(e) {
    showError('Could not load storage stats.');
    console.error(e);
  }
}

function renderStatCards(totalParts, totalChunks, chunkerCount) {
  document.getElementById('storageStatCards').innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Document Parts</div>
      <div class="stat-value accent">${totalParts.toLocaleString()}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total Chunks</div>
      <div class="stat-value green">${typeof totalChunks === 'number' ? totalChunks.toLocaleString() : totalChunks}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Chunker Versions</div>
      <div class="stat-value">${chunkerCount}</div>
    </div>
  `;
}

function renderChunkerFilter(stats) {
  const filter = document.getElementById('chunkerFilter');
  const chunkers = ['all', ...new Set(stats.map(r => r.chunker_name ?? 'unknown'))];

  filter.innerHTML = chunkers.map(c => `
    <button class="view-btn ${c === activeChunker ? 'active' : ''}" data-chunker="${c}">
      ${c === 'all' ? 'All' : c}
    </button>
  `).join('');

  filter.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
      activeChunker = btn.dataset.chunker;
      filter.querySelectorAll('.view-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.chunker === activeChunker));
      renderTable(allStats);
      loadHistograms(); // reload histograms for selected chunker
    }); 
  });
}

function renderTable(stats) {
  const filtered = activeChunker === 'all'
    ? stats
    : stats.filter(r => (r.chunker_name ?? 'unknown') === activeChunker);

  const totalParts = filtered.reduce((s, r) => s + (r.document_part_count ?? 0), 0);

  const rows = filtered.map(r => {
    const pct = totalParts > 0
      ? ((r.document_part_count / totalParts) * 100).toFixed(1)
      : 0;
    const name = r.chunker_name ?? '<null>';
    const version = r.chunker_version ?? '<null>';
    return `
      <tr>
        <td><span class="source-type-tag">${name}</span></td>
        <td><span class="badge">${version}</span></td>
        <td>${r.document_part_count.toLocaleString()}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="flex:1;background:var(--surface2);border-radius:4px;height:6px;overflow:hidden;">
              <div style="width:${pct}%;background:var(--accent);height:100%;border-radius:4px;"></div>
            </div>
            <span style="font-size:11px;color:var(--muted);min-width:36px;">${pct}%</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  document.getElementById('chunkerTable').innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="font-size:10px;font-family:'Space Mono',monospace;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);">
          <th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);">Chunker</th>
          <th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);">Version</th>
          <th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);">Document Parts</th>
          <th style="text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);min-width:160px;">Share</th>
        </tr>
      </thead>
      <tbody>${rows || '<tr><td colspan="4" style="padding:20px;color:var(--muted);text-align:center;">No data</td></tr>'}</tbody>
    </table>
  `;
}

async function loadHistograms() {
  const url = activeChunker === 'all'
    ? '/chunks/stats/distribution'
    : `/chunks/stats/distribution?chunker_name=${encodeURIComponent(activeChunker)}`;

  document.getElementById('histogramsSection').innerHTML =
    '<div class="loading"><div class="spinner"></div> Loading histograms…</div>';

  try {
    const data = await api.get(url);
    renderHistograms(data);
  } catch(e) {
    document.getElementById('histogramsSection').innerHTML =
      '<div class="empty-state">Could not load histogram data.</div>';
  }
}

function renderHistograms(data) {
  const { char_len_histogram, chunks_per_doc_histogram, stats } = data;

  document.getElementById('histogramsSection').innerHTML = `
    <div class="stats-row" style="margin-bottom:20px;">
      ${stats.count ? `
        <div class="stat-card"><div class="stat-label">Chunks</div><div class="stat-value accent">${stats.count.toLocaleString()}</div></div>
        <div class="stat-card"><div class="stat-label">Mean size</div><div class="stat-value">${stats.mean} chars</div></div>
        <div class="stat-card"><div class="stat-label">p50</div><div class="stat-value">${stats.p50} chars</div></div>
        <div class="stat-card"><div class="stat-label">p95</div><div class="stat-value green">${stats.p95} chars</div></div>
        <div class="stat-card"><div class="stat-label">Max</div><div class="stat-value">${stats.max.toLocaleString()} chars</div></div>
      ` : '<div style="color:var(--muted);padding:12px;">No char_len data available.</div>'}
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <div class="section" style="padding:16px;">
        <div class="section-header"><h2>Chunk size distribution</h2></div>
        ${renderBarChart(char_len_histogram)}
      </div>
      <div class="section" style="padding:16px;">
        <div class="section-header"><h2>Chunks per document</h2></div>
        ${renderBarChart(chunks_per_doc_histogram)}
      </div>
    </div>
  `;
}

function renderBarChart(buckets) {
  if (!buckets || !buckets.length) return '<div style="color:var(--muted);">No data</div>';
  const max = Math.max(...buckets.map(b => b.count), 1);
  return `
    <div style="display:flex;flex-direction:column;gap:6px;margin-top:12px;">
      ${buckets.map(b => `
        <div style="display:flex;align-items:center;gap:8px;font-size:12px;font-family:'Space Mono',monospace;">
          <span style="width:72px;text-align:right;color:var(--muted);flex-shrink:0;">${b.label}</span>
          <div style="flex:1;background:var(--surface2);border-radius:3px;height:18px;overflow:hidden;">
            <div style="width:${(b.count/max*100).toFixed(1)}%;background:var(--accent);height:100%;border-radius:3px;transition:width 0.3s;"></div>
          </div>
          <span style="width:48px;color:var(--muted);">${b.count.toLocaleString()}</span>
        </div>
      `).join('')}
    </div>
  `;
}
