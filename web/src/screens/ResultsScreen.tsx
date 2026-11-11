import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowDown, ArrowUp, ArrowUpDown, Scale, Target, Trophy } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Segmented } from "@/components/ui/toggle-group";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Chart, axisBase, tooltipBase } from "@/components/Chart";
import { ChartPanel, Loading, NotAvailable, Reveal, SectionHeader, Stagger, Dot } from "@/components/primitives";
import { useData } from "@/lib/data";
import { BANK_COLORS, BETTER, MODEL_COLORS, WORSE, bankColor, hexA } from "@/lib/theme";
import { pct, sciShort } from "@/lib/format";
import { BANK_NAME, ORDER, POOLED_NAME, dirAcc, pooledRows, relPhrase } from "@/lib/models";
import type { MetricRow, ModelKey } from "@/lib/types";
import { cn } from "@/lib/utils";

type ColKey = "mse" | "mae" | "var_95_error" | "var_99_error" | "kurtosis_error" | "acf_error" | "direction_accuracy";
const COLS: { key: ColKey; label: string; higherBetter?: boolean }[] = [
  { key: "mse", label: "MSE" },
  { key: "mae", label: "MAE" },
  { key: "var_95_error", label: "VaR(95) err" },
  { key: "var_99_error", label: "VaR(99) err" },
  { key: "kurtosis_error", label: "Kurtosis err" },
  { key: "acf_error", label: "ACF err" },
  { key: "direction_accuracy", label: "Direction acc", higherBetter: true },
];

const val = (r: MetricRow, k: ColKey) => (k === "direction_accuracy" ? dirAcc(r) : r[k]);

function pooledBar(rows: MetricRow[], metric: "mse" | "var_95_error", title: string) {
  const items = rows.map((r) => ({ name: POOLED_NAME[r.key], key: r.key, v: r[metric] ?? 0 })).sort((a, b) => b.v - a.v);
  const best = Math.min(...items.map((i) => i.v));
  return {
    grid: { left: 140, right: 70, top: 10, bottom: 30 },
    tooltip: { ...tooltipBase, trigger: "item" as const, formatter: (p: unknown) => { const q = p as { name: string; value: number }; return `${title}<br/><b>${q.name}</b>: ${sciShort(q.value, 4)}`; } },
    xAxis: { type: "value" as const, splitNumber: 3, ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => sciShort(v, 2) } },
    yAxis: { type: "category" as const, data: items.map((i) => i.name), ...axisBase, axisLabel: { color: "#CBD5E1", fontFamily: "Inter", fontSize: 13 } },
    series: [
      {
        type: "bar" as const,
        barWidth: 18,
        animationDelay: (i: number) => i * 90,
        data: items.map((i) => ({
          value: i.v,
          itemStyle: {
            borderRadius: [0, 8, 8, 0],
            color: {
              type: "linear" as const, x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [{ offset: 0, color: hexA(MODEL_COLORS[i.key], 0.25) }, { offset: 1, color: MODEL_COLORS[i.key] }],
            },
            shadowBlur: i.v === best ? 18 : 0,
            shadowColor: MODEL_COLORS[i.key],
          },
        })),
        label: { show: true, position: "right" as const, color: "#E2E8F0", fontFamily: "JetBrains Mono", fontSize: 11, formatter: (p: unknown) => sciShort((p as { value: number }).value, 3) },
      },
    ],
  };
}

export default function ResultsScreen() {
  const { data, loading, missing } = useData("results.json");
  const { data: summary } = useData("summary.json");
  const [scope, setScope] = useState<"pooled" | "bank">("pooled");
  const [bankMetric, setBankMetric] = useState<"mse" | "var_95_error">("mse");
  const [sort, setSort] = useState<{ key: ColKey | "name"; dir: 1 | -1 }>({ key: "mse", dir: 1 });

  const pooled = useMemo(() => (data ? pooledRows(data.rows) : []), [data]);

  const tableRows = useMemo(() => {
    if (!data) return [];
    const rows = data.rows.filter((r) => r.scope === scope);
    return [...rows].sort((a, b) => {
      if (sort.key === "name") return (a.bank_id ?? -1) - (b.bank_id ?? -1) || ORDER.indexOf(a.key) - ORDER.indexOf(b.key);
      const va = val(a, sort.key);
      const vb = val(b, sort.key);
      if (va == null) return 1;
      if (vb == null) return -1;
      return (va - vb) * sort.dir;
    });
  }, [data, scope, sort]);

  // best per column; per-bank view: best within each bank
  const best = useMemo(() => {
    const out = new Map<string, number>();
    for (const c of COLS) {
      const groups = new Map<number, MetricRow[]>();
      tableRows.forEach((r) => {
        const g = r.bank_id ?? -1;
        groups.set(g, [...(groups.get(g) ?? []), r]);
      });
      groups.forEach((rs, g) => {
        const vs = rs.map((r) => val(r, c.key)).filter((v): v is number => v != null);
        if (vs.length) out.set(`${g}:${c.key}`, c.higherBetter ? Math.max(...vs) : Math.min(...vs));
      });
    }
    return out;
  }, [tableRows]);

  if (loading) return <Loading />;
  if (missing || !data) return <NotAvailable what="Evaluation results" file="results.json" />;

  const banks = [...new Set(data.rows.filter((r) => r.scope === "bank").map((r) => r.bank_id as number))].sort();
  const bankKeys = ORDER.filter((k) => data.rows.some((r) => r.scope === "bank" && r.key === k));
  const bankChart = {
    grid: { left: 70, right: 20, top: 46, bottom: 36 },
    legend: { top: 4, textStyle: { color: "#CBD5E1" }, icon: "roundRect", itemWidth: 12, itemHeight: 8 },
    tooltip: { ...tooltipBase, trigger: "axis" as const, axisPointer: { type: "shadow" as const }, valueFormatter: (v: unknown) => sciShort(Number(v), 4) },
    xAxis: { type: "category" as const, data: banks.map((b) => `Bank ${b}`), ...axisBase, axisLabel: { color: "#CBD5E1", fontFamily: "Inter", fontSize: 13 } },
    yAxis: { type: "value" as const, ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => sciShort(v, 2) } },
    series: bankKeys.map((k, i) => ({
      name: BANK_NAME[k],
      type: "bar" as const,
      barGap: "12%",
      animationDelay: (j: number) => j * 60 + i * 40,
      itemStyle: { color: MODEL_COLORS[k], borderRadius: [5, 5, 0, 0] },
      data: banks.map((b) => data.rows.find((r) => r.scope === "bank" && r.key === k && r.bank_id === b)?.[bankMetric] ?? null),
    })),
  };

  // generated comparisons
  const bf = summary?.best_federated ?? null;
  const cm = summary?.comparisons?.mse;
  const cv = summary?.comparisons?.var_95_error;
  const bfName = bf === "fedavg" ? "FedAvg" : bf === "fedprox" ? "FedProx" : null;
  const lines: { icon: JSX.Element; text: string; good: boolean | null }[] = [];
  if (bf && cm?.[bf]) {
    const c = cm[bf]!;
    const p = relPhrase(c.vs_centralized_pct);
    if (p) lines.push({ icon: <Scale className="h-4 w-4" />, text: `${bfName} pooled MSE is ${p} centralized training (without pooling any data).`, good: (c.vs_centralized_pct ?? 0) <= 0 });
    const pl = relPhrase(c.vs_local_ensemble_pct);
    if (pl) lines.push({ icon: <Target className="h-4 w-4" />, text: `${bfName} pooled MSE is ${pl} the local-model ensemble.`, good: (c.vs_local_ensemble_pct ?? 0) < 0 });
    const pz = relPhrase(c.vs_zero_pct);
    if (pz) lines.push({ icon: <Trophy className="h-4 w-4" />, text: `${bfName} pooled MSE is ${pz} always predicting a 0% return.`, good: (c.vs_zero_pct ?? 0) < 0 });
  }
  if (bf && cv?.[bf]) {
    const p = relPhrase(cv[bf]!.vs_centralized_pct);
    if (p) lines.push({ icon: <Scale className="h-4 w-4" />, text: `${bfName} VaR(95) error is ${p} centralized.`, good: (cv[bf]!.vs_centralized_pct ?? 0) <= 0 });
  }

  const sortBy = (key: ColKey | "name") =>
    setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: key === "direction_accuracy" ? -1 : 1 }));

  return (
    <Stagger className="grid gap-6">
      <SectionHeader
        eyebrow="Step 7 · Results"
        title={
          <>
            Federated <span className="text-gradient">vs everyone else</span>
          </>
        }
        subtitle={`All models scored on the same ${data.n_test_pooled.toLocaleString("en-US")} held-out test days (raw daily log returns). Lower is better for every error metric.`}
      />

      {lines.length > 0 && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-4">
          {lines.map((l, i) => (
            <Reveal key={i}>
              <div className="flex h-full items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.03] px-5 py-3 text-[0.95rem] leading-snug text-slate-200">
                <span style={{ color: l.good == null ? "#94A3B8" : l.good ? BETTER : WORSE }}>{l.icon}</span>
                {l.text}
              </div>
            </Reveal>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartPanel title="Pooled MSE" subtitle="all 4 banks' test days · lower is better">
          <Chart option={pooledBar(pooled, "mse", "MSE")} height={270} />
        </ChartPanel>
        <ChartPanel title="Pooled VaR(95) error" subtitle="|predicted − actual 95% VaR| · lower is better">
          <Chart option={pooledBar(pooled, "var_95_error", "VaR(95) error")} height={270} />
        </ChartPanel>
        <ChartPanel
          title="Per bank"
          subtitle="each bank's own test set · lower is better"
          right={
            <Segmented
              layoutId="bank-metric"
              value={bankMetric}
              onChange={setBankMetric}
              options={[{ value: "mse", label: "MSE" }, { value: "var_95_error", label: "VaR(95)" }]}
            />
          }
        >
          <Chart option={bankChart} height={270} notMerge />
        </ChartPanel>
      </div>

      <Reveal>
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-4 px-6 pt-5">
            <div>
              <h3 className="font-display text-lg font-semibold text-white">All metrics</h3>
              <p className="mt-1 text-sm text-muted">Click a column to sort · best value per column{scope === "bank" ? " (per bank)" : ""} highlighted</p>
            </div>
            <Segmented
              layoutId="table-scope"
              value={scope}
              onChange={setScope}
              options={[{ value: "pooled", label: "Pooled (all banks)" }, { value: "bank", label: "Per bank" }]}
            />
          </div>
          <div className="mt-4 max-h-[330px] overflow-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>
                    <button className="flex items-center gap-1.5 hover:text-white" onClick={() => sortBy("name")}>
                      Model <ArrowUpDown className="h-3 w-3" />
                    </button>
                  </TableHead>
                  {COLS.map((c) => (
                    <TableHead key={c.key} className="text-right">
                      <button className="ml-auto flex items-center gap-1.5 hover:text-white" onClick={() => sortBy(c.key)}>
                        {c.label}
                        {sort.key === c.key ? sort.dir === 1 ? <ArrowUp className="h-3 w-3 text-server" /> : <ArrowDown className="h-3 w-3 text-server" /> : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {tableRows.map((r, i) => (
                  <motion.tr
                    key={`${r.key}-${r.bank_id}`}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.015 }}
                    className="group transition-colors hover:bg-white/[0.035]"
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Dot color={MODEL_COLORS[r.key as ModelKey]} />
                        <span className="font-medium text-white">{r.scope === "pooled" ? POOLED_NAME[r.key] : BANK_NAME[r.key]}</span>
                        {r.bank_id != null && (
                          <span className="rounded-md px-2 py-0.5 font-mono text-[0.7rem]" style={{ color: bankColor(r.bank_id), background: hexA(BANK_COLORS[r.bank_id], 0.1) }}>
                            bank {r.bank_id}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    {COLS.map((c) => {
                      const v = val(r, c.key);
                      const isBest = v != null && best.get(`${r.bank_id ?? -1}:${c.key}`) === v;
                      return (
                        <TableCell key={c.key} className={cn("text-right font-mono tabular-nums", isBest ? "text-better" : "text-slate-300")}>
                          <span className={cn(isBest && "rounded-md bg-better/10 px-2 py-0.5 ring-1 ring-better/25")}>
                            {c.key === "direction_accuracy" ? pct(v) : sciShort(v, 3)}
                          </span>
                        </TableCell>
                      );
                    })}
                  </motion.tr>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </Reveal>
    </Stagger>
  );
}
