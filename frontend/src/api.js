const API_BASE = '/api';

async function request(method, url, body, headers = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    method,
    headers,
    body
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listUploads(q) {
    const qs = q && q.trim() ? `?${new URLSearchParams({ q: q.trim() }).toString()}` : '';
    return request('GET', `/uploads${qs}`);
  },
  getUpload(id) {
    return request('GET', `/uploads/${id}`);
  },
  getSegments(id) {
    return request('GET', `/uploads/${id}/segments`);
  },
  updateUpload(id, payload) {
    return request('PATCH', `/uploads/${id}`, JSON.stringify(payload), {
      'Content-Type': 'application/json'
    });
  },
  renameUpload(id, display_name) {
    return this.updateUpload(id, { display_name });
  },
  deleteUpload(id) {
    return request('DELETE', `/uploads/${id}`);
  },
  createUpload(formData) {
    return request('POST', '/uploads', formData);
  },
  reprocessUpload(id, payload) {
    return request('POST', `/uploads/${id}/reprocess`, JSON.stringify(payload), {
      'Content-Type': 'application/json'
    });
  },
  getJob(id) {
    return request('GET', `/jobs/${id}`);
  },
  getJobStats() {
    return request('GET', '/jobs/stats');
  },
  listActiveJobs() {
    return request('GET', '/jobs/active');
  },
  listPrompts() {
    return request('GET', '/prompts');
  },
  updatePrompt(id, payload) {
    return request('PUT', `/prompts/${id}`, JSON.stringify(payload), {
      'Content-Type': 'application/json'
    });
  }
};

