import type { MetricRow, ModelKey } from "./types";

/** Display names per grouping (pooled rows use the "ensemble" naming for local/GARCH). */
export const POOLED_NAME: Record<ModelKey, string> = {
  local: "Local ensemble",
  centralized: "Centralized",
  fedavg: "FedAvg",
  fedprox: "FedProx",
  garch: "GARCH (pooled)",
  zero: "Always predict 0",
};

export const BANK_NAME: Record<ModelKey, string> = {
  local: "Local",
  centralized: "Centralized",
  fedavg: "FedAvg",
  fedprox: "FedProx",
  garch: "GARCH(1,1)",
  zero: "Always predict 0",
};

export const ORDER: ModelKey[] = ["local", "centralized", "fedavg", "fedprox", "garch", "zero"];

export const pooledRows = (rows: MetricRow[]) =>
  ORDER.map((k) => rows.find((r) => r.scope === "pooled" && r.key === k)).filter(Boolean) as MetricRow[];

/** Direction accuracy is meaningless for the constant-zero baseline. */
export const dirAcc = (r: MetricRow) => (r.key === "zero" ? null : r.direction_accuracy);

/** "3.4% lower" / "0.1% higher" from a signed percent difference. */
export function relPhrase(v: number | null | undefined, digits = 1) {
  if (v == null || !Number.isFinite(v)) return null;
  const a = Math.abs(v).toFixed(digits);
  if (Number(a) === 0) return "about the same as";
  return v < 0 ? `${a}% lower than` : `${a}% higher than`;
}
