import {
  Bot,
  Copy,
  Check,
  Send,
  Wrench,
  FileText,
  Database as DbIcon,
  Sparkles,
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCopilotAsk } from "../hooks/useApi";
import { PageHeader } from "../components/ui/page-header";
import { ErrorCard } from "../components/shared";
import { Badge } from "../components/ui/badge";
import { Drawer } from "../components/ui/drawer";
import type { Citation, CopilotAnswer } from "../types/api";

interface Message {
  question: string;
  answer: string;
  citations: Citation[];
  auditId: number;
}

const SUGGESTIONS = [
  "Which customer segment generates the highest revenue?",
  "What is the business overview?",
  "What products are performing best?",
  "Who are our most valuable customers?",
  "How is revenue changing over time?",
  "What products should we recommend to c-001?",
];

function sourceIcon(type: Citation["source_type"]) {
  switch (type) {
    case "tool":
      return <Wrench size={13} />;
    case "report":
      return <FileText size={13} />;
    case "vector":
      return <DbIcon size={13} />;
  }
}

function CitationChips({
  citations,
  onOpen,
}: {
  citations: Citation[];
  onOpen: (c: Citation) => void;
}) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {citations.map((c, i) => (
        <button
          key={`${c.source_id}-${i}`}
          onClick={() => onOpen(c)}
          className="inline-flex items-center gap-1.5 rounded-full border border-[#7c6cff]/30 bg-[#7c6cff]/10 px-2.5 py-1 text-xs font-medium text-[#7c6cff] transition hover:bg-[#7c6cff]/20 hover:border-[#7c6cff]/50"
        >
          {sourceIcon(c.source_type)}
          <span>[{i + 1}]</span>
          <span className="max-w-[140px] truncate">{c.source_id}</span>
        </button>
      ))}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button
      onClick={copy}
      className="rounded-[8px] p-1.5 text-[#71717a] transition hover:bg-white/[0.06] hover:text-[#f4f4f5]"
      aria-label="Copy response"
    >
      {copied ? <Check size={14} className="text-[#84CC16]" /> : <Copy size={14} />}
    </button>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-3 py-2">
      <motion.span
        animate={{ y: [0, -4, 0] }}
        transition={{ repeat: Infinity, duration: 0.6, ease: "easeInOut" }}
        className="h-2 w-2 rounded-full bg-[#2DD4BF]"
      />
      <motion.span
        animate={{ y: [0, -4, 0] }}
        transition={{ repeat: Infinity, duration: 0.6, delay: 0.15, ease: "easeInOut" }}
        className="h-2 w-2 rounded-full bg-[#7392EF]"
      />
      <motion.span
        animate={{ y: [0, -4, 0] }}
        transition={{ repeat: Infinity, duration: 0.6, delay: 0.3, ease: "easeInOut" }}
        className="h-2 w-2 rounded-full bg-[#84CC16]"
      />
      <span className="ml-2 text-xs text-[#a1a1aa]">Analyzing warehouse data…</span>
    </div>
  );
}

export default function CopilotPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeCitation, setActiveCitation] = useState<Citation>();
  const ask = useCopilotAsk();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, ask.isPending]);

  const submit = async () => {
    const value = question.trim();
    if (!value || ask.isPending) return;
    try {
      const result: CopilotAnswer = await ask.mutateAsync(value);
      setMessages((prev) => [
        ...prev,
        {
          question: value,
          answer: result.answer,
          citations: result.citations,
          auditId: result.audit_log_id,
        },
      ]);
      setQuestion("");
    } catch {
      /* Error displayed via ask.isError */
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Insights Copilot"
        subtitle="Conversational business intelligence grounded in real-time database tools and verified citations."
        icon={Bot}
      />

      <div className="grid min-h-[680px] gap-6 xl:grid-cols-[300px_1fr]">
        {/* Left Suggestion Sidebar */}
        <aside className="card flex flex-col p-5 shadow-card">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-[#7c6cff]" />
            <p className="label text-[#f4f4f5]">Suggested Queries</p>
          </div>
          <div className="space-y-2 flex-1">
            {SUGGESTIONS.map((s) => (
              <motion.button
                key={s}
                whileHover={{ x: 2 }}
                onClick={() => setQuestion(s)}
                className="w-full rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3 text-left text-xs leading-relaxed text-[var(--text-secondary)] transition-all hover:border-[var(--accent-border)] hover:bg-[var(--surface-inset-hover)] hover:text-[var(--text-primary)]"
              >
                {s}
              </motion.button>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-white/[0.06] text-[11px] text-[#71717a] leading-relaxed">
            Audit logging tracks query latency, model metadata, and executed warehouse functions for full traceability.
          </div>
        </aside>

        {/* Right Main Chat Panel */}
        <section className="card flex flex-col overflow-hidden shadow-card">
          {/* Messages Stream */}
          <div className="flex-1 space-y-4 overflow-y-auto p-5 sm:p-6">
            {messages.length === 0 && (
              <div className="grid h-full place-items-center py-20 text-center">
                <div className="max-w-md">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-[16px] border border-[#7c6cff]/30 bg-[#7c6cff]/15 text-[#7c6cff] shadow-glow">
                    <Bot size={28} />
                  </div>
                  <h2 className="mt-4 text-lg font-semibold text-[#f4f4f5]">
                    Ask any customer or revenue question
                  </h2>
                  <p className="mt-2 text-sm text-[#71717a] leading-relaxed">
                    The Copilot dynamically executes warehouse aggregations, cohort trends, and hybrid recommendations, providing verifiable citations for every claim.
                  </p>
                </div>
              </div>
            )}

            <AnimatePresence initial={false}>
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-3"
                >
                  {/* User Bubble */}
                  <div className="flex justify-end">
                    <div className="max-w-[85%] rounded-[18px] bg-[#7c6cff] px-4 py-3 text-sm font-medium text-white shadow-sm">
                      {msg.question}
                    </div>
                  </div>

                  {/* Assistant Bubble */}
                  <div className="flex justify-start">
                    <div className="max-w-[92%] rounded-[18px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-4 text-[var(--text-primary)] shadow-card">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm leading-7 text-[var(--text-primary)] whitespace-pre-wrap">
                          {msg.answer}
                        </p>
                        <CopyButton text={msg.answer} />
                      </div>
                      <CitationChips citations={msg.citations} onOpen={setActiveCitation} />
                      <div className="mt-3 flex items-center justify-between border-t border-[var(--border-subtle)] pt-2 text-[11px] text-[var(--text-muted)]">
                        <span>
                          Audit Record:{" "}
                          <strong className="font-mono text-[var(--text-secondary)]">#{msg.auditId}</strong>
                        </span>
                        <span className="flex items-center gap-1 text-[#84CC16]">
                          <span className="h-1.5 w-1.5 rounded-full bg-[#84CC16]" />
                          Verified Warehouse Evidence
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {ask.isPending && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="rounded-[18px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3 shadow-card">
                  <TypingIndicator />
                </div>
              </motion.div>
            )}

            {ask.isError && <ErrorCard error={ask.error} />}
            <div ref={endRef} />
          </div>

          {/* Sticky Input Composer Bar */}
          <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="relative flex items-end rounded-[14px] border border-[var(--border-inset)] bg-[var(--surface-inset)] focus-within:border-[var(--accent)] focus-within:ring-1 focus-within:ring-[var(--accent)] transition-all">
              <textarea
                aria-label="Ask the Insights Copilot"
                className="max-h-32 min-h-[56px] w-full resize-none bg-transparent p-3.5 pr-14 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void submit();
                  }
                }}
                placeholder="Ask about revenue trends, high-value segments, top products, or recommendations..."
              />
              <button
                className="absolute right-2.5 bottom-2.5 flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#7c6cff] text-white shadow-glow transition hover:bg-[#6b58ff] disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                disabled={ask.isPending || !question.trim()}
                onClick={() => void submit()}
                aria-label="Send query"
              >
                <Send size={15} />
              </button>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-[#71717a]">
              <span>Press Enter to send · Shift + Enter for newline</span>
              <span className="hidden sm:inline">Responses audited automatically</span>
            </div>
          </div>
        </section>
      </div>

      {/* Citation Slide-over Drawer */}
      <Drawer
        open={!!activeCitation}
        onClose={() => setActiveCitation(undefined)}
        title="Evidence Source"
        wide
      >
        {activeCitation && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-[#7c6cff]">{sourceIcon(activeCitation.source_type)}</span>
              <Badge
                variant={
                  activeCitation.source_type === "tool"
                    ? "info"
                    : activeCitation.source_type === "report"
                    ? "success"
                    : "default"
                }
              >
                {activeCitation.source_type}
              </Badge>
            </div>
            <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                Source ID
              </p>
              <p className="mt-1 font-mono text-sm font-semibold text-[#f4f4f5]">
                {activeCitation.source_id}
              </p>
            </div>
            <div className="rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset)] p-3.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                Description
              </p>
              <p className="mt-1 text-sm text-[#a1a1aa] leading-relaxed">
                {activeCitation.description}
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
                Query Payload / Execution Parameters
              </p>
              <pre className="mt-2 overflow-auto rounded-[12px] border border-[var(--border-inset)] bg-[var(--surface-inset-hover)] p-4 font-mono text-xs text-[#2dd4bf]">
                {JSON.stringify(activeCitation.query, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
