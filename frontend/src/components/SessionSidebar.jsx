import React, { useState } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import Logo from './Logo';

const Mark = () => (
  <div className="flex h-9 w-9 flex-none items-center justify-center rounded-xl border border-brand-400/35 bg-surface-raised text-ink shadow-soft">
    <Logo className="h-5 w-5" />
  </div>
);

const SessionRow = ({ session, active, onSelect, onDelete, mobile = false }) => {
  const [confirming, setConfirming] = useState(false);
  const detailParts = [
    session.file_name ? session.file_name : 'dataset',
    session.row_count != null ? `${session.row_count.toLocaleString()} rows` : null,
    session.chart_count ? `${session.chart_count.toLocaleString()} visuals` : null,
  ].filter(Boolean);

  const handleDelete = (e) => {
    e.stopPropagation();
    if (confirming) {
      onDelete(session.id);
    } else {
      setConfirming(true);
      // Auto-reset the confirm state if the user doesn't click again.
      const t = window.setTimeout(() => setConfirming(false), 3000);
      // Clean up if the row unmounts before the timeout fires.
      return () => window.clearTimeout(t);
    }
  };

  return (
    <li>
      <div
        className={`group relative w-full rounded-xl border px-3 py-2 text-left transition-all ${
          active
            ? 'border-brand-400/60 bg-brand-500/12 text-ink shadow-soft'
            : 'border-transparent text-ink-soft hover:border-surface-line hover:bg-surface-raised'
        }`}
      >
        <button
          type="button"
          onClick={() => onSelect(session.id)}
          className="block w-full pr-8 text-left"
        >
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 flex-none rounded-full ${active ? 'bg-brand-300' : 'bg-ink-ghost'}`} />
            <span className="truncate text-sm font-semibold">
              {session.title || session.file_name || `Session ${String(session.id).slice(0, 6)}`}
            </span>
          </div>
          {detailParts.length > 0 && (
            <div className="mt-0.5 truncate pl-3.5 text-2xs text-ink-faint">
              {detailParts.join(' - ')}
            </div>
          )}
        </button>
        <button
          type="button"
          onClick={handleDelete}
          aria-label={confirming ? `Confirm delete ${session.title || session.file_name || 'session'}` : `Delete ${session.title || session.file_name || 'session'}`}
          title={confirming ? 'Click again to confirm' : 'Delete session'}
          className={`absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-lg transition-colors ${
            confirming
              ? 'bg-danger-500/15 text-danger-500 opacity-100'
              : 'text-ink-muted opacity-0 hover:bg-surface-hover hover:text-danger-500 group-hover:opacity-100 focus-visible:opacity-100'
          } ${mobile ? 'opacity-100' : ''}`}
        >
          <Trash2 className="h-3.5 w-3.5" strokeWidth={1.8} />
        </button>
      </div>
    </li>
  );
};

const SessionSidebar = ({
  sessions = [],
  currentSession,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  isOpen,
  onClose,
}) => {
  const content = (
    <>
      <div className="mb-7 mt-1 flex items-center gap-2.5 px-1">
        <Mark />
        <div className="min-w-0 leading-tight">
          <div className="truncate font-display text-sm font-semibold text-ink">Universal Analyst</div>
          <div className="text-2xs uppercase tracking-wider text-ink-faint">Analysis workspace</div>
        </div>
      </div>

      <button
        type="button"
        onClick={onNewSession}
        className="mb-6 flex w-full items-center justify-between rounded-xl border border-surface-line bg-surface-raised px-4 py-2.5 text-left text-sm font-semibold text-ink shadow-soft transition-all hover:border-brand-400 hover:text-brand-100"
      >
        <span>New analysis</span>
        <span className="text-brand-300"><Plus className="h-4 w-4" strokeWidth={2} /></span>
      </button>

      <div className="-mr-1 flex-1 overflow-y-auto pr-1 scroll-thin">
        <h3 className="mb-3 px-1 text-2xs font-bold uppercase tracking-widest text-ink-faint">Recent sessions</h3>

        {sessions.length > 0 ? (
          <ul className="space-y-1.5">
            {sessions.map((s) => (
              <SessionRow
                key={s.id}
                session={s}
                active={currentSession === s.id}
                onSelect={onSelectSession}
                onDelete={onDeleteSession}
              />
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-surface-line bg-surface-raised px-3 py-3 text-xs text-ink-muted">No saved sessions in memory.</p>
        )}
      </div>

      <div className="mt-2 border-t border-surface-line px-1 pt-4 text-2xs text-ink-faint">
        Local runtime - data stays on this server
      </div>
    </>
  );

  return (
    <>
      <aside className="hidden h-full w-64 flex-col border-r border-surface-line bg-surface-sunken p-4 md:flex">
        {content}
      </aside>

      {isOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/55 backdrop-blur-sm" onClick={onClose} />
          <aside className="absolute left-0 top-0 flex h-full w-72 flex-col border-r border-surface-line bg-surface-sunken p-4 shadow-float animate-slide-in-right">
            {content}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close sessions"
              className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full bg-surface-muted text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
            >
              <X className="h-4 w-4" strokeWidth={2} />
            </button>
          </aside>
        </div>
      )}
    </>
  );
};

export default SessionSidebar;
