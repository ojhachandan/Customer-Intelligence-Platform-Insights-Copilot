import { X } from "lucide-react";
import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "../../lib/cn";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  wide?: boolean;
}

export function Drawer({ open, onClose, title, children, wide }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            onClick={onClose}
          />

          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 350, damping: 32 }}
            className={cn(
              "relative z-10 flex h-full w-full flex-col overflow-y-auto border-l border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-2xl",
              wide ? "max-w-2xl" : "max-w-lg",
            )}
          >
            {title && (
              <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
                <h2 className="text-base font-semibold text-[#f4f4f5]">{title}</h2>
                <button
                  onClick={onClose}
                  className="rounded-[8px] p-1.5 text-[#71717a] hover:bg-white/[0.06] hover:text-[#f4f4f5] transition-colors"
                  aria-label="Close drawer"
                >
                  <X size={18} />
                </button>
              </div>
            )}
            <div className="flex-1 px-6 py-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
