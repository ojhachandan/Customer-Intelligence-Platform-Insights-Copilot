import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Tooltip } from "../ui/tooltip";

interface SidebarItemProps {
  path: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  badgeVariant?: "new" | "count" | "default";
  collapsed: boolean;
  onClick?: () => void;
}

export function SidebarItem({
  path,
  label,
  icon: Icon,
  badge,
  badgeVariant = "default",
  collapsed,
  onClick,
}: SidebarItemProps) {
  return (
    <Tooltip content={collapsed ? label : ""}>
      <NavLink
        to={path}
        end={path === "/"}
        onClick={onClick}
        className={({ isActive }) =>
          `group relative flex items-center rounded-[12px] text-sm font-medium transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
            collapsed ? "justify-center p-2.5 my-1" : "gap-3 px-3 py-2 my-0.5"
          } ${
            isActive
              ? "text-[var(--accent)] font-semibold"
              : "text-[var(--text-secondary)] [@media(hover:hover)]:hover:bg-[var(--accent-soft)] [@media(hover:hover)]:hover:text-[var(--text-primary)]"
          }`
        }
      >
        {({ isActive }) => (
          <>
            <AnimatePresence>
              {isActive && (
                <motion.div
                  layoutId="activeNavHighlight"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  className="absolute inset-0 rounded-[12px] bg-[var(--accent-soft)] border border-[var(--accent-border)] pointer-events-none"
                />
              )}
            </AnimatePresence>
            <AnimatePresence>
              {isActive && !collapsed && (
                <motion.div
                  layoutId="activeNavIndicator"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-[var(--accent)] pointer-events-none"
                />
              )}
            </AnimatePresence>

            <div className="relative z-10 shrink-0">
              <Icon
                size={18}
                strokeWidth={isActive ? 2 : 1.75}
                className={
                  isActive
                    ? "text-[var(--accent)]"
                    : "text-[var(--text-muted)] transition-colors group-hover:text-[var(--text-primary)]"
                }
              />
            </div>

            <AnimatePresence initial={false}>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.15 }}
                  className="relative z-10 truncate tracking-[-0.01em]"
                >
                  {label}
                </motion.span>
              )}
            </AnimatePresence>

            {!collapsed && badge && (
              <span
                className={`relative z-10 ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
                  badgeVariant === "new"
                    ? "bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent-border)]"
                    : "bg-[var(--bg-subtle)] text-[var(--text-muted)] border border-[var(--border-subtle)]"
                }`}
              >
                {badge}
              </span>
            )}
          </>
        )}
      </NavLink>
    </Tooltip>
  );
}
