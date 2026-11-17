import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ChartCard({
  title,
  subtitle,
  icon: Icon,
  action,
  children,
  className,
}: ChartCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`card p-5 lg:p-6 transition-all hover:border-white/[0.1] ${className ?? ""}`}
    >
      <div className="mb-4 flex items-center justify-between gap-4 border-b border-white/[0.05] pb-3">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-[var(--border-inset)] bg-[var(--surface-inset)] text-[var(--accent)]">
              <Icon size={16} strokeWidth={1.75} />
            </div>
          )}
          <div>
            <h2 className="text-base font-semibold text-[#f4f4f5]">{title}</h2>
            {subtitle && <p className="text-xs text-[#a1a1aa]">{subtitle}</p>}
          </div>
        </div>
        {action && <div>{action}</div>}
      </div>
      <div>{children}</div>
    </motion.section>
  );
}
