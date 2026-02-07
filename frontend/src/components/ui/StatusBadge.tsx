/* ──────────────────────────────────────────────────────────
 * StatusBadge – colored pill for agent status
 * ────────────────────────────────────────────────────────── */

import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/types";

const STATUS_CONFIG: Record<AgentStatus, { label: string; color: string; dot: string }> = {
  pending:       { label: "Pending",       color: "bg-zinc-700 text-zinc-300",      dot: "bg-zinc-400" },
  intake:        { label: "Intake",        color: "bg-blue-500/15 text-blue-400",   dot: "bg-blue-400" },
  hypothesizing: { label: "Hypothesizing", color: "bg-purple-500/15 text-purple-400", dot: "bg-purple-400" },
  reproducing:   { label: "Reproducing",   color: "bg-amber-500/15 text-amber-400", dot: "bg-amber-400" },
  analyzing:     { label: "Analyzing",     color: "bg-cyan-500/15 text-cyan-400",   dot: "bg-cyan-400" },
  root_cause:    { label: "Root Cause",    color: "bg-orange-500/15 text-orange-400", dot: "bg-orange-400" },
  patching:      { label: "Patching",      color: "bg-indigo-500/15 text-indigo-400", dot: "bg-indigo-400" },
  validating:    { label: "Validating",    color: "bg-teal-500/15 text-teal-400",   dot: "bg-teal-400" },
  complete:      { label: "Complete",      color: "bg-green-500/15 text-green-400", dot: "bg-green-400" },
  failed:        { label: "Failed",        color: "bg-red-500/15 text-red-400",     dot: "bg-red-400" },
};

interface Props {
  status: AgentStatus;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.color,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot, {
        "animate-pulse-slow": !["complete", "failed", "pending"].includes(status),
      })} />
      {config.label}
    </span>
  );
}
