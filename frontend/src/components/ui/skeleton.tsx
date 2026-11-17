import { cn } from "../../lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-[10px] bg-[var(--bg-subtle)] animate-pulse border border-[var(--border-subtle)]",
        className,
      )}
    />
  );
}
