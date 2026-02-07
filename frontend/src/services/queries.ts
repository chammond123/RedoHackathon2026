/* ──────────────────────────────────────────────────────────
 * TanStack Query hooks
 * ────────────────────────────────────────────────────────── */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/services/api";
import type { AppConfig } from "@/types";

// ── Dashboard ──

export function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: api.fetchMetrics,
    refetchInterval: 10_000,
  });
}

export function useRecentRequests() {
  return useQuery({
    queryKey: ["requests", "recent"],
    queryFn: api.fetchRecentRequests,
    refetchInterval: 10_000,
  });
}

// ── Requests ──

export function useRequests() {
  return useQuery({
    queryKey: ["requests"],
    queryFn: api.fetchRequests,
    refetchInterval: 5_000,
  });
}

export function useRequest(id: string | undefined) {
  return useQuery({
    queryKey: ["requests", id],
    queryFn: () => api.fetchRequest(id!),
    enabled: !!id,
    refetchInterval: 3_000,
  });
}

export function useSubmitBug() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.submitBugReport,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["requests"] });
      qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}

export function useCancelRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.cancelRequest,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}

// ── Logs ──

export function useLogs(requestId?: string) {
  return useQuery({
    queryKey: ["logs", requestId],
    queryFn: () => api.fetchLogs(requestId),
    refetchInterval: 5_000,
  });
}

export function useToolInvocations(requestId: string | undefined) {
  return useQuery({
    queryKey: ["tools", requestId],
    queryFn: () => api.fetchToolInvocations(requestId!),
    enabled: !!requestId,
  });
}

export function useLLMUsage(requestId?: string) {
  return useQuery({
    queryKey: ["llm-usage", requestId],
    queryFn: () => api.fetchLLMUsage(requestId),
  });
}

// ── Configuration ──

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: api.fetchConfig,
  });
}

export function useUpdateConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: AppConfig) => api.updateConfig(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
    },
  });
}

export function useValidateRepo() {
  return useMutation({
    mutationFn: (path: string) => api.validateRepository(path),
  });
}
