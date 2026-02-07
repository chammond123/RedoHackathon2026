/* ──────────────────────────────────────────────────────────
 * Select – dark-mode styled dropdown
 * ────────────────────────────────────────────────────────── */

import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...rest }, ref) => (
    <select
      ref={ref}
      className={cn(
        "w-full rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-2 text-sm text-zinc-100",
        "focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/40",
        "transition-colors disabled:opacity-50",
        className,
      )}
      {...rest}
    >
      {children}
    </select>
  ),
);
Select.displayName = "Select";
