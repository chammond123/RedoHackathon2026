/* ──────────────────────────────────────────────────────────
 * NodeDetailPanel – sidebar shown when a flow node is clicked
 * ────────────────────────────────────────────────────────── */

import { X } from "lucide-react";
import { StatusBadge } from "@/components/ui";
import type { AgentNodeData } from "@/types";

interface Props {
  data: AgentNodeData;
  onClose: () => void;
}

export function NodeDetailPanel({ data, onClose }: Props) {
  return (
    <div className="w-80 shrink-0 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-zinc-200">{data.label}</h3>
          <StatusBadge status={data.phase} />
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Status info */}
      <div className="space-y-3 text-xs">
        <Section title="Status">
          <p className="text-zinc-400">
            {data.active
              ? "Currently executing"
              : data.completed
                ? "Completed successfully"
                : "Waiting to execute"}
          </p>
        </Section>

        {data.duration_ms != null && (
          <Section title="Duration">
            <p className="text-zinc-400">{(data.duration_ms / 1000).toFixed(2)}s</p>
          </Section>
        )}

        {data.prompt && (
          <Section title="Prompt Used">
            <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-zinc-950 p-2 font-mono text-zinc-400">
              {data.prompt}
            </pre>
          </Section>
        )}

        {data.tools_invoked && data.tools_invoked.length > 0 && (
          <Section title="Tools Invoked">
            <ul className="space-y-1">
              {data.tools_invoked.map((t) => (
                <li key={t} className="rounded bg-zinc-800 px-2 py-1 font-mono text-zinc-400">
                  {t}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {data.state_changes && Object.keys(data.state_changes).length > 0 && (
          <Section title="State Changes">
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-zinc-950 p-2 font-mono text-zinc-400">
              {JSON.stringify(data.state_changes, null, 2)}
            </pre>
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 font-medium text-zinc-500">{title}</p>
      {children}
    </div>
  );
}
