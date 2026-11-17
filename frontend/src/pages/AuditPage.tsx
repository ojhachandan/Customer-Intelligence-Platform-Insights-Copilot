import { useState } from "react";
import { FileSearch, Clock, Wrench, ShieldCheck } from "lucide-react";
import { useAudit } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard, Section } from "../components/shared";
import { EmptyState } from "../components/ui/empty-state";
import { Badge } from "../components/ui/badge";
import type { Citation } from "../types/api";

function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return <p className="text-xs text-[#71717a]">No citations recorded.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {citations.map((c, i) => (
        <span
          key={`${c.source_id}-${i}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-inset)] bg-[var(--surface-inset)] px-3 py-1 text-xs"
        >
          <Badge variant={c.source_type === "tool" ? "info" : c.source_type === "report" ? "success" : "default"}>
            {c.source_type}
          </Badge>
          <span className="font-mono text-xs text-[#a1a1aa]">{c.source_id}</span>
        </span>
      ))}
    </div>
  );
}

export default function AuditPage() {
  const [input, setInput] = useState("");
  const [auditId, setAuditId] = useState<number>();
  const audit = useAudit(auditId);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Copilot Audit History"
        subtitle="Inspect verifiable execution traces, latency, model parameters, and database tool calls by audit record ID."
        icon={ShieldCheck}
      />

      <form
        className="card flex gap-3 p-4 shadow-card"
        onSubmit={(e) => {
          e.preventDefault();
          const id = Number(input);
          if (Number.isInteger(id) && id > 0) setAuditId(id);
        }}
      >
        <input
          className="flex-1 rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] transition-all focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          inputMode="numeric"
          placeholder="Enter numeric audit record ID (e.g. 1)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn-primary" type="submit">
          <FileSearch size={16} />
          Load Audit Trace
        </button>
      </form>

      <div>
        {auditId == null ? (
          <EmptyState
            icon={FileSearch}
            title="No audit record selected"
            description="Enter an audit record ID from a Copilot response to inspect its execution trace, latency, tool calls, and citations."
          />
        ) : audit.isLoading ? (
          <LoadingCard label="Retrieving audit record from persistence layer" />
        ) : audit.error ? (
          <ErrorCard error={audit.error} retry={() => audit.refetch()} />
        ) : (
          audit.data && (
            <div className="space-y-6">
              {/* Overview */}
              <section className="card p-5 lg:p-6 shadow-card">
                <Section title="Request Trace">
                  <div className="space-y-3 mt-2">
                    <div className="flex items-center gap-3">
                      <Badge variant="info">ID #{audit.data.id}</Badge>
                      <div className="flex items-center gap-1.5 text-xs text-[#71717a]">
                        <Clock size={13} />
                        {new Date(audit.data.created_at).toLocaleString()}
                      </div>
                      <span className="rounded-full bg-[#84CC16]/10 px-2 py-0.5 font-mono text-xs text-[#84CC16] border border-[#84CC16]/20">
                        {audit.data.latency_ms}ms execution
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-[var(--text-primary)] bg-[var(--surface-inset)] p-3.5 rounded-[12px] border border-[var(--border-inset)]">
                      {audit.data.prompt}
                    </p>
                  </div>
                </Section>
              </section>

              {/* Model Info */}
              <section className="card p-5 lg:p-6 shadow-card">
                <Section title="Model Configuration & Metadata">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-2">
                    {Object.entries(audit.data.model_metadata).map(([k, v]) => (
                      <div key={k} className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">{k}</span>
                        <p className="mt-1 font-mono text-xs font-semibold text-[var(--text-primary)]">{String(v)}</p>
                      </div>
                    ))}
                  </div>
                </Section>
              </section>

              {/* Tool Calls */}
              {audit.data.tool_calls.length > 0 && (
                <section className="card p-5 lg:p-6 shadow-card">
                  <Section title="Executed Warehouse Tool Calls">
                    <div className="space-y-3 mt-2">
                      {audit.data.tool_calls.map((call, i) => (
                        <div key={i} className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-4">
                          <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                            <Wrench size={14} className="text-[var(--accent)]" />
                            <span>
                              {typeof call === "object" && call !== null && "tool" in call
                                ? String((call as Record<string, unknown>).tool)
                                : `Call #${i + 1}`}
                            </span>
                          </div>
                          <pre className="mt-2.5 overflow-auto rounded-[10px] border border-[var(--border-inset)] bg-[var(--surface-inset-hover)] p-3 font-mono text-xs text-[#2dd4bf]">
                            {JSON.stringify(call, null, 2)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </Section>
                </section>
              )}

              {/* Response */}
              <section className="card p-5 lg:p-6 shadow-card">
                <Section title="Synthesized Grounded Response">
                  <p className="mt-2 text-sm leading-7 text-[var(--text-primary)] whitespace-pre-wrap bg-[var(--surface-inset)] p-4 rounded-[12px] border border-[var(--border-inset)]">
                    {audit.data.response}
                  </p>
                </Section>
              </section>

              {/* Citations */}
              <section className="card p-5 lg:p-6 shadow-card">
                <Section title="Recorded Evidence Citations">
                  <div className="mt-2">
                    <CitationList citations={audit.data.citations} />
                  </div>
                </Section>
              </section>
            </div>
          )
        )}
      </div>
    </div>
  );
}
