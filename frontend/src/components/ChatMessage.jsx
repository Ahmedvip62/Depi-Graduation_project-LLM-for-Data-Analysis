import React, { useState, useEffect } from 'react';
import { BookOpen, BrainCircuit, ChevronRight, Copy, Check, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import LazyChartCard from './LazyChartCard';
import Logo from './Logo';
import { estimateMessageTokens, formatTokens } from '../lib/tokenUsage';

const CODE_BLOCK_RE = /```[\s\S]*?```/g;

const TypingDots = () => (
  <span className="inline-flex items-center gap-1 align-middle">
    <span className="h-1.5 w-1.5 rounded-full bg-brand-300 animate-typing" />
    <span className="h-1.5 w-1.5 rounded-full bg-brand-300 animate-typing animation-delay-150" />
    <span className="h-1.5 w-1.5 rounded-full bg-brand-300 animate-typing animation-delay-300" />
  </span>
);

const markdownComponents = {
  a: ({ node, ...props }) => <a target="_blank" rel="noreferrer" {...props} />,
};

const AttachmentGrid = ({ attachments = [], align = 'right' }) => {
  if (!attachments.length) return null;
  return (
    <div className={`mt-2 grid max-w-[85%] grid-cols-1 gap-2 sm:max-w-[75%] ${align === 'right' ? 'ml-auto' : ''}`}>
      {attachments.map((attachment, idx) => (
        <div key={attachment.id || `${attachment.name}-${idx}`} className="overflow-hidden rounded-xl border border-surface-line bg-surface-raised shadow-soft">
          {attachment.url ? (
            <img src={attachment.url} alt={attachment.name || 'Attached image'} className="max-h-72 w-full object-cover" />
          ) : (
            <div className="flex h-24 items-center justify-center text-xs text-ink-muted">Image attachment</div>
          )}
          <div className="flex items-center justify-between gap-2 px-3 py-2">
            <span className="truncate text-xs font-medium text-ink-soft">{attachment.name || `Image ${idx + 1}`}</span>
            <span className="flex-none text-2xs uppercase tracking-wider text-ink-faint">{attachment.mime_type || 'image'}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

const UserBubble = ({ content, attachments }) => (
  <div className="animate-fade-up">
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md border border-brand-400/35 bg-brand-400/10 px-4 py-2.5 text-[0.9rem] leading-relaxed text-ink shadow-soft whitespace-pre-wrap sm:max-w-[75%]">
        {content}
      </div>
    </div>
    <AttachmentGrid attachments={attachments} align="right" />
  </div>
);

const TokenBadge = ({ message, isStreaming }) => {
  const actual = message.usage?.phase === 'answer' && message.usage.total_tokens != null;
  const count = actual ? message.usage.total_tokens : estimateMessageTokens(message);
  const title = actual
    ? `${message.usage.prompt_tokens || 0} prompt / ${message.usage.completion_tokens || 0} response tokens from Ollama`
    : 'Estimated visible tokens for this message';

  return (
    <span
      title={title}
      className={`rounded-full border px-2 py-0.5 text-2xs font-bold uppercase tracking-wide ${
        actual
          ? 'border-accent-300/35 bg-accent-300/10 text-accent-100'
          : isStreaming
            ? 'border-brand-400/35 bg-brand-400/10 text-brand-100'
            : 'border-surface-line bg-surface-sunken text-ink-muted'
      }`}
    >
      {actual ? '' : '~'}{formatTokens(count)} tokens
    </span>
  );
};

// Hover action bar for a finished assistant turn: copy the answer, regenerate it.
const AssistantActions = ({ content, onRegenerate, disabled }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content || '');
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
      <button
        type="button"
        onClick={copy}
        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-2xs font-semibold uppercase tracking-wider text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
        title="Copy answer"
      >
        {copied ? <Check className="h-3 w-3 text-brand-300" strokeWidth={2.4} /> : <Copy className="h-3 w-3" strokeWidth={1.8} />}
        {copied ? 'Copied' : 'Copy'}
      </button>
      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-2xs font-semibold uppercase tracking-wider text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          title="Regenerate answer"
        >
          <RefreshCw className="h-3 w-3" strokeWidth={1.8} />
          Regenerate
        </button>
      )}
    </div>
  );
};

const Phase = ({ message, isStreaming }) => {
  const { skill, thinking, action, phase } = message;
  const thinkingActive = phase === 'thinking' && isStreaming;
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (phase && phase !== 'thinking') setOpen(false);
    if (phase === 'thinking') setOpen(true);
  }, [phase]);

  const hasThinking = (thinking || '').trim().length > 0 || thinkingActive;

  return (
    <div className="mb-2 space-y-2">
      {skill && (
        <div className="inline-flex max-w-full animate-fade-up items-center gap-2 rounded-lg border border-surface-line bg-surface-raised px-2.5 py-1.5 text-ink-soft shadow-soft">
          <BookOpen className="mt-0.5 h-4 w-4 flex-none text-brand-300" strokeWidth={1.8} />
          <div className="min-w-0">
            <div className="text-2xs font-bold uppercase tracking-wider">Using {skill.label}</div>
            {skill.reason && <div className="mt-0.5 text-xs leading-snug text-ink-muted">{skill.reason}</div>}
          </div>
        </div>
      )}

      {hasThinking && (
        <div className="animate-fade-up overflow-hidden rounded-xl border border-surface-line bg-surface-sunken">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-surface-muted/60"
          >
            <ChevronRight className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? 'rotate-90' : ''}`} strokeWidth={2} />
            <BrainCircuit className={`h-4 w-4 ${thinkingActive ? 'text-accent-300' : 'text-ink-faint'}`} strokeWidth={1.8} />
            <span className="text-2xs font-bold uppercase tracking-wider text-ink-muted">
              {thinkingActive ? 'Thinking' : 'Reasoning pass'}
            </span>
            {thinkingActive && <span className="ml-1 inline-block h-2 w-2 rounded-full bg-accent-300 animate-pulse-soft" />}
          </button>
          {open && (
            <div className="px-3 pb-3 pt-0">
              <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap font-mono text-[0.72rem] leading-relaxed text-ink-muted scroll-thin">
                {thinking}
                {thinkingActive && <span className="ml-0.5 inline-block h-3 w-1.5 bg-accent-300 align-middle animate-caret" />}
                {!thinking && thinkingActive && <span className="text-ink-faint">reasoning...</span>}
              </pre>
            </div>
          )}
        </div>
      )}

      {action && isStreaming && phase !== 'answering' && (
        <div className="inline-flex animate-fade-up items-center gap-2 text-xs text-ink-muted">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-300 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-300" />
          </span>
          <span className="font-medium">{action.label}...</span>
        </div>
      )}
    </div>
  );
};

const ChatMessage = ({ message, exportError, onRegenerate, canRegenerate }) => {
  if (message.role === 'user') return <UserBubble content={message.content} attachments={message.attachments} />;

  const isStreaming = !message.done;
  const isError = message.isError;
  const hasCharts = message.charts && message.charts.length > 0;
  const displayContent = hasCharts ? (message.content || '').replace(CODE_BLOCK_RE, '').trim() : (message.content || '').trim();
  const showAnswer = displayContent.length > 0;
  const showAnswerCaret = isStreaming && message.phase === 'answering';
  const idle = isStreaming && !message.skill && !message.thinking && !showAnswer && !message.action;
  const finished = !isStreaming && !isError;

  return (
    <div className="group flex animate-fade-up gap-3">
      <div className="mt-0.5 flex-none">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-surface-line bg-surface-raised text-ink shadow-soft">
          <Logo className="h-4 w-4" />
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          <span className="text-2xs font-bold uppercase tracking-wider text-brand-100">Analyst</span>
          {message.agent_name && message.agent_name !== 'Routing' && (
            <span className="rounded-full border border-accent-300/35 bg-accent-300/10 px-2 py-0.5 text-2xs font-bold uppercase tracking-wide text-accent-100">
              {message.agent_name}
            </span>
          )}
          {(showAnswer || isStreaming) && <TokenBadge message={message} isStreaming={isStreaming} />}
        </div>

        <Phase message={message} isStreaming={isStreaming} />

        {idle && (
          <div className="flex items-center gap-2 text-ink-faint">
            <TypingDots />
            <span className="text-xs">Reading your request...</span>
          </div>
        )}

        {showAnswer && (
          <div
            className={`rounded-2xl rounded-tl-md border px-4 py-3 shadow-card ${
              isError ? 'border-danger-500/40 bg-danger-500/10 text-ink' : 'border-surface-line bg-surface-raised'
            }`}
          >
            <div className="md">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {displayContent}
              </ReactMarkdown>
            </div>
            {message.usage?.phase === 'answer' && (
              <div className="mt-3 border-t border-surface-line pt-2 text-2xs font-medium uppercase tracking-wider text-ink-faint">
                Ollama usage: {formatTokens(message.usage.prompt_tokens || 0)} prompt - {formatTokens(message.usage.completion_tokens || 0)} response
              </div>
            )}
            {showAnswerCaret && <span className="inline-block h-4 w-1.5 bg-brand-300 align-middle animate-caret" />}
          </div>
        )}

        {finished && showAnswer && (
          <AssistantActions content={displayContent} onRegenerate={onRegenerate} disabled={!canRegenerate} />
        )}

        {hasCharts && (
          <div className="mt-3 grid grid-cols-1 gap-3">
            {message.charts.map((c) => (
              <div key={c.id}>
                <LazyChartCard title={c.title} chartSpec={c.config} height={310} onError={exportError} />
                {c.description && (
                  <p className="mt-2 px-1 text-xs leading-relaxed text-ink-muted">{c.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
