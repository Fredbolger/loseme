// search-ui.js - All DOM rendering and UI manipulation
import { fmtDate } from '../../app.js';

// HTML Template
export const TEMPLATE = `
<div class="chat-container">

  <!-- Sidebar: Conversations -->
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">🔍</span>
        <span class="logo-text">Knowledge Search</span>
      </div>
      <button class="new-chat-btn" id="newChatBtn">
        <span>+</span> New chat
      </button>
    </div>
    
    <div class="conversations-list" id="conversationsList">
      <div class="conversations-placeholder">
        <div class="placeholder-icon">💬</div>
        <div>No conversations yet</div>
        <small>Start a new search to begin</small>
      </div>
    </div>
    
    <div class="sidebar-footer">
      <button class="sidebar-btn" id="clearHistoryBtn">
        <span>🗑</span> Clear all history
      </button>
    </div>
  </aside>

  <!-- Main Content Area -->
  <main class="chat-main">
    <div class="main-header">
      <div class="header-title">
        <h1>Knowledge Assistant</h1>
        <span class="model-badge" id="modelBadge">Loading model...</span>
      </div>
    </div>

    <!-- Messages Area -->
    <div class="messages-area" id="messagesArea">
      <div class="welcome-screen">
        <div class="welcome-icon">🧠</div>
        <h2>How can I help you today?</h2>
        <p>Ask me anything about your documents — I'll search and provide answers with sources.</p>
        <div class="suggestion-chips">
          <button class="chip">What documents do I have?</button>
          <button class="chip">Summarize my recent files</button>
          <button class="chip">Find information about...</button>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <div class="input-container">
        <textarea 
          id="chatInput" 
          placeholder="Ask a question about your documents..."
          rows="1"
          class="chat-input"
        ></textarea>
        <div class="input-actions">
          <div class="input-options">
            <select id="searchModeSelect" class="mode-select">
              <option value="hybrid">🤖 Hybrid (LLM + Search)</option>
              <option value="search">📄 Search only (no LLM)</option>
            </select>
            <div class="topk-control">
              <label>Top K: </label>
              <input type="number" id="topKInput" value="10" min="1" max="50" class="topk-input">
            </div>
            <select id="ollamaModelSelect" class="model-select" style="display: none;">
              <option value="">Select Ollama model...</option>
            </select>
          </div>
          <button class="send-btn" id="sendBtn" disabled>
            <span>➤</span>
          </button>
        </div>
      </div>
      <div class="input-hint">Press Enter to send, Shift+Enter for new line</div>
    </div>
  </main>

  <!-- Sources Panel -->
  <div class="sources-panel" id="sourcesPanel" style="display: none;">
    <div class="sources-header">
      <h3>📄 Sources</h3>
      <button class="close-sources" id="closeSourcesBtn">×</button>
    </div>
    <div class="sources-list" id="sourcesList"></div>
  </div>

  <!-- Document Preview Modal -->
  <div class="doc-modal" id="docModal" style="display: none;" tabindex="0">
    <div class="doc-modal-content">
      <div class="doc-modal-header">
        <h3 id="docModalTitle">Document Preview</h3>
        <button class="close-modal" id="closeModalBtn">×</button>
      </div>
      <div class="doc-modal-body" id="docModalBody"></div>
    </div>
  </div>
</div>

<style>
  .chat-container {
    display: flex;
    height: 100vh;
    width: 100%;
    background: linear-gradient(135deg, #f5f7fa 0%, #f3f5f8 100%);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', system-ui, sans-serif;
  }

  .chat-sidebar {
    width: 280px;
    background: rgba(255, 255, 255, 0.98);
    border-right: 1px solid rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
  }

  .sidebar-header {
    padding: 20px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .logo-icon {
    font-size: 24px;
    background: none;
    -webkit-text-fill-color: initial;
  }

  .new-chat-btn {
    width: 100%;
    padding: 10px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    font-weight: 500;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .new-chat-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .conversations-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }

  .conversation-item {
    padding: 12px;
    margin-bottom: 8px;
    background: white;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid rgba(0, 0, 0, 0.06);
    position: relative;
  }

  .conversation-item:hover {
    background: #f8f9fa;
    border-color: #667eea;
    transform: translateX(4px);
  }

  .conversation-item.active {
    background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
    border-color: #667eea;
  }

  .conversation-title {
    font-weight: 500;
    font-size: 14px;
    margin-bottom: 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .conversation-meta {
    font-size: 11px;
    color: #6c757d;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .conversation-delete {
    opacity: 0;
    background: none;
    border: none;
    cursor: pointer;
    color: #dc3545;
    font-size: 14px;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .conversation-item:hover .conversation-delete {
    opacity: 1;
  }

  .conversation-delete:hover {
    background: #fee;
  }

  .conversations-placeholder {
    text-align: center;
    padding: 40px 20px;
    color: #adb5bd;
  }

  .placeholder-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }

  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }

  .sidebar-btn {
    width: 100%;
    padding: 8px;
    background: none;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #6c757d;
    transition: all 0.2s;
  }

  .sidebar-btn:hover {
    background: #f8f9fa;
    border-color: #dc3545;
    color: #dc3545;
  }

  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: white;
  }

  .main-header {
    padding: 16px 24px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-title h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
    color: #2c3e50;
  }

  .model-badge {
    font-size: 11px;
    padding: 4px 8px;
    background: #f0f0f0;
    border-radius: 12px;
    margin-left: 12px;
  }

  .messages-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .welcome-screen {
    text-align: center;
    padding: 60px 20px;
    max-width: 600px;
    margin: 0 auto;
  }

  .welcome-icon {
    font-size: 64px;
    margin-bottom: 20px;
  }

  .welcome-screen h2 {
    margin-bottom: 12px;
    color: #2c3e50;
  }

  .welcome-screen p {
    color: #6c757d;
    margin-bottom: 32px;
  }

  .suggestion-chips {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .chip {
    padding: 8px 16px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
  }

  .chip:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
  }

  .message {
    margin-bottom: 24px;
    animation: fadeIn 0.3s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .message.user {
    text-align: right;
  }

  .message-content {
    display: inline-block;
    max-width: 70%;
    padding: 12px 18px;
    border-radius: 18px;
    line-height: 1.5;
  }

  .message.user .message-content {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .message.assistant .message-content {
    background: #f8f9fa;
    color: #2c3e50;
    border: 1px solid #e9ecef;
  }

  .message-meta {
    font-size: 11px;
    color: #adb5bd;
    margin-top: 6px;
    margin-bottom: 4px;
  }

  .sources-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    color: #667eea;
    cursor: pointer;
    font-size: 12px;
    margin-top: 8px;
    padding: 4px 8px;
    border-radius: 12px;
  }

  .sources-toggle:hover {
    background: #f0f0f0;
  }

  .input-area {
    padding: 20px 24px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    background: white;
  }

  .input-container {
    max-width: 900px;
    margin: 0 auto;
  }

  .chat-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e9ecef;
    border-radius: 12px;
    font-size: 14px;
    font-family: inherit;
    resize: none;
  }

  .chat-input:focus {
    outline: none;
    border-color: #667eea;
  }

  .input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
  }

  .input-options {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .mode-select, .model-select, .topk-input {
    padding: 6px 10px;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    font-size: 12px;
    background: white;
    cursor: pointer;
  }

  .topk-control {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
  }

  .topk-input {
    width: 60px;
  }

  .send-btn {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .send-btn:hover:not(:disabled) {
    transform: scale(1.05);
  }

  .send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .send-btn span {
    color: white;
    font-size: 18px;
  }

  .input-hint {
    font-size: 11px;
    color: #adb5bd;
    text-align: center;
    margin-top: 8px;
  }

  .sources-panel {
    position: fixed;
    right: 0;
    top: 0;
    width: 320px;
    height: 100vh;
    background: white;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
    display: flex;
    flex-direction: column;
    z-index: 100;
    animation: slideIn 0.3s ease;
  }

  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .sources-header {
    padding: 20px;
    border-bottom: 1px solid #e9ecef;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sources-header h3 {
    margin: 0;
  }

  .close-sources {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #adb5bd;
  }

  .sources-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .source-item {
    padding: 12px;
    margin-bottom: 12px;
    background: #f8f9fa;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .source-item:hover {
    background: #e9ecef;
    transform: translateX(-4px);
  }

  .source-title {
    font-weight: 500;
    font-size: 13px;
    margin-bottom: 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source-score {
    font-size: 10px;
    color: #28a745;
  }

  .source-chunks {
    font-size: 10px;
    color: #667eea;
    margin-top: 4px;
  }

  .doc-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .doc-modal-content {
    background: white;
    border-radius: 16px;
    width: 80%;
    max-width: 900px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .doc-modal-header {
    padding: 16px 20px;
    border-bottom: 1px solid #e9ecef;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .doc-modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
  }

  .close-modal {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
  }

  .typing-indicator {
    display: flex;
    gap: 4px;
    padding: 12px 18px;
    background: #f8f9fa;
    border-radius: 18px;
    width: fit-content;
  }

  .typing-indicator span {
    width: 8px;
    height: 8px;
    background: #adb5bd;
    border-radius: 50%;
    animation: typing 1.4s infinite;
  }

  .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
  .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes typing {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-10px); opacity: 1; }
  }

  ::-webkit-scrollbar {
    width: 6px;
  }

  ::-webkit-scrollbar-track {
    background: #f1f1f1;
  }

  ::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
  }
</style>
`;

// Helper functions
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function basename(path) {
  if (!path) return '—';
  return path.split(/[/\\]/).pop() || path;
}

export function renderMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\[Document (\d+)\]/g, '<span style="background: #667eea20; padding: 2px 6px; border-radius: 12px; font-size: 11px;">📄 Document $1</span>')
    .replace(/\n/g, '<br>');
}

export function addMessageToUI(role, content, isStreaming = false) {
  const messagesArea = document.getElementById('messagesArea');
  const messageId = 'msg_' + Date.now() + '_' + Math.random();
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  messageDiv.id = messageId;
  
  let contentHtml = '';
  if (isStreaming && !content) {
    contentHtml = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
  } else {
    contentHtml = renderMarkdown(content || '');
  }
  
  messageDiv.innerHTML = `
    <div class="message-meta">${role === 'user' ? 'You' : 'Assistant'} • just now</div>
    <div class="message-content">${contentHtml}</div>
  `;
  messagesArea.appendChild(messageDiv);
  messagesArea.scrollTop = messagesArea.scrollHeight;
  return messageId;
}

export function updateMessageContent(messageId, content) {
  const messageDiv = document.getElementById(messageId);
  if (messageDiv) {
    const contentDiv = messageDiv.querySelector('.message-content');
    if (contentDiv) contentDiv.innerHTML = renderMarkdown(content);
  }
}

export function finalizeMessage(messageId, content) {
  const messageDiv = document.getElementById(messageId);
  if (messageDiv) {
    const contentDiv = messageDiv.querySelector('.message-content');
    contentDiv.innerHTML = renderMarkdown(content);
  }
}

export function addTypingIndicator() {
  const messagesArea = document.getElementById('messagesArea');
  const indicatorId = 'typing_' + Date.now();
  const indicator = document.createElement('div');
  indicator.className = 'message assistant';
  indicator.id = indicatorId;
  indicator.innerHTML = `<div class="message-meta">Assistant • typing</div>
    <div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
  messagesArea.appendChild(indicator);
  messagesArea.scrollTop = messagesArea.scrollHeight;
  return indicatorId;
}

export function removeTypingIndicator(indicatorId) {
  const indicator = document.getElementById(indicatorId);
  if (indicator) indicator.remove();
}

export function attachSourcesToMessage(messageId, sources, onViewSources) {
  const messageDiv = document.getElementById(messageId);
  if (messageDiv && sources && sources.length > 0) {
    const toggle = document.createElement('button');
    toggle.className = 'sources-toggle';
    toggle.innerHTML = `📄 View ${sources.length} source${sources.length > 1 ? 's' : ''}`;
    toggle.onclick = onViewSources;
    messageDiv.appendChild(toggle);
  }
}

export function displaySources(sources, onSourceClick) {
  const sourcesList = document.getElementById('sourcesList');
  if (!sources || !sources.length) {
    sourcesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #adb5bd;">No sources available</div>';
    return;
  }
  
  sourcesList.innerHTML = sources.map((s, i) => {
    const name = basename(s.source_path || s.document_part_id || 'Unknown');
    const chunkInfo = s.chunk_count ? ` (${s.chunk_count} chunk${s.chunk_count > 1 ? 's' : ''})` : '';
    return `
      <div class="source-item" data-doc-id="${s.document_part_id}" data-source-path="${escapeHtml(s.source_path || '')}" data-source-type="${escapeHtml(s.source_type || 'filesystem')}">
        <div class="source-title">${escapeHtml(name)}${chunkInfo}</div>
        <div class="source-score">Score: ${(s.score || s.maxScore || 0).toFixed(3)}</div>
        <div class="source-chunks">📄 ${s.chunk_count || 1} relevant section${(s.chunk_count || 1) > 1 ? 's' : ''}</div>
      </div>
    `;
  }).join('');
  
  sourcesList.querySelectorAll('.source-item').forEach(item => {
    item.addEventListener('click', () => onSourceClick(item.dataset));
  });
}

export function showWelcomeScreen() {
  const messagesArea = document.getElementById('messagesArea');
  messagesArea.innerHTML = `<div class="welcome-screen">
    <div class="welcome-icon">🧠</div>
    <h2>How can I help you today?</h2>
    <p>Ask me anything about your documents — I'll search and provide answers with sources.</p>
    <div class="suggestion-chips">
      <button class="chip">What documents do I have?</button>
      <button class="chip">Summarize my recent files</button>
      <button class="chip">Find information about...</button>
    </div>
  </div>`;
}

export function updateConversationsList(sessions, onSelect, onDelete) {
  const list = document.getElementById('conversationsList');
  
  if (!sessions.length) {
    list.innerHTML = `<div class="conversations-placeholder">
      <div class="placeholder-icon">💬</div>
      <div>No conversations yet</div>
      <small>Start a new search to begin</small>
    </div>`;
    return;
  }
  
  list.innerHTML = sessions.map(s => `
    <div class="conversation-item" data-session="${escapeHtml(s.session_id)}">
      <div class="conversation-title">${escapeHtml(s.title || s.query.substring(0, 40))}</div>
      <div class="conversation-meta">
        <span>${s.message_count} messages</span>
        <span>${fmtDate(s.updated_at)}</span>
        <button class="conversation-delete" data-session="${escapeHtml(s.session_id)}">🗑</button>
      </div>
    </div>
  `).join('');
  
  list.querySelectorAll('.conversation-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!e.target.classList.contains('conversation-delete')) {
        onSelect(el.dataset.session);
      }
    });
  });
  
  list.querySelectorAll('.conversation-delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      onDelete(btn.dataset.session);
    });
  });
}

export function setActiveConversation(sessionId) {
  document.querySelectorAll('.conversation-item').forEach(el => {
    el.classList.toggle('active', el.dataset.session === sessionId);
  });
}

export function toggleSourcesPanel(show) {
  const panel = document.getElementById('sourcesPanel');
  panel.style.display = show ? 'flex' : 'none';
}

export function showDocumentModal(title, onLoadContent) {
  const modal = document.getElementById('docModal');
  const titleEl = document.getElementById('docModalTitle');
  const body = document.getElementById('docModalBody');
  
  titleEl.textContent = title;
  body.innerHTML = '<div style="text-align: center; padding: 40px;">Loading document preview...</div>';
  modal.style.display = 'flex';
  modal.focus();
  
  onLoadContent(body);
}

export function closeDocumentModal() {
  const modal = document.getElementById('docModal');
  if (modal) modal.style.display = 'none';
}

export function updateModelBadge(modelName) {
  const badge = document.getElementById('modelBadge');
  badge.textContent = modelName;
}

export function updateModelSelector(models, currentModel) {
  const select = document.getElementById('ollamaModelSelect');
  if (!select) return;
  
  select.innerHTML = '<option value="">Select Ollama model...</option>';
  
  if (models && models.length > 0) {
    models.forEach(model => {
      const option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      if (model === currentModel) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    select.style.display = 'block';
  } else {
    // Show the selector with a placeholder even when no models are available
    select.style.display = 'block';
  }
}

export function getSelectedModel() {
  const select = document.getElementById('ollamaModelSelect');
  return select ? select.value : 'mistral:7b';
}

export function showModelSelector(show) {
  const select = document.getElementById('ollamaModelSelect');
  if (select) {
    select.style.display = show ? 'block' : 'none';
  }
}

export function clearMessagesArea() {
  const messagesArea = document.getElementById('messagesArea');
  if (messagesArea.querySelector('.welcome-screen')) {
    messagesArea.innerHTML = '';
  }
}

export function addOrUpdateConversation(sessionId, query, status = 'pending', messageCount = 0) {
  const list = document.getElementById('conversationsList');
  
  // Check if conversation already exists
  const existingItem = list.querySelector(`[data-session="${escapeHtml(sessionId)}"]`);
  
  if (existingItem) {
    // Update existing conversation
    const titleEl = existingItem.querySelector('.conversation-title');
    const metaEl = existingItem.querySelector('.conversation-meta');
    
    if (titleEl) {
      titleEl.textContent = query.length > 40 ? query.substring(0, 40) + '...' : query;
    }
    
    if (metaEl) {
      const statusIndicator = status === 'pending' ? '⏳ Generating...' : '';
      const msgCount = messageCount > 0 ? `${messageCount} messages` : '0 messages';
      metaEl.innerHTML = `
        <span>${msgCount}</span>
        <span>${statusIndicator || fmtDate(new Date().toISOString())}</span>
        <button class="conversation-delete" data-session="${escapeHtml(sessionId)}">🗑</button>
      `;
    }
    
    // Re-bind delete button
    const deleteBtn = existingItem.querySelector('.conversation-delete');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        // You'll need to pass the delete function here
        // For now, we'll use the global deleteConversation
        if (window.deleteConversationFn) {
          window.deleteConversationFn(sessionId);
        }
      });
    }
    
    return;
  }
  
  // Create new conversation item
  const item = document.createElement('div');
  item.className = 'conversation-item active';
  item.dataset.session = sessionId;
  
  const statusText = status === 'pending' ? '⏳ Generating...' : fmtDate(new Date().toISOString());
  const msgCount = messageCount > 0 ? `${messageCount} messages` : '0 messages';
  
  item.innerHTML = `
    <div class="conversation-title">${escapeHtml(query.length > 40 ? query.substring(0, 40) + '...' : query)}</div>
    <div class="conversation-meta">
      <span>${msgCount}</span>
      <span>${statusText}</span>
      <button class="conversation-delete" data-session="${escapeHtml(sessionId)}">🗑</button>
    </div>
  `;
  
  // Insert at the top of the list
  list.prepend(item);
  
  // Remove placeholder if it exists
  const placeholder = list.querySelector('.conversations-placeholder');
  if (placeholder) {
    placeholder.remove();
  }
  
  // Bind click to load conversation
  item.addEventListener('click', (e) => {
    if (!e.target.classList.contains('conversation-delete')) {
      // You'll need to pass the load function here
      if (window.loadConversationFn) {
        window.loadConversationFn(sessionId);
      }
    }
  });
  
  // Bind delete button
  const deleteBtn = item.querySelector('.conversation-delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (window.deleteConversationFn) {
        window.deleteConversationFn(sessionId);
      }
    });
  }
}
