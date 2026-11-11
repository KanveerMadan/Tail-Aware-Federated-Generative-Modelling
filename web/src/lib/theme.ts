import type { ModelKey } from "./types";

export const BANK_COLORS = ["#22D3EE", "#A78BFA", "#FBBF24", "#34D399"] as const;
export const SERVER_COLOR = "#F472B6";
export const BETTER = "#4ADE80";
export const WORSE = "#F87171";

export const bankColor = (id: number | null | undefined) =>
  id == null ? SERVER_COLOR : BANK_COLORS[id % BANK_COLORS.length];

export const MODEL_COLORS: Record<ModelKey, string> = {
  local: "#94A3B8",
  garch: "#F59E0B",
  centralized: "#E2E8F0",
  fedavg: "#38BDF8",
  fedprox: SERVER_COLOR,
  zero: "#475569",
};

export const MODEL_ORDER: ModelKey[] = ["local", "centralized", "fedavg", "fedprox", "garch", "zero"];

export const hexA = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};
