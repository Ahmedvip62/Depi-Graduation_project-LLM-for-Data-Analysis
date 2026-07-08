import React, { Suspense } from 'react';

// Lazy-load ChartCard (and therefore the ~4.7MB Plotly bundle) so it only
// downloads when a chart actually renders — not on the intake screen's first
// paint. The fallback matches ChartCard's empty-state frame so the layout
// doesn't jump when the chunk resolves.
const ChartCard = React.lazy(() => import('./ChartCard'));

const ChartCardFallback = ({ title, height = 280 }) => (
  <div className="flex flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised shadow-card">
    <div className="flex items-center justify-between gap-2 border-b border-surface-line bg-surface-sunken px-4 py-2.5">
      <h4 className="truncate font-display text-[0.86rem] font-semibold text-ink" title={title || ''}>
        {title || 'Visualization'}
      </h4>
    </div>
    <div
      className="flex w-full flex-1 items-center justify-center bg-surface-raised text-2xs text-ink-faint"
      style={{ height }}
    >
      <span className="shimmer rounded-md px-6 py-2">Rendering…</span>
    </div>
  </div>
);

const LazyChartCard = ({ title, chartSpec, height, expandable, onError, hideHeader }) => (
  <Suspense fallback={<ChartCardFallback title={title} height={height} />}>
    <ChartCard
      title={title}
      chartSpec={chartSpec}
      height={height}
      expandable={expandable}
      onError={onError}
      hideHeader={hideHeader}
    />
  </Suspense>
);

export default LazyChartCard;
