import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CalendarRange, Database, LineChart } from "lucide-react";
import { Chart, axisBase, tooltipBase } from "@/components/Chart";
import { ChartPanel, CountUp, Loading, NotAvailable, SectionHeader, Stagger, StatCard, Reveal } from "@/components/primitives";
import { Badge } from "@/components/ui/badge";
import { useData } from "@/lib/data";
import { bankColor, hexA } from "@/lib/theme";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function DataScreen() {
  const { data: prices, loading, missing } = useData("prices.json");
  const { data: source } = useData("source.json");
  const [bank, setBank] = useState(0);

  const b = prices?.banks.find((x) => x.bank_id === bank) ?? prices?.banks[0];

  const option = useMemo(() => {
    if (!b) return {};
    const color = bankColor(b.bank_id);
    // Rebase every ticker to 100 so different price levels share one axis
    const series = b.series.map((s, i) => {
      const base = s.close[0] || 1;
      const shade = [1, 0.8, 0.62, 0.48, 0.36][i % 5];
      return {
        name: s.ticker,
        type: "line" as const,
        showSymbol: false,
        smooth: 0.2,
        lineStyle: { width: i === 0 ? 2.4 : 1.6, color: hexA(color, shade) },
        itemStyle: { color: hexA(color, shade) },
        areaStyle:
          i === 0
            ? {
                color: {
                  type: "linear" as const, x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: hexA(color, 0.28) },
                    { offset: 1, color: hexA(color, 0) },
                  ],
                },
              }
            : undefined,
        emphasis: { focus: "series" as const },
        data: s.dates.map((d, k) => [d, +((s.close[k] / base) * 100).toFixed(2)]),
      };
    });
    return {
      animationDuration: 1600,
      grid: { left: 56, right: 24, top: 40, bottom: 70 },
      legend: { top: 0, right: 10, textStyle: { color: "#CBD5E1", fontFamily: "JetBrains Mono" }, icon: "roundRect", itemWidth: 14, itemHeight: 4 },
      tooltip: {
        ...tooltipBase,
        trigger: "axis" as const,
        valueFormatter: (v: unknown) => `${Number(v).toFixed(1)}`,
      },
      xAxis: { type: "time" as const, ...axisBase, splitLine: { show: false } },
      yAxis: { type: "value" as const, ...axisBase, name: "rebased to 100", nameGap: 14, scale: true },
      dataZoom: [
        { type: "inside" as const },
        {
          type: "slider" as const, height: 22, bottom: 14, borderColor: "rgba(255,255,255,0.08)",
          backgroundColor: "rgba(255,255,255,0.02)", fillerColor: hexA(color, 0.12),
          dataBackground: { lineStyle: { color: hexA(color, 0.5) }, areaStyle: { color: hexA(color, 0.08) } },
          handleStyle: { color: color }, textStyle: { color: "#8B97B1" },
        },
      ],
      series,
    };
  }, [b]);

  if (loading) return <Loading />;
  if (missing || !prices || !b) return <NotAvailable what="Price data" file="prices.json" />;

  const sourceLabel = source?.kind === "real" ? "Real prices" : source?.kind === "synthetic" ? "Synthetic prices" : "Prices";

  return (
    <Stagger className="grid gap-7">
      <SectionHeader
        eyebrow="Step 1 · The data"
        title={
          <>
            {sourceLabel} for <span className="text-gradient">{prices.n_tickers} stocks</span>
          </>
        }
        subtitle={
          source?.lines?.[1]
            ? `${source.lines[1]}. Each bank only ever sees its own sector and time window.`
            : "Each bank only ever sees its own sector and time window."
        }
        right={
          source && (
            <Badge variant={source.kind === "real" ? "success" : "server"} className="px-4 py-1.5 text-sm">
              <Database className="h-3.5 w-3.5" />
              {source.kind === "real" ? "Real · Yahoo Finance" : source.kind === "synthetic" ? "Synthetic (GBM)" : source.kind}
            </Badge>
          )
        }
      />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <StatCard label="Tickers" icon={<LineChart className="h-3.5 w-3.5" />} value={<CountUp value={prices.n_tickers} />} hint={`${prices.banks.length} sectors × ${prices.banks[0]?.series.length ?? 0} stocks`} accent="#22D3EE" />
        <StatCard label="Trading days" icon={<CalendarRange className="h-3.5 w-3.5" />} value={<CountUp value={prices.n_trading_days} />} hint="distinct dates across all banks" accent="#A78BFA" />
        <StatCard label="Date range" icon={<CalendarRange className="h-3.5 w-3.5" />} value={<span className="text-[1.55rem]">{fmtDate(prices.start)} → {fmtDate(prices.end)}</span>} hint="each bank covers a different 4-year window" accent="#FBBF24" />
      </div>

      <ChartPanel
        title={`${b.name ?? `Bank ${b.bank_id}`} · ${b.sector ?? ""}`}
        subtitle={`${fmtDate(String(b.start))} → ${fmtDate(String(b.end))} · scroll or drag the slider to zoom`}
        right={
          <div className="flex flex-wrap gap-2">
            {prices.banks.map((x) => {
              const c = bankColor(x.bank_id);
              const active = x.bank_id === b.bank_id;
              return (
                <button
                  key={x.bank_id}
                  onClick={() => setBank(x.bank_id)}
                  className={cn("rounded-xl border px-3.5 py-1.5 text-sm font-medium transition-all", active ? "text-white" : "border-white/10 text-slate-400 hover:text-slate-200")}
                  style={active ? { borderColor: hexA(c, 0.5), background: hexA(c, 0.14), boxShadow: `0 0 24px -8px ${c}` } : undefined}
                >
                  {x.sector ?? `Bank ${x.bank_id}`}
                </button>
              );
            })}
          </div>
        }
      >
        <Chart option={option} height={370} notMerge />
      </ChartPanel>

      <Reveal>
        <div className="flex flex-wrap items-center gap-2.5">
          {prices.banks.flatMap((x) =>
            x.series.map((s, i) => (
              <motion.span
                key={s.ticker}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 + (x.bank_id * 5 + i) * 0.03 }}
                whileHover={{ y: -2 }}
                className="rounded-lg border px-3 py-1 font-mono text-sm"
                style={{ borderColor: hexA(bankColor(x.bank_id), 0.35), color: bankColor(x.bank_id), background: hexA(bankColor(x.bank_id), 0.07) }}
              >
                {s.ticker}
              </motion.span>
            ))
          )}
        </div>
      </Reveal>
    </Stagger>
  );
}
