import { useState, useRef, useEffect } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom";
import { useQueryClient, useIsFetching } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  ChevronDown,
  LogOut,
  Menu,
  Moon,
  RefreshCw,
  Search,
  Sparkles,
  Sun,
  User,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useHealth } from "../../hooks/useApi";
import { StatusDot } from "../ui/status-dot";
import { Tooltip } from "../ui/tooltip";
import { navGroups } from "./nav-config";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useSidebar } from "../../context/SidebarContext";

interface TopbarProps {
  onOpenCommand: () => void;
}

export function Topbar({ onOpenCommand }: TopbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isFetching = useIsFetching();
  const health = useHealth();
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { setMobileOpen } = useSidebar();

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(2);

  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  const currentItem = navGroups
    .flatMap(({ items }) => items)
    .find(({ path }) => path === location.pathname);
  const currentGroup = navGroups.find(({ items }) =>
    items.some(({ path }) => path === location.pathname),
  )?.group;

  const label = location.pathname === "/profile"
    ? "Settings & Profile"
    : (currentItem?.label ?? "Workspace");

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotificationsOpen(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleRefresh = () => {
    void queryClient.invalidateQueries();
  };

  const handleLogout = async () => {
    setUserDropdownOpen(false);
    await logout();
    navigate("/auth", { replace: true });
  };

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
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
    <header className="flex h-16 shrink-0 items-center justify-between rounded-[18px] border border-[var(--border-subtle)] bg-[var(--bg-card)]/90 px-4 backdrop-blur-md lg:px-6 shadow-card mb-4 transition-colors">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileOpen(true)}
          className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu size={18} />
        </button>

        <div>
          <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
            <span>Workspace</span>
            {currentGroup && (
              <>
                <span>/</span>
                <span>{currentGroup}</span>
              </>
            )}
          </div>
          <p className="heading-serif text-sm font-semibold tracking-tight text-[var(--text-primary)]">
            {label}
          </p>
        </div>
      </div>

      {/* Right: Quick Actions, Search, Notifications, Theme Toggle, Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Command Search Trigger */}
        <button
          onClick={onOpenCommand}
          className="flex items-center gap-2 rounded-[12px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-all hover:border-[var(--accent-border)] hover:text-[var(--text-primary)]"
          aria-label="Open command search"
        >
          <Search size={14} className="text-[var(--text-muted)]" />
          <span className="hidden sm:inline">Search commands...</span>
          <kbd className="hidden sm:inline-flex items-center rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-1.5 py-0.2 font-mono text-[10px] text-[var(--text-muted)]">
            ⌘K
          </kbd>
        </button>

        {/* Refresh Button with Rotating Animation */}
        <Tooltip content="Refresh warehouse data">
          <button
            onClick={handleRefresh}
            className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] active:scale-95"
            aria-label="Refresh data"
          >
            <motion.div
              animate={{ rotate: isFetching > 0 ? 360 : 0 }}
              transition={{
                repeat: isFetching > 0 ? Infinity : 0,
                duration: 1,
                ease: "linear",
              }}
            >
              <RefreshCw size={15} />
            </motion.div>
          </button>
        </Tooltip>

        {/* Theme Quick Toggle */}
        <Tooltip content={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} theme`}>
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            aria-label="Toggle theme"
          >
            {resolvedTheme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </Tooltip>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <Tooltip content="Notifications">
            <button
              onClick={() => {
                setNotificationsOpen((prev) => !prev);
                setUnreadCount(0);
              }}
              className="relative flex h-9 w-9 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              aria-label="Notifications"
            >
              <Bell size={16} />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--accent)] opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--accent)]" />
                </span>
              )}
            </button>
          </Tooltip>

          <AnimatePresence>
            {notificationsOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 6 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-80 overflow-hidden rounded-[16px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-elevated z-50"
              >
                <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
                  <span className="text-xs font-semibold text-[var(--text-primary)]">Activity Notifications</span>
                  <span className="text-[10px] text-[var(--accent)] font-medium">All caught up</span>
                </div>
                <div className="divide-y divide-[var(--border-subtle)] p-1">
                  <div className="flex items-start gap-3 p-2.5 rounded-[10px] hover:bg-[var(--bg-subtle)] transition-colors">
                    <div className="rounded-[8px] bg-[#84CC16]/15 p-1.5 text-[#84CC16]">
                      <CheckCircle2 size={14} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-[var(--text-primary)]">Segmentation v1.2 Active</p>
                      <p className="text-[11px] text-[var(--text-muted)]">Customer clusters published to Redis cache.</p>
                      <span className="mt-1 block text-[10px] text-[var(--text-muted)]">10m ago</span>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-2.5 rounded-[10px] hover:bg-[var(--bg-subtle)] transition-colors">
                    <div className="rounded-[8px] bg-[var(--accent-soft)] p-1.5 text-[var(--accent)]">
                      <Sparkles size={14} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-[var(--text-primary)]">Copilot Engine Ready</p>
                      <p className="text-[11px] text-[var(--text-muted)]">Warehouse analytics tool pipeline initialized.</p>
                      <span className="mt-1 block text-[10px] text-[var(--text-muted)]">1h ago</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* API Status Pill */}
        <div className="hidden sm:flex items-center rounded-full border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-3 py-1.5">
          <StatusDot
            status={health.data ? "healthy" : health.isLoading ? "unknown" : "critical"}
            label={health.data ? `CIP v${health.data.feature_version}` : health.isLoading ? "Connecting…" : "Offline"}
          />
        </div>

        {/* User Profile Dropdown */}
        <div className="relative" ref={userRef}>
          <button
            onClick={() => setUserDropdownOpen((prev) => !prev)}
            className="flex items-center gap-2 rounded-[12px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-1 pr-2 transition-all hover:bg-[var(--bg-hover)]"
            aria-label="User profile menu"
          >
            {user?.avatar ? (
              <img
                src={user.avatar}
                alt={user.name}
                className="h-7 w-7 rounded-[8px] object-cover border border-[var(--border-subtle)]"
              />
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-[8px] bg-[var(--accent-soft)] font-serif font-bold text-xs text-[var(--accent)]">
                {userInitials}
              </div>
            )}
            <ChevronDown size={12} className="text-[var(--text-muted)]" />
          </button>

          <AnimatePresence>
            {userDropdownOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 6 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-2 w-60 overflow-hidden rounded-[16px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1.5 shadow-elevated z-50"
              >
                <div className="border-b border-[var(--border-subtle)] px-3 py-2.5 mb-1">
                  <p className="text-xs font-semibold text-[var(--text-primary)] truncate">{user?.name || "Enterprise User"}</p>
                  <p className="text-[11px] text-[var(--text-muted)] truncate">{user?.email || "user@company.com"}</p>
                  <span className="inline-block mt-1 text-[10px] text-[var(--accent)] font-medium bg-[var(--accent-soft)] px-2 py-0.5 rounded">
                    {user?.jobTitle || "Analyst"}
                  </span>
                </div>

                <Link
                  to="/profile"
                  onClick={() => setUserDropdownOpen(false)}
                  className="flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <User size={14} />
                  <span>Profile & Settings</span>
                </Link>

                <button
                  type="button"
                  onClick={() => {
                    toggleTheme();
                    setUserDropdownOpen(false);
                  }}
                  className="flex w-full items-center justify-between rounded-[10px] px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <span className="flex items-center gap-2.5">
                    {resolvedTheme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
                    <span>Theme: {theme}</span>
                  </span>
                  <span className="text-[10px] uppercase font-mono text-[var(--text-muted)]">
                    {resolvedTheme}
                  </span>
                </button>

                <div className="border-t border-[var(--border-subtle)] my-1" />

                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2 text-xs text-[#C4554D] hover:bg-[#C4554D]/10 transition-colors"
                >
                  <LogOut size={14} />
                  <span>Sign out</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}