import {
  ArrowRight,
  Calendar,
  Clock,
  IndianRupee,
  Package,
  Search,
  ShoppingBag,
  Tag,
  User,
  Users,
} from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { useCustomer, useRecommendations, useSegmentDetail } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard, Section } from "../components/shared";
import { currency } from "../lib/formatters";
import { Badge } from "../components/ui/badge";
import { EmptyState } from "../components/ui/empty-state";
import { DataTable } from "../components/ui/data-table";
import { AnimatedNumber } from "../components/ui/animated-number";
import type { RecommendationItem } from "../types/api";

function RecTable({ items }: { items: RecommendationItem[] }) {
  const indexed = items.map((item, i) => ({ ...item, _rank: i }));
  const cols = [
    {
      key: "rank",
      header: "#",
      render: (r: (typeof indexed)[0]) => (
        <span className="font-mono text-xs text-[#71717a]">{r._rank + 1}</span>
      ),
    },
    {
      key: "product_id",
      header: "Product",
      render: (r: (typeof indexed)[0]) => (
        <span className="font-medium text-[#f4f4f5]">{r.product_id}</span>
      ),
    },
    {
      key: "category",
      header: "Category",
      render: (r: (typeof indexed)[0]) => <Badge variant="muted">{r.category ?? "—"}</Badge>,
    },
    {
      key: "strategy",
      header: "Strategy",
      render: (r: (typeof indexed)[0]) => (
        <Badge
          variant={
            r.strategy === "hybrid"
              ? "info"
              : r.strategy.includes("cold")
              ? "warning"
              : "default"
          }
        >
          {r.strategy.replaceAll("_", " ")}
        </Badge>
      ),
    },
    {
      key: "score",
      header: "Score",
      align: "right" as const,
      render: (r: (typeof indexed)[0]) => (
        <span className="font-mono text-xs text-[#2dd4bf]">{r.score.toFixed(4)}</span>
      ),
    },
  ];
  return (
    <DataTable
      columns={cols}
      data={indexed}
      rowKey={(r) => `${r.product_id}-${r._rank}`}
      emptyMessage="No recommendations available for this customer."
    />
  );
}

function FeatureBlock({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number | null | undefined;
  icon: typeof IndianRupee;
}) {
  return (
    <motion.div
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
      className="flex items-center gap-3 rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5 transition-all hover:border-white/[0.12] hover:shadow-card"
    >
      <div className="rounded-[10px] border border-[var(--border-inset)] bg-[var(--accent-soft)] p-2 text-[var(--accent)]">
        <Icon size={16} strokeWidth={1.75} />
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">{label}</p>
        <p className="mt-0.5 text-sm font-semibold text-[#f4f4f5]">
          {value != null ? <AnimatedNumber value={value} /> : "—"}
        </p>
      </div>
    </motion.div>
  );
}

export default function CustomerPage() {
  const [input, setInput] = useState("c-001");
  const [customerId, setCustomerId] = useState("c-001");
  const customer = useCustomer(customerId);
  const segDetail = useSegmentDetail(customerId);
  const recommendations = useRecommendations(customerId);

  const f = customer.data?.features ?? {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Intelligence"
        subtitle="Look up any customer ID to inspect behavioral features, RFM metrics, segment cluster, and personalized recommendations."
        icon={Users}
      />

      <form
        className="card flex flex-col gap-3 p-4 sm:flex-row shadow-card"
        onSubmit={(e) => {
          e.preventDefault();
          setCustomerId(input.trim());
        }}
      >
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#71717a]" />
          <input
            id="customer-id"
            className="w-full rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] py-2.5 pl-10 pr-4 text-sm text-[#f4f4f5] placeholder-[#71717a] transition-all focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter customer ID, e.g. c-001"
          />
        </div>
        <button className="btn-primary" type="submit">
          <ArrowRight size={16} />
          Load Profile
        </button>
      </form>

      {customer.isLoading ? (
        <div className="mt-6">
          <LoadingCard label="Retrieving customer profile from warehouse" />
        </div>
      ) : customer.error ? (
        <div className="mt-6">
          <ErrorCard error={customer.error} retry={() => customer.refetch()} />
        </div>
      ) : !customer.data ? (
        <div className="mt-6">
          <EmptyState
            icon={User}
            title="No customer loaded"
            description="Enter a customer ID above to view their behavioral profile and recommendations."
          />
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="space-y-6"
        >
          {/* Profile Overview */}
          <div className="grid gap-6 xl:grid-cols-5">
            <section className="card p-5 xl:col-span-2 shadow-card">
              <Section title="Customer Identity">
                <div className="space-y-4">
                  <div className="flex items-center gap-3.5">
                    <div className="flex h-12 w-12 items-center justify-center rounded-[12px] border border-[var(--accent)]/30 bg-[var(--accent-soft)] text-lg font-bold text-[var(--accent)] shadow-glow">
                      {customer.data.customer_id.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-[#f4f4f5]">{customer.data.customer_id}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <Badge variant={customer.data.segment_id != null ? "info" : "muted"}>
                          {customer.data.segment_id != null
                            ? `Segment ${customer.data.segment_id}`
                            : "Unassigned"}
                        </Badge>
                        <span className="font-mono text-xs text-[#71717a]">
                          v{customer.data.model_version}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Active Snapshot
                    </p>
                    <p className="mt-1 font-mono text-xs font-medium text-[#a1a1aa]">
                      {customer.data.snapshot_id}
                    </p>
                  </div>
                </div>
              </Section>
            </section>

            <section className="card p-5 xl:col-span-3 shadow-card">
              <Section title="RFM & Behavioral Features">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <FeatureBlock
                    label="Recency (days)"
                    value={typeof f.recency_days === "number" ? f.recency_days.toFixed(0) : null}
                    icon={Clock}
                  />
                  <FeatureBlock
                    label="Frequency"
                    value={typeof f.frequency === "number" ? f.frequency.toFixed(0) : null}
                    icon={ShoppingBag}
                  />
                  <FeatureBlock
                    label="Monetary"
                    value={typeof f.monetary === "number" ? currency(f.monetary) : null}
                    icon={IndianRupee}
                  />
                  <FeatureBlock
                    label="Avg Order Value"
                    value={typeof f.avg_order_value === "number" ? currency(f.avg_order_value) : null}
                    icon={Tag}
                  />
                  <FeatureBlock
                    label="Unique Products"
                    value={typeof f.unique_products === "number" ? f.unique_products.toFixed(0) : null}
                    icon={Package}
                  />
                  <FeatureBlock
                    label="Tenure (days)"
                    value={
                      typeof f.purchase_tenure_days === "number"
                        ? f.purchase_tenure_days.toFixed(0)
                        : null
                    }
                    icon={Calendar}
                  />
                </div>
              </Section>
            </section>
          </div>

          {/* Category Preferences */}
          {Array.isArray(f.preferred_categories) && f.preferred_categories.length > 0 && (
            <section className="card p-5 shadow-card">
              <Section title="Category Affinity & Preferences">
                <div className="flex flex-wrap gap-2 mb-4">
                  {(f.preferred_categories as string[]).map((cat) => (
                    <Badge key={cat} variant="default">
                      {cat}
                    </Badge>
                  ))}
                </div>
                {typeof f.category_affinity === "object" && f.category_affinity !== null && (
                  <div className="space-y-3">
                    {Object.entries(f.category_affinity as Record<string, number>)
                      .sort(([, a], [, b]) => b - a)
                      .map(([cat, share]) => (
                        <div key={cat}>
                          <div className="mb-1 flex justify-between text-xs">
                            <span className="text-[#a1a1aa] font-medium">{cat}</span>
                            <span className="font-semibold text-[#f4f4f5]">
                              {(share * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-[var(--surface-inset-hover)] overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(share * 100).toFixed(1)}%` }}
                              transition={{ duration: 0.6, ease: "easeOut" }}
                              className="h-full rounded-full bg-gradient-to-r from-[#2DD4BF] to-[#5EEAD4]"
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </Section>
            </section>
          )}

          {/* Segment Detail */}
          {segDetail.data && (
            <section className="card p-5 shadow-card">
              <Section title="Cluster Assignment & Model Metrics">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Segment ID
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[#f4f4f5]">
                      Cluster {segDetail.data.segment_id}
                    </p>
                  </div>
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Model Version
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[#f4f4f5]">
                      {segDetail.data.model_version}
                    </p>
                  </div>
                  <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                      Feature Pipeline
                    </p>
                    <p className="mt-1 text-sm font-semibold text-[#f4f4f5]">
                      {segDetail.data.feature_version}
                    </p>
                  </div>
                </div>
                {typeof segDetail.data.model_metrics === "object" &&
                  segDetail.data.model_metrics !== null &&
                  Object.keys(segDetail.data.model_metrics).length > 0 && (
                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      {Object.entries(segDetail.data.model_metrics).map(([k, v]) => (
                        <div
                          key={k}
                          className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3"
                        >
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                            {k.replaceAll("_", " ")}
                          </p>
                          <p className="mt-1 font-mono text-sm font-semibold text-[#2dd4bf]">
                            {typeof v === "number" ? v.toFixed(4) : String(v)}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
              </Section>
            </section>
          )}

          {/* Recommendations Table */}
          <section className="card p-5 shadow-card">
            <Section title="Personalized Recommendations">
              {recommendations.isLoading ? (
                <LoadingCard label="Computing hybrid ALS + content recommendations" />
              ) : recommendations.error ? (
                <ErrorCard
                  error={recommendations.error}
                  retry={() => recommendations.refetch()}
                />
              ) : !recommendations.data ? (
                <EmptyState
                  icon={Package}
                  title="No recommendations"
                  description="Recommendation data is not available for this customer account."
                />
              ) : (
                <>
                  <div className="mb-4 flex flex-wrap items-center gap-4 text-xs text-[#71717a]">
                    <span>
                      Version:{" "}
                      <strong className="text-[#f4f4f5]">
                        {recommendations.data.recommendation_version}
                      </strong>
                    </span>
                    <span className="flex items-center gap-1.5">
                      Cache Source:{" "}
                      <Badge
                        variant={
                          recommendations.data.cache_source === "redis"
                            ? "success"
                            : recommendations.data.cache_source === "database"
                            ? "info"
                            : "warning"
                        }
                      >
                        {recommendations.data.cache_source}
                      </Badge>
                    </span>
                  </div>
                  <RecTable items={recommendations.data.items} />
                </>
              )}
            </Section>
          </section>
        </motion.div>
      )}
    </div>
  );
}
