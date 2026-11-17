import { useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, LayoutGroup } from "framer-motion";
import {
  ChevronDown,
  HelpCircle,
  PanelLeft,
  Settings,
  UserCircle,
} from "lucide-react";
import { SidebarItem } from "./SidebarItem";
import { navGroups } from "./nav-config";
import { useSidebar } from "../../context/SidebarContext";
import { useAuth } from "../../context/AuthContext";
import { Tooltip } from "../ui/tooltip";

export function Sidebar() {
  const { isCollapsed, isMobileOpen, toggle, expand, setMobileOpen } = useSidebar();
  const { user } = useAuth();
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  const toggleGroup = (group: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  const userInitials = user?.name
    ? user.name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "CI";

  return (
    <>
      {/* Mobile Dimmed Backdrop */}
      <AnimatePresence>
        {isMobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar Panel */}
      <motion.aside
        animate={{ width: isCollapsed ? 76 : 264 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        onClick={() => {
          if (isCollapsed) expand();
        }}
        className={`fixed inset-y-0 left-0 z-40 flex flex-col transition-transform duration-300 lg:static lg:translate-x-0 ${
          isCollapsed ? "cursor-pointer" : ""
        } ${isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="flex h-full flex-col overflow-hidden rounded-[18px] border border-[var(--border-subtle)] bg-[var(--bg-card)] shadow-card">
          {/* Brand Header */}
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-[var(--border-subtle)] px-3 sm:px-4">
            <div
              className={`flex items-center gap-3 overflow-hidden ${
                isCollapsed ? "justify-center w-full" : ""
              }`}
            >
              <Tooltip content={isCollapsed ? "Click to expand sidebar (Ctrl+B)" : "The Qasar CIP"}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isCollapsed) expand();
                  }}
                  className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-[11px] bg-[var(--accent)] font-serif font-bold text-[var(--on-accent)] shadow-soft transition-transform hover:scale-105 active:scale-95"
                  aria-label="Product logo"
                >
                  <span className="text-base tracking-normal">CI</span>
                </button>
              </Tooltip>

              <AnimatePresence initial={false}>
                {!isCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.15 }}
                    className="min-w-0 flex-1"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="rounded-[4px] bg-[var(--accent-soft)] px-1.5 py-0.2 font-mono text-[9px] font-bold tracking-widest text-[var(--accent)] border border-[var(--accent-border)]">
                        THE QASAR
                      </span>
                    </div>
                    <h1 className="truncate heading-serif text-sm font-semibold tracking-tight text-[var(--text-primary)]">
                      Customer Intelligence
                    </h1>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* TOGGLE BUTTON in expanded header */}
            {!isCollapsed && (
              <Tooltip content="Collapse sidebar (Ctrl+B)">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggle();
                  }}
                  className="hidden lg:flex h-8 w-8 items-center justify-center rounded-[9px] text-[var(--text-muted)] transition-all hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeft size={17} strokeWidth={1.75} className="transition-transform duration-200" />
                </button>
              </Tooltip>
            )}
          </div>

          {/* Collapsed top rail toggle pill */}
          {isCollapsed && (
            <div className="flex justify-center pt-2 pb-1 border-b border-[var(--border-subtle)]/50">
              <Tooltip content="Expand sidebar (Ctrl+B)">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggle();
                  }}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--accent)] transition-all"
                  aria-label="Expand sidebar"
                >
                  <PanelLeft size={16} strokeWidth={1.75} className="rotate-180 text-[var(--accent)]" />
                </button>
              </Tooltip>
            </div>
          )}

          {/* Navigation Section */}
          <LayoutGroup id="sidebar">
            <nav className="flex-1 overflow-y-auto px-2.5 py-3">
              {navGroups.map(({ group, items }) => {
                const isGroupCollapsed = collapsedGroups[group];
                return (
                  <div key={group} className="mb-3.5">
                    {!isCollapsed && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleGroup(group);
                        }}
                        className="group flex w-full items-center justify-between px-2.5 py-1 text-left"
                      >
                        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)] group-hover:text-[var(--text-secondary)] transition-colors">
                          {group}
                        </span>
                        <motion.div
                          animate={{ rotate: isGroupCollapsed ? -90 : 0 }}
                          transition={{ duration: 0.15 }}
                        >
                          <ChevronDown size={11} className="text-[var(--text-muted)]" />
                        </motion.div>
                      </button>
                    )}

                    <AnimatePresence initial={false}>
                      {(!isGroupCollapsed || isCollapsed) && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.18, ease: "easeOut" }}
                          className="space-y-0.5 overflow-hidden"
                        >
                          {items.map((item) => (
                            <SidebarItem
                              key={item.path}
                              path={item.path}
                              label={item.label}
                              icon={item.icon}
                              badge={item.badge}
                              badgeVariant={item.badgeVariant}
                              collapsed={isCollapsed}
                              onClick={() => setMobileOpen(false)}
                            />
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </nav>
          </LayoutGroup>

          {/* Footer Area with Always-Visible Expand Button in Collapsed Mode */}
          <div className="shrink-0 border-t border-[var(--border-subtle)] p-2.5 space-y-1">
            {isCollapsed ? (
              <div className="flex flex-col items-center gap-1.5">
                <Tooltip content="Expand sidebar (Ctrl+B)">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle();
                    }}
                    className="flex h-9 w-9 items-center justify-center rounded-[10px] text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--accent)] transition-colors"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeft size={18} strokeWidth={1.75} className="rotate-180" />
                  </button>
                </Tooltip>

                <Tooltip content="Settings & Profile">
                  <Link
                    to="/profile"
                    onClick={() => setMobileOpen(false)}
                    className="flex h-9 w-9 items-center justify-center rounded-[10px] text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
                  >
                    {user?.avatar ? (
                      <img
                        src={user.avatar}
                        alt={user.name}
                        className="h-6 w-6 rounded-full object-cover border border-[var(--border-subtle)]"
                      />
                    ) : (
                      <UserCircle size={18} strokeWidth={1.75} />
                    )}
                  </Link>
                </Tooltip>
              </div>
            ) : (
              <>
                <SidebarItem
                  path="/profile"
                  label="Settings & Profile"
                  icon={Settings}
                  collapsed={false}
                  onClick={() => setMobileOpen(false)}
                />
                <SidebarItem
                  path="#"
                  label="Help & Documentation"
                  icon={HelpCircle}
                  collapsed={false}
                  onClick={() => window.open("https://github.com", "_blank")}
                />

                <Link
                  to="/profile"
                  onClick={() => setMobileOpen(false)}
                  className="mt-2 block rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-2.5 transition-all hover:border-[var(--border-hover)]"
                >
                  <div className="flex items-center gap-2.5">
                    {user?.avatar ? (
                      <img
                        src={user.avatar}
                        alt={user.name}
                        className="h-8 w-8 rounded-[9px] object-cover border border-[var(--border-subtle)]"
                      />
                    ) : (
                      <div className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-[var(--accent-soft)] font-serif font-bold text-xs text-[var(--accent)]">
                        {userInitials}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-semibold text-[var(--text-primary)]">
                        {user?.name || "Enterprise Analyst"}
                      </p>
                      <p className="truncate text-[10px] text-[var(--text-muted)]">
                        {user?.jobTitle || "Analytics Director"}
                      </p>
                    </div>
                  </div>
                </Link>
              </>
            )}
          </div>
        </div>
      </motion.aside>
    </>
  );
}