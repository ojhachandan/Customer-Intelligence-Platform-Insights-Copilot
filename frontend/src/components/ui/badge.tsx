import { cn } from "../../lib/cn";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info" | "muted";
  className?: string;
}

const variants = {
  default: "bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent-border)]",
  success: "bg-[#84CC16]/12 text-[#84CC16] border-[#84CC16]/25",
  warning: "bg-[#D4A24C]/12 text-[#D4A24C] border-[#D4A24C]/25",
  danger: "bg-[#C4554D]/12 text-[#C4554D] border-[#C4554D]/25",
  info: "bg-[#5B7FA6]/12 text-[#5B7FA6] border-[#5B7FA6]/25",
  muted: "bg-[var(--bg-subtle)] text-[var(--text-secondary)] border-[var(--border-subtle)]",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
