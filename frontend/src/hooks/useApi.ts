import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: api.health, retry: false, refetchInterval: 30_000 });

export const useBusinessOverview = () =>
  useQuery({ queryKey: ["overview"], queryFn: api.overview });

export const useSegments = () =>
  useQuery({ queryKey: ["segments"], queryFn: api.segments });

export const useProducts = (limit?: number) =>
  useQuery({ queryKey: ["products", limit], queryFn: () => api.products(limit) });

export const useRevenueTrend = (start?: string, end?: string) =>
  useQuery({ queryKey: ["revenue-trend", start, end], queryFn: () => api.revenueTrend(start, end) });

export const useDrift = () =>
  useQuery({ queryKey: ["drift"], queryFn: api.drift, retry: false });

export const useCustomer = (id: string) =>
  useQuery({ queryKey: ["customer", id], queryFn: () => api.customer(id), enabled: Boolean(id) });

export const useSegmentDetail = (id: string) =>
  useQuery({ queryKey: ["segment-detail", id], queryFn: () => api.segmentDetail(id), enabled: Boolean(id) });

export const useRecommendations = (id: string) =>
  useQuery({ queryKey: ["recommendations", id], queryFn: () => api.recommendations(id), enabled: Boolean(id) });

export const useCopilotAsk = () =>
  useMutation({ mutationFn: api.askCopilot });

export const useAudit = (id?: number) =>
  useQuery({ queryKey: ["audit", id], queryFn: () => api.audit(id!), enabled: Boolean(id), retry: false });
