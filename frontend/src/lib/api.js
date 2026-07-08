// Tiny API base helper used by all fetches.
//
// In development the Vite proxy maps `/api` -> http://localhost:8000 (stripping
// `/api`), so VITE_API_BASE stays '' and `fetch('/api/...')` just works.
//
// In production the frontend is built as a static SPA and served from `dist/`.
// It calls `${API_BASE}/api/...`. Default API_BASE is '' so that a reverse
// proxy can forward `/api` to the backend. If the backend lives on a different
// origin, set VITE_API_BASE (e.g. "https://gpu-host:8000") at build time.
export const API_BASE = import.meta.env.VITE_API_BASE || '';

/** Build a fully-qualified API path. */
export const apiUrl = (path) => {
  const clean = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${clean}`;
};

/** Thin fetch wrapper that prefixes the API base. */
export const apiFetch = (path, options) => fetch(apiUrl(path), options);

/** Best-effort extraction of an error message from a failed Response. */
export const readError = async (response, defaultMessage = 'Request failed.') => {
  try {
    const data = await response.json();
    return data.detail || data.message || defaultMessage;
  } catch {
    return defaultMessage;
  }
};
