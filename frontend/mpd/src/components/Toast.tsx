export type ToastKind = 'error' | 'success';

interface ToastProps {
  message: string;
  kind: ToastKind;
  onClose: () => void;
}

export function Toast({ message, kind, onClose }: ToastProps) {
  return (
    <div className={`toast alert alert-${kind}`}>
      <span>{message}</span>
      <button type="button" className="toast__close" onClick={onClose} aria-label="Zamknij">
        ×
      </button>
    </div>
  );
}
