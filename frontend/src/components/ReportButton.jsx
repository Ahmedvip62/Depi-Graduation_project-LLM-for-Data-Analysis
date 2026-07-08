import React, { useState } from 'react';
import { FileText, LoaderCircle } from 'lucide-react';
import { downloadReport } from '../lib/reportDownload';

const ReportButton = ({ sessionId, onError }) => {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleDownload = async () => {
    if (!sessionId || isGenerating) return;
    setIsGenerating(true);
    try {
      await downloadReport(sessionId);
    } catch (err) {
      onError?.(err.message || 'Report generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={isGenerating || !sessionId}
      className="flex h-9 items-center gap-1.5 rounded-lg border border-surface-line bg-surface-muted px-3 text-xs font-semibold text-ink-soft shadow-soft transition-colors hover:border-brand-400 hover:text-brand-100 disabled:cursor-not-allowed disabled:opacity-50"
      title="Generate PDF report"
    >
      {isGenerating ? (
        <LoaderCircle className="h-3.5 w-3.5 animate-spin text-brand-100" strokeWidth={2} />
      ) : (
        <FileText className="h-4 w-4" strokeWidth={1.8} />
      )}
      <span className="hidden sm:inline">PDF</span>
    </button>
  );
};

export default ReportButton;