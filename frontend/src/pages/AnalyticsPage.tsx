import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";
import { useProducts, useRevenueTrend, useSegments } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard, Section } from "../components/shared";
import { DataTable } from "../components/ui/data-table";
import { Tabs } from "../components/ui/tabs";
import { currency, percent } from "../lib/formatters";
import { Badge } from "../components/ui/badge";
import {
  formatCurrencyTick,
  formatNumberTick,
  chartTooltipBoxStyle,
  chartTooltipLabelStyle,
  chartTooltipItemStyle,
  lineChartCursor,
  barChartCursor,
} from "../components/ui/chart-helpers";
import { CHART_COLORS } from "../lib/chart-colors";
import type { Product, Segment } from "../types/api";

const productColumns = [
  {
    key: "product_id",
    header: "Product",
    render: (r: Product) => (
      <span className="font-medium text-[#f4f4f5] flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-[#2DD4BF]" />
        {r.product_id}
      </span>
    ),
  },
  {
    key: "category",
    header: "Category",
    render: (r: Product) => <Badge variant="muted">{r.category}</Badge>,
  },
  {
    key: "quantity_sold",
    header: "Units Sold",
    render: (r: Product) => (
      <span className="font-mono text-xs text-[#a1a1aa]">{r.quantity_sold.toLocaleString()}</span>
    ),
  },
  {
    key: "order_count",
    header: "Orders",
    render: (r: Product) => (
      <span className="font-mono text-xs text-[#a1a1aa]">{r.order_count.toLocaleString()}</span>
    ),
  },
  {
    key: "revenue",
    header: "Revenue",
    align: "right" as const,
    render: (r: Product) => (
      <span className="font-semibold text-[#f4f4f5]">{currency(r.revenue)}</span>
    ),
  },
];

const segContribCols = [
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
    key: "total_revenue",
    header: "Revenue",
    align: "right" as const,
    render: (r: Segment) => (
      <span className="font-semibold text-[#f4f4f5]">{currency(r.total_revenue)}</span>
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
];

export default function AnalyticsPage() {
  const [tab, setTab] = useState("revenue");
  const trend = useRevenueTrend();
  const products = useProducts(20);
  const segments = useSegments();

  const tabs = [
    { id: "revenue", label: "Revenue Analytics" },
    { id: "products", label: "Product Analytics" },
    { id: "segments", label: "Segment Analytics" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Business Analytics"
        subtitle="In-depth gross sales trends, product velocity, and revenue contribution metrics."
        icon={BarChart3}
      />
      <Tabs tabs={tabs} active={tab} onChange={setTab} />

      <div>
        {tab === "revenue" && (
          <div className="space-y-6">
            <section className="card p-5 lg:p-6 shadow-card">
              <Section title="Daily Revenue Trend">
                {trend.isLoading ? (
                  <LoadingCard />
                ) : trend.error ? (
                  <ErrorCard error={trend.error} retry={() => trend.refetch()} />
                ) : (
                  <ResponsiveContainer width="100%" height={340}>
                    <AreaChart data={trend.data}>
                      <defs>
                        <linearGradient id="analyticsRevGlow" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#7c6cff" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#7c6cff" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                      <XAxis
                        dataKey="date"
                        stroke="#71717a"
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        tickFormatter={(v) =>
                          new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                        }
                      />
                      <YAxis
                        stroke="#71717a"
                        tickFormatter={formatCurrencyTick}
                        width={56}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        allowDecimals={false}
                      />
                      <Tooltip
                        cursor={lineChartCursor}
                        contentStyle={chartTooltipBoxStyle}
                        labelStyle={chartTooltipLabelStyle}
                        itemStyle={chartTooltipItemStyle}
                        formatter={(v: number) => [currency(v), "Revenue"]}
                        labelFormatter={(v) =>
                          new Date(v).toLocaleDateString("en-US", {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })
                        }
                      />
                      <Area
                        type="monotone"
                        dataKey="revenue"
                        stroke="#7c6cff"
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#analyticsRevGlow)"
                        activeDot={{ r: 5, fill: "#7c6cff" }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </Section>
            </section>

            <section className="card p-5 lg:p-6 shadow-card">
              <Section title="Order Volume Trend">
                {trend.isLoading ? (
                  <LoadingCard />
                ) : trend.error ? (
                  <ErrorCard error={trend.error} />
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={trend.data}>
                      <CartesianGrid vertical={false} stroke="rgba(255, 255, 255, 0.05)" />
                      <XAxis
                        dataKey="date"
                        stroke="#71717a"
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        tickFormatter={(v) =>
                          new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                        }
                      />
                      <YAxis
                        stroke="#71717a"
                        tickFormatter={formatNumberTick}
                        width={44}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        allowDecimals={false}
                      />
                      <Tooltip
                        cursor={barChartCursor}
                        contentStyle={chartTooltipBoxStyle}
                        labelStyle={chartTooltipLabelStyle}
                        itemStyle={chartTooltipItemStyle}
                        formatter={(v: number) => [v, "Orders"]}
                      />
                      <Bar dataKey="order_count" fill="#2dd4bf" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Section>
            </section>
          </div>
        )}

        {tab === "products" && (
          <div className="space-y-6">
            <section className="card p-5 lg:p-6 shadow-card">
              <Section title="Top Products by Revenue">
                {products.isLoading ? (
                  <LoadingCard />
                ) : products.error ? (
                  <ErrorCard error={products.error} retry={() => products.refetch()} />
                ) : (
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={products.data?.slice(0, 10)} layout="vertical">
                      <CartesianGrid horizontal={false} stroke="rgba(255, 255, 255, 0.05)" />
                      <XAxis
                        type="number"
                        stroke="#71717a"
                        tickFormatter={formatCurrencyTick}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        allowDecimals={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="product_id"
                        stroke="#71717a"
                        width={80}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                      />
                      <Tooltip
                        cursor={lineChartCursor}
                        contentStyle={chartTooltipBoxStyle}
                        labelStyle={chartTooltipLabelStyle}
                        itemStyle={chartTooltipItemStyle}
                        formatter={(v: number) => [currency(v), "Revenue"]}
                      />
                      <Bar dataKey="revenue" fill="#2DD4BF" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Section>
            </section>

            <section className="card p-5 shadow-card">
              <Section title="All Catalog Products">
                {products.isLoading ? (
                  <LoadingCard />
                ) : products.error ? (
                  <ErrorCard error={products.error} />
                ) : (
                  <DataTable
                    columns={productColumns}
                    data={products.data ?? []}
                    rowKey={(r) => r.product_id}
                  />
                )}
              </Section>
            </section>
          </div>
        )}

        {tab === "segments" && (
          <div className="space-y-6">
            <section className="card p-5 lg:p-6 shadow-card">
              <Section title="Revenue by Segment">
                {segments.isLoading ? (
                  <LoadingCard />
                ) : segments.error ? (
                  <ErrorCard error={segments.error} retry={() => segments.refetch()} />
                ) : (
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
                        tickFormatter={formatCurrencyTick}
                        width={56}
                        tick={{ fontSize: 11, fill: "#71717a" }}
                        allowDecimals={false}
                      />
                      <Tooltip
                        cursor={lineChartCursor}
                        contentStyle={chartTooltipBoxStyle}
                        labelStyle={chartTooltipLabelStyle}
                        itemStyle={chartTooltipItemStyle}
                        formatter={(v: number) => [currency(v), "Revenue"]}
                      />
                      <Bar dataKey="total_revenue" radius={[6, 6, 0, 0]}>
                        {segments.data?.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Section>
            </section>

            <section className="card p-5 shadow-card">
              <Section title="Segment Contribution Overview">
                {segments.isLoading ? (
                  <LoadingCard />
                ) : segments.error ? (
                  <ErrorCard error={segments.error} />
                ) : (
                  <DataTable
                    columns={segContribCols}
                    data={segments.data ?? []}
                    rowKey={(r) => String(r.segment_id)}
                  />
                )}
              </Section>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
