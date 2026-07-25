import axios from 'axios';

export function getErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { message?: string; detail?: string } | undefined;
    return data?.message || data?.detail || err.message || fallback;
  }
  return fallback;
}
