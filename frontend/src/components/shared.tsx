import { AlertCircle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingCard({ label = "Loading live data" }: { label?: string }) {
  return (
    <div className="card p-5 text-sm text-[var(--text-muted)] flex items-center gap-3">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)]" />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorCard({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="card border-[#C4554D]/30 bg-[#C4554D]/10 p-5 text-sm text-[#C4554D]">
      <div className="flex items-center gap-2">
        <AlertCircle size={18} className="shrink-0" />
        <span>{error instanceof Error ? error.message : "This data is currently unavailable."}</span>
      </div>
      {retry && (
        <button className="btn-secondary mt-3 text-xs" onClick={retry}>
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}

export function Unavailable({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="card p-8 text-center shadow-card">
      <h2 className="heading-serif text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm text-[var(--text-secondary)] leading-relaxed">{detail}</p>
    </div>
  );
}

export function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="heading-serif text-base font-semibold text-[var(--text-primary)]">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}