import React, { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import { LoaderCircle, Mic, Paperclip, Send, SlidersHorizontal, X } from 'lucide-react';

const DEFAULT_ACCEPTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

const fileToAttachment = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result || '');
      const data = url.includes(',') ? url.split(',', 2)[1] : url;
      resolve({
        id: `${Date.now()}-${file.name}-${file.size}`,
        type: 'image',
        mime_type: file.type,
        name: file.name || 'image',
        size: file.size,
        data,
        url,
      });
    };
    reader.onerror = () => reject(new Error('Could not read that image.'));
    reader.readAsDataURL(file);
  });

const ChatInput = ({
  input,
  setInput,
  handleSendMessage,
  isLoading,
  onStop,
  onError,
  maxImages = 3,
  maxImageMb = 5,
  imageChatEnabled = true,
  acceptedImageTypes = DEFAULT_ACCEPTED_IMAGE_TYPES,
  onDraftAttachmentsChange,
}) => {
  const [enableThinking, setEnableThinking] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const allowedImageTypes = Array.isArray(acceptedImageTypes) && acceptedImageTypes.length
    ? acceptedImageTypes
    : DEFAULT_ACCEPTED_IMAGE_TYPES;
  const acceptedTypeLabel = useMemo(
    () => allowedImageTypes.map((type) => type.split('/')[1]?.toUpperCase()).filter(Boolean).join(', '),
    [allowedImageTypes]
  );

  const speechSupported = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  useEffect(() => {
    onDraftAttachmentsChange?.(attachments);
  }, [attachments, onDraftAttachmentsChange]);

  useEffect(() => () => onDraftAttachmentsChange?.([]), [onDraftAttachmentsChange]);

  const addFiles = useCallback(
    async (fileList) => {
      if (!imageChatEnabled || isLoading) return;
      const files = Array.from(fileList || []).filter((file) => file?.type?.startsWith('image/'));
      if (!files.length) return;

      const remaining = maxImages - attachments.length;
      if (remaining <= 0) {
        onError?.(`Attach up to ${maxImages} images per turn.`);
        return;
      }

      const maxBytes = maxImageMb * 1024 * 1024;
      const accepted = [];
      for (const file of files) {
        if (!allowedImageTypes.includes(file.type)) {
          onError?.(`Use ${acceptedTypeLabel || 'supported'} images.`);
          continue;
        }
        if (file.size > maxBytes) {
          onError?.(`${file.name || 'Image'} is larger than ${maxImageMb}MB.`);
          continue;
        }
        accepted.push(file);
      }

      const selected = accepted.slice(0, remaining);
      if (accepted.length > selected.length) {
        onError?.(`Only ${remaining} more image${remaining === 1 ? '' : 's'} can be attached.`);
      }
      if (!selected.length) return;

      try {
        const next = await Promise.all(selected.map(fileToAttachment));
        setAttachments((prev) => [...prev, ...next]);
        setMenuOpen(false);
      } catch (err) {
        onError?.(err.message || 'Could not attach that image.');
      }
    },
    [acceptedTypeLabel, allowedImageTypes, attachments.length, imageChatEnabled, isLoading, maxImageMb, maxImages, onError]
  );

  const removeAttachment = (id) => {
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  };

  const submit = () => {
    if (isLoading) return;
    const text = input.trim();
    if (!text && attachments.length === 0) return;
    const message = text || 'Please analyze the attached image in the context of this dataset.';
    recognitionRef.current?.stop();
    setIsListening(false);
    handleSendMessage(message, enableThinking, attachments);
    setAttachments([]);
    setMenuOpen(false);
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onPaste = (e) => {
    const imageFiles = Array.from(e.clipboardData?.files || []).filter((file) => file.type?.startsWith('image/'));
    if (imageFiles.length) {
      e.preventDefault();
      addFiles(imageFiles);
    }
  };

  const toggleListening = () => {
    if (!speechSupported || isLoading) return;
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event) => {
      setIsListening(false);
      onError?.(event.error ? `Speech input failed: ${event.error}` : 'Speech input failed.');
    };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results || [])
        .map((result) => result?.[0]?.transcript || '')
        .join(' ')
        .trim();
      if (transcript) {
        setInput((prev) => `${prev.trim() ? `${prev.trim()} ` : ''}${transcript}`);
      }
    };
    recognitionRef.current = recognition;
    recognition.start();
    setMenuOpen(false);
  };

  const hasPayload = Boolean(input.trim()) || attachments.length > 0;

  return (
    <div
      className="sticky bottom-0 w-full border-t border-surface-line bg-surface/95 pb-4 pt-3 backdrop-blur-md"
      onDragOver={(e) => {
        if (!imageChatEnabled) return;
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        if (!imageChatEnabled) return;
        e.preventDefault();
        setIsDragOver(false);
        addFiles(e.dataTransfer.files);
      }}
    >
      <div className="mx-auto w-full max-w-5xl">
        {(attachments.length > 0 || isListening || isLoading) && (
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
            <div className="flex flex-wrap items-center gap-2">
              {attachments.length > 0 && (
                <span className="rounded-full border border-brand-400/35 bg-brand-400/10 px-2.5 py-1 text-2xs font-semibold text-brand-100">
                  {attachments.length} image{attachments.length === 1 ? '' : 's'} attached
                </span>
              )}
              {isListening && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-300/35 bg-accent-300/10 px-2.5 py-1 text-2xs font-semibold text-accent-100">
                  <span className="h-2 w-2 rounded-full bg-accent-300 animate-pulse-soft" />
                  Listening
                </span>
              )}
            </div>
            {isLoading && onStop && (
              <button
                type="button"
                onClick={() => {
                  recognitionRef.current?.stop();
                  setIsListening(false);
                  onStop();
                }}
                className="inline-flex items-center gap-1.5 rounded-md border border-surface-line bg-surface-raised px-2.5 py-1 text-2xs font-semibold uppercase tracking-wider text-ink-muted hover:text-brand-100"
              >
                <span className="h-2.5 w-2.5 rounded-[2px] bg-current" />
                Stop
              </button>
            )}
          </div>
        )}

        <div
          className={`relative rounded-2xl border bg-surface-raised p-2 shadow-raised transition-all duration-200 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-400/20 ${
            isDragOver ? 'border-brand-300 ring-2 ring-brand-400/20' : 'border-surface-line'
          }`}
        >
          {attachments.length > 0 && (
            <div className="mb-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {attachments.map((attachment) => (
                <div key={attachment.id} className="relative overflow-hidden rounded-xl border border-surface-line bg-surface-sunken">
                  <img src={attachment.url} alt={attachment.name} className="h-24 w-full object-cover" />
                  <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                    <span className="truncate text-2xs font-medium text-ink-muted">{attachment.name}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachment(attachment.id)}
                      aria-label={`Remove ${attachment.name}`}
                      className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-surface-raised text-ink-muted shadow-soft hover:text-brand-100"
                    >
                      <X className="h-3.5 w-3.5" strokeWidth={2} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept={allowedImageTypes.join(',')}
              multiple
              className="hidden"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = '';
              }}
              disabled={!imageChatEnabled || isLoading}
            />

            <div className="relative flex-none">
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                disabled={isLoading}
                aria-label="Open message tools"
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-surface-line bg-surface-sunken text-ink-soft transition-colors hover:border-brand-400 hover:text-brand-100 disabled:opacity-40"
              >
                <SlidersHorizontal className="h-4 w-4" strokeWidth={1.8} />
              </button>

              {menuOpen && (
                <div className="absolute bottom-full left-0 z-50 mb-2 w-64 overflow-hidden rounded-xl border border-surface-line bg-surface-raised shadow-float">
                  <button
                    type="button"
                    onClick={() => setEnableThinking((value) => !value)}
                    className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left text-sm text-ink-soft hover:bg-surface-sunken"
                  >
                    <span>
                      <span className="block font-semibold text-ink">Extended thinking</span>
                      <span className="text-2xs text-ink-muted">Plan before answering</span>
                    </span>
                    <span className={`relative h-5 w-9 rounded-full transition-colors ${enableThinking ? 'bg-brand-400' : 'bg-surface-hover'}`}>
                      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-surface-sunken shadow-sm transition-transform ${enableThinking ? 'translate-x-[18px]' : 'translate-x-0.5'}`} />
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={!imageChatEnabled || attachments.length >= maxImages}
                    className="flex w-full items-center gap-3 px-3 py-3 text-left text-sm font-semibold text-ink-soft hover:bg-surface-sunken disabled:opacity-40"
                  >
                    <Paperclip className="h-4 w-4" strokeWidth={1.8} />
                    Attach image
                  </button>
                  <button
                    type="button"
                    onClick={toggleListening}
                    disabled={!speechSupported}
                    className="flex w-full items-center gap-3 px-3 py-3 text-left text-sm font-semibold text-ink-soft hover:bg-surface-sunken disabled:opacity-40"
                  >
                    <Mic className="h-4 w-4" strokeWidth={1.8} />
                    Dictate
                  </button>
                </div>
              )}
            </div>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              onPaste={onPaste}
              placeholder={attachments.length ? 'Ask about the attached image...' : 'Ask about the dataset...'}
              disabled={isLoading}
              rows={1}
              aria-label="Message the analyst"
              className="max-h-[150px] min-h-[40px] flex-1 resize-none overflow-y-auto bg-transparent px-2 py-2.5 text-[0.95rem] text-ink placeholder-ink-faint focus:outline-none scroll-thin"
            />

            <button
              type="button"
              onClick={submit}
              disabled={isLoading || !hasPayload}
              className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-brand-400 text-surface-sunken shadow-soft transition-all duration-200 hover:bg-brand-300 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send message"
            >
              {isLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" strokeWidth={2} />
              ) : (
                <Send className="h-4 w-4" fill="currentColor" strokeWidth={0} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
