import type { LucideIcon } from "lucide-react";
import { Info } from "lucide-react";
import { motion } from "framer-motion";
import { AnimatedNumber } from "./animated-number";
import { Tooltip } from "./tooltip";
import { Skeleton } from "./skeleton";

export interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
  infoTooltip?: string;
  iconColor?: string;
  iconBg?: string;
}

export function StatCard({
  icon: Icon,
  label,
  value,
  detail,
  infoTooltip,
  iconColor = "text-[var(--accent)]",
  iconBg = "bg-[var(--accent-soft)] border border-[var(--accent-border)]",
}: StatCardProps) {
  return (
    <motion.div
      whileHover={{ y: -3, transition: { duration: 0.15, ease: "easeOut" } }}
      whileTap={{ scale: 0.98 }}
      className="card p-5 transition-all hover:border-[var(--border-hover)] hover:shadow-soft"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="label">{label}</p>
            {infoTooltip && (
              <Tooltip content={infoTooltip}>
                <button
                  type="button"
                  aria-label={`Information about ${label}`}
                  className="text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
                >
                  <Info size={13} />
                </button>
              </Tooltip>
            )}
          </div>
          <p className="mt-2.5 heading-serif text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            <AnimatedNumber value={value} />
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">{detail}</p>
        </div>
        <div className={`shrink-0 rounded-[12px] p-2.5 ${iconBg} ${iconColor}`}>
          <Icon size={20} strokeWidth={1.75} />
        </div>
      </div>
    </motion.div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <Skeleton className="h-3.5 w-20" />
          <Skeleton className="h-7 w-28" />
          <Skeleton className="h-3 w-36" />
        </div>
        <Skeleton className="h-10 w-10 rounded-[12px]" />
      </div>
    </div>
  );
}
