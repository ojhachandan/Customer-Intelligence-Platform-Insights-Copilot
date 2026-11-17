import { z } from "zod";

// === Analytics ===
export const overviewSchema = z.object({
  total_revenue: z.number(),
  total_orders: z.number(),
  unique_customers: z.number(),
  average_order_value: z.number(),
  total_products_sold: z.number(),
  repeat_customer_rate: z.number(),
});

export const segmentSchema = z.object({
  segment_id: z.number(),
  customer_count: z.number(),
  total_revenue: z.number(),
  revenue_contribution: z.number(),
  total_orders: z.number(),
  average_order_value: z.number(),
  total_products_sold: z.number(),
});

export const productSchema = z.object({
  product_id: z.string(),
  category: z.string(),
  quantity_sold: z.number(),
  revenue: z.number(),
  order_count: z.number(),
});

export const trendSchema = z.object({
  date: z.string(),
  revenue: z.number(),
  order_count: z.number(),
});

// === Customer ===
export const featureSchema = z.record(z.unknown());

export const customerSchema = z.object({
  customer_id: z.string(),
  snapshot_id: z.string(),
  model_version: z.string(),
  segment_id: z.number().nullable(),
  features: featureSchema,
});

export const segmentDetailSchema = z.object({
  customer_id: z.string(),
  segment_id: z.number(),
  snapshot_id: z.string(),
  model_version: z.string(),
  model_metrics: z.record(z.unknown()),
  feature_version: z.string(),
  features: featureSchema,
  segment_summary: z.record(z.unknown()),
});

// === Recommendations ===
export const recommendationItemSchema = z.object({
  product_id: z.string(),
  category: z.string().optional(),
  score: z.number(),
  strategy: z.string(),
  score_components: z.record(z.number()).optional(),
});

export const recommendationResponseSchema = z.object({
  customer_id: z.string(),
  recommendation_version: z.string(),
  cache_source: z.string(),
  items: z.array(recommendationItemSchema),
});

// === Copilot ===
export const citationSchema = z.object({
  source_type: z.enum(["tool", "report", "vector"]),
  source_id: z.string(),
  query: z.record(z.unknown()),
  description: z.string(),
});

export const copilotSchema = z.object({
  answer: z.string(),
  citations: z.array(citationSchema),
  audit_log_id: z.number(),
});

export const auditSchema = z.object({
  id: z.number(),
  prompt: z.string(),
  response: z.string(),
  tool_calls: z.array(z.unknown()),
  citations: z.array(citationSchema),
  model_metadata: z.record(z.unknown()),
  latency_ms: z.number(),
  created_at: z.string(),
});

// === Drift ===
export const driftSchema = z.object({
  baseline_snapshot_id: z.string(),
  comparison_snapshot_id: z.string(),
  psi: z.record(z.number()),
  created_at: z.string(),
});

// === Health ===
export const healthSchema = z.object({
  status: z.string(),
  feature_version: z.string(),
});

// === Inferred types ===
export type Overview = z.infer<typeof overviewSchema>;
export type Segment = z.infer<typeof segmentSchema>;
export type Product = z.infer<typeof productSchema>;
export type TrendPoint = z.infer<typeof trendSchema>;
export type Customer = z.infer<typeof customerSchema>;
export type SegmentDetail = z.infer<typeof segmentDetailSchema>;
export type RecommendationItem = z.infer<typeof recommendationItemSchema>;
export type RecommendationResponse = z.infer<typeof recommendationResponseSchema>;
export type Citation = z.infer<typeof citationSchema>;
export type CopilotAnswer = z.infer<typeof copilotSchema>;
export type Audit = z.infer<typeof auditSchema>;
export type Drift = z.infer<typeof driftSchema>;
export type Health = z.infer<typeof healthSchema>;
