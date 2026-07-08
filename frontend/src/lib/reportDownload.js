import { apiFetch, readError } from './api';

// A real PDF starts with %PDF-. Gate "this isn't a PDF" on the actual bytes,
// not the content-type header: a proxy can rewrite the type, and a successful
// JSON envelope (with detail/message) is the only error case we should treat as
// one.
const PDF_MAGIC = '%PDF-';

export const downloadReport = async (sessionId) => {
  if (!sessionId) throw new Error('No active session to export.');

  const response = await apiFetch(`/api/skills/report?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await readError(response, 'Failed to generate report.'));

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('json')) {
    // A JSON body on a 2xx means the endpoint returned an error envelope, not a PDF.
    const message = await readError(response, 'Report endpoint did not return a PDF.');
    throw new Error(message);
  }

  const blob = await response.blob();
  if (!blob.size) throw new Error('Report generation returned an empty file.');

  // Confirm the bytes are actually a PDF; a mislabeled JSON/text body would
  // otherwise be saved as a corrupt .pdf.
  const head = await blob.slice(0, 5).text();
  if (!head.startsWith(PDF_MAGIC)) {
    // Likely a JSON error envelope that lacked the json content-type; surface it.
    const text = await blob.text();
    try {
      const data = JSON.parse(text);
      throw new Error(data.detail || data.message || 'Report endpoint did not return a PDF.');
    } catch (e) {
      if (e instanceof Error && e.message && !e.message.includes('Unexpected')) throw e;
      throw new Error('Report endpoint did not return a PDF.');
    }
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `Universal_Analyst_Report_${String(sessionId).substring(0, 8)}.pdf`;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};