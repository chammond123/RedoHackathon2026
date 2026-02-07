/* ──────────────────────────────────────────────────────────
 * Logs & Telemetry page – searchable logs, tool invocations, LLM usage
 * ────────────────────────────────────────────────────────── */

import { useState } from "react";
import {
  ScrollText,
  Search,
  Wrench,
  Cpu,
  ExternalLink,
} from "lucide-react";
import { useLogs, useLLMUsage, useToolInvocations } from "@/services/queries";
import {
  Card,
  CardHeader,
  CardTitle,
  CardValue,
  Input,
  LoadingState,
  ErrorState,
  EmptyState,
} from "@/components/ui";
import { cn } from "@/lib/utils";
import { formatTimestamp } from "@/lib/utils";
import type { LogEntry, ToolInvocation } from "@/types";

const LEVEL_COLORS: Record<string, string> = {
  info:  "text-blue-400",
  warn:  "text-amber-400",
  error: "text-red-400",
  debug: "text-zinc-500",
};

export default function LogsPage() {
  const [tab, setTab] = useState<"logs" | "tools" | "llm">("logs");
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Logs & Telemetry</h1>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search logs…"
              className="pl-8 w-64"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-zinc-900 p-1 w-fit">
        {([
          { key: "logs",  icon: ScrollText, label: "Logs" },
          { key: "tools", icon: Wrench,     label: "Tool Invocations" },
          { key: "llm",   icon: Cpu,        label: "LLM Usage" },
        ] as const).map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              tab === key
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === "logs" && <LogsTab searchQuery={searchQuery} />}
      {tab === "tools" && <ToolsTab />}
      {tab === "llm" && <LLMTab />}
    </div>
  );
}

/* ── Logs tab ── */

function LogsTab({ searchQuery }: { searchQuery: string }) {
  const { data, isLoading, isError, error } = useLogs();

  if (isLoading) return <LoadingState message="Loading logs…" />;
  if (isError) return <ErrorState message={error.message} />;
  if (!data || data.length === 0) {
    return <EmptyState icon={<ScrollText className="h-8 w-8" />} title="No logs yet" />;
  }

  const filtered = searchQuery
    ? data.filter((l: LogEntry) => l.message.toLowerCase().includes(searchQuery.toLowerCase()))
    : data;

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-800 bg-zinc-900/60 text-left font-medium uppercase tracking-wider text-zinc-500">
            <th className="px-4 py-2.5 w-20">Level</th>
            <th className="px-4 py-2.5 w-24">Phase</th>
            <th className="px-4 py-2.5">Message</th>
            <th className="px-4 py-2.5 w-32">Time</th>
            <th className="px-4 py-2.5 w-16">Trace</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/50 font-mono">
          {filtered.map((log: LogEntry) => (
            <tr key={log.id} className="hover:bg-zinc-800/20">
              <td className="px-4 py-2">
                <span className={cn("font-medium", LEVEL_COLORS[log.level])}>
                  {log.level.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-2 text-zinc-500">{log.phase}</td>
              <td className="px-4 py-2 text-zinc-300">{log.message}</td>
              <td className="px-4 py-2 text-zinc-600">{formatTimestamp(log.timestamp)}</td>
              <td className="px-4 py-2">
                <button className="text-zinc-600 hover:text-blue-400" title="View in LangSmith">
                  <ExternalLink className="h-3 w-3" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Tools tab ── */

function ToolsTab() {
  const { data, isLoading, isError, error } = useToolInvocations("latest");

  if (isLoading) return <LoadingState message="Loading tool invocations…" />;
  if (isError) return <ErrorState message={error.message} />;
  if (!data || data.length === 0) {
    return <EmptyState icon={<Wrench className="h-8 w-8" />} title="No tool invocations" />;
  }

  return (
    <div className="space-y-2">
      {data.map((tool: ToolInvocation) => (
        <Card key={tool.id} className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Wrench className="h-3.5 w-3.5 text-zinc-500" />
              <span className="font-mono text-sm font-medium text-zinc-200">{tool.tool_name}</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-500">
              <span>{tool.duration_ms}ms</span>
              <span>{formatTimestamp(tool.timestamp)}</span>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="mb-0.5 text-zinc-600">Input</p>
              <pre className="rounded bg-zinc-950 p-2 text-zinc-400">{tool.input_summary}</pre>
            </div>
            <div>
              <p className="mb-0.5 text-zinc-600">Output</p>
              <pre className="rounded bg-zinc-950 p-2 text-zinc-400">{tool.output_summary}</pre>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

/* ── LLM usage tab ── */

function LLMTab() {
  const { data, isLoading, isError, error } = useLLMUsage();

  if (isLoading) return <LoadingState message="Loading LLM metrics…" />;
  if (isError) return <ErrorState message={error.message} />;
  if (!data) return null;

  const cards = [
    { label: "Total Calls",        value: data.total_calls },
    { label: "Prompt Tokens",      value: data.prompt_tokens.toLocaleString() },
    { label: "Completion Tokens",  value: data.completion_tokens.toLocaleString() },
    { label: "Total Tokens",       value: data.total_tokens.toLocaleString() },
    { label: "Est. Cost",          value: `$${data.total_cost_usd.toFixed(4)}` },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
      {cards.map(({ label, value }) => (
        <Card key={label}>
          <CardHeader>
            <CardTitle>{label}</CardTitle>
          </CardHeader>
          <CardValue>{value}</CardValue>
        </Card>
      ))}
    </div>
  );
}
