// search.js - Main component logic
import { showError } from '../../app.js';
import { openPreview } from '../../previews/index.js';
import * as ui from './search-ui.js';
import * as api from './search-api.js';

// ============================================
// STATE
// ============================================
let lastResults = [];
let lastEnriched = {};
let currentSessionId = null;
let currentMessages = [];
let isAwaitingResponse = false;
let availableModels = [];
let selectedModel = null;

// Streaming state that persists across tab switches
let isMounted = false;
let activeStreamController = null;
let activeStreamPromise = null;
let pendingAnswer = null;
let pendingMessageId = null;

// ============================================
// CORE LOGIC
// ============================================
function mergeByPart(raw) {
  const seen = new Map();
  const order = [];
  
  for (const r of raw) {
    const pid = r.document_part_id;
    if (!seen.has(pid)) {
      seen.set(pid, { 
        ...r, 
        chunks: [r],
        maxScore: r.score,
        minScore: r.score,
        chunkCount: 1
      });
      order.push(pid);
    } else {
      const ex = seen.get(pid);
      ex.chunks.push(r);
      ex.maxScore = Math.max(ex.maxScore, r.score);
      ex.minScore = Math.min(ex.minScore, r.score);
      ex.chunkCount++;
      ex.score = ex.maxScore;
    }
  }
  
  return order.map(pid => {
    const item = seen.get(pid);
    item.allChunkTexts = item.chunks.map(c => c.chunk_text || c.text || '').filter(t => t);
    return item;
  });
}

function buildLLMContext(query, mergedResults, history) {
  const contextParts = mergedResults.slice(0, 8).map((doc, i) => {
    const ep = lastEnriched[doc.document_part_id];
    const part = ep?.part || ep || {};
    const name = (part.source_path || doc.source_path || doc.document_part_id || '').split(/[/\\]/).pop() || 'Unknown';
    const allText = doc.allChunkTexts.join('\n\n');
    return `[Document ${i + 1}: ${name}]\n${allText}`;
  });
  
  let context = contextParts.join('\n\n---\n\n');
  
  if (history && history.length > 0) {
    const historyText = history.slice(-5).map(msg => 
      `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content.substring(0, 500)}`
    ).join('\n');
    context = `Previous conversation:\n${historyText}\n\nCurrent search results:\n${context}`;
  }
  
  return context;
}

// ============================================
// SEARCH ACTIONS
// ============================================
async function performVectorSearch(query, topK) {
  const response = await api.performSearch(query, topK, currentSessionId);
  const results = response.results || [];
  const cacheHit = response.cache_hit || false;
  const cacheScore = response.cache_score || null;
  currentSessionId = response.session_id;
  
  const merged = mergeByPart(results);
  lastResults = merged;
  
  const partIds = [...new Set(results.map(r => r.document_part_id).filter(Boolean))];
  if (partIds.length > 0) {
    lastEnriched = await api.batchGetDocuments(partIds);
  }
  
  let messageText = `✅ Search completed. Found ${merged.length} relevant document${merged.length !== 1 ? 's' : ''}.`;
  if (cacheHit && cacheScore) {
    messageText += `\n\n⚡ **Cache hit!** (${(cacheScore * 100).toFixed(1)}% similarity to a previous search)`;
  }
  
  const messageId = ui.addMessageToUI('assistant', messageText);
  
  const sourcesToStore = merged.slice(0, topK).map(doc => ({
    document_part_id: doc.document_part_id,
    source_path: doc.source_path,
    source_type: doc.source_type,
    score: doc.maxScore,
    chunk_count: doc.chunkCount
  }));
  
  ui.attachSourcesToMessage(messageId, sourcesToStore, () => {
    ui.displaySources(sourcesToStore, onSourceClick);
    ui.toggleSourcesPanel(true);
  });
  
  ui.displaySources(sourcesToStore, onSourceClick);
  ui.toggleSourcesPanel(true);
  
  // ✅ FIX: Always store the assistant message
  if (currentSessionId) {
    await api.saveAnswer(
      currentSessionId, 
      messageText,
      merged.slice(0, topK).map(doc => doc.document_part_id),
      sourcesToStore
    );
    
    // ✅ Update currentMessages
    currentMessages.push(
      { role: 'user', content: query },
      { role: 'assistant', content: messageText, sources: sourcesToStore }
    );
    
    // ✅ Refresh conversations list
    await loadAndDisplayConversations();
    
    // ✅ Highlight current conversation
    ui.setActiveConversation(currentSessionId);
  }
}

async function performHybridSearch(query, topK) {
  const response = await api.performSearch(query, topK, currentSessionId);
  const results = response.results || [];
  currentSessionId = response.session_id;
  
  const merged = mergeByPart(results);
  lastResults = merged;
  
  const partIds = [...new Set(results.map(r => r.document_part_id).filter(Boolean))];
  if (partIds.length > 0) {
    lastEnriched = await api.batchGetDocuments(partIds);
  }
  
  await streamLLMAnswer(query, merged, topK);  // Pass topK
}

async function streamLLMAnswer(query, mergedResults, topK) {
  const context = buildLLMContext(query, mergedResults, currentMessages);
  
  // If there's already an active stream, cancel it
  if (activeStreamController) {
    activeStreamController.abort();
    activeStreamController = null;
  }
  
  // Create a new abort controller for this stream
  activeStreamController = new AbortController();
  
  // Store the message ID globally so we can update it even after remounting
  pendingMessageId = null;
  pendingAnswer = '';
  
  const messageId = isMounted ? ui.addMessageToUI('assistant', '', true) : null;
  pendingMessageId = messageId;
  
  try {
    const model = ui.getSelectedModel() || selectedModel || 'mistral:7b';
    const currentController = activeStreamController; // Capture current controller
    
    // Get result_ids for server-side context building
    const resultIds = mergedResults.slice(0, 10).map(doc => doc.document_part_id);
    
    await api.streamLLMResponse(
      query, 
      context, 
      (token) => {
        pendingAnswer += token;
        // Update UI if we're mounted and this is still the active stream
        if (currentController === activeStreamController && isMounted && messageId) {
          const messagesArea = document.getElementById('messagesArea');
          if (messagesArea && messagesArea.querySelector(`#${messageId}`)) {
            ui.updateMessageContent(messageId, pendingAnswer);
          }
        }
      }, 
      model, 
      activeStreamController.signal,
      currentSessionId,  // Pass session ID
      resultIds  // Pass result IDs for server-side context
    );
    
    // Stream completed successfully - save to session if we have one
    if (currentSessionId && pendingAnswer.trim() && currentController === activeStreamController) {
      const sourcesToStore = mergedResults.slice(0, 5).map(doc => ({
        document_part_id: doc.document_part_id,
        source_path: doc.source_path,
        source_type: doc.source_type,
        score: doc.maxScore,
        chunk_count: doc.chunkCount
      }));
      
      await api.saveAnswer(
        currentSessionId,
        pendingAnswer,
        mergedResults.slice(0, 5).map(doc => doc.document_part_id),
        sourcesToStore
      );
      
      // Add to current messages
      currentMessages.push(
        { role: 'user', content: query },
        { role: 'assistant', content: pendingAnswer, sources: sourcesToStore }
      );
    }
    
    // Clear the active controller and pending state
    activeStreamController = null;
    
    // Finalize message if we're still mounted
    if (isMounted && messageId) {
      ui.finalizeMessage(messageId, pendingAnswer);
    }
    
    // Clear pending state
    pendingAnswer = null;
    pendingMessageId = null;
    
  } catch (e) {
    // If the error is due to abort, don't show an error
    if (e.name !== 'AbortError') {
      throw e;
    }
    // Stream was aborted, clear state
    pendingAnswer = null;
    pendingMessageId = null;
  }
  
  activeStreamController = null;
}

// ============================================
// EVENT HANDLERS
// ============================================
async function onSourceClick(dataset) {
  const { docId, sourcePath, sourceType } = dataset;
  ui.showDocumentModal(
    (sourcePath || docId || '').split(/[/\\]/).pop() || 'Document',
    async (body) => {
      await openPreview(body, docId, sourceType || 'filesystem', sourcePath || '');
    }
  );
}
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message || isAwaitingResponse) return;
  
  const searchMode = document.getElementById('searchModeSelect').value;
  const topK = parseInt(document.getElementById('topKInput').value) || 10;
  
  input.value = '';
  document.getElementById('sendBtn').disabled = true;
  
  ui.clearMessagesArea();
  const userMessageId = ui.addMessageToUI('user', message);
  isAwaitingResponse = true;
  
  try {
    if (searchMode === 'search') {
      await performVectorSearch(message, topK);
    } else {
      const typingId = ui.addTypingIndicator();
      await performHybridSearch(message, topK);
      ui.removeTypingIndicator(typingId);
    }
    
    // ✅ Refresh the conversation list after any search
    await loadAndDisplayConversations();
    
  } catch (e) {
    ui.addMessageToUI('assistant', `❌ Error: ${e.message}`);
    showError(e.message);
  } finally {
    isAwaitingResponse = false;
    document.getElementById('sendBtn').disabled = false;
    input.focus();
  }
}


function newChat() {
  // Cancel any active stream
  if (activeStreamController) {
    activeStreamController.abort();
    activeStreamController = null;
  }
  
  // Clear pending state
  pendingAnswer = null;
  pendingMessageId = null;
  
  currentSessionId = null;
  currentMessages = [];
  ui.showWelcomeScreen();
  
  // Re-attach chip event listeners
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.getElementById('chatInput').value = chip.textContent;
      sendMessage();
    });
  });
  
  document.getElementById('chatInput').value = '';
  document.getElementById('chatInput').focus();
  ui.toggleSourcesPanel(false);
  
  // Reset model selector to first available model
  if (availableModels && availableModels.length > 0) {
    selectedModel = availableModels[0];
    ui.updateModelSelector(availableModels, selectedModel);
  }
}

async function loadConversation(sessionId) {
  try {
    const { messages } = await api.getConversation(sessionId);
    currentSessionId = sessionId;
    currentMessages = messages;
    
    ui.showWelcomeScreen(); // Clear area
    const messagesArea = document.getElementById('messagesArea');
    messagesArea.innerHTML = '';
    
    for (const msg of messages) {
      if (msg.role === 'user' || msg.role === 'assistant') {
        const messageId = ui.addMessageToUI(msg.role, msg.content);
        if (msg.role === 'assistant' && msg.sources && msg.sources.length > 0) {
          ui.attachSourcesToMessage(messageId, msg.sources, () => {
            ui.displaySources(msg.sources, onSourceClick);
            ui.toggleSourcesPanel(true);
          });
        }
      }
    }
    
    ui.setActiveConversation(sessionId);
    document.getElementById('chatInput').focus();
  } catch (e) {
    showError('Failed to load conversation');
  }
}

async function deleteConversation(sessionId) {
  try {
    await api.deleteConversation(sessionId);
    if (currentSessionId === sessionId) newChat();
    await loadAndDisplayConversations();
  } catch (e) {
    showError('Failed to delete conversation');
  }
}

async function clearAllHistory() {
  if (!confirm('Delete ALL conversations? This cannot be undone.')) return;
  try {
    const sessions = await api.getConversations(100);
    for (const session of sessions) {
      await api.deleteConversation(session.session_id).catch(() => {});
    }
    newChat();
    await loadAndDisplayConversations();
  } catch (e) {
    showError('Failed to clear history');
  }
}

async function loadAndDisplayConversations() {
  try {
    const sessions = await api.getConversations();
    ui.updateConversationsList(sessions, loadConversation, deleteConversation);
  } catch (e) {
    console.error('Failed to load conversations:', e);
  }
}

async function loadModels() {
  availableModels = await api.loadModels();
  const modeSelect = document.getElementById('searchModeSelect');
  const isHybrid = modeSelect ? modeSelect.value === 'hybrid' : true;
  
  if (availableModels && availableModels.length > 0) {
    selectedModel = availableModels[0];
    ui.updateModelBadge(`🧠 ${selectedModel}`);
    ui.updateModelSelector(availableModels, selectedModel);
    if (isHybrid) {
      ui.showModelSelector(true);
    }
  } else {
    ui.updateModelBadge('Ollama not running');
    ui.updateModelSelector([], null);
    ui.showModelSelector(false);
  }
}

// ============================================
// MOUNT
// ============================================
export function mount(container) {
  container.innerHTML = ui.TEMPLATE;
  
  // Don't reset state when remounting - preserve conversations and streaming state
  // Only reset if this is the first mount
  if (!isMounted) {
    lastResults = [];
    lastEnriched = {};
    currentSessionId = null;
    currentMessages = [];
    isAwaitingResponse = false;
    isMounted = true;
  } else {
    // We're remounting - restore any pending stream state
    isMounted = true;
    if (pendingAnswer && pendingMessageId) {
      // Restore the pending message with current content
      const messagesArea = document.getElementById('messagesArea');
      if (messagesArea) {
        const existingMessage = messagesArea.querySelector(`#${pendingMessageId}`);
        if (existingMessage) {
          ui.updateMessageContent(pendingMessageId, pendingAnswer);
        } else {
          // If the message doesn't exist, add it
          pendingMessageId = ui.addMessageToUI('assistant', pendingAnswer, true);
        }
      }
    }
  }
  
  // Bind events
  document.getElementById('newChatBtn').addEventListener('click', newChat);
  document.getElementById('sendBtn').addEventListener('click', sendMessage);
  document.getElementById('clearHistoryBtn').addEventListener('click', clearAllHistory);
  document.getElementById('closeSourcesBtn').addEventListener('click', () => ui.toggleSourcesPanel(false));
  document.getElementById('closeModalBtn').addEventListener('click', ui.closeDocumentModal);
  
  // Escape key for modal
  window.onkeydown = function(e) {
    if (e.key === 'Escape') {
      ui.closeDocumentModal();
    }
  };
  
  const chatInput = document.getElementById('chatInput');
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  chatInput.addEventListener('input', () => {
    document.getElementById('sendBtn').disabled = !chatInput.value.trim();
  });
  
  // Model selector change handler
  const modelSelect = document.getElementById('ollamaModelSelect');
  const modeSelect = document.getElementById('searchModeSelect');
  if (modelSelect && modeSelect) {
    modelSelect.addEventListener('change', (e) => {
      selectedModel = e.target.value;
      ui.updateModelBadge(selectedModel ? `🧠 ${selectedModel}` : 'Ollama not running');
    });
    
    // Show/hide model selector based on search mode
    modeSelect.addEventListener('change', () => {
      ui.showModelSelector(modeSelect.value === 'hybrid' && availableModels.length > 0);
    });
  }
  
  // Chip suggestions
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent;
      sendMessage();
    });
  });
  
  loadModels();
  loadAndDisplayConversations();
}

export function unmount() {
  isMounted = false;
  
  // Cancel any active stream when unmounting
  if (activeStreamController) {
    activeStreamController.abort();
    activeStreamController = null;
  }
}
