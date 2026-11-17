import { useState, useEffect, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { CommandPalette } from "../ui/command-palette";
import { BackToTop } from "../ui/back-to-top";
import { useQueryClient } from "@tanstack/react-query";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [commandOpen, setCommandOpen] = useState(false);
  const location = useLocation();
  const queryClient = useQueryClient();

  // Scroll to top on route change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname]);

  // Global Ctrl+K / Cmd+K handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-page)] p-2 sm:p-3 lg:p-4 text-[var(--text-primary)] flex gap-3 transition-colors duration-200">
      {/* Sidebar Container */}
      <Sidebar />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          onOpenCommand={() => setCommandOpen(true)}
        />

        <main className="flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>

      <CommandPalette
        open={commandOpen}
        onClose={() => setCommandOpen(false)}
        onRefresh={() => void queryClient.invalidateQueries()}
      />
      <BackToTop />
    </div>
  );
}