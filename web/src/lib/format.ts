const SUP: Record<string, string> = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };

/** Scientific with unicode superscript exponent: 4.12 × 10⁻⁴ */
export function sci(v: number | null | undefined, digits = 3): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  const [m, e] = v.toExponential(digits - 1).split("e");
  const exp = parseInt(e, 10);
  if (exp === 0) return m;
  return `${m} × 10${String(exp).split("").map((c) => SUP[c] ?? c).join("")}`;
}

/** Compact scientific for tables/axes: 4.12e-4 */
export function sciShort(v: number | null | undefined, digits = 3): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e-2 && a < 1e4) return v.toPrecision(digits);
  return v.toExponential(digits - 1).replace("e+", "e");
}

/** Smart number: plain when readable, scientific otherwise. */
export function num(v: number | null | undefined, digits = 4): string {
  if (v == null || !Number.isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1e5 || a < 1e-3) return sciShort(v, digits);
  return v.toFixed(a >= 100 ? 1 : a >= 1 ? 3 : digits);
}

export const int = (v: number | null | undefined) =>
  v == null || !Number.isFinite(v) ? "—" : Math.round(v).toLocaleString("en-US");

export const pct = (v: number | null | undefined, digits = 1) =>
  v == null || !Number.isFinite(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

/** Signed relative change already in percent units: +3.2% / −1.4% */
export const signedPct = (v: number | null | undefined, digits = 1) =>
  v == null || !Number.isFinite(v) ? "—" : `${v > 0 ? "+" : v < 0 ? "−" : "±"}${Math.abs(v).toFixed(digits)}%`;

export const fmtDate = (s: string | null | undefined) => {
  if (!s) return "—";
  const d = new Date(s + "T00:00:00");
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
};
