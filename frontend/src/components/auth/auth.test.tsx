import { render, screen, act } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";
import { authService } from "../../services/authService";
import { SidebarProvider, useSidebar } from "../../context/SidebarContext";

function TestSidebarConsumer() {
  const { isCollapsed, toggle, expand, collapse } = useSidebar();
  return (
    <div>
      <span data-testid="sidebar-state">{isCollapsed ? "collapsed" : "expanded"}</span>
      <button onClick={toggle}>Toggle</button>
      <button onClick={expand}>Expand</button>
      <button onClick={collapse}>Collapse</button>
    </div>
  );
}

describe("PasswordStrengthMeter", () => {
  it("renders null when password is empty", () => {
    const { container } = render(<PasswordStrengthMeter password="" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders strength label for strong password", () => {
    render(<PasswordStrengthMeter password="StrongP@ssw0rd123" />);
    expect(screen.getByText("Password strength")).toBeInTheDocument();
    expect(screen.getByText("Strong")).toBeInTheDocument();
  });
});

describe("SidebarContext single source of truth", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("provides default expanded state and toggles correctly", () => {
    render(
      <SidebarProvider>
        <TestSidebarConsumer />
      </SidebarProvider>,
    );

    expect(screen.getByTestId("sidebar-state").textContent).toBe("expanded");

    act(() => {
      screen.getByText("Toggle").click();
    });
    expect(screen.getByTestId("sidebar-state").textContent).toBe("collapsed");

    act(() => {
      screen.getByText("Expand").click();
    });
    expect(screen.getByTestId("sidebar-state").textContent).toBe("expanded");
  });
});

describe("AuthService client persistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("handles login, session persistence, and logout flow", async () => {
    const user = await authService.login({
      email: "test.director@company.com",
      password: "Password123!",
    });

    expect(user.email).toBe("test.director@company.com");
    expect(authService.isAuthenticated()).toBe(true);

    await authService.logout();
    expect(authService.isAuthenticated()).toBe(false);
  });
});

