/* ──────────────────────────────────────────────────────────
 * EmptyState & LoadingState – placeholder components
 * ────────────────────────────────────────────────────────── */

import { Loader2 } from "lucide-react";

export function LoadingState({ message = "Loading…" }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-zinc-500">
      <Loader2 className="h-6 w-6 animate-spin" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
      {icon && <div className="text-zinc-600">{icon}</div>}
      <p className="text-sm font-medium text-zinc-400">{title}</p>
      {description && <p className="max-w-sm text-xs text-zinc-500">{description}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
      <div className="rounded-full bg-red-500/10 p-3">
        <span className="text-2xl">⚠️</span>
      </div>
      <p className="text-sm font-medium text-red-400">Something went wrong</p>
      <p className="max-w-sm text-xs text-zinc-500">{message}</p>
    </div>
  );
}
