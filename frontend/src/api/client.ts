import axios, { AxiosHeaders, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';
import type { AccessTokenResponse } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';
const WS_BASE_URL = (import.meta.env.VITE_WS_BASE_URL as string | undefined) ?? API_BASE_URL.replace(/^http/i, 'ws');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

const rawClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

let refreshPromise: Promise<string | null> | null = null;

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    const headers = AxiosHeaders.from(config.headers);
    headers.set('Authorization', `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    if (
      status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes('/api/auth/login') ||
      originalRequest.url?.includes('/api/auth/refresh')
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const token = await refreshAccessToken();
      if (!token) {
        return Promise.reject(error);
      }

      const headers = AxiosHeaders.from(originalRequest.headers);
      headers.set('Authorization', `Bearer ${token}`);
      originalRequest.headers = headers;

      return apiClient(originalRequest);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    }
  },
);

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const authState = useAuthStore.getState();
    if (!authState.refreshToken) {
      authState.clearSession();
      return null;
    }

    try {
      const response = await rawClient.post<AccessTokenResponse>('/api/auth/refresh', {
        refresh_token: authState.refreshToken,
      });

      const accessToken = response.data.access_token;
      authState.setSession(
        {
          accessToken,
          refreshToken: authState.refreshToken,
        },
        authState.user,
      );
      return accessToken;
    } catch {
      authState.clearSession();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login');
      }
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export function buildWebSocketUrl(token: string): string {
  const normalized = WS_BASE_URL.endsWith('/') ? WS_BASE_URL.slice(0, -1) : WS_BASE_URL;
  return `${normalized}/ws?token=${encodeURIComponent(token)}`;
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: string } | undefined;
    if (typeof detail?.detail === 'string') {
      return detail.detail;
    }
    if (typeof error.message === 'string') {
      return error.message;
    }
  }
  return 'Unexpected error';
}

export { API_BASE_URL, apiClient, rawClient };
