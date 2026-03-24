import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getCurrentUser, login } from '../api/auth';
import { getApiErrorMessage } from '../api/client';
import { Panel } from '../components/common/Panel';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);
  const syncLanguage = useUiStore((state) => state.syncLanguage);
  const pushToast = useUiStore((state) => state.pushToast);

  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin123456');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const tokens = await login({ email, password });
      setSession(
        {
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        },
        null,
      );

      const profile = await getCurrentUser();
      setSession(
        {
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        },
        profile,
      );
      syncLanguage(profile.preferred_lang);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      clearSession();
      const message = getApiErrorMessage(error);
      setErrorMessage(message);
      pushToast({
        tone: 'error',
        title: t('auth.error'),
        message,
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-hero">
        <p className="auth-eyebrow">Coffee Time Saver</p>
        <h1>{t('auth.welcome')}</h1>
        <p className="auth-copy">
          Phase 1 frontend is aligned to the shipped backend: login, daily dashboard, tasks, project access,
          uploads, tools, and constrained admin settings.
        </p>
      </div>

      <Panel title={t('auth.signIn')} className="auth-card">
        <form className="form-grid padded-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>{t('auth.email')}</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>

          <label className="field">
            <span>{t('auth.password')}</span>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
          </label>

          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

          <div className="form-actions">
            <button type="submit" className="primary-button" disabled={isSubmitting}>
              {isSubmitting ? t('common.loading') : t('auth.submit')}
            </button>
          </div>

          <p className="helper-text">
            Seed defaults: `admin@example.com / admin123456` and optional demo PM `pm@example.com / pm123456`.
          </p>
        </form>
      </Panel>
    </div>
  );
}
