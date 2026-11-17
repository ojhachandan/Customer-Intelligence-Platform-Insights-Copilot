import { motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface Tab {
  id: string;
  label: string;
  count?: number;
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="border-b border-[var(--border-subtle)]">
      <nav className="-mb-px flex gap-2 sm:gap-4" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={cn(
                "relative whitespace-nowrap px-3 pb-3 pt-1 text-sm font-medium transition-colors duration-150",
                isActive
                  ? "text-[var(--accent)] font-semibold"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]",
              )}
            >
              <span className="relative z-10">{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={cn(
                    "relative z-10 ml-2 rounded-full px-2 py-0.5 text-xs font-semibold",
                    isActive
                      ? "bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent-border)]"
                      : "bg-[var(--surface-inset)] text-[var(--text-muted)] border border-[var(--border-inset)]",
                  )}
                >
                  {tab.count}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="activeTabUnderline"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent)] rounded-full shadow-glow"
                />
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
