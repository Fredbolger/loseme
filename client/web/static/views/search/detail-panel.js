// ============================================================
// FILE: client/web/static/views/search/detail-panel.js
// Slide-in Document Detail Panel - FIXED
// ============================================================

import { openPreview } from '../../previews/index.js';

// ── State ──
let currentDocuments = [];
let currentIndex = -1;
let isOpen = false;
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
      <button class="detail-close-btn" id="detailCloseBtn">✕</button>
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
  `;
  document.body.appendChild(panel);

  // Bind events
  document.getElementById('detailCloseBtn').addEventListener('click', closeDetail);
  document.getElementById('detailPrevBtn').addEventListener('click', () => navigateDetail(-1));
  document.getElementById('detailNextBtn').addEventListener('click', () => navigateDetail(1));

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
    closeDetail();
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    navigateDetail(-1);
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    navigateDetail(1);
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
  
  document.body.style.overflow = '';
}

// ── Clean up panel (called on unmount) ──
export function cleanupDetail() {
  if (overlay && overlay.parentNode) {
    overlay.parentNode.removeChild(overlay);
  }
  if (panel && panel.parentNode) {
    panel.parentNode.removeChild(panel);
  }
  overlay = null;
  panel = null;
  isOpen = false;
  
  document.removeEventListener('keydown', handleKeydown);
  document.body.style.overflow = '';
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
