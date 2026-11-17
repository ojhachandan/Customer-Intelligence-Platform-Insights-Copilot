import { cn } from "../../lib/cn";

type Status = "healthy" | "warning" | "critical" | "unknown";

const statusClasses: Record<Status, string> = {
  healthy: "bg-[#84CC16]",
  warning: "bg-[#D4A24C]",
  critical: "bg-[#C4554D]",
  unknown: "bg-[#9C9A92]",
};

const statusLabels: Record<Status, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
  unknown: "Unknown",
};

export function StatusDot({ status, label }: { status: Status; label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs">
      <span className="relative flex h-2 w-2">
        {status === "healthy" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#84CC16] opacity-75" />
        )}
        <span
          className={cn("relative inline-block h-2 w-2 rounded-full", statusClasses[status])}
          aria-hidden="true"
        />
      </span>
      <span className="text-[var(--text-secondary)] font-medium">{label ?? statusLabels[status]}</span>
    </span>
  );
}
