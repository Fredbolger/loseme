// search.js - Main component logic
import { showError } from '../../app.js';
import { openPreview } from '../../previews/index.js';
import * as ui from './search-ui.js';
import * as api from './search-api.js';
import { openDetail, openDetailFromChip, closeDetail } from './detail-panel.js';


// ============================================
// STATE
// ============================================
let lastResults = [];
let lastEnriched = {};
let lastSources = [];
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
  currentSessionId = response.session_id;
  
  const merged = mergeByPart(results);
  lastResults = merged;
  
  const partIds = [...new Set(results.map(r => r.document_part_id).filter(Boolean))];
  if (partIds.length > 0) {
    lastEnriched = await api.batchGetDocuments(partIds);
  }
  
  // Build sources for display
  const sourcesToStore = merged.slice(0, topK).map(doc => ({
    document_part_id: doc.document_part_id,
    source_path: doc.source_path,
    source_type: doc.source_type,
    score: doc.maxScore,
    chunk_count: doc.chunkCount
  }));
  
  // Show results with source chips
  let messageText = `✅ Search completed. Found ${merged.length} relevant document${merged.length !== 1 ? 's' : ''}.`;
  
  const messageId = ui.addMessageToUI('assistant', messageText);
  
  // Attach sources widget with click handler
  ui.attachSourcesToMessage(messageId, sourcesToStore, (sources) => {
    // When the sources widget is clicked, it will call onSourceClick with the sources array
    onSourceClick(sources);
  });
  
  if (currentSessionId) {
    await api.saveAnswer(
      currentSessionId, 
      messageText,
      merged.slice(0, topK).map(doc => doc.document_part_id),
      sourcesToStore
    );
    
    currentMessages.push(
      { role: 'user', content: query },
      { role: 'assistant', content: messageText, sources: sourcesToStore }
    );
    
    await loadAndDisplayConversations();
    ui.setActiveConversation(currentSessionId);
  }
}

async function performHybridSearch(query, topK) {
  const response = await api.performSearch(query, topK, currentSessionId);
  const results = response.results || [];
  currentSessionId = response.session_id;
  
  // Show conversation in sidebar
  ui.addOrUpdateConversation(currentSessionId, query, 'pending', 0);
  ui.setActiveConversation(currentSessionId);
  
  const merged = mergeByPart(results);
  lastResults = merged;
  
  const partIds = [...new Set(results.map(r => r.document_part_id).filter(Boolean))];
  if (partIds.length > 0) {
    lastEnriched = await api.batchGetDocuments(partIds);
  }
  
  // Build sources for display
  const sourcesToStore = merged.slice(0, topK).map(doc => ({
    document_part_id: doc.document_part_id,
    source_path: doc.source_path,
    source_type: doc.source_type,
    score: doc.maxScore,
    chunk_count: doc.chunkCount
  }));
  
  // Save sources for later
  lastSources = sourcesToStore;
  
  await streamLLMAnswer(query, merged, topK);

  // Final update after LLM completes
  await loadAndDisplayConversations();
  ui.setActiveConversation(currentSessionId);
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
    
    // Get result_ids for server-side context building - use topK here too
    const resultIds = mergedResults.slice(0, topK).map(doc => doc.document_part_id);
    
    await api.streamLLMResponse(
      query, 
      context, 
      (token) => {
        pendingAnswer += token;
        // Update UI if we're mounted and this is still the active stream
        if (currentController === activeStreamController && isMounted && messageId) {
          const messageElement = document.getElementById(messageId);
          if (messageElement) {
            ui.updateMessageContent(messageId, pendingAnswer);
          }
        }
      }, 
      model, 
      activeStreamController.signal,
      currentSessionId,  // Pass session ID
      resultIds,  // Pass result IDs for server-side context
      topK  // Pass topK
    );
    
    // Stream completed successfully
    if (currentController === activeStreamController) {
      // Finalize the message content
      if (isMounted && messageId) {
        ui.finalizeMessage(messageId, pendingAnswer);
      }
      
      // ✅ Use topK instead of hardcoded 5 for sources
      console.log('Stream completed, mergedResults:', mergedResults); // Debug log
      if (mergedResults && mergedResults.length > 0 && messageId) {
        const sourcesToStore = mergedResults.slice(0, topK).map(doc => ({
          document_part_id: doc.document_part_id,
          source_path: doc.source_path,
          source_type: doc.source_type,
          score: doc.maxScore,
          chunk_count: doc.chunkCount
        }));
      
        // Attach sources widget with click handler
        ui.attachSourcesToMessage(messageId, sourcesToStore, (sources) => {
          onSourceClick(sources);
        });
      } else {
        console.log('No sources to display - mergedResults empty or no messageId'); // Debug log
      }

      // ✅ Use topK instead of hardcoded 5 for saving
      if (currentSessionId && pendingAnswer.trim()) {
        const sourcesToStore = mergedResults.slice(0, topK).map(doc => ({
          document_part_id: doc.document_part_id,
          source_path: doc.source_path,
          source_type: doc.source_type,
          score: doc.maxScore,
          chunk_count: doc.chunkCount
        }));
        
        await api.saveAnswer(
          currentSessionId,
          pendingAnswer,
          mergedResults.slice(0, topK).map(doc => doc.document_part_id),
          sourcesToStore
        );
        
        // Add to current messages
        currentMessages.push(
          { role: 'user', content: query },
          { role: 'assistant', content: pendingAnswer, sources: sourcesToStore }
        );
        
        // Update the conversation in the sidebar with the final content
        ui.addOrUpdateConversation(currentSessionId, query, 'completed', currentMessages.length);
      }
    }
    
    // Clear the active controller and pending state
    activeStreamController = null;
    
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
function onSourceClick(sourcesOrDataset) {
  console.log('onSourceClick called with:', sourcesOrDataset); // Debug log
  
  // Check if we received an array of sources (from widget) or a single source (from panel)
  if (Array.isArray(sourcesOrDataset)) {
    // This came from the sources widget - open sources panel
    const sources = sourcesOrDataset;
    ui.displaySources(sources, (source) => {
      // When a source is clicked in the panel, open detail panel
      if (lastResults && lastResults.length > 0) {
        const detailedSources = lastResults.map(doc => ({
          document_part_id: doc.document_part_id,
          source_path: doc.source_path,
          source_type: doc.source_type,
          score: doc.maxScore,
          chunk_count: doc.chunkCount
        }));
        openDetail(source.document_part_id, detailedSources, source.source_type || 'filesystem', source.source_path || '');
      } else {
        // Fallback for single document
        openDetail(source.document_part_id, sources, source.source_type || 'filesystem', source.source_path || '');
      }
    });
    ui.toggleSourcesPanel(true);
  } else {
    // This came from the sources panel - open detail panel directly
    const source = sourcesOrDataset;
    if (lastResults && lastResults.length > 0) {
      const sources = lastResults.map(doc => ({
        document_part_id: doc.document_part_id,
        source_path: doc.source_path,
        source_type: doc.source_type,
        score: doc.maxScore,
        chunk_count: doc.chunkCount
      }));
      openDetail(source.docId, sources, source.sourceType || 'filesystem', source.sourcePath || '');
    } else {
      // Fallback: single document
      openDetail(source.docId, [source], source.sourceType || 'filesystem', source.sourcePath || '');
    }
  }
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  
  if (!input || !sendBtn) return;
  
  const message = input.value.trim();
  if (!message || isAwaitingResponse) return;
  
  const searchModeSelect = document.getElementById('searchModeSelect');
  const topKInput = document.getElementById('topKInput');
  
  if (!searchModeSelect || !topKInput) return;
  
  const searchMode = searchModeSelect.value;
  const topK = parseInt(topKInput.value) || 10;
  
  input.value = '';
  sendBtn.disabled = true;
  
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
    if (sendBtn) sendBtn.disabled = false;
    if (input) input.focus();
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
          ui.attachSourcesToMessage(messageId, msg.sources, (sources) => {
            onSourceClick(sources);
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
  try {
    availableModels = await api.loadModels();
  } catch (e) {
    console.error('Failed to load models:', e);
    availableModels = [];
  }
  
  const modeSelect = document.getElementById('searchModeSelect');
  const isHybrid = modeSelect ? modeSelect.value === 'hybrid' : true;
  
  if (availableModels && availableModels.length > 0) {
    selectedModel = availableModels[0];
    ui.updateModelBadge(`🧠 ${selectedModel}`);
    ui.updateModelSelector(availableModels, selectedModel);
  } else {
    ui.updateModelBadge('Ollama not running');
    ui.updateModelSelector([], null);
  }
  
  // Show model selector in hybrid mode regardless of model availability
  if (isHybrid) {
    ui.showModelSelector(true);
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
  
  // Hide sources button in header
  const hideSourcesBtn = document.getElementById('hideSourcesBtn');
  if (hideSourcesBtn) {
    hideSourcesBtn.addEventListener('click', () => ui.toggleSourcesPanel(false));
  }
  
  // Collapsible sidebar functionality
  const sidebar = document.getElementById('searchSidebar');
  const collapseBtn = document.getElementById('collapseSidebarBtn');
  const mainContent = document.querySelector('.search-main');
  
  if (collapseBtn && sidebar && mainContent) {
    collapseBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      mainContent.classList.toggle('expanded');
      collapseBtn.textContent = sidebar.classList.contains('collapsed') ? '→' : '←';
    });
  }
  
  // Chip suggestions
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.getElementById('chatInput').value = chip.textContent;
      sendMessage();
    });
  });
  
  window.loadConversationFn = loadConversation;
  window.deleteConversationFn = deleteConversation
  
  loadModels();
  loadAndDisplayConversations();
  
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
      // Show selector in hybrid mode regardless of model availability
      ui.showModelSelector(modeSelect.value === 'hybrid');
    });
  }
  
  // Chip suggestions
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent;
      sendMessage();
    });
  });
 
  window.loadConversationFn = loadConversation;
  window.deleteConversationFn = deleteConversation

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
