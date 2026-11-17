import { ArrowRight, PackageSearch, Search, ShoppingBag, Sparkles } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { useCustomer, useRecommendations } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard } from "../components/shared";
import { EmptyState } from "../components/ui/empty-state";
import { Badge } from "../components/ui/badge";
import { cn } from "../lib/cn";

export default function RecommendationsPage() {
  const [input, setInput] = useState("c-001");
  const [customerId, setCustomerId] = useState("c-001");
  const customer = useCustomer(customerId);
  const recs = useRecommendations(customerId);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personalized Recommendations"
        subtitle="Implicit ALS collaborative filtering + category affinity hybrid recommendation inference."
        icon={Sparkles}
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
            className="w-full rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] py-2.5 pl-10 pr-4 text-sm text-[#f4f4f5] placeholder-[#71717a] transition-all focus:border-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Customer ID, e.g. c-001"
          />
        </div>
        <button className="btn-primary" type="submit">
          <ArrowRight size={16} />
          Generate Recommendations
        </button>
      </form>

      <div>
        {recs.isLoading ? (
          <LoadingCard label="Computing personalized hybrid ranking" />
        ) : recs.error ? (
          <ErrorCard error={recs.error} retry={() => recs.refetch()} />
        ) : !recs.data ? (
          <EmptyState
            icon={PackageSearch}
            title="No customer selected"
            description="Enter a customer ID above to retrieve personalized product recommendations."
          />
        ) : (
          <div className="space-y-6">
            {/* Context bar */}
            <div className="card flex flex-wrap items-center gap-4 p-4 text-sm shadow-card">
              <span className="font-semibold text-[#f4f4f5]">{recs.data.customer_id}</span>
              {customer.data?.segment_id != null && (
                <Badge variant="info">Segment {customer.data.segment_id}</Badge>
              )}
              <span className="text-white/[0.1]">|</span>
              <span className="text-[#71717a]">
                Version: <strong className="text-[#f4f4f5]">{recs.data.recommendation_version}</strong>
              </span>
              <Badge
                variant={
                  recs.data.cache_source === "redis"
                    ? "success"
                    : recs.data.cache_source === "database"
                    ? "info"
                    : "warning"
                }
              >
                {recs.data.cache_source} cache
              </Badge>
            </div>

            {recs.data.items.length === 0 ? (
              <EmptyState
                icon={ShoppingBag}
                title="No recommendations found"
                description="The backend returned no recommendation items for this customer. This may indicate a cold-start scenario with no prior category interactions."
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {recs.data.items.map((item, i) => (
                  <motion.div
                    key={`${item.product_id}-${i}`}
                    whileHover={{ y: -3, transition: { duration: 0.15 } }}
                    className={cn(
                      "card p-5 transition-all hover:border-white/[0.14] hover:shadow-glow",
                      i === 0
                        ? "border-[var(--accent)]/40 bg-[var(--accent-soft)] shadow-card"
                        : "bg-[var(--surface-inset)]",
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-semibold text-[#f4f4f5]">{item.product_id}</p>
                        <p className="mt-0.5 text-xs text-[#71717a]">{item.category ?? "Product"}</p>
                      </div>
                      <span
                        className={cn(
                          "flex h-7 w-7 items-center justify-center rounded-[8px] text-xs font-bold",
                          i === 0
                            ? "bg-[var(--accent)] text-[#0c0d12] shadow-glow"
                            : "border border-[var(--border-inset)] bg-[var(--surface-inset-hover)] text-[#a1a1aa]",
                        )}
                      >
                        {i + 1}
                      </span>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <Badge
                        variant={
                          item.strategy === "hybrid"
                            ? "info"
                            : item.strategy.includes("cold")
                            ? "warning"
                            : "default"
                        }
                      >
                        {item.strategy.replaceAll("_", " ")}
                      </Badge>
                      <span className="font-mono text-xs text-[#71717a]">
                        Score: <span className="text-[#2dd4bf] font-semibold">{item.score.toFixed(4)}</span>
                      </span>
                    </div>

                    {item.score_components && Object.keys(item.score_components).length > 0 && (
                      <div className="mt-4 space-y-1.5 border-t border-white/[0.06] pt-3">
                        {Object.entries(item.score_components).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-[#71717a]">{k.replaceAll("_", " ")}</span>
                            <span className="font-mono text-[#a1a1aa]">{v.toFixed(4)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
