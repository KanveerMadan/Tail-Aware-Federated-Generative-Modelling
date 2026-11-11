import { useMemo, useState } from "react";
import { Activity, Crosshair, Gauge, TrendingUp } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Chart, axisBase, tooltipBase } from "@/components/Chart";
import { ChartPanel, CountUp, Dot, Loading, NotAvailable, SectionHeader, Stagger, StatCard } from "@/components/primitives";
import { useData } from "@/lib/data";
import { MODEL_COLORS, bankColor, hexA } from "@/lib/theme";
import { fmtDate, sciShort } from "@/lib/format";
import { BANK_NAME, ORDER, dirAcc } from "@/lib/models";
import type { ModelKey } from "@/lib/types";

export default function PredictScreen() {
  const { data, loading, missing } = useData("predictions.json");
  const { data: results } = useData("results.json");
  const { data: banksData } = useData("banks.json");
  const [bank, setBank] = useState(0);
  const [model, setModel] = useState<ModelKey>("fedavg");

  const b = data?.banks.find((x) => x.bank_id === bank) ?? data?.banks[0];
  const models = b ? ORDER.filter((k) => b.models[k] && k !== "zero") : [];
  const key: ModelKey = b && b.models[model] ? model : models[0] ?? "local";
  const pred = b?.models[key];
  const sector = banksData?.banks.find((x) => x.bank_id === b?.bank_id)?.sector;

  const row = results?.rows.find((r) => r.scope === "bank" && r.bank_id === b?.bank_id && r.key === key);

  const option = useMemo(() => {
    if (!b || !pred) return {};
    const x = b.dates ?? b.actual.map((_, i) => String(i + 1));
    const color = MODEL_COLORS[key];
    const bc = bankColor(b.bank_id);
    return {
      animationDuration: 1400,
      grid: { left: 70, right: 36, top: 50, bottom: 84 },
      legend: { top: 6, left: 10, textStyle: { color: "#CBD5E1" }, icon: "roundRect", itemWidth: 14, itemHeight: 4 },
      toolbox: {
        right: 16, top: 2, iconStyle: { borderColor: "#8B97B1" }, emphasis: { iconStyle: { borderColor: "#fff" } },
        feature: { dataZoom: { yAxisIndex: "none" as const, title: { zoom: "Brush to zoom", back: "Undo zoom" } }, restore: { title: "Reset" } },
      },
      tooltip: {
        ...tooltipBase,
        trigger: "axis" as const,
        formatter: (params: unknown) => {
          const ps = params as { dataIndex: number }[];
          const i = ps[0]?.dataIndex ?? 0;
          const a = b.actual[i];
          const p = pred[i];
          const t = b.tickers?.[i];
          return `<div style="font-family:Inter"><div style="color:#8B97B1;margin-bottom:6px">${b.dates ? fmtDate(b.dates[i]) : `day ${i + 1}`}${t ? ` · ${t}` : ""}</div>
            <div style="font-family:JetBrains Mono;display:grid;grid-template-columns:auto auto;gap:2px 16px">
            <span style="color:${color}">predicted</span><span>${(p * 100).toFixed(3)}%</span>
            <span style="color:#CBD5E1">actual</span><span>${(a * 100).toFixed(3)}%</span>
            <span style="color:#8B97B1">error</span><span>${((p - a) * 100).toFixed(3)}%</span></div></div>`;
        },
      },
      xAxis: { type: "category" as const, data: x, ...axisBase, axisLabel: { ...axisBase.axisLabel, hideOverlap: true, formatter: (v: string) => (b.dates ? new Date(v + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" }) : v) }, splitLine: { show: false } },
      yAxis: { type: "value" as const, ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => `${(v * 100).toFixed(1)}%` } },
      dataZoom: [
        { type: "inside" as const, start: 0, end: 100 },
        {
          type: "slider" as const, height: 24, bottom: 18, borderColor: "rgba(255,255,255,0.08)", backgroundColor: "rgba(255,255,255,0.02)",
          fillerColor: hexA(color, 0.12), handleStyle: { color }, textStyle: { color: "#8B97B1" },
          dataBackground: { lineStyle: { color: hexA(bc, 0.5) }, areaStyle: { color: hexA(bc, 0.08) } },
        },
      ],
      series: [
        { name: "Actual", type: "line" as const, data: b.actual, showSymbol: false, lineStyle: { width: 1.1, color: "rgba(203,213,225,0.45)" }, itemStyle: { color: "#CBD5E1" }, z: 1 },
        {
          name: `Predicted · ${BANK_NAME[key]}`, type: "line" as const, data: pred, showSymbol: false, smooth: 0.3,
          lineStyle: { width: 2.6, color, shadowBlur: 10, shadowColor: hexA(color, 0.6) }, itemStyle: { color }, z: 2,
        },
      ],
    };
  }, [b, pred, key]);

  if (loading) return <Loading />;
  if (missing || !data || !b || !pred) return <NotAvailable what="Test predictions" file="predictions.json" />;

  const mse = row?.mse ?? null;
  const mae = row?.mae ?? null;
  const da = row ? dirAcc(row) : null;

  return (
    <Stagger className="grid gap-6">
      <SectionHeader
        eyebrow="Step 8 · Predict a stock"
        title={
          <>
            Predicted vs actual, <span className="text-gradient">day by day</span>
          </>
        }
        subtitle={`Next-day return forecasts on Bank ${b.bank_id}'s held-out test period (${b.actual.length} days${b.dates ? `, ${fmtDate(b.dates[0])} → ${fmtDate(b.dates[b.dates.length - 1])}` : ""}). Daily returns are mostly noise, so good models predict small, cautious values.`}
        right={
          <div className="flex flex-wrap gap-3">
            <Select value={String(b.bank_id)} onValueChange={(v) => setBank(Number(v))}>
              <SelectTrigger aria-label="Bank">
                <span className="flex items-center gap-2.5">
                  <Dot color={bankColor(b.bank_id)} />
                  <SelectValue />
                </span>
              </SelectTrigger>
              <SelectContent>
                {data.banks.map((x) => (
                  <SelectItem key={x.bank_id} value={String(x.bank_id)}>
                    Bank {x.bank_id} · {banksData?.banks.find((y) => y.bank_id === x.bank_id)?.sector ?? x.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={key} onValueChange={(v) => setModel(v as ModelKey)}>
              <SelectTrigger aria-label="Model">
                <span className="flex items-center gap-2.5">
                  <Dot color={MODEL_COLORS[key]} />
                  <SelectValue />
                </span>
              </SelectTrigger>
              <SelectContent>
                {models.map((k) => (
                  <SelectItem key={k} value={k}>
                    {BANK_NAME[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-4">
        <StatCard label="MSE" icon={<Gauge className="h-3.5 w-3.5" />} accent={MODEL_COLORS[key]} value={mse != null ? <CountUp key={`${key}-${b.bank_id}-mse`} value={mse} decimals={12} formatter={(v) => sciShort(v, 3)} /> : "—"} hint="mean squared error · lower is better" />
        <StatCard label="MAE" icon={<Activity className="h-3.5 w-3.5" />} accent={MODEL_COLORS[key]} value={mae != null ? <CountUp key={`${key}-${b.bank_id}-mae`} value={mae * 100} decimals={3} formatter={(v) => `${v.toFixed(3)}%`} /> : "—"} hint="mean absolute error, in return %" />
        <StatCard label="Direction accuracy" icon={<Crosshair className="h-3.5 w-3.5" />} accent={MODEL_COLORS[key]} value={da != null ? <CountUp key={`${key}-${b.bank_id}-da`} value={da * 100} decimals={1} formatter={(v) => `${v.toFixed(1)}%`} /> : "—"} hint="share of days with the right sign" />
        <StatCard label="Test days" icon={<TrendingUp className="h-3.5 w-3.5" />} accent={bankColor(b.bank_id)} value={<CountUp key={`${b.bank_id}-n`} value={b.actual.length} />} hint={sector ? `Bank ${b.bank_id} · ${sector}` : `Bank ${b.bank_id}`} />
      </div>

      <ChartPanel title={`${BANK_NAME[key]} on Bank ${b.bank_id}`} subtitle="Daily log return · scroll to zoom, drag the timeline, or use the brush tool (top right)">
        <Chart option={option} height={400} notMerge />
      </ChartPanel>
    </Stagger>
  );
}
