import { z } from "zod";
import {
  auditSchema,
  copilotSchema,
  customerSchema,
  driftSchema,
  healthSchema,
  overviewSchema,
  productSchema,
  recommendationResponseSchema,
  segmentDetailSchema,
  segmentSchema,
  trendSchema,
  type Overview,
  type Segment,
  type Product,
  type TrendPoint,
  type Customer,
  type SegmentDetail,
} from "../types/api";
import { usdToInr } from "../config/currency";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15_000);
  try {
    const headers = new Headers(init?.headers);
    if (init?.body) headers.set("Content-Type", "application/json");
    const response = await fetch(`${baseUrl}${path}`, { ...init, signal: controller.signal, headers });
    if (!response.ok)
      throw new ApiError((await response.text()) || `Request failed (${response.status})`, response.status);
    return schema.parse(await response.json());
  } catch (error) {
    if (error instanceof ApiError || error instanceof z.ZodError) throw error;
    throw new ApiError(
      error instanceof DOMException && error.name === "AbortError"
        ? "The backend request timed out."
        : "The backend is unavailable.",
    );
  } finally {
    window.clearTimeout(timeout);
  }
}

function mapOverviewToINR(overview: Overview): Overview {
  const convertedTotalRevenue = usdToInr(overview.total_revenue);
  const derivedAov =
    overview.total_orders > 0
      ? convertedTotalRevenue / overview.total_orders
      : usdToInr(overview.average_order_value);

  return {
    ...overview,
    total_revenue: convertedTotalRevenue,
    average_order_value: derivedAov,
  };
}

function mapSegmentToINR(seg: Segment): Segment {
  const convertedRevenue = usdToInr(seg.total_revenue);
  const derivedAov =
    seg.total_orders > 0
      ? convertedRevenue / seg.total_orders
      : usdToInr(seg.average_order_value);

  return {
    ...seg,
    total_revenue: convertedRevenue,
    average_order_value: derivedAov,
  };
}

function mapProductToINR(prod: Product): Product {
  return {
    ...prod,
    revenue: usdToInr(prod.revenue),
  };
}

function mapTrendPointToINR(point: TrendPoint): TrendPoint {
  return {
    ...point,
    revenue: usdToInr(point.revenue),
  };
}

function mapCustomerFeaturesToINR(features: Record<string, unknown>): Record<string, unknown> {
  const updated: Record<string, unknown> = { ...features };
  if (typeof updated.monetary === "number") {
    updated.monetary = usdToInr(updated.monetary);
  }
  if (typeof updated.avg_order_value === "number") {
    updated.avg_order_value = usdToInr(updated.avg_order_value);
  }
  return updated;
}

function mapCustomerToINR(customer: Customer): Customer {
  return {
    ...customer,
    features: customer.features ? mapCustomerFeaturesToINR(customer.features) : {},
  };
}

function mapSegmentDetailToINR(detail: SegmentDetail): SegmentDetail {
  const mappedFeatures = detail.features ? mapCustomerFeaturesToINR(detail.features) : {};
  const mappedSummary: Record<string, unknown> = { ...detail.segment_summary };
  if (typeof mappedSummary.total_revenue === "number") {
    mappedSummary.total_revenue = usdToInr(mappedSummary.total_revenue);
  }
  if (typeof mappedSummary.average_order_value === "number") {
    mappedSummary.average_order_value = usdToInr(mappedSummary.average_order_value);
  }

  return {
    ...detail,
    features: mappedFeatures,
    segment_summary: mappedSummary,
  };
}

export const api = {
  health: () => request("/health", healthSchema),

  overview: () =>
    request("/analytics/overview", overviewSchema).then(mapOverviewToINR),

  segments: () =>
    request("/analytics/segments", z.object({ items: z.array(segmentSchema) })).then((d) =>
      d.items.map(mapSegmentToINR),
    ),

  products: (limit = 10) =>
    request(`/analytics/products?limit=${limit}`, z.object({ items: z.array(productSchema) })).then(
      (d) => d.items.map(mapProductToINR),
    ),

  revenueTrend: (start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const qs = params.toString();
    return request(`/analytics/revenue-trend${qs ? `?${qs}` : ""}`, z.object({ items: z.array(trendSchema) })).then(
      (d) => d.items.map(mapTrendPointToINR),
    );
  },

  drift: () => request("/analytics/drift/latest", driftSchema),

  customer: (id: string) =>
    request(`/customer/${encodeURIComponent(id)}`, customerSchema).then(mapCustomerToINR),

  segmentDetail: (id: string) =>
    request(`/segment/${encodeURIComponent(id)}`, segmentDetailSchema).then(mapSegmentDetailToINR),

  recommendations: (id: string) => request(`/recommend/${encodeURIComponent(id)}`, recommendationResponseSchema),

  askCopilot: (question: string) =>
    request("/copilot/ask", copilotSchema, { method: "POST", body: JSON.stringify({ question }) }),

  audit: (id: number) => request(`/copilot/audit/${id}`, auditSchema),
};
