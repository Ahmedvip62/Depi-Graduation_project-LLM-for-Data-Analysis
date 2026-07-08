import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * A render-level error boundary. A crash in any subtree (e.g. a malformed
 * chart spec, a hook misuse) renders a recoverable fallback instead of a blank
 * white screen, with a button to reset and try again. Without this, one bad
 * component takes the whole app down.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught a render error:', error, info);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex h-screen items-center justify-center bg-surface px-6 text-center">
        <div className="max-w-md animate-fade-up rounded-2xl border border-surface-line bg-surface-raised p-7 shadow-card">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-danger-500/30 bg-danger-500/10 text-danger-500">
            <AlertTriangle className="h-6 w-6" strokeWidth={1.8} />
          </div>
          <h2 className="font-display text-lg font-semibold text-ink">Something rendered badly</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">
            A component hit an error while drawing. The rest of the app is intact — reload the view to try again. If it keeps happening, the runtime logs have the details.
          </p>
          <button
            type="button"
            onClick={this.reset}
            className="mt-5 inline-flex items-center gap-2 rounded-lg border border-brand-400/40 bg-brand-400/10 px-3 py-2 text-sm font-semibold text-brand-100 transition-colors hover:bg-brand-400/15"
          >
            <RefreshCw className="h-4 w-4" strokeWidth={1.8} />
            Try again
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
