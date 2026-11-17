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
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Bot,
  Calendar,
  CheckCircle2,
  IndianRupee,
  LayoutDashboard,
  PackageSearch,
  RefreshCw,
  Search,
  ShoppingBag,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import { motion, type Variants } from "framer-motion";
import { useBusinessOverview, useProducts, useRevenueTrend, useSegments } from "../hooks/useApi";
import { StatCard, StatCardSkeleton } from "../components/ui/stat-card";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard, LoadingCard } from "../components/shared";
import { currency, percent } from "../lib/formatters";
import { DataTable } from "../components/ui/data-table";
import { Badge } from "../components/ui/badge";
import {
  formatCurrencyTick,
  chartTooltipBoxStyle,
  chartTooltipLabelStyle,
  chartTooltipItemStyle,
  lineChartCursor,
  barChartCursor,
} from "../components/ui/chart-helpers";
import { useAuth } from "../context/AuthContext";
import { CHART_COLORS } from "../lib/chart-colors";
import type { Product, Segment } from "../types/api";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

function IntelligenceSummaryCard({ segments }: { segments: Segment[] }) {
  if (!segments.length) return null;
  const top = [...segments].sort((a, b) => b.revenue_contribution - a.revenue_contribution)[0];
  const highAov = [...segments].sort((a, b) => b.average_order_value - a.average_order_value)[0];

  return (
    <div className="card p-5 lg:p-6 transition-all hover:border-[var(--border-hover)] hover:shadow-soft">
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-[8px] bg-[var(--accent-soft)] text-[var(--accent)]">
            <Sparkles size={16} />
          </div>
          <h2 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Intelligence Summary</h2>
        </div>
        <span className="rounded-full bg-[var(--accent-soft)] px-2.5 py-0.5 font-mono text-[11px] font-medium text-[var(--accent)] border border-[var(--accent-border)]">
          Auto-Synthesized
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="group rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--accent-border)]">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            <TrendingUp size={14} className="text-[var(--accent)]" />
            <span>Revenue Leader</span>
          </div>
          <p className="mt-2 text-sm text-[var(--text-secondary)] leading-relaxed">
            Segment <strong className="text-[var(--text-primary)]">{top.segment_id}</strong> commands{" "}
            <strong className="text-[#84CC16] font-semibold">{percent(top.revenue_contribution)}</strong>{" "}
            of gross revenue across {top.customer_count.toLocaleString()} customers.
          </p>
        </div>

        <div className="group rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#84CC16]/30">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            <IndianRupee size={14} className="text-[#84CC16]" />
            <span>Highest Order Value</span>
          </div>
          <p className="mt-2 text-sm text-[var(--text-secondary)] leading-relaxed">
            Segment <strong className="text-[var(--text-primary)]">{highAov.segment_id}</strong> generates the peak
            average order size at{" "}
            <strong className="text-[var(--text-primary)] font-semibold">{currency(highAov.average_order_value)}</strong>.
          </p>
        </div>

        <div className="group rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#5B7FA6]/30">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            <Users size={14} className="text-[#5B7FA6]" />
            <span>Audience Distribution</span>
          </div>
          <p className="mt-2 text-sm text-[var(--text-secondary)] leading-relaxed">
            <strong className="text-[var(--text-primary)]">{segments.length} active segments</strong> mapped over{" "}
            <strong className="text-[var(--text-primary)]">{segments.reduce((s, seg) => s + seg.customer_count, 0).toLocaleString()}</strong>{" "}
            verified warehouse accounts.
          </p>
        </div>
      </div>
    </div>
  );
}

const productColumns = [
  {
    key: "product_id",
    header: "Product",
    render: (r: Product) => (
      <span className="font-medium text-[var(--text-primary)] flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
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
      <span className="font-mono text-xs text-[var(--text-secondary)]">{r.quantity_sold.toLocaleString()}</span>
    ),
  },
  {
    key: "order_count",
    header: "Orders",
    render: (r: Product) => (
      <span className="font-mono text-xs text-[var(--text-secondary)]">{r.order_count.toLocaleString()}</span>
    ),
  },
  {
    key: "revenue",
    header: "Revenue",
    align: "right" as const,
    render: (r: Product) => (
      <span className="font-semibold text-[var(--text-primary)]">{currency(r.revenue)}</span>
    ),
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const overview = useBusinessOverview();
  const trend = useRevenueTrend();
  const segments = useSegments();
  const products = useProducts(8);

  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const displayName = user?.firstName || "there";

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <span>{timeGreeting}, {displayName}</span>
            <motion.span
              animate={{ rotate: [0, 14, -8, 14, -4, 10, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 3 }}
              className="inline-block origin-[70%_70%]"
            >
              👋
            </motion.span>
          </span>
        }
        subtitle="Live business performance and synthesized customer intelligence from the analytics warehouse."
        icon={LayoutDashboard}
      />

      {/* KPI Stat Cards Grid */}
      {overview.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      ) : overview.error ? (
        <ErrorCard error={overview.error} retry={() => overview.refetch()} />
      ) : (
        <motion.div variants={itemVariants} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard
            icon={IndianRupee}
            label="Total Revenue"
            value={currency(overview.data!.total_revenue)}
            detail="Aggregated loaded orders"
            infoTooltip="Gross revenue accumulated across all customer orders stored in warehouse tables."
            iconColor="text-[#84CC16]"
            iconBg="bg-[#84CC16]/12 border border-[#84CC16]/20"
          />
          <StatCard
            icon={ShoppingBag}
            label="Total Orders"
            value={overview.data!.total_orders.toLocaleString()}
            detail="Distinct completed orders"
            infoTooltip="Count of unique purchase transactions processed."
            iconColor="text-[var(--accent)]"
            iconBg="bg-[var(--accent-soft)] border border-[var(--accent-border)]"
          />
          <StatCard
            icon={Users}
            label="Unique Customers"
            value={overview.data!.unique_customers.toLocaleString()}
            detail="Active customer accounts"
            infoTooltip="Distinct customer accounts with at least one recorded order."
            iconColor="text-[#5B7FA6]"
            iconBg="bg-[#5B7FA6]/12 border border-[#5B7FA6]/20"
          />
          <StatCard
            icon={BarChart3}
            label="Average Order Value"
            value={currency(overview.data!.average_order_value)}
            detail="Revenue ÷ distinct orders"
            infoTooltip="Mean order monetary size calculated across completed purchases."
            iconColor="text-[#D4A24C]"
            iconBg="bg-[#D4A24C]/12 border border-[#D4A24C]/20"
          />
          <StatCard
            icon={RefreshCw}
            label="Repeat Customer Rate"
            value={percent(overview.data!.repeat_customer_rate)}
            detail="Customers with 2+ orders"
            infoTooltip="Percentage of customer base with recurring purchases."
            iconColor="text-[var(--accent)]"
            iconBg="bg-[var(--accent-soft)] border border-[var(--accent-border)]"
          />
        </motion.div>
      )}

      {/* Main Charts + Right Widgets Layout */}
      <div className="grid gap-6 xl:grid-cols-12">
        {/* Left Column: Revenue Trend + Segment Charts (8 cols) */}
        <div className="space-y-6 xl:col-span-8">
          {/* Revenue Over Time Chart */}
          <motion.section
            variants={itemVariants}
            className="card p-5 lg:p-6 transition-all hover:border-[var(--border-hover)] shadow-card"
          >
            <div className="mb-4 flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--accent)]">
                  <TrendingUp size={16} strokeWidth={1.75} />
                </div>
                <div>
                  <h2 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Revenue Over Time</h2>
                  <p className="text-xs text-[var(--text-muted)]">Daily gross sales velocity and transaction trajectory</p>
                </div>
              </div>
              <span className="flex items-center gap-1.5 text-xs text-[#84CC16] font-medium bg-[#84CC16]/10 px-2.5 py-1 rounded-full border border-[#84CC16]/20">
                <span className="h-1.5 w-1.5 rounded-full bg-[#84CC16]" />
                Live Feed
              </span>
            </div>

            {trend.isLoading ? (
              <LoadingCard />
            ) : trend.error ? (
              <ErrorCard error={trend.error} retry={() => trend.refetch()} />
            ) : (
              <ResponsiveContainer width="100%" height={290}>
                <AreaChart data={trend.data}>
                  <defs>
                    <linearGradient id="revenueGlow" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2DD4BF" stopOpacity={0.30} />
                      <stop offset="95%" stopColor="#2DD4BF" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="var(--border-subtle)" />
                  <XAxis
                    dataKey="date"
                    stroke="var(--text-muted)"
                    tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                    tickFormatter={(v) =>
                      new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                    }
                  />
                  <YAxis
                    stroke="var(--text-muted)"
                    tickFormatter={formatCurrencyTick}
                    width={56}
                    tick={{ fontSize: 11, fill: "var(--text-muted)" }}
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
                        year: "numeric",
                      })
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#2DD4BF"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#revenueGlow)"
                    activeDot={{ r: 5, fill: "#2DD4BF", stroke: "#12141C", strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </motion.section>

          {/* Segment Revenue Distribution */}
          <motion.section
            variants={itemVariants}
            className="card p-5 lg:p-6 transition-all hover:border-[var(--border-hover)] shadow-card"
          >
            <div className="mb-4 flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[#5B7FA6]">
                  <BarChart3 size={16} strokeWidth={1.75} />
                </div>
                <div>
                  <h2 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Segment Revenue Distribution</h2>
                  <p className="text-xs text-[var(--text-muted)]">Aggregated monetary value attributed per customer cluster</p>
                </div>
              </div>
            </div>

            {segments.isLoading ? (
              <LoadingCard />
            ) : segments.error ? (
              <ErrorCard error={segments.error} retry={() => segments.refetch()} />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={segments.data}>
                  <CartesianGrid vertical={false} stroke="var(--border-subtle)" />
                  <XAxis
                    dataKey="segment_id"
                    stroke="var(--text-muted)"
                    tickFormatter={(v) => `Seg ${v}`}
                    tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                  />
                  <YAxis
                    stroke="var(--text-muted)"
                    tickFormatter={formatCurrencyTick}
                    width={56}
                    tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={barChartCursor}
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
          </motion.section>
        </div>

        {/* Right Column: Widgets (4 cols) */}
        <div className="space-y-6 xl:col-span-4">
          {/* Insights of the Day Card */}
          <motion.div
            variants={itemVariants}
            className="card p-5 transition-all hover:border-[var(--border-hover)] shadow-card"
          >
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3 mb-3">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[#D4A24C]" />
                <h3 className="heading-serif text-sm font-semibold text-[var(--text-primary)]">Insights of the Day</h3>
              </div>
              <span className="text-[10px] font-mono text-[var(--text-muted)]">DAILY BRIEF</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Cluster 0 accounts for the bulk of repeat orders. Hybrid collaborative filtering shows highest
              affinity in the top category with zero cold-start fallbacks in the last 24h.
            </p>
            <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-between">
              <span className="text-[11px] text-[var(--text-muted)]">Grounded in warehouse data</span>
              <Link
                to="/copilot"
                className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent)] hover:underline transition-colors"
              >
                Ask Copilot <ArrowUpRight size={13} />
              </Link>
            </div>
          </motion.div>

          {/* Quick Actions Card */}
          <motion.div variants={itemVariants} className="card p-5 shadow-card">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Quick Actions
            </h3>
            <div className="space-y-2">
              <Link
                to="/customers"
                className="flex items-center justify-between p-2.5 rounded-[12px] bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-primary)] hover:border-[var(--accent-border)] transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-[8px] bg-[var(--accent-soft)] text-[var(--accent)]">
                    <Search size={14} />
                  </div>
                  <span>Lookup Customer Profile</span>
                </div>
                <ArrowUpRight size={14} className="text-[var(--text-muted)] group-hover:text-[var(--text-primary)] transition-colors" />
              </Link>

              <Link
                to="/recommendations"
                className="flex items-center justify-between p-2.5 rounded-[12px] bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-primary)] hover:border-[#84CC16]/40 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-[8px] bg-[#84CC16]/10 text-[#84CC16]">
                    <PackageSearch size={14} />
                  </div>
                  <span>Test Recommendation Engine</span>
                </div>
                <ArrowUpRight size={14} className="text-[var(--text-muted)] group-hover:text-[var(--text-primary)] transition-colors" />
              </Link>

              <Link
                to="/monitoring"
                className="flex items-center justify-between p-2.5 rounded-[12px] bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-primary)] hover:border-[#D4A24C]/40 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-[8px] bg-[#D4A24C]/10 text-[#D4A24C]">
                    <Activity size={14} />
                  </div>
                  <span>Inspect Population Drift (PSI)</span>
                </div>
                <ArrowUpRight size={14} className="text-[var(--text-muted)] group-hover:text-[var(--text-primary)] transition-colors" />
              </Link>

              <Link
                to="/copilot"
                className="flex items-center justify-between p-2.5 rounded-[12px] bg-[var(--bg-subtle)] border border-[var(--border-subtle)] text-xs font-medium text-[var(--text-primary)] hover:border-[#5B7FA6]/40 transition-all group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-[8px] bg-[#5B7FA6]/10 text-[#5B7FA6]">
                    <Bot size={14} />
                  </div>
                  <span>Launch AI Insights Copilot</span>
                </div>
                <ArrowUpRight size={14} className="text-[var(--text-muted)] group-hover:text-[var(--text-primary)] transition-colors" />
              </Link>
            </div>
          </motion.div>

          {/* Operational Health Checklist */}
          <motion.div variants={itemVariants} className="card p-5 shadow-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Operational Status
              </h3>
              <span className="flex h-2 w-2 rounded-full bg-[#84CC16]" />
            </div>
            <div className="space-y-2 text-xs text-[var(--text-secondary)]">
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]">
                <span className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-[#84CC16]" />
                  <span>K-Means Segmentation</span>
                </span>
                <span className="font-mono text-[var(--text-muted)]">Optimal K</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-[var(--border-subtle)]">
                <span className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-[#84CC16]" />
                  <span>Implicit ALS Matrix</span>
                </span>
                <span className="font-mono text-[var(--text-muted)]">64-dim</span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="flex items-center gap-2">
                  <Calendar size={13} className="text-[var(--accent)]" />
                  <span>Snapshot Freshness</span>
                </span>
                <span className="font-mono text-[var(--text-muted)]">Synced</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Intelligence Summary Row */}
      {segments.data && segments.data.length > 0 && (
        <motion.div variants={itemVariants}>
          <IntelligenceSummaryCard segments={segments.data} />
        </motion.div>
      )}

      {/* Leading Products Table */}
      <motion.section variants={itemVariants} className="card p-5 lg:p-6 shadow-card">
        <div className="mb-4 flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[#D4A24C]">
              <ShoppingBag size={16} strokeWidth={1.75} />
            </div>
            <div>
              <h2 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Leading Catalog Products</h2>
              <p className="text-xs text-[var(--text-muted)]">Top merchandise ordered across customer segments</p>
            </div>
          </div>
          <Link
            to="/analytics"
            className="text-xs font-semibold text-[var(--accent)] hover:underline transition-colors flex items-center gap-1"
          >
            All Products <ArrowUpRight size={13} />
          </Link>
        </div>

        {products.isLoading ? (
          <LoadingCard />
        ) : products.error ? (
          <ErrorCard error={products.error} retry={() => products.refetch()} />
        ) : (
          <DataTable
            columns={productColumns}
            data={products.data ?? []}
            rowKey={(r) => r.product_id}
          />
        )}
      </motion.section>
    </motion.div>
  );
}