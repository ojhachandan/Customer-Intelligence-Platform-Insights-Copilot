import { motion } from "framer-motion";

function evaluatePassword(pass: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!pass) return { score: 0, label: "Too weak", color: "#C4554D" };
  let score = 0;
  if (pass.length >= 8) score += 1;
  if (/[A-Z]/.test(pass)) score += 1;
  if (/[0-9]/.test(pass)) score += 1;
  if (/[^A-Za-z0-9]/.test(pass)) score += 1;

  switch (score) {
    case 1:
      return { score: 25, label: "Weak", color: "#C4554D" };
    case 2:
      return { score: 50, label: "Fair", color: "#D4A24C" };
    case 3:
      return { score: 75, label: "Good", color: "#5B7FA6" };
    case 4:
      return { score: 100, label: "Strong", color: "#84CC16" };
    default:
      return { score: 10, label: "Too short", color: "#C4554D" };
  }
}

export function PasswordStrengthMeter({ password }: { password: string }) {
  const { score, label, color } = evaluatePassword(password);

  if (!password) return null;

  return (
    <div className="mt-2 space-y-1">
      <div className="flex justify-between items-center text-[10px]">
        <span className="text-[var(--text-muted)]">Password strength</span>
        <span className="font-semibold" style={{ color }}>
          {label}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-[var(--bg-subtle)] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${score}%`, backgroundColor: color }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="h-full rounded-full"
        />
      </div>
    </div>
  );
}
