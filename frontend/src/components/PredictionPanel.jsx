import React, { useState, useCallback, useRef } from 'react';
import {
  BrainCircuit,
  Target,
  TrendingUp,
  Loader2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  Sparkles,
  Crosshair,
  Layers,
  Zap,
} from 'lucide-react';
import { apiFetch } from '../lib/api';

/* ── Status step indicator ────────────────────────────────────────────── */

const STEPS = [
  { key: 'analyzing', label: 'Analyzing dataset', icon: BrainCircuit },
  { key: 'selecting_model', label: 'Selecting model', icon: Target },
  { key: 'preparing', label: 'Preparing data', icon: Layers },
  { key: 'training', label: 'Training model', icon: Zap },
  { key: 'evaluating', label: 'Evaluating', icon: BarChart3 },
];

const StatusStep = ({ step, currentStatus, completedSteps }) => {
  const isActive = currentStatus === step.key;
  const isCompleted = completedSteps.has(step.key);
  const Icon = step.icon;

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300 ${
      isActive ? 'bg-brand-400/10 border border-brand-400/30' :
      isCompleted ? 'bg-surface-muted/50 border border-surface-line/50' :
      'border border-transparent opacity-40'
    }`}>
      <div className={`flex items-center justify-center w-7 h-7 rounded-full transition-all ${
        isActive ? 'bg-brand-400/20 text-brand-100' :
        isCompleted ? 'bg-emerald-500/15 text-emerald-400' :
        'bg-surface-muted text-ink-muted'
      }`}>
        {isCompleted ? (
          <CheckCircle2 className="w-4 h-4" />
        ) : isActive ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Icon className="w-4 h-4" />
        )}
      </div>
      <span className={`text-sm font-medium transition-colors ${
        isActive ? 'text-brand-100' : isCompleted ? 'text-ink-faint' : 'text-ink-muted'
      }`}>
        {step.label}
      </span>
    </div>
  );
};

/* ── Metric card ─────────────────────────────────────────────────────── */

const MetricCard = ({ label, value, highlight, subtext }) => (
  <div className={`relative overflow-hidden rounded-xl border p-4 transition-all hover:border-brand-400/30 ${
    highlight ? 'border-brand-400/40 bg-brand-400/5' : 'border-surface-line bg-surface-raised'
  }`}>
    {highlight && (
      <div className="absolute inset-0 bg-gradient-to-br from-brand-400/5 to-transparent pointer-events-none" />
    )}
    <p className="text-2xs font-semibold uppercase tracking-wider text-ink-muted mb-1">{label}</p>
    <p className="font-mono text-2xl font-bold text-ink tabular-nums">{value}</p>
    {subtext && <p className="text-2xs text-ink-faint mt-1">{subtext}</p>}
  </div>
);

/* ── Confusion matrix ────────────────────────────────────────────────── */

const ConfusionMatrix = ({ matrix, labels }) => {
  if (!matrix || matrix.length === 0) return null;

  const maxVal = Math.max(...matrix.flat());
  const getIntensity = (val) => Math.round((val / Math.max(maxVal, 1)) * 100);

  const displayLabels = labels || matrix.map((_, i) => `Class ${i}`);

  return (
    <div className="rounded-xl border border-surface-line bg-surface-raised p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-3 flex items-center gap-2">
        <Crosshair className="w-3.5 h-3.5" />
        Confusion Matrix
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-2xs text-ink-faint p-1.5 text-left">Actual ↓ / Predicted →</th>
              {displayLabels.map((label, i) => (
                <th key={i} className="text-2xs text-ink-muted p-1.5 text-center font-mono">
                  {String(label).length > 10 ? String(label).slice(0, 10) + '…' : String(label)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, ri) => (
              <tr key={ri}>
                <td className="text-2xs text-ink-muted p-1.5 font-mono">
                  {String(displayLabels[ri]).length > 10 ? String(displayLabels[ri]).slice(0, 10) + '…' : String(displayLabels[ri])}
                </td>
                {row.map((val, ci) => {
                  const intensity = getIntensity(val);
                  const isDiagonal = ri === ci;
                  return (
                    <td
                      key={ci}
                      className="p-1.5 text-center font-mono text-xs font-semibold"
                      style={{
                        backgroundColor: isDiagonal
                          ? `rgba(99, 102, 241, ${intensity / 100 * 0.4})`
                          : `rgba(239, 68, 68, ${intensity / 100 * 0.3})`,
                        color: intensity > 50 ? '#fff' : 'var(--ink)',
                      }}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ── Feature importance bars ─────────────────────────────────────────── */

const FeatureImportances = ({ features }) => {
  const [expanded, setExpanded] = useState(false);
  if (!features || features.length === 0) return null;

  const maxImportance = Math.max(...features.map((f) => f.importance));
  const visible = expanded ? features : features.slice(0, 8);

  return (
    <div className="rounded-xl border border-surface-line bg-surface-raised p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-3 flex items-center gap-2">
        <BarChart3 className="w-3.5 h-3.5" />
        Feature Importances
      </h4>
      <div className="space-y-2">
        {visible.map((feat, i) => {
          const pct = (feat.importance / Math.max(maxImportance, 0.001)) * 100;
          return (
            <div key={feat.feature} className="group">
              <div className="flex items-center justify-between text-2xs mb-0.5">
                <span className="text-ink-muted font-medium truncate max-w-[65%]">{feat.feature}</span>
                <span className="font-mono text-ink-faint tabular-nums">{feat.importance.toFixed(4)}</span>
              </div>
              <div className="h-2 rounded-full bg-surface-sunken overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${pct}%`,
                    background: i === 0
                      ? 'linear-gradient(90deg, var(--brand-400), var(--brand-300))'
                      : i < 3
                        ? 'var(--brand-400)'
                        : 'var(--ink-muted)',
                    opacity: i < 3 ? 1 : 0.5,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {features.length > 8 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-2xs text-brand-200 hover:text-brand-100 flex items-center gap-1 transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${features.length} features`}
        </button>
      )}
    </div>
  );
};

/* ── Sample predictions table ────────────────────────────────────────── */

const SamplePredictions = ({ samples, taskType }) => {
  const [expanded, setExpanded] = useState(false);
  if (!samples || samples.length === 0) return null;

  const visible = expanded ? samples : samples.slice(0, 10);

  return (
    <div className="rounded-xl border border-surface-line bg-surface-raised p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-3 flex items-center gap-2">
        <TrendingUp className="w-3.5 h-3.5" />
        Sample Predictions
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-surface-line">
              <th className="text-left p-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted">#</th>
              <th className="text-left p-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted">Actual</th>
              <th className="text-left p-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted">Predicted</th>
              <th className="text-left p-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted">
                {taskType === 'classification' ? 'Correct' : 'Error'}
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((sample) => {
              const isCorrect = taskType === 'classification' ? sample.correct : null;
              return (
                <tr
                  key={sample.index}
                  className="border-b border-surface-line/50 hover:bg-surface-hover/50 transition-colors"
                >
                  <td className="p-2 font-mono text-ink-faint">{sample.index + 1}</td>
                  <td className="p-2 font-mono text-ink">{sample.actual}</td>
                  <td className="p-2 font-mono text-ink">{sample.predicted}</td>
                  <td className="p-2 font-mono">
                    {taskType === 'classification' ? (
                      <span className={isCorrect ? 'text-emerald-400' : 'text-red-400'}>
                        {isCorrect ? '✓' : '✗'}
                      </span>
                    ) : (
                      <span className="text-accent-400">{sample.error}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {samples.length > 10 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-2xs text-brand-200 hover:text-brand-100 flex items-center gap-1 transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          {expanded ? 'Show less' : `Show all ${samples.length} predictions`}
        </button>
      )}
    </div>
  );
};

/* ── LLM reasoning card ──────────────────────────────────────────────── */

const ReasoningCard = ({ title, icon: Icon, reason, tag, tagColor }) => (
  <div className="rounded-xl border border-surface-line bg-surface-raised p-4 relative overflow-hidden">
    <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-brand-400 via-brand-300 to-transparent" />
    <div className="flex items-start gap-3">
      <div className="flex-none w-9 h-9 rounded-lg bg-brand-400/10 flex items-center justify-center text-brand-200">
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="text-sm font-semibold text-ink">{title}</h4>
          {tag && (
            <span className={`text-2xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
              tagColor || 'bg-brand-400/15 text-brand-200'
            }`}>
              {tag}
            </span>
          )}
        </div>
        <p className="text-xs text-ink-muted leading-relaxed">{reason}</p>
      </div>
    </div>
  </div>
);

/* ── Main PredictionPanel ────────────────────────────────────────────── */

export default function PredictionPanel({ sessionId, profile, onError }) {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStatus, setCurrentStatus] = useState(null);
  const [statusDetail, setStatusDetail] = useState('');
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const [targetInfo, setTargetInfo] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const markCompleted = (status) => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      next.add(status);
      return next;
    });
  };

  const resetState = () => {
    setCurrentStatus(null);
    setStatusDetail('');
    setCompletedSteps(new Set());
    setTargetInfo(null);
    setModelInfo(null);
    setResult(null);
    setError(null);
  };

  const runPrediction = useCallback(async () => {
    if (!sessionId || isRunning) return;

    resetState();
    setIsRunning(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await apiFetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        let errMsg = 'Prediction failed.';
        try {
          const errData = await response.json();
          errMsg = errData.detail || errMsg;
        } catch { /* ignore */ }
        throw new Error(errMsg);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let prevStatus = null;

      const handleFrame = (frame) => {
        let eventName = 'message';
        const dataLines = [];
        for (const raw of frame.split('\n')) {
          const line = raw.replace(/\r$/, '');
          if (line.startsWith('event:')) eventName = line.slice(6).trim();
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
        }
        if (dataLines.length === 0) return;

        let payload;
        try {
          payload = JSON.parse(dataLines.join('\n'));
        } catch { return; }

        switch (eventName) {
          case 'prediction_status':
            if (prevStatus) markCompleted(prevStatus);
            prevStatus = payload.status;
            setCurrentStatus(payload.status);
            setStatusDetail(payload.detail || '');
            break;

          case 'prediction_target':
            markCompleted('analyzing');
            setTargetInfo(payload.target);
            break;

          case 'prediction_model':
            markCompleted('selecting_model');
            setModelInfo(payload.model);
            break;

          case 'prediction_result':
            markCompleted('preparing');
            markCompleted('training');
            markCompleted('evaluating');
            setResult(payload.result);
            break;

          case 'prediction_error':
            setError(payload.message);
            break;

          case 'prediction_done':
            // All done
            break;

          default:
            break;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let delimIdx;
        while ((delimIdx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, delimIdx);
          buffer = buffer.slice(delimIdx + 2);
          if (frame.trim()) handleFrame(frame);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) handleFrame(buffer);

    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Prediction failed.');
        onError?.(err.message || 'Prediction failed.');
      }
    } finally {
      abortRef.current = null;
      setIsRunning(false);
    }
  }, [sessionId, isRunning, onError]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const hasResult = result != null;
  const metrics = result?.metrics || {};
  const taskType = result?.task_type || targetInfo?.task_type || 'classification';
  const isClassification = taskType === 'classification';

  /* ── Empty state ─────────────────────────────────────────────────────── */

  if (!hasResult && !isRunning && !error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-brand-400/10 flex items-center justify-center mb-6">
          <BrainCircuit className="w-8 h-8 text-brand-200" strokeWidth={1.5} />
        </div>
        <h2 className="text-lg font-display font-semibold text-ink mb-2">
          LLM-Driven Prediction
        </h2>
        <p className="text-sm text-ink-muted max-w-md mb-8 leading-relaxed">
          The LLM will analyze your dataset, choose the best target column and ML model,
          then train and evaluate it automatically.
        </p>
        <button
          onClick={runPrediction}
          disabled={!sessionId}
          className="group flex items-center gap-2.5 rounded-xl bg-brand-400 px-6 py-3 text-sm font-semibold text-surface-sunken shadow-soft transition-all hover:bg-brand-300 hover:shadow-md disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Sparkles className="w-4.5 h-4.5 transition-transform group-hover:rotate-12" />
          Run Prediction
        </button>
      </div>
    );
  }

  /* ── Main view (running / results) ───────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-display font-semibold text-ink">
            {hasResult ? 'Prediction Results' : 'Running Prediction Pipeline'}
          </h2>
          {statusDetail && !hasResult && (
            <p className="text-xs text-ink-muted mt-0.5">{statusDetail}</p>
          )}
        </div>
        {isRunning ? (
          <button
            onClick={handleStop}
            className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold text-red-400 transition-colors hover:bg-red-500/20"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={runPrediction}
            className="flex items-center gap-2 rounded-lg bg-brand-400 px-4 py-2 text-xs font-semibold text-surface-sunken transition-colors hover:bg-brand-300"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {hasResult ? 'Re-run' : 'Run'}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-none mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Progress steps (while running) */}
      {isRunning && (
        <div className="rounded-xl border border-surface-line bg-surface-raised p-4">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            {STEPS.map((step) => (
              <StatusStep
                key={step.key}
                step={step}
                currentStatus={currentStatus}
                completedSteps={completedSteps}
              />
            ))}
          </div>
        </div>
      )}

      {/* LLM reasoning cards */}
      {targetInfo && (
        <ReasoningCard
          title={`Target: ${targetInfo.column}`}
          icon={Target}
          reason={targetInfo.reason}
          tag={targetInfo.task_type}
          tagColor={isClassification ? 'bg-indigo-500/15 text-indigo-300' : 'bg-emerald-500/15 text-emerald-300'}
        />
      )}

      {modelInfo && (
        <ReasoningCard
          title={modelInfo.display_name}
          icon={BrainCircuit}
          reason={modelInfo.reason}
          tag="selected model"
        />
      )}

      {/* Results */}
      {hasResult && (
        <>
          {/* Data summary */}
          <div className="flex items-center gap-4 text-2xs text-ink-faint font-mono">
            <span>{result.train_samples.toLocaleString()} train</span>
            <span className="w-1 h-1 rounded-full bg-ink-faint" />
            <span>{result.test_samples.toLocaleString()} test</span>
            <span className="w-1 h-1 rounded-full bg-ink-faint" />
            <span>{result.feature_count} features</span>
          </div>

          {/* Metrics grid */}
          <div className={`grid gap-3 ${isClassification ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-2 sm:grid-cols-4'}`}>
            {isClassification ? (
              <>
                <MetricCard label="Accuracy" value={`${(metrics.accuracy * 100).toFixed(1)}%`} highlight />
                <MetricCard label="Precision" value={`${(metrics.precision * 100).toFixed(1)}%`} />
                <MetricCard label="Recall" value={`${(metrics.recall * 100).toFixed(1)}%`} />
                <MetricCard label="F1 Score" value={`${(metrics.f1_score * 100).toFixed(1)}%`} highlight />
              </>
            ) : (
              <>
                <MetricCard label="R² Score" value={metrics.r2_score?.toFixed(4)} highlight subtext="Higher is better" />
                <MetricCard label="MAE" value={metrics.mae?.toFixed(4)} subtext="Mean Absolute Error" />
                <MetricCard label="RMSE" value={metrics.rmse?.toFixed(4)} highlight subtext="Root Mean Squared Error" />
                <MetricCard label="MSE" value={metrics.mse?.toFixed(4)} subtext="Mean Squared Error" />
              </>
            )}
          </div>

          {/* Confusion matrix (classification) + Feature importances */}
          <div className={`grid gap-4 ${isClassification && metrics.confusion_matrix ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
            {isClassification && (
              <ConfusionMatrix matrix={metrics.confusion_matrix} labels={metrics.class_labels} />
            )}
            <FeatureImportances features={result.feature_importances} />
          </div>

          {/* Sample predictions */}
          <SamplePredictions samples={metrics.sample_predictions} taskType={taskType} />
        </>
      )}
    </div>
  );
}
