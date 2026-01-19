const API_BASE = '/api';

export const api = {
  async get(url) {
    const response = await fetch(`${API_BASE}${url}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  },

  async post(url, data) {
    const response = await fetch(`${API_BASE}${url}`, {
      method: 'POST',
      headers: data instanceof FormData ? {} : { 'Content-Type': 'application/json' },
      body: data instanceof FormData ? data : JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  },

  async put(url, data) {
    const response = await fetch(`${API_BASE}${url}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  },

  async delete(url) {
    const response = await fetch(`${API_BASE}${url}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    if (response.status === 204) return null;
    return response.json();
  },

  async uploadFile(formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          onProgress(percentComplete);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            reject(new Error('Failed to parse response'));
          }
        } else {
          reject(new Error(xhr.statusText || 'Upload failed'));
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error')));
      xhr.open('POST', `${API_BASE}/upload`);
      xhr.send(formData);
    });
  },
};
