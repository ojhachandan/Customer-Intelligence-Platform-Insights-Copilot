import type { LucideIcon } from "lucide-react";
import { StatCard, StatCardSkeleton } from "./stat-card";

export function MetricCard({
  icon,
  label,
  value,
  detail,
  iconColor,
  iconBg,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
  iconColor?: string;
  iconBg?: string;
}) {
  return (
    <StatCard
      icon={icon}
      label={label}
      value={value}
      detail={detail}
      iconColor={iconColor}
      iconBg={iconBg}
    />
  );
}

export function MetricCardSkeleton() {
  return <StatCardSkeleton />;
}
