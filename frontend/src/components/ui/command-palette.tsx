import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Bot,
  Database,
  LayoutDashboard,
  PieChart,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  User,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";

interface CommandItem {
  id: string;
  title: string;
  group: string;
  path?: string;
  action?: () => void;
  icon: LucideIcon;
  shortcut?: string;
}

export function CommandPalette({
  open,
  onClose,
  onRefresh,
}: {
  open: boolean;
  onClose: () => void;
  onRefresh?: () => void;
}) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const items: CommandItem[] = [
    {
      id: "overview",
      title: "Executive Overview",
      group: "Navigation",
      path: "/",
      icon: LayoutDashboard,
      shortcut: "G O",
    },
    {
      id: "customers",
      title: "Customer Intelligence",
      group: "Navigation",
      path: "/customers",
      icon: Users,
      shortcut: "G C",
    },
    {
      id: "segments",
      title: "Segmentation",
      group: "Navigation",
      path: "/segments",
      icon: PieChart,
      shortcut: "G S",
    },
    {
      id: "recommendations",
      title: "Recommendations Engine",
      group: "Navigation",
      path: "/recommendations",
      icon: Sparkles,
      shortcut: "G R",
    },
    {
      id: "analytics",
      title: "Business Analytics",
      group: "Navigation",
      path: "/analytics",
      icon: BarChart3,
      shortcut: "G A",
    },
    {
      id: "copilot",
      title: "Insights Copilot",
      group: "AI Tools",
      path: "/copilot",
      icon: Bot,
      shortcut: "G I",
    },
    {
      id: "audit",
      title: "Audit History",
      group: "AI Tools",
      path: "/audit",
      icon: ShieldCheck,
    },
    {
      id: "monitoring",
      title: "Model Monitoring & Drift",
      group: "Platform",
      path: "/monitoring",
      icon: Activity,
    },
    {
      id: "data",
      title: "Data & Pipeline Status",
      group: "Platform",
      path: "/data",
      icon: Database,
    },
    {
      id: "profile",
      title: "Settings & Profile",
      group: "Account",
      path: "/profile",
      icon: User,
      shortcut: "G P",
    },
    {
      id: "refresh",
      title: "Refresh Analytics Warehouse Data",
      group: "Actions",
      action: () => {
        if (onRefresh) onRefresh();
      },
      icon: RefreshCw,
      shortcut: "Ctrl + R",
    },
  ];

  const filtered = items.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.group.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [open]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        onClose();
      }
      if (!open) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % (filtered.length || 1));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        const selected = filtered[selectedIndex];
        if (selected.path) {
          navigate(selected.path);
        } else if (selected.action) {
          selected.action();
        }
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, filtered, selectedIndex, navigate, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 sm:pt-28">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-xs"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative w-full max-w-xl overflow-hidden rounded-[20px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-elevated"
          >
            <div className="flex items-center border-b border-[var(--border-subtle)] px-4 py-3">
              <Search size={18} className="text-[var(--text-muted)] shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search commands, pages, or tools..."
                className="ml-3 flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none"
              />
              <button
                onClick={onClose}
                className="rounded-[8px] p-1 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
                aria-label="Close command palette"
              >
                <X size={16} />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto p-2">
              {filtered.length === 0 ? (
                <div className="py-12 text-center text-sm text-[var(--text-muted)]">
                  No matching results found for &ldquo;{query}&rdquo;
                </div>
              ) : (
                <div className="space-y-1">
                  {filtered.map((item, idx) => {
                    const Icon = item.icon;
                    const isSelected = idx === selectedIndex;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          if (item.path) navigate(item.path);
                          else if (item.action) item.action();
                          onClose();
                        }}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className={`flex w-full items-center justify-between rounded-[12px] px-3 py-2.5 text-sm transition-colors ${
                          isSelected
                            ? "bg-[var(--accent-soft)] text-[var(--text-primary)]"
                            : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <Icon
                            size={16}
                            className={isSelected ? "text-[var(--accent)]" : "text-[var(--text-muted)]"}
                          />
                          <span className="font-medium">{item.title}</span>
                          <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                            {item.group}
                          </span>
                        </div>
                        {item.shortcut && (
                          <span className="rounded bg-[var(--bg-subtle)] border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                            {item.shortcut}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-4 py-2.5 text-[11px] text-[var(--text-muted)]">
              <div className="flex items-center gap-3">
                <span>↑↓ Navigate</span>
                <span>↵ Select</span>
                <span>ESC Close</span>
              </div>
              <span className="font-serif">The Qasar Intelligence</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
