/* ──────────────────────────────────────────────────────────
 * Card – reusable dark-mode card container
 * ────────────────────────────────────────────────────────── */

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Props {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export function Card({ children, className, onClick, hover }: Props) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/60 p-5",
        hover && "cursor-pointer transition-colors hover:border-zinc-700 hover:bg-zinc-900",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("mb-3 flex items-center justify-between", className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h3 className={cn("text-sm font-medium text-zinc-300", className)}>{children}</h3>;
}

export function CardValue({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-2xl font-semibold text-zinc-100", className)}>{children}</p>;
}
