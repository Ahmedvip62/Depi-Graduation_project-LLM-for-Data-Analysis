import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  BarChart3,
  BrainCircuit,
  FileText,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react';
import FileUpload from './components/FileUpload';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import DataOverview from './components/DataOverview';
import SessionSidebar from './components/SessionSidebar';
import ContextRing from './components/ContextRing';
import LoadingBar from './components/LoadingBar';
import ChartGallery from './components/ChartDrawer';
import ReportButton from './components/ReportButton';
import CommandPalette from './components/CommandPalette';
import Toast from './components/Toast';
import { useFileUpload } from './hooks/useFileUpload';
import { useChat } from './hooks/useChat';
import { useSessions, fetchSessionDetail } from './hooks/useSessions';
import { apiFetch } from './lib/api';
import { downloadReport } from './lib/reportDownload';
import DashboardGrid from './components/DashboardGrid';
import PredictionPanel from './components/PredictionPanel';
import {
  DEFAULT_CONTEXT_WINDOW_TOKENS,
  estimateConversationTokens,
  getLatestAnswerUsage,
} from './lib/tokenUsage';

const TABS = { PROFILE: 'profile', DASHBOARD: 'dashboard', CHAT: 'chat', PREDICTION: 'prediction' };

const TabButton = ({ value, label, activeTab, onSelect }) => (
  <button
    type="button"
    onClick={() => onSelect(value)}
    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
      activeTab === value
        ? 'bg-brand-400 text-surface-sunken shadow-soft'
        : 'text-ink-muted hover:bg-surface-hover hover:text-ink'
    }`}
  >
    {label}
  </button>
);

const isDashboardIntent = (text = '') => {
  const value = text.toLowerCase();
  return ['dashboard', 'visual overview', 'eda', 'exploratory', 'generate charts', 'generate visuals']
    .some((term) => value.includes(term));
};

const normalizeSessionCharts = (rawCharts = [], ownerSessionId = null) =>
  rawCharts
    .map((chart, index) => {
      const config = chart.config || chart.chart_spec;
      if (!config) return null;
      const title = chart.title || config.layout?.title?.text || `Visualization ${index + 1}`;
      const rawId = chart.id || `session-chart-${index}`;
      return {
        id: `${ownerSessionId || 'session'}-${rawId}`,
        artifactId: rawId,
        sessionId: ownerSessionId,
        title,
        description: chart.description || '',
        config,
        source: chart.source || 'chat',
      };
    })
    .filter(Boolean);

function App() {
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [eda, setEda] = useState(null);
  const [input, setInput] = useState('');
  const [draftAttachments, setDraftAttachments] = useState([]);
  const [charts, setCharts] = useState([]);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [tab, setTab] = useState(TABS.PROFILE);
  const [dashboardLayout, setDashboardLayout] = useState(null);
  const [toast, setToast] = useState(null);
  const [isCleaning, setIsCleaning] = useState(false);
  const [capabilities, setCapabilities] = useState({
    image_chat_enabled: true,
    max_chat_images: 3,
    max_chat_image_mb: 5,
    supported_image_mime_types: ['image/png', 'image/jpeg', 'image/webp'],
    supported_chart_types: ['bar', 'line', 'scatter', 'pie', 'histogram', 'heatmap', 'box'],
    supported_chart_aggregations: ['sum', 'mean', 'median', 'min', 'max', 'count'],
    context_window_tokens: DEFAULT_CONTEXT_WINDOW_TOKENS,
  });

  const { isUploading, uploadFile, uploadError, clearError } = useFileUpload();
  const { sessions, refreshSessions, deleteSession } = useSessions();
  const activeSessionRef = useRef(session);
  const sessionLoadRequestRef = useRef(0);

  useEffect(() => {
    activeSessionRef.current = session;
  }, [session]);

  const showToast = useCallback((message, type = 'error') => {
    setToast({ message, type, id: Date.now() });
  }, []);

  useEffect(() => {
    let active = true;
    apiFetch('/api/capabilities')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (active && data) setCapabilities((prev) => ({ ...prev, ...data }));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Global Cmd/Ctrl+K opens the command palette.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const onTurnComplete = useCallback(() => {
    refreshSessions();
  }, [refreshSessions]);

  const handleCommand = useCallback((payload) => {
    const commandSession = payload?.session_id || activeSessionRef.current;
    if (commandSession && commandSession !== activeSessionRef.current) return;

    if (payload?.command === 'show_dashboard') {
      setTab(TABS.DASHBOARD);
    }
    if (payload?.command === 'dashboard_layout') {
      setDashboardLayout(payload.layout);
    }
    if (payload?.command === 'download_report') {
      downloadReport(commandSession).catch((err) => {
        showToast(err.message || 'Report generation failed.');
      });
    }
  }, [showToast]);

  const { messages, isLoading, sendMessage, regenerate, hydrateMessages, clearChat, stop } =
    useChat(session, setCharts, onTurnComplete, handleCommand);


  const handleSelectFile = useCallback(
    async (file) => {
      const requestId = ++sessionLoadRequestRef.current;
      const data = await uploadFile(file);
      if (data && requestId === sessionLoadRequestRef.current) {
        setSession(data.session_id);
        setProfile(data.profile || null);
        setEda(data.eda || null);
        setCharts([]);
        setDashboardLayout(null);

        // Load chat history (includes cleaning summary) instead of clearing
        try {
          const detail = await fetchSessionDetail(data.session_id);
          hydrateMessages(detail.chat_history || []);
        } catch {
          clearChat();
        }

        setTab(TABS.PROFILE);
        refreshSessions();

        // Show cleaning results toast
        if (data.cleaning_applied && data.cleaning_actions?.length > 0) {
          const count = data.cleaning_actions.length;
          showToast(`🧹 LLM cleaned dataset: ${count} action${count > 1 ? 's' : ''} applied`, 'success');
        }
      }
    },
    [uploadFile, clearChat, hydrateMessages, refreshSessions, showToast]
  );

  const handleNewSession = useCallback(() => {
    sessionLoadRequestRef.current += 1;
    setSession(null);
    setProfile(null);
    setEda(null);
    setCharts([]);
    setDashboardLayout(null);
    clearChat();
    clearError();
    setSidebarOpen(false);
    setTab(TABS.PROFILE);
  }, [clearChat, clearError]);

  const handleSelectSession = useCallback(
    async (id) => {
      const requestId = ++sessionLoadRequestRef.current;
      stop();
      setSidebarOpen(false);
      try {
        const detail = await fetchSessionDetail(id);
        if (requestId !== sessionLoadRequestRef.current) return;
        setSession(id);
        const restoredCharts = normalizeSessionCharts(detail.charts || [], id);
        setProfile(detail.profile || null);
        setEda(detail.profile?.eda || detail.eda || null);
        setCharts(restoredCharts);
        setDashboardLayout(detail.dashboard_layout || null);
        hydrateMessages(detail.chat_history || []);
        setTab(restoredCharts.length > 0 ? TABS.DASHBOARD : ((detail.chat_history || []).length > 0 ? TABS.CHAT : TABS.PROFILE));
      } catch (err) {
        if (requestId !== sessionLoadRequestRef.current) return;
        showToast(err.message || 'Could not load that session.');
      }
    },
    [hydrateMessages, showToast, stop]
  );

  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        await deleteSession(id);
        if (id === session) {
          sessionLoadRequestRef.current += 1;
          setSession(null);
          setProfile(null);
          setEda(null);
          setCharts([]);
          setDashboardLayout(null);
          clearChat();
          setTab(TABS.PROFILE);
        }
      } catch (err) {
        showToast(err.message || 'Could not delete that session.');
      }
    },
    [deleteSession, session, clearChat, showToast]
  );

  const handleCleanDataset = useCallback(
    async (instructions, createNewSession) => {
      try {
        setIsCleaning(true);
        const response = await apiFetch('/api/clean', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: session,
            instructions: instructions || null,
            create_new_session: createNewSession || false,
          }),
        });
        if (!response.ok) {
          throw new Error(await readError(response, 'Data cleaning failed.'));
        }
        const result = await response.json();
        showToast(result.message || 'Dataset cleaned successfully!', 'success');
        
        // Reload or switch to the target session
        await handleSelectSession(result.session_id);
      } catch (err) {
        showToast(err.message || 'Data cleaning failed.');
      } finally {
        setIsCleaning(false);
      }
    },
    [session, handleSelectSession, showToast]
  );

  const handleSend = useCallback(
    (text, enableThinking, attachments = []) => {
      setTab(isDashboardIntent(text) ? TABS.DASHBOARD : TABS.CHAT);
      sendMessage(text, enableThinking, attachments);
      setInput('');
    },
    [sendMessage]
  );

  const handleSuggestion = useCallback(
    (text) => {
      setTab(isDashboardIntent(text) ? TABS.DASHBOARD : TABS.CHAT);
      sendMessage(text, false, []);
    },
    [sendMessage]
  );

  const usedTokens = useMemo(
    () => estimateConversationTokens(messages, input, draftAttachments),
    [messages, input, draftAttachments]
  );
  const latestUsage = useMemo(() => getLatestAnswerUsage(messages), [messages]);
  const maxTokens = capabilities.context_window_tokens || DEFAULT_CONTEXT_WINDOW_TOKENS;
  const hasData = Boolean(session);
  const activeCharts = useMemo(
    () => charts.filter((chart) => !chart.sessionId || chart.sessionId === session),
    [charts, session]
  );
  const generatedCharts = useMemo(() => activeCharts.filter((chart) => chart.source === 'chat'), [activeCharts]);

  const askPrompt = useCallback(
    (text) => {
      setTab(isDashboardIntent(text) ? TABS.DASHBOARD : TABS.CHAT);
      sendMessage(text, false, []);
    },
    [sendMessage]
  );

  // Command palette entries. Built from the current app state so unavailable
  // actions (e.g. "export PDF" with no session) are disabled rather than hidden.
  const paletteCommands = useMemo(() => {
    const nav = [
      { id: 'go-dashboard', label: 'Go to dashboard', group: 'Navigate', icon: <LayoutDashboard className="h-4 w-4" strokeWidth={1.8} />, run: () => setTab(TABS.DASHBOARD), disabled: !hasData },
      { id: 'go-chat', label: 'Go to chat', group: 'Navigate', icon: <MessageSquare className="h-4 w-4" strokeWidth={1.8} />, run: () => setTab(TABS.CHAT), disabled: !hasData },
      { id: 'open-visuals', label: 'Open visual gallery', hint: `${activeCharts.length} saved`, group: 'Navigate', icon: <BarChart3 className="h-4 w-4" strokeWidth={1.8} />, run: () => setGalleryOpen(true), disabled: !hasData },
      { id: 'toggle-sidebar', label: 'Toggle sessions', group: 'Navigate', icon: <Menu className="h-4 w-4" strokeWidth={1.8} />, run: () => setSidebarOpen((o) => !o) },
    ];
    const actions = [
      { id: 'new-analysis', label: 'New analysis', group: 'Actions', icon: <Plus className="h-4 w-4" strokeWidth={1.8} />, run: handleNewSession },
      { id: 'gen-dashboard', label: 'Generate dashboard', hint: 'Ask the model for visuals', group: 'Actions', icon: <Sparkles className="h-4 w-4" strokeWidth={1.8} />, run: () => askPrompt('Generate a dashboard for this dataset'), disabled: !hasData || isLoading },
      { id: 'regenerate', label: 'Regenerate last answer', group: 'Actions', icon: <RefreshCw className="h-4 w-4" strokeWidth={1.8} />, run: regenerate, disabled: !hasData || isLoading || messages.length < 2 },
      { id: 'export-pdf', label: 'Export PDF report', group: 'Actions', icon: <FileText className="h-4 w-4" strokeWidth={1.8} />, run: () => session && downloadReport(session).catch((err) => showToast(err.message || 'Report generation failed.')), disabled: !hasData },
    ];
    return [...nav, ...actions];
  }, [hasData, isLoading, messages.length, session, activeCharts.length, handleNewSession, regenerate, askPrompt, showToast]);



  return (
    <div className="relative flex h-screen overflow-hidden bg-surface font-sans text-ink">
      <LoadingBar isLoading={isUploading || isLoading} />

      <SessionSidebar
        sessions={sessions}
        currentSession={session}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="z-30 flex w-full flex-none items-start justify-between gap-3 border-b border-surface-line bg-surface-raised/88 px-4 py-3 backdrop-blur-md sm:items-center sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-9 w-9 flex-none items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink md:hidden"
              aria-label="Open sessions"
            >
              <Menu className="h-5 w-5" strokeWidth={2} />
            </button>
            <div className="min-w-0">
              <h1 className="truncate font-display text-base font-semibold tracking-tight text-ink sm:text-lg">
                {profile?.file_name || 'Universal Analyst'}
              </h1>
              {profile ? (
                <p className="truncate text-2xs data-label">
                  {profile.row_count?.toLocaleString()} rows · {profile.column_count} cols
                </p>
              ) : (
                <p className="truncate text-2xs data-label">Analysis workspace</p>
              )}
            </div>
          </div>

          <div className="flex flex-none flex-wrap items-center justify-end gap-2 sm:gap-3">
            {hasData && (
              <div className="hidden items-center rounded-xl border border-surface-line bg-surface-sunken p-1 sm:flex">
                <TabButton value={TABS.PROFILE} label="Profile" activeTab={tab} onSelect={setTab} />
                <TabButton value={TABS.DASHBOARD} label="Dashboard" activeTab={tab} onSelect={setTab} />
                <TabButton value={TABS.CHAT} label="Chat" activeTab={tab} onSelect={setTab} />
                <TabButton value={TABS.PREDICTION} label="Prediction" activeTab={tab} onSelect={setTab} />
              </div>
            )}

            {hasData && <ReportButton sessionId={session} onError={showToast} />}

            <button
              type="button"
              onClick={() => setGalleryOpen(true)}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-surface-line bg-surface-muted px-3 text-xs font-semibold text-brand-100 transition-colors hover:border-brand-400 hover:bg-surface-hover"
              title="View visualizations"
            >
              <BarChart3 className="h-4 w-4" strokeWidth={1.8} />
              <span className="hidden sm:inline">Visuals{activeCharts.length > 0 ? ` (${activeCharts.length})` : ''}</span>
            </button>

            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="flex h-9 items-center gap-2 rounded-lg border border-surface-line bg-surface-sunken px-3 text-xs font-medium text-ink-muted transition-colors hover:border-brand-400 hover:text-brand-100"
              title="Open command palette"
              aria-label="Open command palette"
            >
              <Search className="h-3.5 w-3.5" strokeWidth={1.8} />
              <span className="hidden md:inline">Search</span>
              <kbd className="hidden rounded border border-surface-line bg-surface-raised px-1.5 py-0.5 font-mono text-2xs text-ink-muted md:block">
                ⌘K
              </kbd>
            </button>

            <ContextRing usedTokens={usedTokens} maxTokens={maxTokens} latestUsage={latestUsage} />
          </div>
        </header>

        {hasData && (
          <div className="flex flex-none border-b border-surface-line bg-surface-sunken px-4 py-2 sm:hidden">
            <div className="grid w-full grid-cols-4 rounded-xl border border-surface-line bg-surface-muted p-1">
              <TabButton value={TABS.PROFILE} label="Profile" activeTab={tab} onSelect={setTab} />
              <TabButton value={TABS.DASHBOARD} label="Dashboard" activeTab={tab} onSelect={setTab} />
              <TabButton value={TABS.CHAT} label="Chat" activeTab={tab} onSelect={setTab} />
              <TabButton value={TABS.PREDICTION} label="Predict" activeTab={tab} onSelect={setTab} />
            </div>
          </div>
        )}

        {!hasData ? (
          <div className="flex-1 overflow-y-auto scroll-thin">
            <FileUpload
              onSelectFile={handleSelectFile}
              isUploading={isUploading}
              error={uploadError}
              onClearError={clearError}
            />
          </div>
        ) : tab === TABS.PROFILE ? (
          <div className="flex-1 overflow-y-auto scroll-thin">
            <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6">
              <DataOverview
                profile={profile}
                eda={eda}
                sessionCharts={[]}
                onSuggestion={handleSuggestion}
                onChartError={showToast}
                onCleanDataset={handleCleanDataset}
                isCleaning={isCleaning}
              />
            </div>
          </div>
        ) : tab === TABS.DASHBOARD ? (
          <div className="flex-1 overflow-y-auto scroll-thin">
            <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6">
              <DashboardGrid
                charts={generatedCharts}
                layout={dashboardLayout}
                profile={profile}
                onChartError={showToast}
                onSuggestion={handleSuggestion}
              />
            </div>
          </div>
        ) : tab === TABS.PREDICTION ? (
          <div className="flex-1 overflow-y-auto scroll-thin">
            <div className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6">
              <PredictionPanel
                sessionId={session}
                profile={profile}
                onError={showToast}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col overflow-hidden px-4 sm:px-6">
              <MessageList
                messages={messages}
                suggestions={eda?.suggestions || []}
                onSuggestion={handleSuggestion}
                exportError={showToast}
                onRegenerate={regenerate}
                isLoading={isLoading}
              />
              <ChatInput
                input={input}
                setInput={setInput}
                handleSendMessage={handleSend}
                isLoading={isLoading}
                onStop={stop}
                onError={showToast}
                imageChatEnabled={capabilities.image_chat_enabled !== false}
                maxImages={capabilities.max_chat_images || 3}
                maxImageMb={capabilities.max_chat_image_mb || 5}
                acceptedImageTypes={capabilities.supported_image_mime_types}
                onDraftAttachmentsChange={setDraftAttachments}
              />
            </div>
          </div>
        )}

        <ChartGallery
          isOpen={galleryOpen}
          onClose={() => setGalleryOpen(false)}
          charts={activeCharts}
          onError={showToast}
        />
      </main>

      <CommandPalette
        open={paletteOpen}
        commands={paletteCommands}
        onClose={() => setPaletteOpen(false)}
      />
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

export default App;
