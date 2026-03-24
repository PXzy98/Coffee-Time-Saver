import { useEffect, useRef } from 'react';
import { RouterProvider } from 'react-router-dom';
import i18n from './i18n';
import { getCurrentUser } from './api/auth';
import { appRouter } from './routes';
import { useAuthStore } from './store/authStore';
import { useUiStore } from './store/uiStore';

function App() {
  const hydrate = useAuthStore((state) => state.hydrate);
  const hydrated = useAuthStore((state) => state.hydrated);
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const clearSession = useAuthStore((state) => state.clearSession);
  const language = useUiStore((state) => state.language);
  const syncLanguage = useUiStore((state) => state.syncLanguage);

  const profileRequestedRef = useRef(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    void i18n.changeLanguage(language);
  }, [language]);

  useEffect(() => {
    if (!hydrated || !accessToken || user || profileRequestedRef.current) {
      return;
    }

    profileRequestedRef.current = true;

    void getCurrentUser()
      .then((profile) => {
        setUser(profile);
        syncLanguage(profile.preferred_lang);
      })
      .catch(() => {
        clearSession();
      });
  }, [accessToken, clearSession, hydrated, setUser, syncLanguage, user]);

  useEffect(() => {
    if (!accessToken) {
      profileRequestedRef.current = false;
    }
  }, [accessToken]);

  return <RouterProvider router={appRouter} />;
}

export default App;
