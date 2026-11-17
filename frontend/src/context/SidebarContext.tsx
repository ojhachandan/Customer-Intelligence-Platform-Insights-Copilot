import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface SidebarContextType {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  toggle: () => void;
  expand: () => void;
  collapse: () => void;
  setMobileOpen: (open: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

const STORAGE_KEY = "the_qasar_sidebar_collapsed";

// One-time key migration from legacy storage key
try {
  if (typeof window !== "undefined") {
    const legacy = localStorage.getItem("cip_sidebar_collapsed");
    if (legacy !== null && localStorage.getItem(STORAGE_KEY) === null) {
      localStorage.setItem(STORAGE_KEY, legacy);
    }
  }
} catch {
  /* ignore */
}

export function SidebarProvider({ children }: { children: ReactNode }) {
  // 1. Validate persisted localStorage value safely
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      if (typeof window !== "undefined") {
        // Below 1024px default to collapsed
        if (window.innerWidth < 1024) return true;
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === "true") return true;
        if (saved === "false") return false;
      }
    } catch {
      /* ignore */
    }
    return false; // Default expanded on desktop
  });

  const [isMobileOpen, setMobileOpen] = useState(false);

  // 2. Persist safely to localStorage whenever user changes desktop preference
  const updateCollapsed = (collapsed: boolean) => {
    setIsCollapsed(collapsed);
    try {
      if (typeof window !== "undefined" && window.innerWidth >= 1024) {
        localStorage.setItem(STORAGE_KEY, collapsed ? "true" : "false");
      }
    } catch {
      /* ignore */
    }
  };

  const toggle = () => updateCollapsed(!isCollapsed);
  const expand = () => updateCollapsed(false);
  const collapse = () => updateCollapsed(true);

  // 3. Screen resize listener: auto-collapse below 1024px; restore saved preference above 1024px
  useEffect(() => {
    let wasBelow1024 = window.innerWidth < 1024;

    const handleResize = () => {
      const isNowBelow1024 = window.innerWidth < 1024;

      if (isNowBelow1024 && !wasBelow1024) {
        // Shrunk below 1024px -> auto-collapse
        setIsCollapsed(true);
      } else if (!isNowBelow1024 && wasBelow1024) {
        // Grown back above 1024px -> restore user saved preference
        try {
          const saved = localStorage.getItem(STORAGE_KEY);
          setIsCollapsed(saved === "true");
        } catch {
          setIsCollapsed(false);
        }
      }

      wasBelow1024 = isNowBelow1024;
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 4. Global keyboard shortcut: Ctrl+B / Cmd+B toggles sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        setIsCollapsed((prev) => {
          const next = !prev;
          try {
            if (window.innerWidth >= 1024) {
              localStorage.setItem(STORAGE_KEY, next ? "true" : "false");
            }
          } catch {
            /* ignore */
          }
          return next;
        });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed,
        isMobileOpen,
        toggle,
        expand,
        collapse,
        setMobileOpen,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}

