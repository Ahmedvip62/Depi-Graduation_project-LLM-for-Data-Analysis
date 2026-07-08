import { useState, useCallback, useRef } from 'react';
import { apiFetch, readError } from '../lib/api';

let _seq = 0;
const nextId = () => `${Date.now()}-${_seq++}`;

const toBackendAttachment = (attachment) => ({
  type: attachment.type || 'image',
  mime_type: attachment.mime_type,
  data: attachment.data,
  name: attachment.name,
  size: attachment.size,
});

const toDisplayAttachment = (attachment) => ({
  id: attachment.id || nextId(),
  type: attachment.type || 'image',
  mime_type: attachment.mime_type,
  name: attachment.name,
  size: attachment.size,
  url: attachment.url,
});

const toDisplayChart = (chart, index) => {
  const config = chart.config || chart.chart_spec;
  if (!config) return null;
  return {
    id: chart.id || `history-chart-${index}`,
    title: chart.title || config.layout?.title?.text || `Visualization ${index + 1}`,
    description: chart.description || '',
    config,
    source: chart.source || 'chat',
  };
};

export const useChat = (sessionId, setCharts, onTurnComplete, onCommand) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const isLoadingRef = useRef(false);

  const hydrateMessages = useCallback((history) => {
    if (!Array.isArray(history)) {
      setMessages([]);
      return;
    }
    setMessages(
      history.map((m) => ({
        id: nextId(),
        role: m.role,
        content: m.content || '',
        attachments: m.attachments || [],
        thinking: '',
        skill: null,
        phase: null,
        action: null,
        agent_name: m.role === 'assistant' ? 'Analyst' : null,
        charts: (m.charts || []).map(toDisplayChart).filter(Boolean),
        usage: null,
        done: true,
      }))
    );
  }, []);

  const clearChat = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    isLoadingRef.current = false;
    setIsLoading(false);
    setMessages([]);
    setError(null);
  }, []);

  // Shared stream runner. `assistantId` is the message id to patch; `displayText`
  // and `attachments` are the user turn being answered (re-sent to the backend).
  const streamAssistant = useCallback(
    async (assistantId, displayText, enableThinking, attachments) => {
      const cleanAttachments = Array.isArray(attachments) ? attachments : [];
      const patch = (updater) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, ...updater(m) } : m))
        );

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await apiFetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            message: displayText,
            enable_thinking: enableThinking,
            attachments: cleanAttachments.map(toBackendAttachment),
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(await readError(response, 'Failed to reach the analyst.'));
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let chartIndex = 0;

        const handleFrame = (frame) => {
          let eventName = 'message';
          const dataLines = [];
          for (const raw of frame.split('\n')) {
            const line = raw.replace(/\r$/, '');
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              dataLines.push(line.slice(5).replace(/^ /, ''));
            }
          }
          if (dataLines.length === 0) return;

          const dataStr = dataLines.join('\n');
          if (dataStr === '[DONE]') {
            patch(() => ({ done: true, phase: null, action: null }));
            return;
          }

          let payload;
          try {
            payload = JSON.parse(dataStr);
          } catch {
            return;
          }

          switch (eventName) {
            case 'skill':
              patch(() => ({
                skill: {
                  skill: payload.skill,
                  label: payload.label || payload.skill,
                  reason: payload.reason || '',
                },
                phase: 'routing',
              }));
              break;

            case 'command':
              onCommand?.(payload);
              break;

            case 'dashboard_layout':
              onCommand?.({ command: 'dashboard_layout', layout: payload.layout, session_id: payload.session_id });
              break;

            case 'thinking':
              patch((m) => ({
                thinking: (m.thinking || '') + (payload.token || ''),
                phase: 'thinking',
              }));
              break;

            case 'action':
              patch(() => ({
                phase: payload.action === 'thinking' ? 'thinking' : 'acting',
                action: { action: payload.action, label: payload.label || payload.action },
              }));
              break;

            case 'token':
              patch((m) => ({
                content: (m.content || '') + (payload.token || ''),
                agent_name: payload.agent_name || m.agent_name,
                phase: 'answering',
              }));
              break;

            case 'usage':
              patch(() => ({ usage: payload }));
              break;

            case 'chart': {
              const spec = payload.chart_spec;
              if (!spec) break;
              const title = payload.title || spec.layout?.title?.text || `Visualization ${chartIndex + 1}`;
              const sourceSessionId = payload.session_id || sessionId;
              const rawId = payload.id || `${assistantId}-chart-${payload.index ?? chartIndex}`;
              const chart = {
                id: `${sourceSessionId || 'session'}-${rawId}`,
                artifactId: rawId,
                sessionId: sourceSessionId,
                title,
                description: payload.description || '',
                config: spec,
                source: payload.source || 'chat',
              };
              chartIndex += 1;
              patch((m) => ({ charts: [...(m.charts || []), chart] }));
              if (setCharts) {
                setCharts((prev) =>
                  prev.some((c) => c.id === chart.id) ? prev : [...prev, chart]
                );
              }
              break;
            }

            case 'done':
              patch(() => ({ done: true, phase: null, action: null }));
              break;

            case 'error':
              patch((m) => ({
                done: payload.status === 'error' ? true : m.done,
                phase: payload.status === 'error' ? null : m.phase,
                isError: true,
                content:
                  (m.content ? `${m.content}\n\n` : '') +
                  (payload.message || 'The analyst encountered an error.'),
              }));
              setError(payload.message || 'Stream error');
              break;

            default:
              break;
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let delimIdx;
          while ((delimIdx = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, delimIdx);
            buffer = buffer.slice(delimIdx + 2);
            if (frame.trim()) handleFrame(frame);
          }
        }

        buffer += decoder.decode();
        if (buffer.trim()) handleFrame(buffer);

        patch((m) => ({ done: true, phase: null, action: null, agent_name: m.agent_name || 'Analyst' }));
      } catch (err) {
        if (err.name === 'AbortError') {
          patch(() => ({ done: true, phase: null, action: null }));
        } else {
          patch((m) => ({
            done: true,
            phase: null,
            action: null,
            isError: true,
            content: m.content || err.message || 'An unexpected error occurred.',
          }));
          setError(err.message);
        }
      } finally {
        abortRef.current = null;
        isLoadingRef.current = false;
        setIsLoading(false);
        if (onTurnComplete) onTurnComplete();
      }
    },
    [sessionId, setCharts, onTurnComplete, onCommand]
  );

  const sendMessage = useCallback(
    async (content, enableThinking = false, attachments = []) => {
      const text = (content || '').trim();
      const cleanAttachments = Array.isArray(attachments) ? attachments : [];
      if ((!text && cleanAttachments.length === 0) || !sessionId || isLoadingRef.current) return;

      const displayText = text || 'Please analyze the attached image in the context of this dataset.';
      const displayAttachments = cleanAttachments.map(toDisplayAttachment);
      const assistantId = nextId();

      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: 'user',
          content: displayText,
          attachments: displayAttachments,
          done: true,
        },
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          thinking: '',
          skill: null,
          phase: 'queued',
          action: { action: 'queued', label: 'Starting analysis' },
          agent_name: 'Routing',
          charts: [],
          usage: null,
          done: false,
          isError: false,
        },
      ]);
      isLoadingRef.current = true;
      setIsLoading(true);
      setError(null);

      await streamAssistant(assistantId, displayText, enableThinking, cleanAttachments);
    },
    [sessionId, streamAssistant]
  );

  // Regenerate: drop the trailing assistant turn and re-stream the last user
  // message without duplicating it. If the last user turn had attachments, those
  // are re-sent too (display copies are rebuilt from the stored user message).
  const regenerate = useCallback(async () => {
    if (isLoadingRef.current || !sessionId) return;
    setMessages((prev) => {
      if (prev.length < 2) return prev;
      // Find the last assistant turn and the user turn that prompted it.
      let lastAssistantIdx = -1;
      for (let i = prev.length - 1; i >= 0; i--) {
        if (prev[i].role === 'assistant') { lastAssistantIdx = i; break; }
      }
      if (lastAssistantIdx === -1) return prev;
      const userTurn = prev.slice(0, lastAssistantIdx).reverse().find((m) => m.role === 'user');
      if (!userTurn) return prev;
      // Drop everything from the last assistant turn onward.
      const trimmed = prev.slice(0, lastAssistantIdx);
      const assistantId = nextId();
      trimmed.push({
        id: assistantId,
        role: 'assistant',
        content: '',
        thinking: '',
        skill: null,
        phase: 'queued',
        action: { action: 'queued', label: 'Regenerating' },
        agent_name: 'Routing',
        charts: [],
        usage: null,
        done: false,
        isError: false,
      });
      // Kick off the stream after state is set.
      isLoadingRef.current = true;
      setIsLoading(true);
      setError(null);
      streamAssistant(
        assistantId,
        userTurn.content,
        false,
        (userTurn.attachments || []).map((a) => ({
          type: a.type || 'image',
          mime_type: a.mime_type,
          data: a.data,
          name: a.name,
          size: a.size,
        })).filter((a) => a.data)
      );
      return trimmed;
    });
  }, [sessionId, streamAssistant]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    regenerate,
    clearChat,
    hydrateMessages,
    stop,
  };
};
