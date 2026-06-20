// search-api.js - All API calls
import { api, getBase, authHeaders } from '../../app.js';

// Cache for LLM models
export let llmModelsCache = [];

// Flag to track if we're using server-side LLM (default: true)
// Can be set to false to use direct Ollama calls (legacy mode)
export let useServerSideLLM = true;

export async function loadModels() {
  // Try server-side endpoint first
  if (useServerSideLLM) {
    try {
      const data = await api.get('/llm/models');
      llmModelsCache = data || [];
      return llmModelsCache;
    } catch {
      // Fall back to direct Ollama call
      return await loadModelsDirect();
    }
  }
  return await loadModelsDirect();
}

async function loadModelsDirect() {
  const ollamaBase = getBase().replace(':8000', ':11434').replace(':8080', ':11434');
  try {
    const data = await fetch(`${ollamaBase}/api/tags`).then(r => r.json());
    const models = data.models || [];
    return models.map(m => m.name);
  } catch {
    return [];
  }
}

// Check LLM server health (server-side endpoint)
export async function checkLLMHealth() {
  if (useServerSideLLM) {
    try {
      const health = await api.get('/llm/health');
      return health;
    } catch {
      return { status: 'error', models: [], url: '' };
    }
  }
  // For direct mode, we don't have a health endpoint
  return { status: 'unknown', models: [], url: '' };
}

export async function getConversations(limit = 50) {
  const data = await api.get(`/search/history?limit=${limit}`);
  return data.sessions || [];
}

export async function getConversation(sessionId) {
  const data = await api.get(`/search/sessions/${sessionId}`);
  return { messages: data.messages || [], sessionId };
}

export async function deleteConversation(sessionId) {
  await api.delete(`/search/sessions/${sessionId}`);
}

export async function saveAnswer(sessionId, answer, searchResultsUsed, sources) {
  await api.post(`/search/sessions/${sessionId}/answer`, {
    answer,
    search_results_used: searchResultsUsed,
    sources
  });
}

export async function performSearch(query, topK, sessionId = null) {
  const requestBody = { query, top_k: topK };
  if (sessionId) requestBody.session_id = sessionId;
  return await api.post('/search', requestBody);
}

export async function batchGetDocuments(partIds) {
  if (!partIds.length) return {};
  try {
    const bd = await api.post('/documents/batch_get', { document_part_ids: partIds });
    const enriched = {};
    (bd.documents_parts || []).forEach(p => {
      const id = p.document_part_id || p.part?.document_part_id;
      if (id) enriched[id] = p;
    });
    return enriched;
  } catch {
    return {};
  }
}


export async function streamLLMResponse(query, context, onToken, modelName = 'mistral:7b', signal = null, sessionId = null, resultIds = [], topK = 10) {
  // If using server-side LLM (default), call the API endpoint
  if (useServerSideLLM) {
    await streamLLMFromServer(query, context, onToken, modelName, signal, sessionId, resultIds, topK);
  } else {
    // Legacy: direct Ollama call
    await streamLLMFromOllama(query, context, onToken, modelName, signal);
  }
}

async function streamLLMFromServer(query, context, onToken, modelName, signal, sessionId, resultIds, topK = 10) {
  const requestBody = {
    query,
    context: context || "",
    topK: topK || 10,  // ✅ Use the passed topK
    model: modelName || "mistral:7b",
    result_ids: resultIds || [],
    session_id: sessionId,
    stream: true
  };

  // Use the api client's headers by making a small request to get the key
  // or just use the api client's approach
  const apiKey = localStorage.getItem('apiKey') || '';
  
  const fetchOptions = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify(requestBody),
  };
  
  if (apiKey) {
    fetchOptions.headers['X-API-Key'] = apiKey;
  }
  
  if (signal) {
    fetchOptions.signal = signal;
  }
  
  const apiBase = getBase();
  const response = await fetch(`${apiBase}/llm/generate`, fetchOptions);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`LLM server error: ${response.status} - ${errorText}`);
  }
  
  // Handle SSE stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n\n').filter(Boolean);
    
    for (const line of lines) {
      // SSE format: "data: {...}\n\n"
      if (line.startsWith('data: ')) {
        const dataStr = line.substring(6); // Remove "data: " prefix
        if (dataStr === '[DONE]') {
          // Stream completed
          break;
        }
        try {
          const data = JSON.parse(dataStr);
          if (data.token) {
            onToken(data.token);
          } else if (data.error) {
            throw new Error(data.error);
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e, dataStr);
        }
      }
    }
  }
}

// Legacy: Direct Ollama call (for backward compatibility)
async function streamLLMFromOllama(query, context, onToken, modelName, signal) {
  const ollamaBase = getBase().replace(':8000', ':11434');
  const prompt = `You are a helpful assistant. Answer using ONLY the provided document excerpts. Cite sources with [Document N]. Use conversation history for context.\n\n${context}\n\nQuestion: ${query}`;
  
  const fetchOptions = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: modelName,
      prompt,
      stream: true,
    }),
  };
  
  // Add signal if provided for abort support
  if (signal) {
    fetchOptions.signal = signal;
  }
  
  const response = await fetch(`${ollamaBase}/api/generate`, fetchOptions);
  
  if (!response.ok) throw new Error(`Ollama error: ${response.status}`);
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(Boolean);
    for (const line of lines) {
      try {
        const data = JSON.parse(line);
        if (data.response) onToken(data.response);
      } catch {}
    }
  }
}
