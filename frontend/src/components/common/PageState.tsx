import type { ReactNode } from 'react';

interface StateProps {
  title: string;
  message?: string;
  action?: ReactNode;
}

export function LoadingState({ title }: Pick<StateProps, 'title'>) {
  return (
    <div className="state-card">
      <div className="spinner" />
      <p>{title}</p>
    </div>
  );
}

export function ErrorState({ title, message, action }: StateProps) {
  return (
    <div className="state-card state-card-error">
      <p className="state-title">{title}</p>
      {message ? <p className="state-message">{message}</p> : null}
      {action}
    </div>
  );
}

export function EmptyState({ title, message, action }: StateProps) {
  return (
    <div className="state-card">
      <p className="state-title">{title}</p>
      {message ? <p className="state-message">{message}</p> : null}
      {action}
    </div>
  );
}
