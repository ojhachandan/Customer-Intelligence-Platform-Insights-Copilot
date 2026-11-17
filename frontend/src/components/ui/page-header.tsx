import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export function PageHeader({
  title,
  subtitle,
  icon: Icon,
  actions,
}: {
  title: ReactNode;
  subtitle: string;
  icon?: LucideIcon;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--accent)] shadow-soft">
              <Icon size={22} strokeWidth={1.75} />
            </div>
          )}
          <h1 className="heading-serif text-2xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-[28px]">
            {title}
          </h1>
        </div>
        <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{subtitle}</p>
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}