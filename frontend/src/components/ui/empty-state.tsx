import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-[16px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4 text-[var(--accent)] shadow-soft">
        <Icon size={30} strokeWidth={1.75} />
      </div>
      <h3 className="heading-serif mt-4 text-base font-semibold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-[var(--text-secondary)]">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
