// ============================================================
// FILE: client/web/static/views/search/detail-panel.js
// Slide-in Document Detail Panel - FIXED
// ============================================================

import { openPreview } from '../../previews/index.js';
import { api } from '../../app.js';

// ── State ──
let currentDocuments = [];
let currentIndex = -1;
let isOpen = false;
let chunksPreviewOpen = false;
let currentChunks = [];
let currentChunkIndex = -1;
let overlay = null;
let panel = null;

// ── Create Panel (lazy init) ──
function createPanel() {
  if (panel) return;

  // Overlay
  overlay = document.createElement('div');
  overlay.className = 'detail-overlay';
  overlay.addEventListener('click', closeDetail);
  document.body.appendChild(overlay);

  // Panel
  panel = document.createElement('div');
  panel.className = 'detail-panel';
  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-header-left">
        <span class="icon">📄</span>
        <span class="detail-title" id="detailTitle">Document</span>
      </div>
      <div class="detail-header-right">
        <div class="detail-toggle-container">
          <label class="detail-toggle-switch">
            <input type="checkbox" id="chunksToggleCheckbox" class="detail-toggle-checkbox">
            <span class="detail-toggle-slider"></span>
          </label>
          <span class="detail-toggle-label">Chunks</span>
        </div>
        <button class="detail-close-btn" id="detailCloseBtn">✕</button>
      </div>
    </div>
    <div class="detail-meta" id="detailMeta">
      <span class="detail-meta-item">
        <span class="label">Path:</span>
        <span class="value" id="detailPath">—</span>
      </span>
      <span class="detail-meta-item">
        <span class="label">Type:</span>
        <span class="value" id="detailType">—</span>
      </span>
      <span class="detail-meta-item">
        <span class="label">Chunks:</span>
        <span class="value" id="detailChunks">—</span>
      </span>
    </div>
    <div class="detail-body" id="detailBody">
      <div class="preview-loading">
        <div class="spinner"></div>
        <span>Loading document...</span>
      </div>
    </div>
    <div class="detail-nav">
      <span class="detail-nav-info" id="detailNavInfo">1 / 1</span>
      <div class="detail-nav-buttons">
        <button class="detail-nav-btn" id="detailPrevBtn">← Previous</button>
        <button class="detail-nav-btn" id="detailNextBtn">Next →</button>
      </div>
    </div>
    <div class="chunks-preview-panel" id="chunksPreviewPanel">
      <div class="chunks-preview-header">
        <div class="chunks-preview-header-left">
          <h4>Chunks Preview</h4>
        </div>
        <button class="chunks-preview-close-btn" id="chunksPreviewCloseBtn">✕</button>
      </div>
      <div class="chunks-preview-body" id="chunksPreviewBody">
        <div class="chunks-loading">Loading chunks...</div>
      </div>
      <div class="chunks-preview-nav" id="chunksPreviewNav">
        <span class="chunk-nav-info" id="chunkNavInfo">1 / 1</span>
        <div class="chunk-nav-buttons">
          <button class="chunk-nav-btn" id="chunkPrevBtn">← Previous</button>
          <button class="chunk-nav-btn" id="chunkNextBtn">Next →</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(panel);

  // Bind events
  document.getElementById('detailCloseBtn').addEventListener('click', closeDetail);
  document.getElementById('detailPrevBtn').addEventListener('click', () => navigateDetail(-1));
  document.getElementById('detailNextBtn').addEventListener('click', () => navigateDetail(1));
  document.getElementById('chunksToggleCheckbox').addEventListener('change', (e) => {
    toggleChunksPreview(e.target.checked);
  });
  document.getElementById('chunksPreviewCloseBtn').addEventListener('click', () => {
    toggleChunksPreview(false);
  });
  document.getElementById('chunkPrevBtn').addEventListener('click', () => navigateChunks(-1));
  document.getElementById('chunkNextBtn').addEventListener('click', () => navigateChunks(1));

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeydown);
}

// ── Handle keyboard shortcuts ──
function handleKeydown(e) {
  if (!isOpen) return;
  
  // Don't trigger if typing in an input
  const target = e.target;
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
    return;
  }
  
  if (e.key === 'Escape') {
    e.preventDefault();
    if (chunksPreviewOpen) {
      toggleChunksPreview(false);
    } else {
      closeDetail();
    }
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    if (chunksPreviewOpen) {
      navigateChunks(-1);
    } else {
      navigateDetail(-1);
    }
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    if (chunksPreviewOpen) {
      navigateChunks(1);
    } else {
      navigateDetail(1);
    }
  } else if (e.key === 'c' && e.ctrlKey) {
    e.preventDefault();
    toggleChunksPreview(!chunksPreviewOpen);
  }
}

// ── Toggle Chunks Preview ──
function toggleChunksPreview(forceState) {
  const panel = document.getElementById('chunksPreviewPanel');
  const checkbox = document.getElementById('chunksToggleCheckbox');
  
  if (!panel || !checkbox) return;
  
  // Determine new state
  const newState = typeof forceState === 'boolean' ? forceState : !chunksPreviewOpen;
  chunksPreviewOpen = newState;
  checkbox.checked = chunksPreviewOpen;
  
  // Update panel visibility - use display property for instant show/hide
  panel.style.display = chunksPreviewOpen ? 'flex' : 'none';
  
  // If opening and we have a current document, load chunks
  if (chunksPreviewOpen && currentDocuments.length > 0) {
    const doc = currentDocuments[currentIndex];
    if (doc) {
      loadChunksForDocument(doc.document_part_id);
    }
  }
}

// ── Open Detail ──
export function openDetail(docId, sources, sourceType, sourcePath) {
  createPanel();

  // Store documents for navigation
  currentDocuments = sources || [];
  currentIndex = currentDocuments.findIndex(d => d.document_part_id === docId);
  if (currentIndex === -1 && sources && sources.length > 0) {
    currentIndex = 0;
  }
  if (currentIndex === -1) {
    // Single document, no navigation
    currentDocuments = [{ document_part_id: docId, source_type: sourceType, source_path: sourcePath }];
    currentIndex = 0;
  }

  // Update UI
  isOpen = true;
  overlay.classList.add('open');
  panel.classList.add('open');
  
  // Shift main content left
  const searchMain = document.querySelector('.search-main');
  const sourcesMain = document.querySelector('.sources-main');
  
  if (searchMain) {
    searchMain.classList.add('detail-panel-open');
  }
  if (sourcesMain) {
    sourcesMain.classList.add('detail-panel-open');
  }
  
  document.body.style.overflow = 'hidden';

  // Load document
  loadDetail(docId, sourceType, sourcePath);
}

// ── Close Detail ──
export function closeDetail() {
  if (!isOpen) return;
  
  isOpen = false;
  
  if (overlay) {
    overlay.classList.remove('open');
  }
  if (panel) {
    panel.classList.remove('open');
  }
  
  // Shift main content back to original position
  const searchMain = document.querySelector('.search-main');
  const sourcesMain = document.querySelector('.sources-main');
  
  if (searchMain) {
    searchMain.classList.remove('detail-panel-open');
  }
  if (sourcesMain) {
    sourcesMain.classList.remove('detail-panel-open');
  }
  
  document.body.style.overflow = '';
}

// ── Utility Functions ──
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Clean up panel (called on unmount) ──
export function cleanupDetail() {
  // Reset main content position if needed
  const searchMain = document.querySelector('.search-main');
  const sourcesMain = document.querySelector('.sources-main');
  
  if (searchMain) {
    searchMain.classList.remove('detail-panel-open');
  }
  if (sourcesMain) {
    sourcesMain.classList.remove('detail-panel-open');
  }
  
  if (overlay && overlay.parentNode) {
    overlay.parentNode.removeChild(overlay);
  }
  if (panel && panel.parentNode) {
    panel.parentNode.removeChild(panel);
  }
  overlay = null;
  panel = null;
  isOpen = false;
  chunksPreviewOpen = false;
  currentChunks = [];
  currentChunkIndex = -1;
  
  document.removeEventListener('keydown', handleKeydown);
  document.body.style.overflow = '';
}

// ── Load Chunks for Document ──
async function loadChunksForDocument(docId) {
  const body = document.getElementById('chunksPreviewBody');
  const navInfo = document.getElementById('chunkNavInfo');
  
  if (!body || !navInfo) return;
  
  // Show loading
  body.innerHTML = '<div class="chunks-loading"><div class="spinner"></div><span>Loading chunks...</span></div>';
  
  try {
    // API call to get chunks for this document
    const data = await api.get(`/documents/${docId}/chunks`);
    currentChunks = data.chunks || [];
    currentChunkIndex = 0;
    
    if (currentChunks.length === 0) {
      body.innerHTML = '<div class="chunks-empty">No chunks found for this document</div>';
      navInfo.textContent = '0 / 0';
      return;
    }
    
    // Update navigation
    navInfo.textContent = `${currentChunkIndex + 1} / ${currentChunks.length}`;
    
    // Show first chunk
    renderChunk(currentChunkIndex);
    
    // Update navigation buttons
    document.getElementById('chunkPrevBtn').disabled = currentChunkIndex <= 0;
    document.getElementById('chunkNextBtn').disabled = currentChunkIndex >= currentChunks.length - 1;
    
  } catch (e) {
    body.innerHTML = `<div class="chunks-error">Failed to load chunks: ${e.message}</div>`;
    navInfo.textContent = 'Error';
  }
}

// ── Render Individual Chunk ──
function renderChunk(index) {
  const chunk = currentChunks[index];
  if (!chunk) return;
  
  const body = document.getElementById('chunksPreviewBody');
  if (!body) return;
  
  body.innerHTML = `
    <div class="chunk-container">
      <div class="chunk-header">
        <span class="chunk-index">Chunk #${index + 1}</span>
        ${chunk.metadata?.char_len ? `<span class="chunk-length">${chunk.metadata.char_len} characters</span>` : ''}
      </div>
      <div class="chunk-content">
        <pre>${escapeHtml(chunk.text || chunk.content || 'No content')}</pre>
      </div>
      ${chunk.metadata?.unit_locator ? `<div class="chunk-meta">Unit: ${chunk.metadata.unit_locator}</div>` : ''}
    </div>
  `;
}

// ── Navigate Chunks ──
function navigateChunks(direction) {
  if (currentChunks.length <= 1) return;
  
  const newIndex = currentChunkIndex + direction;
  if (newIndex < 0 || newIndex >= currentChunks.length) return;
  
  currentChunkIndex = newIndex;
  renderChunk(currentChunkIndex);
  
  // Update navigation info
  const navInfo = document.getElementById('chunkNavInfo');
  if (navInfo) {
    navInfo.textContent = `${currentChunkIndex + 1} / ${currentChunks.length}`;
  }
  
  // Update navigation buttons
  document.getElementById('chunkPrevBtn').disabled = currentChunkIndex <= 0;
  document.getElementById('chunkNextBtn').disabled = currentChunkIndex >= currentChunks.length - 1;
}

// ── Load Document ──
async function loadDetail(docId, sourceType, sourcePath) {
  const body = document.getElementById('detailBody');
  const title = document.getElementById('detailTitle');
  const path = document.getElementById('detailPath');
  const type = document.getElementById('detailType');
  const chunks = document.getElementById('detailChunks');
  const navInfo = document.getElementById('detailNavInfo');

  // Update meta
  const fileName = (sourcePath || docId || '').split(/[/\\]/).pop() || 'Document';
  title.textContent = fileName;
  path.textContent = sourcePath || '—';
  type.textContent = sourceType || '—';
  chunks.textContent = 'Loading...';

  // Update navigation
  const total = currentDocuments.length;
  if (total > 1) {
    navInfo.textContent = `${currentIndex + 1} / ${total}`;
    document.getElementById('detailPrevBtn').style.display = '';
    document.getElementById('detailNextBtn').style.display = '';
  } else {
    navInfo.textContent = '';
    document.getElementById('detailPrevBtn').style.display = 'none';
    document.getElementById('detailNextBtn').style.display = 'none';
  }
  
  document.getElementById('detailPrevBtn').disabled = currentIndex <= 0;
  document.getElementById('detailNextBtn').disabled = currentIndex >= total - 1;

  // Show loading
  body.innerHTML = `
    <div class="preview-loading">
      <div class="spinner"></div>
      <span>Loading document...</span>
    </div>
  `;

  try {
    // Load preview using existing openPreview
    await openPreview(body, docId, sourceType || 'filesystem', sourcePath || '');
    
    // Try to get chunks count from the document if available
    try {
      // We'll add a better way to get chunk count later
      chunks.textContent = '—';
    } catch {
      chunks.textContent = '—';
    }

  } catch (e) {
    body.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:var(--space-md);color:var(--text-tertiary);padding:var(--space-xl);text-align:center;">
        <span style="font-size:32px;">⚠️</span>
        <span>Failed to load document: ${e.message}</span>
      </div>
    `;
  }
}

// ── Navigate ──
function navigateDetail(direction) {
  if (currentDocuments.length <= 1) return;
  
  const newIndex = currentIndex + direction;
  if (newIndex < 0 || newIndex >= currentDocuments.length) return;

  const doc = currentDocuments[newIndex];
  if (!doc) return;

  currentIndex = newIndex;
  loadDetail(
    doc.document_part_id,
    doc.source_type || 'filesystem',
    doc.source_path || ''
  );
}

// ── Open from source chip ──
export function openDetailFromChip(docId, sources) {
  // Find the document in sources
  const doc = sources.find(s => s.document_part_id === docId);
  if (!doc) {
    // Try to find by ID only
    openDetail(docId, sources, 'filesystem', '');
    return;
  }

  openDetail(
    docId,
    sources,
    doc.source_type || 'filesystem',
    doc.source_path || ''
  );
}
