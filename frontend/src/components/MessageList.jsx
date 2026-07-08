import React, { useRef, useEffect } from 'react';
import { MessageSquareText } from 'lucide-react';
import ChatMessage from './ChatMessage';

const MessageList = ({ messages, suggestions = [], onSuggestion, exportError, onRegenerate, isLoading }) => {
  const endRef = useRef(null);
  const wasStreamingRef = useRef(false);

  // Snap-scroll while a turn is streaming (every token), so a long answer
  // doesn't stutter on repeated smooth-scrolls or fight a user scrolling up.
  // Smooth-scroll only when a turn completes (streaming -> not streaming).
  useEffect(() => {
    const last = messages[messages.length - 1];
    const streaming = last && !last.done;
    const justFinished = wasStreamingRef.current && !streaming;
    wasStreamingRef.current = streaming;
    endRef.current?.scrollIntoView({ behavior: justFinished ? 'smooth' : 'auto' });
  }, [messages]);

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4 text-center animate-fade-in">
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-400/30 bg-brand-400/10 text-brand-100 shadow-soft">
          <MessageSquareText className="h-7 w-7" strokeWidth={1.7} />
        </div>
        <h3 className="mb-2 font-display text-2xl font-semibold text-ink">Start an analysis turn</h3>
        <p className="max-w-md text-sm leading-relaxed text-ink-muted">
          Ask about the active dataset, attach an image, or dictate the question from the composer.
        </p>
        {suggestions.length > 0 && (
          <div className="mt-6 flex max-w-xl flex-wrap justify-center gap-2">
            {suggestions.slice(0, 6).map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggestion?.(s)}
                className="rounded-lg border border-surface-line bg-surface-raised px-4 py-2 text-sm text-ink-soft shadow-soft transition-all hover:border-brand-400 hover:text-brand-100 animate-fade-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-x-hidden overflow-y-auto px-1 sm:px-2 scroll-thin">
      <div className="h-4" />
      <div className="space-y-6">
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            exportError={exportError}
            onRegenerate={onRegenerate}
            canRegenerate={!isLoading && msg.id === messages[messages.length - 1]?.id}
          />
        ))}
      </div>
      <div ref={endRef} className="h-4" />
    </div>
  );
};

export default MessageList;