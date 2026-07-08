import React, { useEffect } from 'react';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';

const Toast = ({ toast, onDismiss, duration = 5000 }) => {
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(onDismiss, duration);
    return () => clearTimeout(t);
  }, [toast, onDismiss, duration]);

  if (!toast) return null;

  const isError = toast.type !== 'success';
  const Icon = isError ? AlertTriangle : CheckCircle2;

  return (
    <div role="status" aria-live="polite" className="fixed bottom-5 left-1/2 z-[70] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 animate-fade-up">
      <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 shadow-float ${isError ? 'border-danger-500/40 bg-danger-500/12 text-ink' : 'border-brand-400/40 bg-brand-400/12 text-ink'}`}>
        <Icon className={`mt-0.5 h-4 w-4 flex-none ${isError ? 'text-danger-500' : 'text-brand-300'}`} strokeWidth={1.8} />
        <p className="flex-1 text-sm leading-snug text-ink-soft">{toast.message}</p>
        <button type="button" onClick={onDismiss} aria-label="Dismiss" className="flex-none text-ink-faint transition-colors hover:text-ink">
          <X className="h-4 w-4" strokeWidth={2} />
        </button>
      </div>
    </div>
  );
};

export default Toast;