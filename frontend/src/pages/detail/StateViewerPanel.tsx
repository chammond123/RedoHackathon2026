/* ──────────────────────────────────────────────────────────
 * StateViewerPanel – structured view of AgentState
 * ────────────────────────────────────────────────────────── */

import {
  FileCode,
  FlaskConical,
  Terminal,
  Search,
  Wrench,
  GitPullRequest,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentState } from "@/types";

interface Props {
  state: AgentState | null;
}

export function StateViewerPanel({ state }: Props) {
  if (!state) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-zinc-600">
        No agent state available.
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="border-b border-zinc-800 px-4 py-3">
        <h3 className="text-sm font-medium text-zinc-300">Agent State</h3>
      </div>

      <div className="space-y-4 p-4">
        {/* Hypothesis */}
        <StateSection icon={Search} title="Hypothesis" color="text-purple-400">
          <pre className="whitespace-pre-wrap text-xs text-zinc-400">
            {state.hypothesis || "—"}
          </pre>
        </StateSection>

        {/* Suspected Files */}
        <StateSection icon={FileCode} title="Suspected Files" color="text-blue-400">
          {state.suspected_files?.length > 0 ? (
            <ul className="space-y-1">
              {state.suspected_files.map((f) => (
                <li key={f} className="font-mono text-xs text-zinc-400">{f}</li>
              ))}
            </ul>
          ) : (
            <Placeholder />
          )}
        </StateSection>

        {/* Failing Tests */}
        <StateSection icon={FlaskConical} title="Failing Tests" color="text-red-400">
          {state.failing_tests?.length > 0 ? (
            <ul className="space-y-1">
              {state.failing_tests.map((t) => (
                <li key={t} className="font-mono text-xs text-red-400/80">{t}</li>
              ))}
            </ul>
          ) : (
            <Placeholder />
          )}
        </StateSection>

        {/* Root Cause */}
        <StateSection icon={Search} title="Root Cause" color="text-orange-400">
          <pre className="whitespace-pre-wrap text-xs text-zinc-400">
            {state.root_cause || "—"}
          </pre>
        </StateSection>

        {/* Error Output */}
        <StateSection icon={Terminal} title="Error Output" color="text-amber-400">
          {state.error_output ? (
            <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-zinc-950 p-2 font-mono text-xs text-zinc-400">
              {state.error_output}
            </pre>
          ) : (
            <Placeholder />
          )}
        </StateSection>

        {/* Patch */}
        <StateSection icon={Wrench} title="Patch" color="text-green-400">
          {state.patch ? (
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-zinc-950 p-2 font-mono text-xs text-zinc-400">
              {state.patch}
            </pre>
          ) : (
            <Placeholder />
          )}
        </StateSection>

        {/* PR Summary */}
        <StateSection icon={GitPullRequest} title="PR Summary" color="text-cyan-400">
          {state.pr_title ? (
            <div className="space-y-1">
              <p className="text-xs font-medium text-zinc-300">{state.pr_title}</p>
              <pre className="whitespace-pre-wrap text-xs text-zinc-400">{state.pr_summary}</pre>
            </div>
          ) : (
            <Placeholder />
          )}
        </StateSection>
      </div>
    </div>
  );
}

/* ── Helpers ── */

function StateSection({
  icon: Icon,
  title,
  color,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-900/30 p-3">
      <div className="mb-2 flex items-center gap-2">
        <Icon className={cn("h-3.5 w-3.5", color)} />
        <span className="text-xs font-medium text-zinc-400">{title}</span>
      </div>
      {children}
    </div>
  );
}

function Placeholder() {
  return <span className="text-xs text-zinc-600">—</span>;
}
