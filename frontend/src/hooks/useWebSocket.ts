import { useEffect, useRef } from 'react';
import i18n from '../i18n';
import { buildWebSocketUrl } from '../api/client';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import type { WsEvent } from '../types';

function describeEvent(event: WsEvent): { title: string; message?: string } {
  switch (event.type) {
    case 'task.updated':
      return { title: i18n.t('notifications.taskUpdated') };
    case 'dashboard.refresh':
      return { title: i18n.t('notifications.dashboardRefresh') };
    case 'file.status_changed':
      return { title: i18n.t('notifications.fileStatusChanged') };
    case 'tool.risk_analyzer.completed':
      return { title: i18n.t('notifications.riskCompleted') };
    default:
      return { title: event.type };
  }
}

export function useWebSocket(): void {
  const accessToken = useAuthStore((state) => state.accessToken);
  const setWebsocketStatus = useUiStore((state) => state.setWebsocketStatus);
  const pushNotification = useUiStore((state) => state.pushNotification);
  const pushToast = useUiStore((state) => state.pushToast);

  const reconnectTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    if (!accessToken) {
      setWebsocketStatus('disconnected');
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectAttempt = 0;

    const connect = () => {
      if (cancelled) {
        return;
      }

      setWebsocketStatus('connecting');
      socket = new WebSocket(buildWebSocketUrl(accessToken));

      socket.onopen = () => {
        reconnectAttempt = 0;
        setWebsocketStatus('connected');
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as WsEvent;
          const notification = describeEvent(event);
          pushNotification({
            type: event.type,
            title: notification.title,
            message: notification.message,
          });

          if (event.type === 'tool.risk_analyzer.completed') {
            pushToast({
              tone: 'success',
              title: notification.title,
            });
          }

          window.dispatchEvent(new CustomEvent('cts:ws', { detail: event }));
        } catch {
          pushToast({
            tone: 'warning',
            title: 'Live update parsing failed',
          });
        }
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }

        setWebsocketStatus('disconnected');
        reconnectAttempt += 1;
        const delay = Math.min(1000 * reconnectAttempt, 8000);
        reconnectTimeoutRef.current = window.setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      socket?.close();
    };
  }, [accessToken, pushNotification, pushToast, setWebsocketStatus]);
}
