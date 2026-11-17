import { formatINRCompact } from "../../lib/formatCurrency";
import {
  chartTooltipBoxStyle,
  chartTooltipLabelStyle,
  chartTooltipItemStyle,
  barChartCursor,
  lineChartCursor,
} from "../../lib/chartTheme";

export function formatCurrencyTick(value: number): string {
  return formatINRCompact(value, 1);
}

export function formatNumberTick(value: number): string {
  if (value === 0) return "0";
  if (Math.abs(value) >= 1_000_000) {
    const formatted = (value / 1_000_000).toFixed(1).replace(/\.0$/, "");
    return `${formatted}M`;
  }
  if (Math.abs(value) >= 1_000) {
    const formatted = (value / 1_000).toFixed(1).replace(/\.0$/, "");
    return `${formatted}k`;
  }
  return String(Math.round(value));
}

export const chartTooltipStyle = chartTooltipBoxStyle;

export {
  chartTooltipBoxStyle,
  chartTooltipLabelStyle,
  chartTooltipItemStyle,
  barChartCursor,
  lineChartCursor,
};
