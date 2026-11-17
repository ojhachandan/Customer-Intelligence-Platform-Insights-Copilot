/**
 * Currency Configuration Module (Single Source of Truth)
 * Source data is in USD and is converted to INR for display at USD_TO_INR_RATE.
 * Configured: 2026-11-03
 */

const parsedRate = Number(import.meta.env.VITE_USD_TO_INR ?? "94.68");

if (!Number.isFinite(parsedRate) || parsedRate <= 0) {
  console.error(
    `[Currency Config] Invalid VITE_USD_TO_INR rate: "${import.meta.env.VITE_USD_TO_INR}". Must be a finite positive number. Falling back to 94.68.`,
  );
}

export const USD_TO_INR_RATE: number =
  Number.isFinite(parsedRate) && parsedRate > 0 ? parsedRate : 94.68;

export type NumberNotation = "indian" | "international";

export const NUMBER_NOTATION: NumberNotation =
  (import.meta.env.VITE_NUMBER_NOTATION as NumberNotation) === "international"
    ? "international"
    : "indian";

/**
 * Converts a source USD money amount to INR once at the presentation mapping layer.
 * Does not format into a string; returns the numerical value in INR.
 */
export function usdToInr(usdAmount: number | null | undefined): number {
  if (usdAmount === null || usdAmount === undefined || !Number.isFinite(usdAmount)) {
    return 0;
  }
  return usdAmount * USD_TO_INR_RATE;
}

