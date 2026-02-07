/* ──────────────────────────────────────────────────────────
 * Header – top bar with repo indicator, status, submit button
 * ────────────────────────────────────────────────────────── */

import { GitBranch, Radio, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store";
import { Button } from "@/components/ui";

export function Header() {
  const connectionStatus = useAppStore((s) => s.connectionStatus);
  const openSubmitModal = useAppStore((s) => s.openSubmitModal);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-6">
      {/* Left: repo info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <GitBranch className="h-4 w-4" />
          <span className="font-medium text-zinc-300">RedoHackathon2026</span>
          <span className="text-zinc-600">/</span>
          <span>main</span>
        </div>

        <div className="h-4 w-px bg-zinc-800" />

        <div className="flex items-center gap-1.5 text-xs text-zinc-500">
          <span className="font-medium">Mode:</span>
          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-zinc-300">Fix & PR</span>
        </div>
      </div>

      {/* Right: status + submit */}
      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        <div className="flex items-center gap-1.5 text-xs">
          <Radio
            className={cn("h-3 w-3", {
              "text-green-400": connectionStatus === "connected",
              "text-red-400":   connectionStatus === "error",
              "text-zinc-500":  connectionStatus === "disconnected",
            })}
          />
          <span className="text-zinc-500 capitalize">{connectionStatus}</span>
        </div>

        {/* Submit bug button */}
        <Button size="sm" onClick={openSubmitModal}>
          <Plus className="h-3.5 w-3.5" />
          Submit Bug
        </Button>
      </div>
    </header>
  );
}
