/* ──────────────────────────────────────────────────────────
 * App – top-level routing and layout
 * ────────────────────────────────────────────────────────── */

import { Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { useWebSocket } from "@/services/websocket";

// Pages (lazy-loadable, but kept simple for now)
import DashboardPage from "@/pages/DashboardPage";
import RequestsPage from "@/pages/RequestsPage";
import RequestDetailPage from "@/pages/RequestDetailPage";
import FlowExplorerPage from "@/pages/flow/FlowExplorerPage";
import ConfigPage from "@/pages/ConfigPage";
import LogsPage from "@/pages/LogsPage";

export default function App() {
  // Establish WebSocket connection globally
  useWebSocket();

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="requests" element={<RequestsPage />} />
        <Route path="requests/:id" element={<RequestDetailPage />} />
        <Route path="flow" element={<FlowExplorerPage />} />
        <Route path="config" element={<ConfigPage />} />
        <Route path="logs" element={<LogsPage />} />
      </Route>
    </Routes>
  );
}
