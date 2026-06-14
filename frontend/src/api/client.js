const BASE = '';

// WHY: Backend'de API_TOKEN ayarlıysa veri uçları "Authorization: Bearer <token>"
// bekler. Token build sırasında VITE_API_TOKEN ile verilebilir; verilmezse
// (yerel geliştirme, auth kapalı) header eklenmez.
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

function buildHeaders(extra = {}) {
  const headers = { 'Content-Type': 'application/json', ...extra };
  if (API_TOKEN) {
    headers.Authorization = `Bearer ${API_TOKEN}`;
  }
  return headers;
}

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: buildHeaders(options.headers),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore parse error */ }
    throw new Error(detail);
  }

  return res.json();
}

export function fetchHealth() {
  return request('/health');
}

export function fetchRecentContacts() {
  return request('/recent-contacts');
}

export function postSearch(query, topK = 5) {
  return request('/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}

function parseSSE(raw) {
  let event = 'message';
  const dataLines = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    return null;
  }
}

// Streaming RAG Q&A. Olaylar: sources -> token* -> done (veya error).
// callbacks: { onSources, onToken, onDone, onError, signal }
export async function postSearchStream(query, topK = 5, callbacks = {}) {
  const { onSources, onToken, onDone, onError, signal } = callbacks;
  let res;
  try {
    res = await fetch(`${BASE}/search-stream`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({ query, top_k: topK }),
      signal,
    });
  } catch (err) {
    onError?.(err);
    return;
  }

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore */ }
    onError?.(new Error(detail));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const evt = parseSSE(raw);
        if (!evt) continue;
        if (evt.event === 'sources') onSources?.(evt.data);
        else if (evt.event === 'token') onToken?.(evt.data.text);
        else if (evt.event === 'done') onDone?.(evt.data);
        else if (evt.event === 'error') onError?.(new Error(evt.data.detail || 'stream error'));
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') onError?.(err);
  }
}

export function postAsk(query, topK = 5) {
  return request('/ask', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export function postSummarize(contactEmail, limit = 15) {
  return request('/summarize', {
    method: 'POST',
    body: JSON.stringify({ contact_email: contactEmail, limit }),
  });
}

export function postReplySuggest(contactEmail, tone = 'friendly') {
  return request('/reply-suggest', {
    method: 'POST',
    body: JSON.stringify({ contact_email: contactEmail, tone }),
  });
}
