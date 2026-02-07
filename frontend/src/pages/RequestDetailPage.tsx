/* ──────────────────────────────────────────────────────────
 * Request Detail page – three-panel view
 * ────────────────────────────────────────────────────────── */

import { useParams } from "react-router-dom";
import { useRequest } from "@/services/queries";
import { LoadingState, ErrorState, StatusBadge } from "@/components/ui";
import { ConversationPanel } from "./detail/ConversationPanel";
import { StateViewerPanel } from "./detail/StateViewerPanel";
import { LogsPanel } from "./detail/LogsPanel";

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: request, isLoading, isError, error } = useRequest(id);

  if (isLoading) return <LoadingState message="Loading request…" />;
  if (isError) return <ErrorState message={error.message} />;
  if (!request) return <ErrorState message="Request not found" />;

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-zinc-100">Request</h1>
          <code className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{request.id}</code>
          <StatusBadge status={request.status} />
        </div>
        <div className="text-xs text-zinc-500">
          Attempts: {request.agent_state?.attempt_count ?? 0} / {request.agent_state?.max_attempts ?? 5}
        </div>
      </div>

      {/* Three-panel layout */}
      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-3">
        <div className="overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/40">
          <ConversationPanel messages={request.messages} />
        </div>
        <div className="overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/40">
          <StateViewerPanel state={request.agent_state} />
        </div>
        <div className="overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/40">
          <LogsPanel logs={request.agent_state?.logs ?? []} status={request.status} />
        </div>
      </div>
    </div>
  );
}
