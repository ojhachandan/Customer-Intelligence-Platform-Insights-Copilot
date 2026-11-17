import { Activity } from "lucide-react";
import { useDrift } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { LoadingCard, Unavailable, Section } from "../components/shared";
import { Badge } from "../components/ui/badge";
import { cn } from "../lib/cn";

function psiSeverity(value: number): { label: string; variant: "success" | "warning" | "danger" | "muted" } {
  if (value < 0.1) return { label: "Low drift", variant: "success" };
  if (value < 0.25) return { label: "Moderate drift", variant: "warning" };
  return { label: "High drift", variant: "danger" };
}

export default function MonitoringPage() {
  const drift = useDrift();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Monitoring & Drift"
        subtitle="Feature-distribution drift and Population Stability Index (PSI) computed across completed snapshots."
        icon={Activity}
      />

      {drift.isLoading ? (
        <LoadingCard label="Evaluating feature distribution drift" />
      ) : drift.error ? (
        <Unavailable
          title="Drift report unavailable"
          detail="The backend has not published a drift comparison yet. Generate at least two feature snapshots and run the drift job."
        />
      ) : (
        drift.data && (
          <div className="space-y-6">
            <div className="card p-5 lg:p-6 shadow-card">
              <Section title="Drift Comparison Configuration">
                <div className="grid gap-3 sm:grid-cols-3 mt-2">
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Baseline Snapshot
                    </p>
                    <p className="mt-1 font-mono text-xs font-semibold text-[#f4f4f5]">
                      {drift.data.baseline_snapshot_id}
                    </p>
                  </div>
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Comparison Snapshot
                    </p>
                    <p className="mt-1 font-mono text-xs font-semibold text-[#f4f4f5]">
                      {drift.data.comparison_snapshot_id}
                    </p>
                  </div>
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Calculated At
                    </p>
                    <p className="mt-1 text-xs font-medium text-[#a1a1aa]">
                      {new Date(drift.data.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </Section>
            </div>

            <section className="card p-5 lg:p-6 shadow-card">
              <Section title="Feature-Level Population Stability Index (PSI)">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mt-3">
                  {Object.entries(drift.data.psi)
                    .sort(([, a], [, b]) => b - a)
                    .map(([feature, value]) => {
                      const severity = psiSeverity(value);
                      return (
                        <div
                          key={feature}
                          className={cn(
                            "rounded-[12px] border p-4 transition-all hover:-translate-y-0.5",
                            severity.variant === "danger"
                              ? "border-[#f87171]/40 bg-[#f87171]/[0.08]"
                              : severity.variant === "warning"
                              ? "border-[#f5b942]/40 bg-[#f5b942]/[0.08]"
                              : "border-[var(--border-inset)] bg-[var(--surface-inset)] hover:bg-[var(--surface-inset-hover)]",
                          )}
                        >
                          <div className="flex items-start justify-between">
                            <p className="text-sm font-medium text-[#f4f4f5]">{feature.replaceAll("_", " ")}</p>
                            <Badge variant={severity.variant}>{severity.label}</Badge>
                          </div>
                          <p className="mt-2 font-mono text-2xl font-semibold tracking-tight text-[#f4f4f5]">
                            {value.toFixed(4)}
                          </p>
                          <p className="mt-1 text-[11px] text-[#71717a]">Population Stability Index</p>
                        </div>
                      );
                    })}
                </div>
              </Section>
            </section>
          </div>
        )
      )}
    </div>
  );
}
