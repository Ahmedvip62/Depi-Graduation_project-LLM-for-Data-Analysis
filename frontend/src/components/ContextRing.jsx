import React from 'react';
import { formatTokens, usageLabel } from '../lib/tokenUsage';

const ContextRing = ({ usedTokens = 0, maxTokens = 256000, latestUsage = null }) => {
  const safeMax = Math.max(1, maxTokens || 256000);
  const percentage = Math.min((usedTokens / safeMax) * 100, 100);
  const tone = percentage > 85 ? 'bg-danger-500' : percentage > 65 ? 'bg-accent-300' : 'bg-brand-300';

  return (
    <div
      className="group relative hidden min-w-[174px] rounded-xl border border-surface-line bg-surface-sunken px-3 py-2 shadow-soft sm:block"
      title="Approximate visible context usage"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-wider text-ink-faint">Tokens</div>
          <div className="text-xs font-semibold text-ink whitespace-nowrap">
            ~{formatTokens(usedTokens)} / {formatTokens(safeMax)}
          </div>
        </div>
        <div className="text-xs font-bold text-ink-soft">{Math.round(percentage)}%</div>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-hover">
        <div
          className={`h-full rounded-full transition-all duration-700 ${tone}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="absolute right-0 top-full z-50 mt-2 hidden w-72 rounded-xl border border-surface-line bg-surface-raised px-3 py-2 text-2xs text-ink-soft shadow-float group-hover:block group-focus-within:block">
        <div className="font-semibold uppercase tracking-wider text-ink-faint">Current estimate</div>
        <div className="mt-1">~{usedTokens.toLocaleString()} visible tokens in this session.</div>
        {latestUsage && (
          <div className="mt-2 border-t border-surface-line pt-2">
            <div className="font-semibold uppercase tracking-wider text-ink-faint">Latest turn</div>
            <div className="mt-1">
              {usageLabel(latestUsage)}: {formatTokens(latestUsage.total_tokens)} total
              {latestUsage.prompt_tokens != null && latestUsage.completion_tokens != null
                ? ` (${formatTokens(latestUsage.prompt_tokens)} prompt, ${formatTokens(latestUsage.completion_tokens)} response)`
                : ''}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextRing;