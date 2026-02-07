/* ──────────────────────────────────────────────────────────
 * ConversationPanel – timeline of messages
 * ────────────────────────────────────────────────────────── */

import { User, Bot, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatTimestamp } from "@/lib/utils";
import type { ConversationMessage } from "@/types";

interface Props {
  messages: ConversationMessage[];
}

const ROLE_CONFIG = {
  user:   { icon: User, color: "border-blue-500/40",   bg: "bg-blue-500/5",   label: "User" },
  agent:  { icon: Bot,  color: "border-purple-500/40", bg: "bg-purple-500/5", label: "Agent" },
  system: { icon: Info, color: "border-zinc-600/40",   bg: "bg-zinc-800/30",  label: "System" },
} as const;

export function ConversationPanel({ messages }: Props) {
  return (
    <div className="flex flex-col">
      <div className="border-b border-zinc-800 px-4 py-3">
        <h3 className="text-sm font-medium text-zinc-300">Conversation</h3>
      </div>

      <div className="flex-1 space-y-3 p-4">
        {messages.length === 0 && (
          <p className="text-center text-xs text-zinc-600 py-8">No messages yet.</p>
        )}
        {messages.map((msg) => {
          const cfg = ROLE_CONFIG[msg.role];
          const Icon = cfg.icon;
          return (
            <div
              key={msg.id}
              className={cn(
                "animate-slide-in rounded-lg border-l-2 p-3",
                cfg.color,
                cfg.bg,
              )}
            >
              <div className="mb-1 flex items-center gap-2 text-xs text-zinc-500">
                <Icon className="h-3 w-3" />
                <span className="font-medium text-zinc-400">{cfg.label}</span>
                {msg.phase && (
                  <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-500">
                    {msg.phase}
                  </span>
                )}
                <span className="ml-auto">{formatTimestamp(msg.timestamp)}</span>
              </div>
              <p className="whitespace-pre-wrap text-sm text-zinc-300">{msg.content}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
