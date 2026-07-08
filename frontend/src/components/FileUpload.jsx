import React, { useRef, useState } from 'react';
import { AlertTriangle, ArrowRight, FileSpreadsheet, LoaderCircle, Sparkles, UploadCloud } from 'lucide-react';
import Logo from './Logo';

const FORMATS = ['CSV', 'JSON', 'Parquet', 'PDF', 'SQLite', 'DB'];
const ACCEPT = '.csv,.json,.parquet,.pdf,.sqlite,.db';

// Static sample datasets served from /public/samples so the quickstart works
// even before the backend is reachable. Each becomes a real File and flows
// through the normal upload path — same profiling/RAG/chart pipeline.
const SAMPLES = [
  { name: 'Sales data', file: 'sales_data.csv', blurb: 'Regions, products, revenue' },
  { name: 'Customer survey', file: 'customer_survey.json', blurb: 'Satisfaction & demographics' },
];

const PILLARS = [
  { label: 'Profile', note: 'auto EDA' },
  { label: 'Grounded Q&A', note: 'local LLM' },
  { label: 'Live charts', note: 'Plotly' },
  { label: 'PDF report', note: 'export' },
];

const FileUpload = ({ onSelectFile, isUploading, error, onClearError }) => {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(null);
  
  const [autoClean, setAutoClean] = useState(true);
  const [cleaningInstructions, setCleaningInstructions] = useState('');

  const openPicker = () => fileInputRef.current?.click();

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (isUploading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) {
      onClearError?.();
      onSelectFile(file, { autoClean, cleaningInstructions });
    }
  };

  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onClearError?.();
      onSelectFile(file, { autoClean, cleaningInstructions });
    }
  };

  const loadSample = async (sample) => {
    if (isUploading || sampleLoading) return;
    setSampleLoading(sample.file);
    onClearError?.();
    try {
      const res = await fetch(`${import.meta.env.BASE_URL}samples/${sample.file}`);
      if (!res.ok) throw new Error('Sample unavailable');
      const blob = await res.blob();
      const file = new File([blob], sample.file, { type: blob.type || 'text/plain' });
      onSelectFile(file, { autoClean, cleaningInstructions });
    } catch {
      setSampleLoading(null);
    }
  };

  return (
    <div className="min-h-full px-4 py-6 sm:px-6 lg:py-10">
      <div className="mx-auto grid w-full max-w-6xl gap-5 lg:grid-cols-[0.82fr_1.18fr] lg:items-stretch">
        {/* Brand / value pillar */}
        <section className="signal-rail flex flex-col overflow-hidden rounded-2xl border border-surface-line bg-surface-raised p-6 shadow-card sm:p-7">
          <div className="pl-3 flex flex-1 flex-col">
            <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-brand-400/25 bg-brand-400/10 px-3 py-1 text-2xs font-bold uppercase tracking-wider text-brand-100">
              <Logo className="h-3.5 w-3.5 text-brand-100" />
              Universal Analyst
            </div>
            <h1 className="font-display text-3xl font-semibold leading-tight text-ink sm:text-[2.6rem] sm:leading-[1.1]">
              Ask a dataset real questions.
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-muted">
              Drop in a file and a local model profiles it, grounds your questions in the data, draws validated charts, and writes a report you can hand to a stakeholder.
            </p>

            <div className="mt-8 grid grid-cols-2 gap-2.5">
              {PILLARS.map((p) => (
                <div key={p.label} className="rounded-xl border border-surface-line bg-surface-sunken px-3 py-2.5">
                  <div className="font-display text-sm font-semibold text-ink">{p.label}</div>
                  <div className="mt-0.5 text-2xs data-label">{p.note}</div>
                </div>
              ))}
            </div>

            <div className="mt-auto pt-7">
              <div className="mb-2 flex items-center gap-1.5 text-2xs data-label">
                <Sparkles className="h-3 w-3 text-accent-300" strokeWidth={2} />
                Try a sample dataset
              </div>
              <div className="flex flex-col gap-2">
                {SAMPLES.map((s) => (
                  <button
                    key={s.file}
                    type="button"
                    onClick={() => loadSample(s)}
                    disabled={isUploading || Boolean(sampleLoading)}
                    className="group flex items-center gap-3 rounded-xl border border-surface-line bg-surface-sunken px-3 py-2.5 text-left transition-all hover:border-brand-400 hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className="flex h-8 w-8 flex-none items-center justify-center rounded-lg border border-surface-line bg-surface-raised text-brand-200">
                      <FileSpreadsheet className="h-4 w-4" strokeWidth={1.8} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-ink">{s.name}</span>
                      <span className="block truncate text-2xs text-ink-muted">{s.blurb}</span>
                    </span>
                    {sampleLoading === s.file ? (
                      <LoaderCircle className="h-4 w-4 flex-none animate-spin text-brand-200" strokeWidth={2} />
                    ) : (
                      <ArrowRight className="h-4 w-4 flex-none text-ink-ghost transition-colors group-hover:text-brand-200" strokeWidth={2} />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Dropzone & Options */}
        <div className="flex flex-col gap-5">
          <section
            className={`relative flex min-h-[390px] cursor-pointer flex-col justify-between overflow-hidden rounded-2xl border bg-surface-raised p-5 shadow-card transition-all duration-300 sm:p-6 flex-1 ${
              isDragOver
                ? 'border-brand-300 shadow-glow ring-2 ring-brand-400/20'
                : 'border-surface-line hover:border-brand-400/70 hover:shadow-raised'
            } ${isUploading ? 'pointer-events-none opacity-75' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={openPicker}
            role="button"
            tabIndex={0}
            aria-label="Upload a data file"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') openPicker();
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleChange}
              className="hidden"
              accept={ACCEPT}
              disabled={isUploading}
            />

            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-2xs data-label">Dataset intake</div>
                <h2 className="mt-2 font-display text-2xl font-semibold text-ink">
                  {isUploading ? (autoClean ? 'Profiling & Cleaning dataset' : 'Profiling dataset') : 'Drop a file here'}
                </h2>
              </div>
              <div className={`flex h-12 w-12 flex-none items-center justify-center rounded-xl border ${isDragOver ? 'border-brand-300 bg-brand-400/10 text-brand-100' : 'border-surface-line bg-surface-sunken text-ink-muted'}`}>
                {isUploading ? (
                  <LoaderCircle className="h-5 w-5 animate-spin" strokeWidth={2} />
                ) : (
                  <UploadCloud className="h-5 w-5" strokeWidth={1.8} />
                )}
              </div>
            </div>

            <div className="my-8 flex flex-1 items-center justify-center rounded-xl border border-dashed border-surface-line bg-surface-sunken/75 px-5 text-center">
              <div>
                <p className="font-display text-lg font-semibold text-ink">
                  {isUploading ? (autoClean ? 'Cleaning dataset via LLM & reading profile' : 'Reading columns, quality, and profile metadata') : 'Choose or drag one dataset'}
                </p>
                <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-ink-muted">
                  {isUploading
                    ? 'The profile opens as soon as processing is complete.'
                    : 'Tabular files, PDFs with tables, and SQLite databases are accepted.'}
                </p>
                {isUploading && (
                  <div className="mx-auto mt-5 h-1.5 max-w-[280px] overflow-hidden rounded-full bg-surface-hover">
                    <div className="h-full w-1/3 rounded-full bg-brand-300 animate-slide" />
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {FORMATS.map((ext) => (
                <span key={ext} className="rounded-md border border-surface-line bg-surface-sunken px-2.5 py-1 text-2xs data-label">
                  {ext}
                </span>
              ))}
            </div>
          </section>

          <div className="flex flex-col gap-3 rounded-2xl border border-surface-line bg-surface-raised p-5 shadow-card sm:p-6">
            <label className="flex cursor-pointer items-center gap-3 text-sm font-semibold text-ink">
              <input
                type="checkbox"
                checked={autoClean}
                onChange={(e) => setAutoClean(e.target.checked)}
                className="h-4.5 w-4.5 rounded border-surface-line bg-surface-raised text-brand-400 focus:ring-brand-400 focus:ring-offset-surface-raised disabled:opacity-50"
                disabled={isUploading}
              />
              Auto-clean dataset with LLM upon upload
            </label>
            {autoClean && (
              <div className="pl-7">
                <input
                  type="text"
                  placeholder="Optional cleaning instructions (e.g. 'remove outliers', 'standardize column names')"
                  value={cleaningInstructions}
                  onChange={(e) => setCleaningInstructions(e.target.value)}
                  disabled={isUploading}
                  className="w-full rounded-xl border border-surface-line bg-surface-sunken px-3 py-2.5 text-sm text-ink placeholder:text-ink-muted focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 disabled:opacity-50"
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="mx-auto mt-5 flex w-full max-w-6xl items-start gap-2 rounded-xl border border-danger-500/40 bg-danger-500/10 px-4 py-3 text-sm text-danger-50 shadow-soft animate-fade-up">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-danger-500" strokeWidth={1.8} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
