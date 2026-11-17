import { Database } from "lucide-react";
import { PageHeader } from "../components/ui/page-header";
import { Unavailable, Section } from "../components/shared";
import { useHealth } from "../hooks/useApi";
import { StatusDot } from "../components/ui/status-dot";

export default function DataPage() {
  const health = useHealth();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data & Pipeline Status"
        subtitle="Operational telemetry and warehouse ingestion status."
        icon={Database}
      />

      <div className="space-y-6">
        {/* API Connectivity */}
        <section className="card p-5 lg:p-6 shadow-card">
          <Section title="Backend Connectivity & Telemetry">
            <div className="grid gap-3 sm:grid-cols-3 mt-2">
              <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                  API Status
                </p>
                <div className="mt-2.5">
                  <StatusDot
                    status={health.data ? "healthy" : health.isLoading ? "unknown" : "critical"}
                    label={health.data ? "Connected & Operational" : health.isLoading ? "Probing endpoint…" : "Unreachable"}
                  />
                </div>
              </div>
              <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                  Feature Engine
                </p>
                <p className="mt-2 font-mono text-sm font-semibold text-[#f4f4f5]">
                  {health.data?.feature_version ? `v${health.data.feature_version}` : "—"}
                </p>
              </div>
              <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                  Health Probe
                </p>
                <p className="mt-2 text-sm font-semibold text-[#84CC16]">
                  {health.data?.status ?? "—"}
                </p>
              </div>
            </div>
          </Section>
        </section>

        {/* Pipeline status — unavailable (preserved per truthfulness contract) */}
        <Unavailable
          title="Pipeline execution status is not exposed"
          detail="The current FastAPI contract has no endpoint for ingestion, scheduler, model training, embedding, or drift job status. This page intentionally does not infer pipeline health from API availability alone. A dedicated pipeline-status endpoint would be required to display individual step outcomes."
        />
      </div>
    </div>
  );
}
