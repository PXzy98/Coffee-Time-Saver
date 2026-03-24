import type { PropsWithChildren } from 'react';
import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import { LoadingState } from '../common/PageState';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { t } = useTranslation();
  const hydrated = useAuthStore((state) => state.hydrated);
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);

  if (!hydrated) {
    return <LoadingState title={t('common.loading')} />;
  }

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  if (!user) {
    return <LoadingState title={t('common.loading')} />;
  }

  return <>{children}</>;
}
