/* ──────────────────────────────────────────────────────────
 * Button – consistent dark-mode button
 * ────────────────────────────────────────────────────────── */

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const VARIANT_STYLES: Record<Variant, string> = {
  primary:   "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800",
  secondary: "bg-zinc-800 text-zinc-200 hover:bg-zinc-700 border border-zinc-700",
  ghost:     "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800",
  danger:    "bg-red-600/15 text-red-400 hover:bg-red-600/25 border border-red-600/30",
};

const SIZE_STYLES: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs rounded-md gap-1",
  md: "px-4 py-2 text-sm rounded-lg gap-2",
  lg: "px-5 py-2.5 text-base rounded-lg gap-2",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = "primary", size = "md", className, children, ...rest }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50",
        "disabled:pointer-events-none disabled:opacity-50",
        VARIANT_STYLES[variant],
        SIZE_STYLES[size],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  ),
);

Button.displayName = "Button";
