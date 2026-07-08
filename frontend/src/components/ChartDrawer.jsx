import React, { useEffect, useRef } from 'react';
import { BarChart3, X } from 'lucide-react';
import LazyChartCard from './LazyChartCard';

const ChartGallery = ({ isOpen, onClose, charts = [], onError }) => {
  const closeRef = useRef(null);

  // Escape closes; focus the close button on open and restore focus on close.
  useEffect(() => {
    if (!isOpen) return undefined;
    const previouslyFocused = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus();
      }
    };
  }, [isOpen, onClose]);

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-surface-sunken/80 backdrop-blur-[2px]" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-[430px] flex-col border-l border-surface-line bg-surface-sunken shadow-float transition-transform duration-500 ease-smooth lg:max-w-[620px] ${
          isOpen ? 'translate-x-0' : 'translate-x-[105%]'
        }`}
        aria-hidden={!isOpen}
        // `inert` removes the closed drawer from the tab order and the accessibility
        // tree, so its (off-screen) buttons can't receive focus while hidden.
        {...(!isOpen ? { inert: '' } : {})}
        aria-label="Visualization gallery"
      >
        <div className="flex flex-none items-center justify-between border-b border-surface-line bg-surface-raised px-4 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-brand-400/30 bg-brand-400/10 text-brand-100">
              <BarChart3 className="h-4 w-4" strokeWidth={1.8} />
            </div>
            <div>
              <h2 className="font-display text-base font-semibold text-ink">Visuals</h2>
              <div className="text-2xs uppercase tracking-wider text-ink-faint">{charts.length} saved in this session</div>
            </div>
          </div>
          <button
            type="button"
            ref={closeRef}
            onClick={onClose}
            aria-label="Close gallery"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-muted text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        </div>

        <div className="relative flex-1 overflow-y-auto p-4 scroll-thin">
          {charts.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-surface-line bg-surface-raised text-ink-faint shadow-soft">
                <BarChart3 className="h-7 w-7" strokeWidth={1.6} />
              </div>
              <p className="font-display text-sm font-semibold text-ink">No charts yet</p>
              <p className="mt-1 max-w-[240px] text-xs text-ink-muted">Generated visuals appear here after upload or chart requests.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {charts.map((chart, idx) => (
                <div key={chart.id || idx}>
                  <LazyChartCard title={chart.title} chartSpec={chart.config} height={280} onError={onError} />
                  {chart.description && (
                    <p className="mt-2 px-1 text-xs leading-relaxed text-ink-muted">{chart.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

export default ChartGallery;
