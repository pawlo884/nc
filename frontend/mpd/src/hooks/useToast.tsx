import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { Toast, type ToastKind } from '../components/Toast';

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  showToast: (kind: ToastKind, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_DURATION_MS = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts(prev => [...prev, { id, kind, message }]);
      window.setTimeout(() => removeToast(id), TOAST_DURATION_MS);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-stack">
        {toasts.map(t => (
          <Toast key={t.id} message={t.message} kind={t.kind} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast musi być używany wewnątrz ToastProvider');
  }
  return context;
}
