import { mount as mountIndex, unmount as unmountIndex }   from './views/index.js';
import { mount as mountSearch, unmount as unmountSearch } from './views/search.js';
import { mount as mountRuns, unmount as unmountRuns }   from './views/runs.js';
import { mount as mountStorage, unmount as unmountStorage } from './views/storage.js';


// ── Shared state ────────────────────────────────────────────
export let API_BASE = 'http://localhost:8000';
export let CLIENT_BASE = 'http://localhost:3000';

export function getBase() {
  return document.getElementById('apiBase').value.replace(/\/$/, '');
}

export function getClientBase() {
  return CLIENT_BASE;
}

export function showError(msg) {
  const el = document.getElementById('errorMsg');
  el.textContent = msg;
  el.style.display = 'block';
}

export function clearError() {
  document.getElementById('errorMsg').style.display = 'none';
}

export function fmtDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso), diff = Date.now() - d;
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return d.toLocaleDateString('de-DE', { month: 'short', day: 'numeric', year: '2-digit' });
  } catch { return iso; }
}

// ── API client ──────────────────────────────────────────────
export const api = {
  get(path) {
    return fetch(getBase() + path).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  },
  post(path, body) {
    return fetch(getBase() + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  },
};

// ── Theme ────────────────────────────────────────────────────
const THEME_KEY = 'sw-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'dark';
  applyTheme(saved);

  document.getElementById('themeToggle').addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });
}

// ── Router ──────────────────────────────────────────────────
const VIEWS = {
  index:  { mount: mountIndex,  unmount: unmountIndex  },
  search: { mount: mountSearch, unmount: unmountSearch },
  runs:   { mount: mountRuns,   unmount: unmountRuns   },
  storage: { mount: mountStorage, unmount: unmountStorage },
};

let currentTab = null;
const app = document.getElementById('app');
const refreshBtn = document.getElementById('refreshBtn');

function switchTab(name) {
  if (currentTab && VIEWS[currentTab]) VIEWS[currentTab].unmount();
  currentTab = name;

  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === name);
  });

  clearError();
  refreshBtn.style.display = '';
  VIEWS[name].mount(app);
}

// Refresh button delegates to the active view
refreshBtn.addEventListener('click', () => {
  if (currentTab && VIEWS[currentTab]) {
    VIEWS[currentTab].unmount();
    VIEWS[currentTab].mount(app);
  }
});

refreshBtn.addEventListener('click', () => {
  if (currentTab && VIEWS[currentTab]) {
    VIEWS[currentTab].unmount();
    VIEWS[currentTab].mount(app);
  }
});

document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => switchTab(t.dataset.tab));
});



// Tab clicks
//document.querySelectorAll('.tab').forEach(t => {
// t.addEventListener('click', () => switchTab(t.dataset.tab));
//});

// ── Bootstrap ───────────────────────────────────────────────
async function bootstrap() {
  initTheme();
  try {
    const config = await fetch('/config').then(r => r.json());
    API_BASE = config.api_url;
    CLIENT_BASE = config.client_url
    document.getElementById('apiBase').value = API_BASE;
  } catch {
    // /config unreachable (e.g. opening file:// directly) — keep default
  }
  switchTab('index');
}

bootstrap();
