import { useEffect, useState } from "react";

interface AnimatedNumberProps {
  value: string | number;
  duration?: number;
  className?: string;
}

export function AnimatedNumber({ value, duration = 800, className }: AnimatedNumberProps) {
  const str = String(value);
  const match = str.match(/^([^0-9.-]*)([0-9,.]+)(.*)$/);

  const prefix = match ? match[1] : "";
  const numericPart = match ? match[2].replace(/,/g, "") : "";
  const suffix = match ? match[3] : "";
  const target = parseFloat(numericPart);
  const isDecimal = numericPart.includes(".");
  const decimals = isDecimal ? numericPart.split(".")[1]?.length ?? 0 : 0;
  const hasCommas = match ? match[2].includes(",") : false;

  const isTest = typeof process !== "undefined" && process.env?.NODE_ENV === "test";
  const [displayValue, setDisplayValue] = useState<number>(
    isTest || isNaN(target) ? target : 0,
  );

  useEffect(() => {
    if (isNaN(target)) return;

    if (isTest || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplayValue(target);
      return;
    }

    const start = 0;
    let startTime: number | null = null;
    let animationFrame: number;

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutExpo
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = start + (target - start) * ease;

      setDisplayValue(current);

      if (progress < 1) {
        animationFrame = requestAnimationFrame(step);
      } else {
        setDisplayValue(target);
      }
    };

    animationFrame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationFrame);
  }, [target, duration, isTest]);

  if (isNaN(target)) {
    return <span className={className}>{str}</span>;
  }

  const formattedNum = isDecimal
    ? displayValue.toFixed(decimals)
    : Math.round(displayValue).toString();

  const withCommas = hasCommas
    ? formattedNum.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
    : formattedNum;

  return (
    <span className={className}>
      {prefix}
      {withCommas}
      {suffix}
    </span>
  );
}
