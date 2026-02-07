/* ──────────────────────────────────────────────────────────
 * Requests list page
 * ────────────────────────────────────────────────────────── */

import { useNavigate } from "react-router-dom";
import { useRequests } from "@/services/queries";
import { StatusBadge, LoadingState, ErrorState, EmptyState } from "@/components/ui";
import { formatTimestamp, truncate } from "@/lib/utils";
import { Bug } from "lucide-react";
import type { BugRequest } from "@/types";

export default function RequestsPage() {
  const { data, isLoading, isError, error } = useRequests();
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-zinc-100">Bug Requests</h1>

      {isLoading && <LoadingState message="Fetching requests…" />}
      {isError && <ErrorState message={error.message} />}
      {data && data.length === 0 && (
        <EmptyState
          icon={<Bug className="h-8 w-8" />}
          title="No bug requests yet"
          description="Submit a bug report using the button in the top bar."
        />
      )}

      {data && data.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/60 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Bug Report</th>
                <th className="px-4 py-3 hidden md:table-cell">Repository</th>
                <th className="px-4 py-3 hidden lg:table-cell">Mode</th>
                <th className="px-4 py-3">Repro</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {data.map((req: BugRequest) => (
                <tr
                  key={req.id}
                  onClick={() => navigate(`/requests/${req.id}`)}
                  className="cursor-pointer transition-colors hover:bg-zinc-800/30"
                >
                  <td className="px-4 py-3">
                    <StatusBadge status={req.status} />
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-zinc-200">
                    {truncate(req.bug_report, 60)}
                  </td>
                  <td className="hidden px-4 py-3 text-zinc-500 md:table-cell">
                    {req.repo_path}
                  </td>
                  <td className="hidden px-4 py-3 text-zinc-500 lg:table-cell capitalize">
                    {req.agent_mode.replace("_", " ")}
                  </td>
                  <td className="px-4 py-3">
                    {req.agent_state?.repro_confirmed ? (
                      <span className="text-green-400 text-xs">Confirmed</span>
                    ) : (
                      <span className="text-zinc-600 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    {formatTimestamp(req.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
