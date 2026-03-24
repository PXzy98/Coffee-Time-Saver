import { useEffect } from 'react';
import type { WsEvent } from '../types';

export function useWsEvent(handler: (event: WsEvent) => void): void {
  useEffect(() => {
    const listener = (event: Event) => {
      const customEvent = event as CustomEvent<WsEvent>;
      handler(customEvent.detail);
    };

    window.addEventListener('cts:ws', listener as EventListener);
    return () => {
      window.removeEventListener('cts:ws', listener as EventListener);
    };
  }, [handler]);
}
