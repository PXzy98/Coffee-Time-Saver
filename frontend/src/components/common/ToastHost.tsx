import { useEffect } from 'react';
import { useUiStore } from '../../store/uiStore';

export function ToastHost() {
  const toasts = useUiStore((state) => state.toasts);
  const dismissToast = useUiStore((state) => state.dismissToast);

  useEffect(() => {
    const timers = toasts.map((toast) =>
      window.setTimeout(() => {
        dismissToast(toast.id);
      }, toast.tone === 'error' ? 6000 : 4000),
    );

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [dismissToast, toasts]);

  return (
    <div className="toast-host">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.tone}`}>
          <p className="toast-title">{toast.title}</p>
          {toast.message ? <p className="toast-message">{toast.message}</p> : null}
        </div>
      ))}
    </div>
  );
}
