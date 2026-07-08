import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search, CornerDownLeft } from 'lucide-react';

// A Cmd/Ctrl+K command palette. Self-contained keyboard nav:
//   ↑/↓ move selection, Enter runs, Esc closes, typing filters.
// `commands` is an array of { id, label, hint?, icon?, group?, run, disabled? }.
const CommandPalette = ({ open, commands = [], onClose }) => {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Reset state whenever the palette opens.
  useEffect(() => {
    if (open) {
      setQuery('');
      setActive(0);
      // Focus on the next tick so the input is mounted.
      const t = window.setTimeout(() => inputRef.current?.focus(), 0);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => {
      const hay = `${c.label} ${c.group || ''} ${c.hint || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [query, commands]);

  // Keep the active index valid as the filter changes.
  useEffect(() => {
    setActive((prev) => (prev >= filtered.length ? 0 : prev));
  }, [filtered.length]);

  // Scroll the active row into view.
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-idx="${active}"]`);
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'nearest' });
    }
  }, [active, open]);

  const runCommand = (cmd) => {
    if (!cmd || cmd.disabled) return;
    onClose?.();
    // Defer so the palette closes before the command's side effects fire.
    window.setTimeout(() => cmd.run?.(), 0);
  };

  const onKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose?.();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, filtered.length - 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      runCommand(filtered[active]);
    }
  };

  // Group filtered commands preserving their original order/group.
  // (Declared before the early return so the hook order is stable across renders.)
  const grouped = useMemo(() => {
    const order = [];
    const map = new Map();
    filtered.forEach((c) => {
      const g = c.group || 'Actions';
      if (!map.has(g)) {
        map.set(g, []);
        order.push(g);
      }
      map.get(g).push(c);
    });
    return order.map((g) => ({ group: g, items: map.get(g) }));
  }, [filtered]);

  if (!open) return null;

  // Flatten for index mapping against the filtered list.
  let flatIdx = -1;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-start justify-center bg-black/55 p-4 pt-[12vh] backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="flex w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised shadow-float animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-surface-line px-4 py-3">
          <Search className="h-4 w-4 flex-none text-ink-muted" strokeWidth={1.8} />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type a command or search…"
            className="flex-1 bg-transparent text-sm text-ink placeholder-ink-faint focus:outline-none"
            aria-label="Command search"
          />
          <kbd className="hidden flex-none rounded border border-surface-line bg-surface-sunken px-1.5 py-0.5 text-2xs font-mono text-ink-muted sm:block">
            esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[52vh] overflow-y-auto p-2 scroll-thin">
          {filtered.length === 0 ? (
            <div className="px-3 py-8 text-center text-sm text-ink-muted">No commands match “{query}”.</div>
          ) : (
            grouped.map(({ group, items }) => (
              <div key={group} className="mb-1">
                <div className="px-2 py-1.5 text-2xs data-label">{group}</div>
                {items.map((cmd) => {
                  flatIdx += 1;
                  const idx = flatIdx;
                  const isActive = idx === active;
                  return (
                    <button
                      key={cmd.id}
                      type="button"
                      data-idx={idx}
                      disabled={cmd.disabled}
                      onMouseEnter={() => setActive(idx)}
                      onClick={() => runCommand(cmd)}
                      className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors ${
                        isActive ? 'bg-surface-hover' : ''
                      } ${cmd.disabled ? 'cursor-not-allowed opacity-40' : ''}`}
                    >
                      <span className="flex h-7 w-7 flex-none items-center justify-center rounded-md border border-surface-line bg-surface-sunken text-brand-200">
                        {cmd.icon}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-ink">{cmd.label}</span>
                        {cmd.hint && <span className="block truncate text-2xs text-ink-muted">{cmd.hint}</span>}
                      </span>
                      {isActive && (
                        <CornerDownLeft className="h-3.5 w-3.5 flex-none text-ink-muted" strokeWidth={1.8} />
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-surface-line px-4 py-2 text-2xs data-label">
          <span>Universal Analyst</span>
          <span className="flex items-center gap-2">
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-surface-line bg-surface-sunken px-1 py-0.5 font-mono">↑↓</kbd>
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-surface-line bg-surface-sunken px-1 py-0.5 font-mono">↵</kbd>
              run
            </span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
