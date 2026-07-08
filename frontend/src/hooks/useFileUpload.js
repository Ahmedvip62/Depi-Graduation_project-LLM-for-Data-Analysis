import { useState, useCallback } from 'react';
import { apiFetch, readError } from '../lib/api';

/**
 * useFileUpload — POST /api/upload (multipart field 'file', 'auto_clean', 'cleaning_instructions').
 * Returns the full payload: { session_id, profile, eda }.
 */
export const useFileUpload = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const clearError = useCallback(() => setUploadError(null), []);

  const uploadFile = useCallback(async (file, options = {}) => {
    if (!file) return null;
    const { autoClean = true, cleaningInstructions = '' } = options;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_clean', autoClean);
    if (cleaningInstructions) {
      formData.append('cleaning_instructions', cleaningInstructions);
    }

    try {
      const response = await apiFetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(await readError(response, 'Failed to upload the file.'));
      }

      return await response.json(); // { session_id, profile, eda }
    } catch (err) {
      setUploadError(err.message);
      return null;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return {
    isUploading,
    uploadError,
    uploadFile,
    clearError,
  };
};
