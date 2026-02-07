/* ──────────────────────────────────────────────────────────
 * Zustand global UI store
 * ────────────────────────────────────────────────────────── */

import { create } from "zustand";
import type { AgentState, DashboardMetrics, LogEntry } from "@/types";

interface AppStoreState {
  // ── Sidebar ──
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // ── Connection ──
  connectionStatus: "connected" | "disconnected" | "error";
  setConnectionStatus: (s: "connected" | "disconnected" | "error") => void;

  // ── Live state updates from WebSocket ──
  liveStates: Record<string, Partial<AgentState>>;
  updateRequestState: (id: string, partial: Partial<AgentState>) => void;

  // ── Live logs from WebSocket ──
  liveLogs: Record<string, LogEntry[]>;
  addLog: (requestId: string, entry: LogEntry) => void;

  // ── Metrics (pushed via WS) ──
  metrics: DashboardMetrics | null;
  setMetrics: (m: DashboardMetrics) => void;

  // ── Submit Bug modal ──
  submitModalOpen: boolean;
  openSubmitModal: () => void;
  closeSubmitModal: () => void;
}

export const useAppStore = create<AppStoreState>((set) => ({
  // Sidebar
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  // Connection
  connectionStatus: "disconnected",
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  // Live states
  liveStates: {},
  updateRequestState: (id, partial) =>
    set((s) => ({
      liveStates: {
        ...s.liveStates,
        [id]: { ...s.liveStates[id], ...partial },
      },
    })),

  // Live logs
  liveLogs: {},
  addLog: (requestId, entry) =>
    set((s) => ({
      liveLogs: {
        ...s.liveLogs,
        [requestId]: [...(s.liveLogs[requestId] ?? []), entry],
      },
    })),

  // Metrics
  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  // Submit modal
  submitModalOpen: false,
  openSubmitModal: () => set({ submitModalOpen: true }),
  closeSubmitModal: () => set({ submitModalOpen: false }),
}));
