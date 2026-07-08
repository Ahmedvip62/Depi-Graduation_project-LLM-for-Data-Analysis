import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { Download, Maximize2, X } from 'lucide-react';
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import { exportChartPNG, exportChartCSV } from '../lib/chartExport';

// Build the Plot component from the prebuilt bundle we already ship
// (plotly.js-dist-min) instead of react-plotly.js's default export, which
// requires the bare `plotly.js` package. This keeps a single Plotly instance
// shared with chartExport.js and avoids bundling Plotly twice.
const Plot = createPlotlyComponent(Plotly);

const themeLayout = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: {
    family: 'IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace',
    color: '#C7CEDA',
    size: 11,
  },
  colorway: ['#6366F1', '#F0A92B', '#9098FB', '#34D399', '#F472B6', '#22D3EE', '#98A2B3'],
  xaxis: { gridcolor: '#232A36', zerolinecolor: '#2B3342', automargin: true, color: '#98A2B3' },
  yaxis: { gridcolor: '#232A36', zerolinecolor: '#2B3342', automargin: true, color: '#98A2B3' },
  legend: { font: { size: 11, color: '#98A2B3' }, orientation: 'h', y: -0.2 },
  margin: { l: 56, r: 24, t: 24, b: 64 },
};

const IconBtn = ({ onClick, label, children, disabled }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    aria-label={label}
    title={label}
    className="flex h-8 items-center gap-1 rounded-md border border-surface-line bg-surface-sunken px-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted transition-colors hover:border-brand-400 hover:text-brand-100 disabled:cursor-not-allowed disabled:opacity-40"
  >
    {children}
  </button>
);

// Hoisted out of ChartCard so it has a STABLE component identity across re-renders.
// Declaring it inside ChartCard gave every render a new function type, which made
// React unmount+remount the Plotly graph on every setBusy/setExpanded — flicker,
// lost zoom/hover state, and a redundant Plotly init.
const ChartPlot = React.forwardRef(({ chartSpec, layout, height }, ref) => {
  if (!chartSpec) {
    return (
      <div className="flex items-center justify-center text-xs text-ink-faint" style={{ height }}>
        <span className="shimmer rounded-md px-6 py-2">Rendering...</span>
      </div>
    );
  }
  return (
    <Plot
      data={chartSpec.data}
      layout={layout}
      useResizeHandler
      onInitialized={(_, gd) => {
        if (ref) ref.current = gd;
      }}
      onUpdate={(_, gd) => {
        if (ref) ref.current = gd;
      }}
      config={{ displayModeBar: 'hover', responsive: true }}
      style={{ width: '100%', height }}
    />
  );
});
ChartPlot.displayName = 'ChartPlot';

const ChartCard = ({ title, chartSpec, height = 280, expandable = true, onError, hideHeader = false }) => {
  const graphRef = useRef(null);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const closeRef = useRef(null);

  const handlePNG = useCallback(async () => {
    try {
      setBusy(true);
      await exportChartPNG(graphRef.current, title);
    } catch (e) {
      onError?.(e.message || 'PNG export failed.');
    } finally {
      setBusy(false);
    }
  }, [title, onError]);

  const handleCSV = useCallback(() => {
    try {
      exportChartCSV(chartSpec, title);
    } catch (e) {
      onError?.(e.message || 'CSV export failed.');
    }
  }, [chartSpec, title, onError]);

  // Stable layout object: only changes when the chart spec changes, so PNG export
  // and expand toggles no longer force a re-layout.
  const mergedLayout = useMemo(() => ({
    ...themeLayout,
    ...(chartSpec?.layout || {}),
    autosize: true,
    title: undefined,
    margin: { ...themeLayout.margin, ...(chartSpec?.layout?.margin || {}) },
    font: { ...themeLayout.font, ...(chartSpec?.layout?.font || {}) },
    xaxis: { ...themeLayout.xaxis, ...(chartSpec?.layout?.xaxis || {}) },
    yaxis: { ...themeLayout.yaxis, ...(chartSpec?.layout?.yaxis || {}) },
    legend: { ...themeLayout.legend, ...(chartSpec?.layout?.legend || {}) },
  }), [chartSpec]);

  // Escape closes the modal; focus the close button on open. Restore focus on close.
  useEffect(() => {
    if (!expanded) return undefined;
    const previouslyFocused = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus();
      }
    };
  }, [expanded]);

  return (
    <>
      <div className="group flex flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised shadow-card transition-shadow hover:shadow-raised">
        {!hideHeader && (
          <div className="flex items-center justify-between gap-2 border-b border-surface-line bg-surface-sunken px-4 py-2.5">
            <h4 className="truncate font-display text-[0.86rem] font-semibold text-ink" title={title}>
              {title || 'Visualization'}
            </h4>
            <div className="flex flex-none gap-1.5">
              <IconBtn onClick={handlePNG} label="Export as PNG" disabled={busy}>
                <Download className="h-3 w-3" strokeWidth={1.8} />
                PNG
              </IconBtn>
              <IconBtn onClick={handleCSV} label="Export data as CSV">CSV</IconBtn>
              {expandable && (
                <IconBtn onClick={() => setExpanded(true)} label="Expand chart">
                  <Maximize2 className="h-3 w-3" strokeWidth={1.8} />
                </IconBtn>
              )}
            </div>
          </div>
        )}
        <div className="w-full flex-1 bg-surface-raised p-2">
          <ChartPlot ref={graphRef} chartSpec={chartSpec} layout={mergedLayout} height={`${height}px`} />
        </div>
      </div>

      {expanded && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-fade-in sm:p-8"
          onClick={() => setExpanded(false)}
          role="dialog"
          aria-modal="true"
          aria-label={`${title} expanded`}
        >
          <div
            className="flex max-h-full w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised shadow-float animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-surface-line px-5 py-3.5">
              <h3 className="font-display font-semibold text-ink">{title || 'Visualization'}</h3>
              <div className="flex items-center gap-2">
                <IconBtn onClick={handlePNG} label="Export as PNG" disabled={busy}>PNG</IconBtn>
                <IconBtn onClick={handleCSV} label="Export data as CSV">CSV</IconBtn>
                <button
                  type="button"
                  ref={closeRef}
                  onClick={() => setExpanded(false)}
                  aria-label="Close expanded chart"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-muted text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
                >
                  <X className="h-4 w-4" strokeWidth={2} />
                </button>
              </div>
            </div>
            <div className="min-h-0 flex-1 p-4">
              <ChartPlot ref={graphRef} chartSpec={chartSpec} layout={mergedLayout} height="72vh" />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ChartCard;