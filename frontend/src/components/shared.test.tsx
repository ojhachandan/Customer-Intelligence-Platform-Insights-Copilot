import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErrorCard, Unavailable } from "./shared";
import { currency } from "../lib/formatters";

describe("shared UI states", () => {
  it("formats business currency consistently", () => {
    expect(currency(1234)).toBe("₹1,234");
  });

  it("renders an honest unavailable state", () => {
    render(<Unavailable title="Pipeline status is not exposed" detail="No backend endpoint exists." />);
    expect(screen.getByText("Pipeline status is not exposed")).toBeInTheDocument();
    expect(screen.getByText("No backend endpoint exists.")).toBeInTheDocument();
  });

  it("renders an API error without masking it as data", () => {
    render(<ErrorCard error={new Error("The backend is unavailable.")} />);
    expect(screen.getByText("The backend is unavailable.")).toBeInTheDocument();
  });
});
