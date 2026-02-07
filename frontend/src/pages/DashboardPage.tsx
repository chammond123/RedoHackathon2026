/* ──────────────────────────────────────────────────────────
 * Dashboard page – high-level system metrics + recent requests
 * ────────────────────────────────────────────────────────── */

import {
  Activity,
  Bug,
  CheckCircle2,
  XCircle,
  Timer,
  GitPullRequest,
  Ticket,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMetrics, useRecentRequests } from "@/services/queries";
import { Card, CardHeader, CardTitle, CardValue, StatusBadge, LoadingState, ErrorState } from "@/components/ui";
import { formatTimestamp, truncate } from "@/lib/utils";
import type { DashboardMetrics } from "@/types";

export default function DashboardPage() {
  const metrics = useMetrics();
  const recent = useRecentRequests();

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-zinc-100">Dashboard</h1>

      {/* Metric cards */}
      {metrics.isLoading ? (
        <LoadingState message="Loading metrics…" />
      ) : metrics.isError ? (
        <ErrorState message={metrics.error.message} />
      ) : (
        <MetricCards data={metrics.data!} />
      )}

      {/* Recent requests */}
      <div>
        <h2 className="mb-3 text-sm font-medium text-zinc-400">Recent Bug Reports</h2>
        {recent.isLoading ? (
          <LoadingState message="Loading requests…" />
        ) : recent.isError ? (
          <ErrorState message={recent.error.message} />
        ) : (
          <RecentRequestsList items={recent.data!} />
        )}
      </div>
    </div>
  );
}

/* ── Metric cards grid ── */

function MetricCards({ data }: { data: DashboardMetrics }) {
  const cards = [
    { label: "Active Runs",         value: data.active_runs,             icon: Activity,       color: "text-blue-400" },
    { label: "Total Requests",      value: data.total_requests,          icon: Bug,            color: "text-zinc-300" },
    { label: "Successful Fixes",    value: data.success_count,           icon: CheckCircle2,   color: "text-green-400" },
    { label: "Failed",              value: data.failure_count,           icon: XCircle,         color: "text-red-400" },
    { label: "Avg Repro Time",      value: `${data.avg_repro_time_seconds.toFixed(1)}s`, icon: Timer, color: "text-amber-400" },
    { label: "PRs Created",         value: data.prs_created,             icon: GitPullRequest,  color: "text-purple-400" },
    { label: "Tickets Created",     value: data.tickets_created,         icon: Ticket,          color: "text-cyan-400" },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
      {cards.map(({ label, value, icon: Icon, color }) => (
        <Card key={label}>
          <CardHeader>
            <CardTitle>{label}</CardTitle>
            <Icon className={`h-4 w-4 ${color}`} />
          </CardHeader>
          <CardValue>{value}</CardValue>
        </Card>
      ))}
    </div>
  );
}

/* ── Recent requests list ── */

function RecentRequestsList({ items }: { items: { id: string; bug_report: string; status: string; repo_path: string; created_at: string }[] }) {
  const navigate = useNavigate();

  if (items.length === 0) {
    return <p className="text-sm text-zinc-500">No requests yet.</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((r) => (
        <Card
          key={r.id}
          hover
          onClick={() => navigate(`/requests/${r.id}`)}
          className="flex items-center justify-between py-3"
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <StatusBadge status={r.status as never} />
            <span className="truncate text-sm text-zinc-200">{truncate(r.bug_report, 80)}</span>
          </div>
          <div className="flex shrink-0 items-center gap-4 text-xs text-zinc-500">
            <span className="hidden md:inline">{r.repo_path}</span>
            <span>{formatTimestamp(r.created_at)}</span>
          </div>
        </Card>
      ))}
    </div>
  );
}
