import { create } from 'zustand';
import type { UserResponse } from '../types';

const ACCESS_TOKEN_KEY = 'cts.access_token';
const REFRESH_TOKEN_KEY = 'cts.refresh_token';
const USER_KEY = 'cts.user';

interface AuthState {
  hydrated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  hydrate: () => void;
  setSession: (tokens: { accessToken: string; refreshToken: string }, user?: UserResponse | null) => void;
  setUser: (user: UserResponse | null) => void;
  clearSession: () => void;
}

function safeRead<T>(key: string): T | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  hydrated: false,
  accessToken: null,
  refreshToken: null,
  user: null,
  hydrate: () => {
    if (typeof window === 'undefined') {
      set({ hydrated: true });
      return;
    }

    set({
      hydrated: true,
      accessToken: window.localStorage.getItem(ACCESS_TOKEN_KEY),
      refreshToken: window.localStorage.getItem(REFRESH_TOKEN_KEY),
      user: safeRead<UserResponse>(USER_KEY),
    });
  },
  setSession: ({ accessToken, refreshToken }, user) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      if (user) {
        window.localStorage.setItem(USER_KEY, JSON.stringify(user));
      }
    }

    set({
      accessToken,
      refreshToken,
      user: user ?? null,
    });
  },
  setUser: (user) => {
    if (typeof window !== 'undefined') {
      if (user) {
        window.localStorage.setItem(USER_KEY, JSON.stringify(user));
      } else {
        window.localStorage.removeItem(USER_KEY);
      }
    }

    set({ user });
  },
  clearSession: () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
      window.localStorage.removeItem(USER_KEY);
    }

    set({
      accessToken: null,
      refreshToken: null,
      user: null,
    });
  },
}));

export function isAdmin(user: UserResponse | null): boolean {
  return Boolean(user?.roles.includes('admin'));
}
