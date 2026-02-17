const BASE = '';

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
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

export function postAsk(query, topK = 5) {
  return request('/ask', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export function postSummarize(contactEmail, limit = 5) {
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
