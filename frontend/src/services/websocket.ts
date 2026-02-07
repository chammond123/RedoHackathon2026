/* ──────────────────────────────────────────────────────────
 * WebSocket hook – real-time agent updates
 * ────────────────────────────────────────────────────────── */

import { useEffect, useRef, useCallback } from "react";
import { useAppStore } from "@/store";
import type { WSEvent } from "@/types";

const WS_URL = `ws://${window.location.host}/ws`;
const RECONNECT_DELAY = 3000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const { addLog, updateRequestState, setConnectionStatus } = useAppStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
    };

    ws.onmessage = (evt) => {
      try {
        const event = JSON.parse(evt.data) as WSEvent;
        switch (event.type) {
          case "state_update":
            updateRequestState(event.request_id, event.state);
            break;
          case "log":
            addLog(event.request_id, event.entry);
            break;
          case "phase_change":
            updateRequestState(event.request_id, { status: event.phase });
            break;
          case "run_complete":
            updateRequestState(event.request_id, { status: event.status });
            break;
          case "metrics_update":
            useAppStore.getState().setMetrics(event.metrics);
            break;
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnectionStatus("disconnected");
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      setConnectionStatus("error");
      ws.close();
    };
  }, [addLog, updateRequestState, setConnectionStatus]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}
