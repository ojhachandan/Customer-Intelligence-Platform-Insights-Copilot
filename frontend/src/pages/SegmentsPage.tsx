import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart } from "lucide-react";
import { useSegments } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard, Section } from "../components/shared";
import { DataTable } from "../components/ui/data-table";
import { currency, percent } from "../lib/formatters";
import { Badge } from "../components/ui/badge";
import { Tabs } from "../components/ui/tabs";
import {
  formatCurrencyTick,
  chartTooltipBoxStyle,
  chartTooltipLabelStyle,
  chartTooltipItemStyle,
  barChartCursor,
} from "../components/ui/chart-helpers";
import { CHART_COLORS } from "../lib/chart-colors";
import type { Segment } from "../types/api";

const segmentColumns = [
  {
    key: "segment_id",
    header: "Segment",
    render: (r: Segment) => (
      <Badge variant="info">
        <span className="h-1.5 w-1.5 rounded-full bg-[#2dd4bf] mr-1" />
        Segment {r.segment_id}
      </Badge>
    ),
  },
  {
    key: "customer_count",
    header: "Customers",
    render: (r: Segment) => (
      <span className="font-mono text-xs text-[#a1a1aa]">{r.customer_count.toLocaleString()}</span>
    ),
  },
  {
    key: "total_orders",
    header: "Orders",
    render: (r: Segment) => (
      <span className="font-mono text-xs text-[#a1a1aa]">{r.total_orders.toLocaleString()}</span>
    ),
  },
  {
    key: "total_revenue",
    header: "Revenue",
    align: "right" as const,
    render: (r: Segment) => (
      <span className="font-semibold text-[#f4f4f5]">{currency(r.total_revenue)}</span>
    ),
  },
  {
    key: "average_order_value",
    header: "AOV",
    align: "right" as const,
    render: (r: Segment) => (
      <span className="text-[#f4f4f5] font-mono text-xs">{currency(r.average_order_value)}</span>
    ),
  },
  {
    key: "revenue_contribution",
    header: "Contribution",
    align: "right" as const,
    render: (r: Segment) => (
      <span className="font-mono text-xs font-semibold text-[#2dd4bf]">
        {percent(r.revenue_contribution)}
      </span>
    ),
  },
  {
    key: "products",
    header: "Products Sold",
    align: "right" as const,
    render: (r: Segment) => (
      <span className="font-mono text-xs text-[#a1a1aa]">{r.total_products_sold.toLocaleString()}</span>
    ),
  },
];

export default function SegmentsPage() {
  const segments = useSegments();
  const [chartType, setChartType] = useState("revenue");
  const tabs = [
    { id: "revenue", label: "Revenue" },
    { id: "customers", label: "Customers" },
    { id: "aov", label: "Avg Order Value" },
  ];

  const chartKey =
    chartType === "revenue"
      ? "total_revenue"
      : chartType === "customers"
      ? "customer_count"
      : "average_order_value";

  const chartFormat =
    chartType === "revenue" || chartType === "aov"
      ? (v: number) => currency(v)
      : (v: number) => v.toLocaleString();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Segmentation"
        subtitle="Active K-Means behavioral segments and aggregated performance profiles."
        icon={PieChart}
      />

      {segments.isLoading ? (
        <LoadingCard label="Loading segment metrics" />
      ) : segments.error ? (
        <ErrorCard error={segments.error} retry={() => segments.refetch()} />
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-5">
            <section className="card p-5 xl:col-span-3 shadow-card">
              <Section title="Segment Metric Comparison">
                <Tabs tabs={tabs} active={chartType} onChange={setChartType} />
                <div className="mt-5">
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={segments.data}>
                      <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                      <XAxis
                        dataKey="segment_id"
                        stroke="#71717a"
                        tickFormatter={(v) => `Seg ${v}`}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                      />
                      <YAxis
                        stroke="#71717a"
                        tickFormatter={chartType !== "customers" ? formatCurrencyTick : (v) => String(v)}
                        width={56}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        allowDecimals={false}
                      />
                      <Tooltip
                        cursor={barChartCursor}
                        contentStyle={chartTooltipBoxStyle}
                        labelStyle={chartTooltipLabelStyle}
                        itemStyle={chartTooltipItemStyle}
                        formatter={(v: number) => [
                          chartFormat(v),
                          tabs.find((t) => t.id === chartType)?.label ?? "",
                        ]}
                      />
                      <Bar dataKey={chartKey} radius={[6, 6, 0, 0]}>
                        {segments.data?.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Section>
            </section>

            <section className="card p-5 xl:col-span-2 shadow-card">
              <Section title="Audience Share & Revenue Contribution">
                <div className="space-y-4 mt-2">
                  {segments.data?.map((seg, i) => (
                    <div key={seg.segment_id} className="p-2.5 rounded-[12px] bg-[var(--surface-inset)] border border-[var(--border-inset)]">
                      <div className="mb-2 flex justify-between text-sm">
                        <span className="font-medium text-[#f4f4f5]">Segment {seg.segment_id}</span>
                        <div className="flex items-center gap-3 text-xs">
                          <span className="text-[#71717a]">{seg.customer_count.toLocaleString()} customers</span>
                          <span className="font-semibold text-[#2dd4bf]">
                            {percent(seg.revenue_contribution)}
                          </span>
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--surface-inset-hover)] overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: percent(seg.revenue_contribution) }}
                          transition={{ duration: 0.6, ease: "easeOut" }}
                          className="h-full rounded-full transition-all"
                          style={{
                            backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            </section>
          </div>

          <section className="card p-5 shadow-card">
            <Section title="Detailed Segment Aggregations">
              <DataTable
                columns={segmentColumns}
                data={segments.data ?? []}
                rowKey={(r) => String(r.segment_id)}
              />
            </Section>
          </section>
        </>
      )}
    </div>
  );
}
