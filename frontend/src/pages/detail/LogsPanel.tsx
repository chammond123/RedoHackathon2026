/* ──────────────────────────────────────────────────────────
 * LogsPanel – streaming execution logs grouped by phase
 * ────────────────────────────────────────────────────────── */

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/types";

interface Props {
  logs: string[];
  status: AgentStatus;
}

const PHASE_TAGS = [
  "init", "intake", "hypothesis", "repro", "analysis",
  "root_cause", "patch", "validate", "complete",
] as const;

const PHASE_COLORS: Record<string, string> = {
  init:       "text-zinc-500",
  intake:     "text-blue-400",
  hypothesis: "text-purple-400",
  repro:      "text-amber-400",
  analysis:   "text-cyan-400",
  root_cause: "text-orange-400",
  patch:      "text-green-400",
  validate:   "text-teal-400",
  complete:   "text-emerald-400",
};

export function LogsPanel({ logs, status }: Props) {
  const [filter, setFilter] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new logs
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  const filteredLogs = filter
    ? logs.filter((l) => l.startsWith(`[${filter}]`))
    : logs;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-zinc-300">Execution Logs</h3>
          <span className="text-xs text-zinc-600">{logs.length} entries</span>
        </div>

        {/* Phase filter chips */}
        <div className="mt-2 flex flex-wrap gap-1">
          <FilterChip
            label="All"
            active={filter === null}
            onClick={() => setFilter(null)}
          />
          {PHASE_TAGS.map((tag) => (
            <FilterChip
              key={tag}
              label={tag}
              active={filter === tag}
              onClick={() => setFilter(filter === tag ? null : tag)}
            />
          ))}
        </div>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs">
        {filteredLogs.length === 0 && (
          <p className="py-8 text-center text-zinc-600">No logs match the filter.</p>
        )}
        {filteredLogs.map((entry, i) => (
          <LogLine key={i} entry={entry} />
        ))}

        {/* Live indicator */}
        {!["complete", "failed"].includes(status) && (
          <div className="mt-2 flex items-center gap-2 text-zinc-600">
            <span className="h-1.5 w-1.5 animate-pulse-slow rounded-full bg-blue-400" />
            <span>Agent is running…</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/* ── Log line parser ── */

function LogLine({ entry }: { entry: string }) {
  const match = entry.match(/^\[(\w+)\]\s*(.*)/);
  if (!match) {
    return <div className="py-0.5 text-zinc-400">{entry}</div>;
  }

  const [, tag, message] = match;
  const color = PHASE_COLORS[tag] ?? "text-zinc-500";

  return (
    <div className="py-0.5 leading-relaxed">
      <span className={cn("font-semibold", color)}>[{tag}]</span>{" "}
      <span className="text-zinc-400">{message}</span>
    </div>
  );
}

/* ── Filter chip ── */

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md px-2 py-0.5 text-[10px] font-medium transition-colors",
        active
          ? "bg-blue-600/20 text-blue-400"
          : "bg-zinc-800 text-zinc-500 hover:text-zinc-300",
      )}
    >
      {label}
    </button>
  );
}
