/* ──────────────────────────────────────────────────────────
 * AgentNode – custom React Flow node for each agent phase
 * ────────────────────────────────────────────────────────── */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { AgentNodeData } from "@/types";
import {
  Search,
  Lightbulb,
  RotateCcw,
  FlaskConical,
  Target,
  Wrench,
  CheckCircle2,
  Trophy,
  XCircle,
} from "lucide-react";
import type { AgentStatus } from "@/types";

const PHASE_ICONS: Record<AgentStatus, React.ComponentType<{ className?: string }>> = {
  pending:       Search,
  intake:        Search,
  hypothesizing: Lightbulb,
  reproducing:   RotateCcw,
  analyzing:     FlaskConical,
  root_cause:    Target,
  patching:      Wrench,
  validating:    CheckCircle2,
  complete:      Trophy,
  failed:        XCircle,
};

export const AgentNode = memo(({ data }: NodeProps) => {
  const d = data as unknown as AgentNodeData;
  const Icon = PHASE_ICONS[d.phase] ?? Search;

  return (
    <div
      className={cn(
        "min-w-[200px] rounded-xl border px-4 py-3 shadow-lg transition-all",
        d.active && "border-blue-500 bg-blue-500/10 ring-2 ring-blue-500/20",
        d.completed && !d.active && "border-green-500/40 bg-green-500/5",
        !d.active && !d.completed && "border-zinc-700 bg-zinc-900",
        d.phase === "failed" && "border-red-500/40 bg-red-500/5",
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-zinc-600 !border-zinc-500" />

      <div className="flex items-center gap-2.5">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            d.active && "bg-blue-500/20 text-blue-400",
            d.completed && !d.active && "bg-green-500/20 text-green-400",
            !d.active && !d.completed && "bg-zinc-800 text-zinc-500",
            d.phase === "failed" && "bg-red-500/20 text-red-400",
          )}
        >
          <Icon className={cn("h-4 w-4", d.active && "animate-pulse-slow")} />
        </div>
        <div>
          <p className="text-sm font-medium text-zinc-200">{d.label}</p>
          <p className="text-[10px] text-zinc-500">
            {d.active ? "In progress" : d.completed ? "Completed" : "Pending"}
          </p>
        </div>
      </div>

      {d.duration_ms != null && (
        <p className="mt-1.5 text-[10px] text-zinc-600">
          {(d.duration_ms / 1000).toFixed(1)}s
        </p>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-zinc-600 !border-zinc-500" />
    </div>
  );
});

AgentNode.displayName = "AgentNode";
