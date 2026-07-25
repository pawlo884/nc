import { useCallback } from 'react';
import { getErrorMessage } from '../utils/errors';
import { useToast } from './useToast';

export function useActionMessages() {
  const { showToast } = useToast();

  const setError = useCallback(
    (message: string | null) => {
      if (message) {
        showToast('error', message);
      }
    },
    [showToast]
  );

  const setSuccess = useCallback(
    (message: string | null) => {
      if (message) {
        showToast('success', message);
      }
    },
    [showToast]
  );

  const reportError = useCallback(
    (err: unknown, fallback: string) => {
      showToast('error', getErrorMessage(err, fallback));
    },
    [showToast]
  );

  return { setError, setSuccess, reportError };
}
