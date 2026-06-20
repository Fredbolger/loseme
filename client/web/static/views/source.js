// ── Source View ──────────────────────────────────────────────
import { api, getClientBase, showError, clearError } from '../app.js';
import { openPreview } from '../previews/index.js';

let currentSourceId = null;
let selectedDocId = null;
let currentView = 'preview'; // 'preview' | 'chunks' | 'attachments'

// ── DOM refs ──────────────────────────────────────────────────
function getEl(id) { return document.getElementById(id); }

function renderSourceView(app) {
  app.innerHTML = `
    <div class="source-view">
      <div class="source-sidebar">
        <div class="source-header">
          <h2>Sources</h2>
          <button id="refreshSourcesBtn" class="icon-btn">⟳</button>
        </div>
        <div id="sourceList" class="source-list">
          <div class="loading">Loading sources...</div>
        </div>
      </div>
      
      <div class="source-documents">
        <div class="doc-header">
          <h3 id="sourceTitle">Select a source</h3>
          <div class="doc-actions">
            <button id="previewTab" class="tab-btn active">Preview</button>
            <button id="chunksTab" class="tab-btn">Chunks</button>
            <button id="attachmentsTab" class="tab-btn">Attachments</button>
          </div>
        </div>
        
        <div class="doc-content">
          <div id="documentList" class="document-list">
            <div class="empty-state">Select a source to view documents</div>
          </div>
          <div id="documentView" class="document-view">
            <div class="empty-state">Select a document to view</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ── Load Sources ──────────────────────────────────────────────
async function loadSources() {
  try {
    const data = await api.get('/sources/get_all_sources');
    renderSourceList(data.sources);
  } catch (err) {
    showError('Failed to load sources: ' + err.message);
  }
}

function renderSourceList(sources) {
  const list = document.getElementById('sourceList');
  if (!sources || sources.length === 0) {
    list.innerHTML = '<div class="empty-state">No sources found</div>';
    return;
  }
  
  list.innerHTML = sources.map(source => `
    <div class="source-item" data-source-id="${source.id}">
      <div class="source-icon">${getSourceIcon(source.source_type)}</div>
      <div class="source-info">
        <div class="source-name">${source.locator || source.id.slice(0,8)}</div>
        <div class="source-meta">${source.source_type} • ${source.device_id || 'unknown'}</div>
      </div>
      <div class="source-status ${source.enabled ? 'enabled' : 'disabled'}">
        ${source.enabled ? '✓' : '✗'}
      </div>
    </div>
  `).join('');
  
  // Click handlers
  list.querySelectorAll('.source-item').forEach(el => {
    el.addEventListener('click', () => selectSource(el.dataset.sourceId));
  });
  
  // Load first source by default
  if (sources.length > 0 && !currentSourceId) {
    selectSource(sources[0].id);
  }
}

function getSourceIcon(type) {
  const icons = {
    'filesystem': '📁',
    'thunderbird': '📧',
    'url': '🔗'
  };
  return icons[type] || '📄';
}

// ── Select Source ──────────────────────────────────────────────
async function selectSource(sourceId) {
  currentSourceId = sourceId;
  selectedDocId = null;
  
  // Update UI
  document.querySelectorAll('.source-item').forEach(el => {
    el.classList.toggle('active', el.dataset.sourceId === sourceId);
  });
  
  try {
    // Get source details
    const sourceData = await api.get(`/sources/get/${sourceId}`);
    const source = sourceData.source;
    document.getElementById('sourceTitle').textContent = source.locator || source.id.slice(0,8);
    
    // Load documents
    const docsData = await api.get(`/documents/by_source/${sourceId}`);
    renderDocumentList(docsData.documents);
  } catch (err) {
    showError('Failed to load documents: ' + err.message);
  }
}

// ── Render Document List ──────────────────────────────────────
function renderDocumentList(documents) {
  const list = document.getElementById('documentList');
  if (!documents || documents.length === 0) {
    list.innerHTML = '<div class="empty-state">No documents in this source</div>';
    return;
  }
  
  list.innerHTML = documents.map(doc => `
    <div class="document-item" data-doc-id="${doc.document_part_id}">
      <div class="doc-icon">${getDocIcon(doc.content_type)}</div>
      <div class="doc-info">
        <div class="doc-name">${doc.source_path.split('/').pop() || 'Untitled'}</div>
        <div class="doc-meta">${doc.content_type || 'unknown'} • ${doc.chunker_name || 'not chunked'}</div>
      </div>
      <div class="doc-badge ${doc.chunk_ids ? 'chunked' : 'no-chunk'}">
        ${doc.chunk_ids ? (JSON.parse(doc.chunk_ids)?.length || 0) + ' chunks' : 'no chunks'}
      </div>
    </div>
  `).join('');
  
  list.querySelectorAll('.document-item').forEach(el => {
    el.addEventListener('click', () => selectDocument(el.dataset.docId));
  });
  
  // Select first document
  if (documents.length > 0 && !selectedDocId) {
    selectDocument(documents[0].document_part_id);
  }
}

function getDocIcon(contentType) {
  if (!contentType) return '📄';
  if (contentType.includes('pdf')) return '📕';
  if (contentType.includes('email') || contentType.includes('eml')) return '📧';
  if (contentType.includes('text')) return '📝';
  if (contentType.includes('html')) return '🌐';
  return '📄';
}

// ── Select Document ────────────────────────────────────────────
async function selectDocument(docId) {
  selectedDocId = docId;
  
  // Update UI
  document.querySelectorAll('.document-item').forEach(el => {
    el.classList.toggle('active', el.dataset.docId === docId);
  });
  
  // Load document details based on active tab
  await loadDocumentView(docId, currentView);
}

// ── Load Document View ────────────────────────────────────────
async function loadDocumentView(docId, view) {
  const viewContainer = document.getElementById('documentView');
  currentView = view;
  
  // Update tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.id === view + 'Tab');
  });
  
  try {
    const docData = await api.get(`/documents/${docId}`);
    const doc = docData.document_part;
    
    switch(view) {
      case 'preview':
        await renderPreview(viewContainer, doc);
        break;
      case 'chunks':
        await renderChunks(viewContainer, doc);
        break;
      case 'attachments':
        await renderAttachments(viewContainer, doc);
        break;
    }
  } catch (err) {
    viewContainer.innerHTML = `<div class="error">Error: ${err.message}</div>`;
  }
}

// ── Render Preview ────────────────────────────────────────────
async function renderPreview(container, doc) {
  container.innerHTML = `
    <div class="preview-container">
      <div class="preview-header">
        <h4>${doc.source_path.split('/').pop()}</h4>
        <div class="preview-meta">
          <span>Type: ${doc.content_type || 'unknown'}</span>
          <span>Chunker: ${doc.chunker_name || 'none'}</span>
          <span>Chunks: ${doc.chunk_ids ? JSON.parse(doc.chunk_ids)?.length || 0 : 0}</span>
        </div>
      </div>
      <div class="preview-body" id="previewBody">
        <div class="loading">Loading preview...</div>
      </div>
    </div>
  `;
  
  try {
    // Use the same openPreview function as the search view for consistent rendering
    const previewBody = document.getElementById('previewBody');
    await openPreview(previewBody, doc.document_part_id, doc.source_type || 'filesystem', doc.source_path || '');
  } catch (err) {
    // Fallback to metadata view if preview fails
    console.error('Preview failed, falling back to metadata:', err);
    const previewBody = document.getElementById('previewBody');
    previewBody.innerHTML = `
      <div class="preview-info">
        <p><strong>Path:</strong> ${doc.source_path}</p>
        <p><strong>Type:</strong> ${doc.content_type}</p>
        <p><strong>Checksum:</strong> ${doc.checksum}</p>
        <p><strong>Created:</strong> ${doc.created_at}</p>
        <p><strong>Updated:</strong> ${doc.updated_at}</p>
        ${doc.metadata_json ? `<p><strong>Metadata:</strong> <pre>${JSON.stringify(JSON.parse(doc.metadata_json), null, 2)}</pre></p>` : ''}
      </div>
    `;
  }
}

// ── Render Chunks ──────────────────────────────────────────────
async function renderChunks(container, doc) {
  container.innerHTML = `
    <div class="chunks-container">
      <div class="chunks-header">
        <h4>Chunks</h4>
        <span class="chunk-count">${doc.chunk_ids ? JSON.parse(doc.chunk_ids)?.length || 0 : 0} chunks</span>
      </div>
      <div class="chunks-list" id="chunksList">
        <div class="loading">Loading chunks...</div>
      </div>
    </div>
  `;
  
  try {
    const data = await api.get(`/documents/${doc.document_part_id}/chunks`);
    const chunksList = document.getElementById('chunksList');
    
    if (!data.chunks || data.chunks.length === 0) {
      chunksList.innerHTML = '<div class="empty-state">No chunks found</div>';
      return;
    }
    
    chunksList.innerHTML = data.chunks.map((chunk, index) => `
      <div class="chunk-item" data-chunk-id="${chunk.id}">
        <div class="chunk-header">
          <span class="chunk-index">#${index + 1}</span>
          <span class="chunk-char-len">${chunk.metadata?.char_len || '?'} chars</span>
        </div>
        <div class="chunk-text">${escapeHtml(chunk.text || chunk.content || 'No text')}</div>
        <div class="chunk-meta">
          <span>Unit: ${chunk.unit_locator || 'none'}</span>
        </div>
      </div>
    `).join('');
    
  } catch (err) {
    chunksList.innerHTML = `<div class="error">Failed to load chunks: ${err.message}</div>`;
  }
}

// ── Render Attachments ────────────────────────────────────────
async function renderAttachments(container, doc) {
  container.innerHTML = `
    <div class="attachments-container">
      <div class="attachments-header">
        <h4>Attachments</h4>
      </div>
      <div class="attachments-list" id="attachmentsList">
        <div class="loading">Loading attachments...</div>
      </div>
    </div>
  `;
  
  try {
    const data = await api.get(`/documents/${doc.document_part_id}/attachments`);
    const attachmentsList = document.getElementById('attachmentsList');
    
    if (!data.attachments || data.attachments.length === 0) {
      attachmentsList.innerHTML = '<div class="empty-state">No attachments found</div>';
      return;
    }
    
    attachmentsList.innerHTML = data.attachments.map(att => `
      <div class="attachment-item">
        <div class="att-icon">📎</div>
        <div class="att-info">
          <div class="att-name">${att.filename || 'Unnamed'}</div>
          <div class="att-meta">${att.mime_type || 'unknown'} • ${att.size ? formatSize(att.size) : '?'}</div>
        </div>
        <button class="att-download" data-att-id="${att.id}">⬇</button>
      </div>
    `).join('');
    
  } catch (err) {
    attachmentsList.innerHTML = `<div class="error">Failed to load attachments: ${err.message}</div>`;
  }
}

// ── Utility Functions ──────────────────────────────────────────
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatSize(bytes) {
  if (!bytes) return '?';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

// ── Tab Switching ─────────────────────────────────────────────
function setupTabHandlers() {
  document.addEventListener('click', (e) => {
    const tabBtn = e.target.closest('.tab-btn');
    if (!tabBtn) return;
    
    const view = tabBtn.id.replace('Tab', '');
    if (selectedDocId) {
      loadDocumentView(selectedDocId, view);
    }
  });
}

// ── Mount / Unmount ────────────────────────────────────────────
export function mount(app) {
  renderSourceView(app);
  setupTabHandlers();
  
  // Load sources on mount
  loadSources();
  
  // Refresh button handler
  document.getElementById('refreshSourcesBtn')?.addEventListener('click', loadSources);
}

export function unmount() {
  // Cleanup
  currentSourceId = null;
  selectedDocId = null;
}
