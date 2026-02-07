/* ──────────────────────────────────────────────────────────
 * Sidebar – persistent left navigation
 * ────────────────────────────────────────────────────────── */

import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bug,
  GitBranchPlus,
  Settings,
  ScrollText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store";

const NAV_ITEMS = [
  { to: "/",             icon: LayoutDashboard, label: "Dashboard" },
  { to: "/requests",     icon: Bug,             label: "Requests" },
  { to: "/flow",         icon: GitBranchPlus,   label: "Agent Flow" },
  { to: "/config",       icon: Settings,        label: "Configuration" },
  { to: "/logs",         icon: ScrollText,      label: "Logs & Telemetry" },
] as const;

export function Sidebar() {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggle = useAppStore((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-zinc-800 bg-zinc-950 transition-all duration-200",
        collapsed ? "w-16" : "w-56",
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
          BF
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-zinc-100">BugFixer</span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200",
                collapsed && "justify-center px-2",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={toggle}
        className="flex h-10 items-center justify-center border-t border-zinc-800 text-zinc-500 transition-colors hover:text-zinc-300"
      >
        {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>
    </aside>
  );
}
