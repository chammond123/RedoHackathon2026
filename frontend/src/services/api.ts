/* ──────────────────────────────────────────────────────────
 * REST API client
 * ────────────────────────────────────────────────────────── */

const BASE = "/api";
const API_KEY = import.meta.env.VITE_API_KEY || "internal-dev";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...opts?.headers
    },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ──

import type {
  BugRequest,
  DashboardMetrics,
  RecentRequest,
  AppConfig,
  LogEntry,
  ToolInvocation,
  LLMUsage,
} from "@/types";

// ── Dashboard ──

export function fetchMetrics(): Promise<DashboardMetrics> {
  return request<DashboardMetrics>("/metrics");
}

export function fetchRecentRequests(): Promise<RecentRequest[]> {
  return request<RecentRequest[]>("/requests/recent");
}

// ── Requests ──

export function fetchRequests(): Promise<BugRequest[]> {
  return request<BugRequest[]>("/requests");
}

export function fetchRequest(id: string): Promise<BugRequest> {
  return request<BugRequest>(`/requests/${id}`);
}

export function submitBugReport(data: {
  bug_report: string;
  repo_path: string;
  agent_mode: string;
}): Promise<BugRequest> {
  return request<BugRequest>("/requests", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function cancelRequest(id: string): Promise<void> {
  return request<void>(`/requests/${id}/cancel`, { method: "POST" });
}

// ── Logs ──

export function fetchLogs(requestId?: string): Promise<LogEntry[]> {
  const qs = requestId ? `?request_id=${requestId}` : "";
  return request<LogEntry[]>(`/logs${qs}`);
}

export function fetchToolInvocations(requestId: string): Promise<ToolInvocation[]> {
  return request<ToolInvocation[]>(`/requests/${requestId}/tools`);
}

export function fetchLLMUsage(requestId?: string): Promise<LLMUsage> {
  const qs = requestId ? `?request_id=${requestId}` : "";
  return request<LLMUsage>(`/telemetry/llm${qs}`);
}

// ── Configuration ──

export function fetchConfig(): Promise<AppConfig> {
  return request<AppConfig>("/config");
}

export function updateConfig(config: AppConfig): Promise<AppConfig> {
  return request<AppConfig>("/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export function validateRepository(path: string): Promise<{ valid: boolean; message: string }> {
  return request<{ valid: boolean; message: string }>("/config/validate-repo", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

// ── Bug Tickets (synced from BuggyDemo chat) ──

export interface BugTicket {
  id: string;
  title: string;
  description: string;
  module: string;
  severity: string;
  reporter: string;
  steps: string;
  submitted_at: string;
  status: "pending" | "running" | "complete" | "failed";
  run_id: string | null;
}

export function fetchTickets(): Promise<BugTicket[]> {
  return request<BugTicket[]>("/tickets");
}

export function fetchTicket(id: string): Promise<BugTicket> {
  return request<BugTicket>(`/tickets/${id}`);
}

export function startTicketRun(ticketId: string, repoPath?: string): Promise<{ ticket: BugTicket; run: BugRequest }> {
  return request<{ ticket: BugTicket; run: BugRequest }>(`/tickets/${ticketId}/start`, {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath }),
  });
}
