import React, { useMemo, useState } from 'react';
import { ArrowRight, AlertTriangle, Sparkles, TrendingUp, X, ShieldCheck } from 'lucide-react';
import LazyChartCard from './LazyChartCard';

const fmtNum = (n) =>
  typeof n === 'number' ? n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : n ?? '-';
const fmtPct = (n) => (typeof n === 'number' ? `${n.toFixed(1)}%` : '-');

const StatCard = ({ label, value, sub, accent }) => (
  <div className="rounded-xl border border-surface-line bg-surface-raised px-4 py-3 shadow-card animate-fade-up">
    <div className="text-2xs data-label">{label}</div>
    <div className={`mt-1 font-display text-2xl font-semibold tabular-nums ${accent || 'text-ink'}`}>{value}</div>
    {sub && <div className="mt-0.5 text-2xs text-ink-muted">{sub}</div>}
  </div>
);

const SectionHeader = ({ title, count, action }) => (
  <div className="mb-3 flex items-center justify-between gap-3">
    <h3 className="font-display text-sm font-semibold text-ink">
      {title}
      {count != null && <span className="ml-2 text-2xs data-label">{count}</span>}
    </h3>
    {action}
  </div>
);

const TypeBadge = ({ type }) => {
  const map = {
    numeric: 'bg-brand-400/10 text-brand-100 border-brand-400/30',
    integer: 'bg-brand-400/10 text-brand-100 border-brand-400/30',
    float: 'bg-brand-400/10 text-brand-100 border-brand-400/30',
    continuous: 'bg-brand-400/10 text-brand-100 border-brand-400/30',
    categorical: 'bg-accent-300/10 text-accent-100 border-accent-300/30',
    category: 'bg-accent-300/10 text-accent-100 border-accent-300/30',
    string: 'bg-accent-300/10 text-accent-100 border-accent-300/30',
    datetime: 'bg-surface-sunken text-ink-soft border-surface-line',
    date: 'bg-surface-sunken text-ink-soft border-surface-line',
    boolean: 'bg-surface-muted text-ink-soft border-surface-line',
    id: 'bg-surface-muted text-ink-soft border-surface-line',
  };
  const cls = map[(type || '').toLowerCase()] || 'bg-surface-muted text-ink-muted border-surface-line';
  return <span className={`inline-block rounded-md border px-2 py-0.5 text-2xs font-semibold ${cls}`}>{type || 'unknown'}</span>;
};

// Derive a short list of data-quality signals from the profile, client-side.
const qualitySignals = (profile) => {
  if (!profile?.columns) return [];
  const rows = profile.row_count || 0;
  const signals = [];
  for (const [name, info] of Object.entries(profile.columns)) {
    const missing = info.missing_pct ?? 0;
    if (missing > 0) {
      signals.push({
        severity: missing > 20 ? 'high' : missing > 5 ? 'med' : 'low',
        label: `${name}: ${fmtPct(missing)} missing`,
      });
    }
    const unique = info.unique_count ?? 0;
    if (rows && unique / rows > 0.9 && (info.semantic_type !== 'id')) {
      signals.push({ severity: 'info', label: `${name}: high cardinality (${fmtNum(unique)} unique)` });
    }
  }
  // Sort high → med → low → info, then cap.
  const order = { high: 0, med: 1, low: 2, info: 3 };
  return signals.sort((a, b) => order[a.severity] - order[b.severity]).slice(0, 6);
};

// Strongest correlations from the profile, if present.
const topCorrelations = (profile) => {
  const corr = profile?.correlations;
  if (!corr || typeof corr !== 'object') return [];
  const seen = new Set();
  const pairs = [];
  for (const [a, row] of Object.entries(corr)) {
    if (!row || typeof row !== 'object') continue;
    for (const [b, v] of Object.entries(row)) {
      if (a === b) continue;
      const key = [a, b].sort().join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      const num = typeof v === 'number' ? v : null;
      if (num === null) continue;
      pairs.push({ a, b, v: num, abs: Math.abs(num) });
    }
  }
  return pairs.sort((x, y) => y.abs - x.abs).slice(0, 4);
};

const QualityPanel = ({ signals }) => {
  if (!signals.length) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-brand-400/25 bg-brand-400/5 px-4 py-3 text-sm text-ink-soft">
        <Sparkles className="h-4 w-4 flex-none text-brand-200" strokeWidth={1.8} />
        No notable quality issues detected across the profiled columns.
      </div>
    );
  }
  const dot = (sev) =>
    sev === 'high' ? 'bg-danger-500' : sev === 'med' ? 'bg-accent-300' : sev === 'low' ? 'bg-brand-300' : 'bg-ink-ghost';
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {signals.map((s, i) => (
        <div key={i} className="flex items-center gap-2 rounded-lg border border-surface-line bg-surface-sunken px-3 py-2 text-xs text-ink-soft">
          <span className={`h-1.5 w-1.5 flex-none rounded-full ${dot(s.severity)}`} />
          <span className="truncate">{s.label}</span>
        </div>
      ))}
    </div>
  );
};

const CorrelationStrip = ({ pairs }) => {
  if (!pairs.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {pairs.map((p, i) => {
        const tone = p.v >= 0 ? 'text-brand-100' : 'text-accent-100';
        return (
          <div key={i} className="rounded-lg border border-surface-line bg-surface-sunken px-3 py-1.5 text-xs">
            <span className="text-ink-muted">{p.a} ↔ {p.b}</span>{' '}
            <span className={`font-mono font-semibold tabular-nums ${tone}`}>{p.v.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
};

const ChartSection = ({ charts, onChartError }) => {
  if (!charts?.length) return null;
  return (
    <section>
      <SectionHeader title="Requested visuals" count={charts.length} />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {charts.map((c, idx) => (
          <div key={c.id || idx} className="flex flex-col">
            <LazyChartCard title={c.title} chartSpec={c.config || c.chart_spec} height={300} onError={onChartError} />
            {c.description && <p className="mt-1.5 px-1 text-2xs leading-snug text-ink-muted">{c.description}</p>}
          </div>
        ))}
      </div>
    </section>
  );
};

const DataOverview = ({ profile, eda, sessionCharts = [], onSuggestion, onChartError, onCleanDataset, isCleaning }) => {
  if (!eda && !profile) return null;

  const [showCleanModal, setShowCleanModal] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [newSession, setNewSession] = useState(false);

  const summary = eda?.summary || {};
  const suggestions = eda?.suggestions || [];
  const columns = profile?.columns || {};
  const columnList = Object.entries(columns).map(([name, info]) => ({ name, ...info }));

  const signals = useMemo(() => qualitySignals(profile), [profile]);
  const correlations = useMemo(() => topCorrelations(profile), [profile]);

  const stats = [
    { label: 'Rows', value: fmtNum(summary.row_count ?? profile?.row_count), accent: 'text-ink' },
    { label: 'Columns', value: fmtNum(summary.column_count ?? profile?.column_count), accent: 'text-ink' },
    { label: 'Missing', value: fmtPct(summary.missing_pct ?? profile?.missing_pct), accent: 'text-brand-100' },
    { label: 'Memory', value: summary.memory_human || '-', accent: 'text-ink' },
    { label: 'Numeric', value: fmtNum(summary.numeric_count ?? profile?.numeric_columns?.length), accent: 'text-brand-100' },
    { label: 'Categorical', value: fmtNum(summary.categorical_count ?? profile?.categorical_columns?.length), accent: 'text-accent-100' },
    { label: 'Datetime', value: fmtNum(summary.datetime_count ?? profile?.datetime_columns?.length), accent: 'text-ink-soft' },
  ];

  return (
    <div className="space-y-7 pb-5 animate-fade-in">
      {/* Profile header */}
      <section className="signal-rail rounded-2xl border border-surface-line bg-surface-raised px-5 py-5 shadow-card sm:px-6">
        <div className="pl-3">
          <div className="text-2xs data-label text-brand-100">Dataset profile</div>
          <div className="mt-2 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div className="min-w-0">
              <h2 className="truncate font-display text-2xl font-semibold text-ink sm:text-3xl">
                {profile?.file_name || 'Active dataset'}
              </h2>
              <p className="mt-1 text-sm data-label normal-case tracking-wide text-ink-muted">
                {profile?.file_type ? `${profile.file_type} · ` : ''}
                {fmtNum(profile?.row_count)} rows × {fmtNum(profile?.column_count)} cols
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setShowCleanModal(true)}
                disabled={isCleaning}
                className="inline-flex items-center gap-2 rounded-lg border border-brand-400/40 bg-brand-400/10 px-4 py-2 text-xs font-semibold text-brand-100 transition-colors hover:bg-brand-400/15 disabled:opacity-40 disabled:cursor-not-allowed shadow-soft"
              >
                <Sparkles className="h-4 w-4" />
                {isCleaning ? 'Cleaning...' : 'Clean Dataset'}
              </button>
              {suggestions.slice(0, 1).map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSuggestion?.(q)}
                  className="rounded-lg border border-surface-line bg-surface-sunken px-3 py-2 text-left text-xs font-medium text-ink-soft transition-all hover:border-brand-400 hover:text-brand-100 hover:shadow-soft"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* LLM Data Cleaning Modal */}
      {showCleanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-surface-line bg-surface-raised p-6 shadow-float animate-scale-up">
            <div className="flex items-center justify-between border-b border-surface-line/60 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-brand-200" />
                <h3 className="font-display text-base font-semibold text-ink">LLM Data Cleaning</h3>
              </div>
              <button 
                type="button" 
                onClick={() => setShowCleanModal(false)}
                className="text-ink-muted hover:text-ink transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="mt-4 space-y-4">
              <p className="text-2xs text-ink-muted leading-relaxed">
                The model will review the dataset profile, auto-detect skewness to decide between mean/median fills, remove outliers, drop duplicate rows, and standardize text columns dynamically.
              </p>
              
              <div>
                <label className="block text-3xs uppercase tracking-wider text-ink-muted font-semibold mb-1">
                  Custom Instructions (Optional)
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="e.g. Do not remove outliers for column 'price', keep columns with > 80% null values..."
                  className="w-full min-h-[80px] rounded-lg border border-surface-line bg-surface-sunken p-2.5 text-xs text-ink placeholder:text-ink-faint focus:border-brand-400 focus:outline-none scroll-thin focus:ring-1 focus:ring-brand-400"
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="newSession"
                  checked={newSession}
                  onChange={(e) => setNewSession(e.target.checked)}
                  className="h-4 w-4 rounded border-surface-line bg-surface-sunken text-brand-400 focus:ring-brand-400 focus:ring-offset-0 focus:outline-none"
                />
                <label htmlFor="newSession" className="text-xs text-ink-soft cursor-pointer select-none">
                  Create a new session (keep original session intact)
                </label>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCleanModal(false)}
                className="rounded-lg border border-surface-line bg-surface-muted px-4 py-2 text-xs font-semibold text-ink hover:bg-surface-hover transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  setShowCleanModal(false);
                  await onCleanDataset?.(instructions, newSession);
                  setInstructions('');
                }}
                disabled={isCleaning}
                className="inline-flex items-center gap-2 rounded-lg bg-brand-400 px-4 py-2 text-xs font-semibold text-surface-sunken hover:bg-brand-300 disabled:opacity-40 disabled:cursor-not-allowed shadow-soft transition-colors"
              >
                <ShieldCheck className="h-4 w-4" />
                {isCleaning ? 'Cleaning...' : 'Run Auto-Clean'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="tick-rule -mt-2" aria-hidden="true" />

      {/* KPI strip */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
        {stats.map((s, i) => (
          <div key={s.label} style={{ animationDelay: `${i * 35}ms` }}>
            <StatCard {...s} />
          </div>
        ))}
      </section>

      {/* Data quality + correlations row */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-surface-line bg-surface-raised p-5 shadow-card">
          <SectionHeader title="Data quality" count={signals.length || null} />
          <QualityPanel signals={signals} />
        </div>
        <div className="rounded-2xl border border-surface-line bg-surface-raised p-5 shadow-card">
          <SectionHeader
            title="Strongest correlations"
            action={
              correlations.length ? (
                <span className="inline-flex items-center gap-1 text-2xs data-label text-ink-muted">
                  <TrendingUp className="h-3 w-3" strokeWidth={1.8} /> pearson r
                </span>
              ) : null
            }
          />
          {correlations.length ? (
            <CorrelationStrip pairs={correlations} />
          ) : (
            <p className="text-xs text-ink-muted">Fewer than two numeric columns — no correlations computed.</p>
          )}
        </div>
      </section>

      {suggestions.length > 2 && (
        <section>
          <SectionHeader title="Suggested next questions" />
          <div className="flex flex-wrap gap-2">
            {suggestions.slice(2).map((q, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onSuggestion?.(q)}
                className="group flex items-center gap-2 rounded-lg border border-surface-line bg-surface-raised px-3 py-2 text-sm text-ink-soft shadow-soft transition-all hover:border-brand-400 hover:text-brand-100"
              >
                {q}
                <ArrowRight className="h-3.5 w-3.5 text-ink-ghost transition-colors group-hover:text-brand-200" strokeWidth={2} />
              </button>
            ))}
          </div>
        </section>
      )}

      <ChartSection charts={sessionCharts} onChartError={onChartError} />
      {sessionCharts.length === 0 && (
        <section className="rounded-2xl border border-dashed border-surface-line bg-surface-raised/70 px-5 py-5 shadow-card">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="font-display text-base font-semibold text-ink">Dynamic visual canvas</h3>
              <p className="mt-1 text-sm text-ink-muted">No model-generated visuals have been requested in this session yet.</p>
            </div>
            <button
              type="button"
              onClick={() => onSuggestion?.('Generate a dashboard for this dataset')}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-brand-400/40 bg-brand-400/10 px-3 py-2 text-sm font-semibold text-brand-100 transition-colors hover:bg-brand-400/15"
            >
              <Sparkles className="h-4 w-4" strokeWidth={1.8} />
              Generate dashboard
            </button>
          </div>
        </section>
      )}

      {columnList.length > 0 && (
        <section>
          <SectionHeader title="Column dictionary" count={columnList.length} />
          <div className="overflow-hidden rounded-2xl border border-surface-line bg-surface-raised shadow-card">
            <div className="overflow-x-auto scroll-thin">
              <table className="w-full text-sm">
                <thead className="bg-surface-sunken">
                  <tr className="text-left">
                    <th className="whitespace-nowrap px-4 py-2.5 font-semibold text-ink">Column</th>
                    <th className="whitespace-nowrap px-4 py-2.5 font-semibold text-ink">Type</th>
                    <th className="whitespace-nowrap px-4 py-2.5 font-semibold text-ink">Missing</th>
                    <th className="whitespace-nowrap px-4 py-2.5 font-semibold text-ink">Unique</th>
                    <th className="hidden whitespace-nowrap px-4 py-2.5 font-semibold text-ink sm:table-cell">Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {columnList.map((col) => (
                    <tr key={col.name} className="border-t border-surface-line/70 transition-colors hover:bg-surface-muted/70">
                      <td className="whitespace-nowrap px-4 py-2.5 font-medium text-ink">{col.name}</td>
                      <td className="px-4 py-2.5"><TypeBadge type={col.semantic_type || col.dtype} /></td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-ink-soft tabular-nums">{fmtPct(col.missing_pct)}</td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-ink-soft tabular-nums">{fmtNum(col.unique_count)}</td>
                      <td className="hidden max-w-[260px] truncate px-4 py-2.5 text-2xs text-ink-muted sm:table-cell">
                        {Array.isArray(col.sample_values) ? col.sample_values.slice(0, 4).join(', ') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default DataOverview;
