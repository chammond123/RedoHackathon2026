/* ──────────────────────────────────────────────────────────
 * ConversationPanel – timeline of messages + email communication
 * ────────────────────────────────────────────────────────── */

import { useState, useEffect } from "react";
import { User, Bot, Info, Mail, Send, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatTimestamp } from "@/lib/utils";
import { fetchEmailHistory, sendEmail } from "@/services/api";
import type { ConversationMessage, EmailMessage } from "@/types";

interface Props {
  messages: ConversationMessage[];
  email?: string;
  requestId: string;
}

const ROLE_CONFIG = {
  user: { icon: User, color: "border-blue-500/40", bg: "bg-blue-500/5", label: "User" },
  agent: { icon: Bot, color: "border-purple-500/40", bg: "bg-purple-500/5", label: "Agent" },
  system: { icon: Info, color: "border-zinc-600/40", bg: "bg-zinc-800/30", label: "System" },
} as const;

export function ConversationPanel({ messages, email, requestId }: Props) {
  const [emailHistory, setEmailHistory] = useState<EmailMessage[]>([]);
  const [showComposer, setShowComposer] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  // Fetch email history
  useEffect(() => {
    if (requestId) {
      fetchEmailHistory(requestId)
        .then(setEmailHistory)
        .catch(console.error);
    }
  }, [requestId]);

  const handleSendEmail = async () => {
    if (!subject.trim() || !body.trim()) return;

    setSending(true);
    setSendError(null);

    try {
      const result = await sendEmail(requestId, { subject: subject.trim(), body: body.trim() });
      setEmailHistory((prev) => [...prev, result.email]);
      setSubject("");
      setBody("");
      setShowComposer(false);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : "Failed to send email");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-zinc-300">Conversation</h3>
        </div>
        {/* Reporter contact info */}
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs">
            <Mail className="h-3 w-3 text-zinc-500" />
            {email ? (
              <a
                href={`mailto:${email}`}
                className="text-blue-400 hover:text-blue-300 transition-colors"
                title="Contact reporter"
              >
                {email}
              </a>
            ) : (
              <span className="text-zinc-600 italic">No email provided</span>
            )}
          </div>
          {email && (
            <button
              onClick={() => setShowComposer(!showComposer)}
              className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <Send className="h-3 w-3" />
              Send Email
              {showComposer ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
        </div>
      </div>

      {/* Email Composer */}
      {showComposer && email && (
        <div className="border-b border-zinc-800 p-4 bg-zinc-900/60 space-y-3">
          <div>
            <label className="text-xs text-zinc-500 block mb-1">To</label>
            <div className="text-sm text-zinc-300 bg-zinc-800/50 px-3 py-2 rounded">{email}</div>
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject..."
              className="w-full text-sm text-zinc-100 bg-zinc-800 px-3 py-2 rounded border border-zinc-700 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Message</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Type your message..."
              rows={4}
              className="w-full text-sm text-zinc-100 bg-zinc-800 px-3 py-2 rounded border border-zinc-700 focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
          {sendError && (
            <div className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded">{sendError}</div>
          )}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowComposer(false)}
              className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-300"
            >
              Cancel
            </button>
            <button
              onClick={handleSendEmail}
              disabled={sending || !subject.trim() || !body.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-3 w-3" />
              {sending ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      )}

      {/* Email History */}
      {emailHistory.length > 0 && (
        <div className="border-b border-zinc-800 px-4 py-3 bg-zinc-900/30">
          <h4 className="text-xs font-medium text-zinc-400 mb-2 flex items-center gap-1.5">
            <Mail className="h-3 w-3" />
            Email History ({emailHistory.length})
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {emailHistory.map((em) => (
              <div
                key={em.id}
                className="text-xs bg-zinc-800/50 rounded p-2 border-l-2 border-green-500/40"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-zinc-300">{em.subject}</span>
                  <span className="text-zinc-600">{formatTimestamp(em.timestamp)}</span>
                </div>
                <p className="text-zinc-500 line-clamp-2">{em.body}</p>
                {em.previewUrl && (
                  <a
                    href={em.previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-1 text-blue-400 hover:text-blue-300"
                  >
                    <ExternalLink className="h-3 w-3" />
                    View in Ethereal
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 space-y-3 p-4 overflow-y-auto">
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
