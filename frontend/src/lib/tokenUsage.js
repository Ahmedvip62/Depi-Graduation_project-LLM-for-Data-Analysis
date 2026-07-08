export const DEFAULT_CONTEXT_WINDOW_TOKENS = 256000;
export const IMAGE_TOKEN_ESTIMATE = 256;

export const estimateTextTokens = (text = '') => {
  const value = String(text || '');
  if (!value.trim()) return 0;
  return Math.max(1, Math.ceil(value.length / 4));
};

export const estimateAttachmentTokens = (attachment) => {
  if (!attachment) return 0;
  if (attachment.type === 'image') return IMAGE_TOKEN_ESTIMATE;
  return 0;
};

export const estimateMessageTokens = (message = {}) => {
  const textTokens = estimateTextTokens(message.content) + estimateTextTokens(message.thinking);
  const attachmentTokens = (message.attachments || []).reduce(
    (sum, item) => sum + estimateAttachmentTokens(item),
    0
  );
  return textTokens + attachmentTokens + 12;
};

export const estimateConversationTokens = (messages = [], draft = '', draftAttachments = []) => {
  const historyTokens = messages.reduce((sum, message) => sum + estimateMessageTokens(message), 0);
  const draftTokens = estimateTextTokens(draft) + draftAttachments.reduce(
    (sum, item) => sum + estimateAttachmentTokens(item),
    0
  );
  return historyTokens + draftTokens;
};

export const getLatestAnswerUsage = (messages = []) => {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const usage = messages[i]?.usage;
    if (usage && usage.phase === 'answer') return usage;
  }
  return null;
};

export const formatTokens = (value = 0) => {
  const n = Number(value || 0);
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 10000) return `${Math.round(n / 1000)}K`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toLocaleString();
};

export const usageLabel = (usage) => {
  if (!usage) return 'estimated';
  return usage.source ? `${usage.source} usage` : 'actual usage';
};
