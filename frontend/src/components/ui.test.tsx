import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Users } from "lucide-react";
import { Badge } from "./ui/badge";
import { MetricCard } from "./ui/metric-card";
import { StatusDot } from "./ui/status-dot";
import { EmptyState } from "./ui/empty-state";
import { currency, percent } from "../lib/formatters";

describe("UI primitives & formatters", () => {
  it("formats percentages correctly", () => {
    expect(percent(0.1234)).toBe("12.3%");
    expect(percent(0.5)).toBe("50%");
    expect(percent(1)).toBe("100%");
  });

  it("formats currency correctly", () => {
    expect(currency(50000)).toBe("₹50,000");
    expect(currency(0)).toBe("₹0");
  });

  it("renders Badge variants", () => {
    render(<Badge variant="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders MetricCard with label and value", () => {
    render(
      <MetricCard
        icon={Users}
        label="Total Customers"
        value="1,200"
        detail="Active records"
      />
    );
    expect(screen.getByText("Total Customers")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("Active records")).toBeInTheDocument();
  });

  it("renders StatusDot with appropriate label", () => {
    render(<StatusDot status="healthy" label="Online" />);
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("renders EmptyState", () => {
    render(
      <EmptyState
        icon={Users}
        title="No customers"
        description="Try searching for another customer ID."
      />
    );
    expect(screen.getByText("No customers")).toBeInTheDocument();
    expect(screen.getByText("Try searching for another customer ID.")).toBeInTheDocument();
  });
});
