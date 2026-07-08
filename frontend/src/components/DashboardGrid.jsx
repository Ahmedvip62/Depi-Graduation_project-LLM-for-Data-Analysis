import React, { useMemo } from 'react';
import { LayoutDashboard, AlertCircle, TrendingUp, Sparkles, Database, FileSpreadsheet } from 'lucide-react';
import LazyChartCard from './LazyChartCard';

const DashboardGrid = ({ charts = [], layout = null, profile = null, onChartError, onSuggestion }) => {
  const gridCols = layout?.grid_cols || 3;
  const positions = layout?.positions || [];

  // Group gauge/KPI charts to show at the top of the dashboard, PowerBI-style.
  const kpis = useMemo(() => {
    return charts.filter(c => {
      const type = c.config?.type || c.config?.chart_spec?.type || '';
      return type === 'gauge' || String(c.title).toLowerCase().includes('kpi') || String(c.title).toLowerCase().includes('total');
    });
  }, [charts]);

  const analyticalCharts = useMemo(() => {
    return charts.filter(c => !kpis.includes(c));
  }, [charts, kpis]);

  if (charts.length === 0) {
    return (
      <div className="flex min-h-[450px] flex-col items-center justify-center rounded-2xl border border-dashed border-surface-line bg-surface-raised/40 p-8 text-center animate-fade-in">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-surface-line bg-surface-sunken text-ink-faint shadow-soft">
          <LayoutDashboard className="h-6 w-6" strokeWidth={1.8} />
        </div>
        <h3 className="font-display text-base font-semibold text-ink">Empty Dashboard</h3>
        <p className="mt-2 max-w-sm text-xs leading-relaxed text-ink-muted">
          No visualizations have been generated for this session yet. Ask the assistant to "generate a dashboard overview" to begin.
        </p>
        <button
          type="button"
          onClick={() => onSuggestion?.('Generate a dashboard for this dataset')}
          className="mt-5 inline-flex items-center gap-2 rounded-lg border border-brand-400/40 bg-brand-400/10 px-4 py-2.5 text-xs font-semibold text-brand-100 transition-colors hover:bg-brand-400/15"
        >
          <Sparkles className="h-4 w-4" strokeWidth={1.8} />
          Create Auto-Dashboard
        </button>
      </div>
    );
  }

  // Fallback layout algorithm if the LLM did not specify layouts or if layout is empty
  const getLayoutProps = (chart, index) => {
    // If layout specified this index, use it
    const pos = positions.find(p => p.chart_index === index);
    if (pos) {
      return {
        colSpan: pos.col_span || 1,
        rowSpan: pos.row_span || 1,
        priority: pos.visual_priority || 'standard',
      };
    }

    // Default positioning heuristic
    const spec = chart.config || {};
    const type = String(spec.type || spec.chart_spec?.type || '').toLowerCase();
    
    let colSpan = 1;
    let rowSpan = 1;
    let priority = 'standard';

    if (type === 'choropleth' || type === 'scatter_geo' || type === 'scatter_matrix' || type === 'parallel_coordinates' || type === 'parallel_categories') {
      colSpan = gridCols; // Full-width
      priority = 'full-width';
    } else if (type === 'heatmap' || type === 'density_heatmap' || type === 'density_contour' || type === 'timeline') {
      colSpan = Math.min(2, gridCols);
    }

    return { colSpan, rowSpan, priority };
  };

  return (
    <div className="space-y-6 pb-8 animate-fade-in">
      {/* Dashboard KPI Top Banner */}
      {kpis.length > 0 && (
        <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {kpis.map((chart, idx) => (
            <div key={chart.id || idx} className="flex flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised p-4 shadow-card">
              <div className="text-2xs uppercase tracking-wider text-ink-muted">{chart.title}</div>
              <div className="mt-2 flex-1">
                <LazyChartCard title={chart.title} chartSpec={chart.config} height={120} onError={onChartError} hideHeader={true} />
              </div>
              {chart.description && (
                <div className="mt-1 text-4xs leading-relaxed text-ink-faint truncate">{chart.description}</div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Main Layout Grid */}
      <section 
        className={`grid gap-5 grid-cols-1 ${gridCols >= 2 ? 'md:grid-cols-2' : ''} ${gridCols >= 3 ? 'lg:grid-cols-3' : ''}`}
      >
        {analyticalCharts.map((chart, idx) => {
          const actualIdx = charts.indexOf(chart);
          const { colSpan, rowSpan } = getLayoutProps(chart, actualIdx);
          const chartHeight = rowSpan > 1 ? 280 * rowSpan + 20 * (rowSpan - 1) : 280;

          // Map spans to responsive Tailwind classes
          const colSpanClass = colSpan === 1 ? 'col-span-1' :
                               colSpan === 2 ? 'col-span-1 md:col-span-2' :
                               colSpan === 3 ? 'col-span-1 md:col-span-2 lg:col-span-3' :
                               'col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-4';
                               
          const rowSpanClass = rowSpan === 1 ? 'row-span-1' :
                               rowSpan === 2 ? 'row-span-1 md:row-span-2' :
                               'row-span-1 md:row-span-3';
          
          return (
            <div
              key={chart.id || idx}
              className={`flex flex-col rounded-2xl border border-surface-line bg-surface-raised shadow-card transition-all duration-300 hover:shadow-float ${colSpanClass} ${rowSpanClass}`}
            >
              <div className="flex-1">
                <LazyChartCard title={chart.title} chartSpec={chart.config} height={chartHeight} onError={onChartError} />
              </div>
              {chart.description && (
                <p className="px-4 pb-3 pt-2 text-2xs leading-relaxed text-ink-muted border-t border-surface-line/20">
                  {chart.description}
                </p>
              )}
            </div>
          );
        })}
      </section>

      {/* Dataset Summary footer card */}
      {profile && (
        <footer className="rounded-2xl border border-surface-line bg-surface-raised px-5 py-4 shadow-card animate-fade-up">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-surface-line bg-surface-sunken text-brand-100">
                <Database className="h-4 w-4" />
              </div>
              <div>
                <div className="font-display text-xs font-semibold text-ink">{profile.file_name}</div>
                <div className="text-3xs uppercase tracking-wider text-ink-muted">
                  {profile.row_count?.toLocaleString()} rows · {profile.column_count} columns · {profile.file_type}
                </div>
              </div>
            </div>
            {layout && (
              <div className="flex items-center gap-2 rounded-lg border border-brand-400/20 bg-brand-400/5 px-3 py-1.5 text-2xs text-brand-200">
                <Sparkles className="h-3.5 w-3.5" />
                Layout dynamically optimized by model
              </div>
            )}
          </div>
        </footer>
      )}
    </div>
  );
};

export default DashboardGrid;
