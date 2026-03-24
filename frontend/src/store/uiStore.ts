import { create } from 'zustand';
import type { Locale } from '../types';

const LANGUAGE_KEY = 'cts.language';

export interface ToastItem {
  id: string;
  title: string;
  message?: string;
  tone: 'info' | 'success' | 'warning' | 'error';
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message?: string;
  createdAt: string;
  unread: boolean;
}

interface UiState {
  language: Locale;
  sidebarOpen: boolean;
  websocketStatus: 'connecting' | 'connected' | 'disconnected';
  toasts: ToastItem[];
  notifications: NotificationItem[];
  setLanguage: (language: Locale) => void;
  syncLanguage: (language: Locale) => void;
  setSidebarOpen: (open: boolean) => void;
  setWebsocketStatus: (status: UiState['websocketStatus']) => void;
  pushToast: (toast: Omit<ToastItem, 'id'>) => void;
  dismissToast: (id: string) => void;
  pushNotification: (notification: Omit<NotificationItem, 'id' | 'createdAt' | 'unread'>) => void;
  markNotificationsSeen: () => void;
}

function getStoredLanguage(): Locale | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const value = window.localStorage.getItem(LANGUAGE_KEY);
  return value === 'en' || value === 'fr' ? value : null;
}

function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export const useUiStore = create<UiState>((set) => ({
  language: getStoredLanguage() ?? 'en',
  sidebarOpen: false,
  websocketStatus: 'disconnected',
  toasts: [],
  notifications: [],
  setLanguage: (language) => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LANGUAGE_KEY, language);
    }
    set({ language });
  },
  syncLanguage: (language) => {
    if (!getStoredLanguage()) {
      set({ language });
    }
  },
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setWebsocketStatus: (websocketStatus) => set({ websocketStatus }),
  pushToast: (toast) =>
    set((state) => ({
      toasts: [{ id: generateId(), ...toast }, ...state.toasts].slice(0, 4),
    })),
  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
  pushNotification: (notification) =>
    set((state) => ({
      notifications: [
        {
          id: generateId(),
          createdAt: new Date().toISOString(),
          unread: true,
          ...notification,
        },
        ...state.notifications,
      ].slice(0, 12),
    })),
  markNotificationsSeen: () =>
    set((state) => ({
      notifications: state.notifications.map((item) => ({ ...item, unread: false })),
    })),
}));
