import { useState, useCallback, useEffect } from 'react';
import { apiFetch, readError } from '../lib/api';

/**
 * Loads the session list from GET /api/sessions.
 * Backend returns: [{ id, title, file_name, row_count, chart_count, message_count }]
 */
export const useSessions = () => {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiFetch('/api/sessions');
      if (!response.ok) {
        throw new Error(await readError(response, 'Failed to fetch sessions.'));
      }
      const data = await response.json();
      setSessions(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch sessions.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const deleteSession = useCallback(async (id) => {
    const response = await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' });
    if (!response.ok) {
      throw new Error(await readError(response, 'Failed to delete session.'));
    }
    // Optimistically remove from the list; the caller handles app state.
    setSessions((prev) => prev.filter((s) => s.id !== id));
    return true;
  }, []);

  return {
    sessions,
    isLoading,
    error,
    refreshSessions: fetchSessions,
    deleteSession,
  };
};

export const fetchSessionDetail = async (id) => {
  const response = await apiFetch(`/api/sessions/${id}`);
  if (!response.ok) {
    throw new Error(await readError(response, 'Failed to load session.'));
  }
  return response.json();
};
