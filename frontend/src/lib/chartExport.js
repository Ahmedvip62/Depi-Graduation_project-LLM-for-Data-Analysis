// Real chart export helpers.
//
// PNG export uses the bundled plotly.js instance (the same one react-plotly.js
// renders with) via Plotly.toImage / Plotly.downloadImage against the live
// graph DOM node. CSV export reconstructs a tabular form from the figure's
// traces (x/y, or labels/values for pie-like traces).

import Plotly from 'plotly.js-dist-min';

const slug = (s) =>
  (s || 'chart')
    .toString()
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .slice(0, 60) || 'chart';

/** Trigger a browser download for arbitrary text content. */
const downloadText = (filename, text, mime = 'text/csv;charset=utf-8') => {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

/**
 * Export the rendered chart as a PNG. `graphDiv` is the DOM node react-plotly.js
 * mounts (obtained from the <Plot onInitialized/onUpdate> graphDiv arg).
 */
export const exportChartPNG = async (graphDiv, title) => {
  if (!graphDiv) throw new Error('Chart is not ready yet.');
  await Plotly.downloadImage(graphDiv, {
    format: 'png',
    width: 1280,
    height: 800,
    scale: 2,
    filename: slug(title),
  });
};

const csvCell = (v) => {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/**
 * Reconstruct CSV from a plotly figure spec (chartSpec = { data, layout }).
 * Handles x/y traces (multiple series share x where possible) and
 * labels/values traces (pie/donut/funnel).
 */
export const exportChartCSV = (chartSpec, title) => {
  const data = chartSpec?.data || [];
  if (!Array.isArray(data) || data.length === 0) {
    throw new Error('No data available to export.');
  }

  // labels/values style (pie, donut, funnelarea, sunburst-ish)
  const labelTrace = data.find((t) => Array.isArray(t.labels) && Array.isArray(t.values));
  if (labelTrace) {
    const rows = [['label', 'value']];
    labelTrace.labels.forEach((l, i) => rows.push([l, labelTrace.values[i]]));
    downloadText(`${slug(title)}.csv`, rows.map((r) => r.map(csvCell).join(',')).join('\n'));
    return;
  }

  // x/y style. Use the first trace's x as the index column; align each trace's y.
  const base = data.find((t) => Array.isArray(t.x)) || data[0];
  const xs = Array.isArray(base?.x) ? base.x : null;
  const seriesName = (t, i) => t.name || t.type || `series_${i + 1}`;

  if (xs) {
    const header = ['x', ...data.map((t, i) => seriesName(t, i))];
    const rows = [header];
    for (let i = 0; i < xs.length; i++) {
      const row = [xs[i]];
      data.forEach((t) => {
        const yv = Array.isArray(t.y) ? t.y[i] : '';
        row.push(yv);
      });
      rows.push(row);
    }
    downloadText(`${slug(title)}.csv`, rows.map((r) => r.map(csvCell).join(',')).join('\n'));
    return;
  }

  // CSV export shape: dump y values per trace as columns of differing length.
  const cols = data.map((t, i) => ({ name: seriesName(t, i), vals: t.y || t.x || [] }));
  const maxLen = Math.max(...cols.map((c) => c.vals.length), 0);
  const rows = [cols.map((c) => c.name)];
  for (let i = 0; i < maxLen; i++) rows.push(cols.map((c) => c.vals[i]));
  downloadText(`${slug(title)}.csv`, rows.map((r) => r.map(csvCell).join(',')).join('\n'));
};
