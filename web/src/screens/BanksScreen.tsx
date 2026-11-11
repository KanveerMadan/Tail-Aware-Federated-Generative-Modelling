import { useEffect, useState } from "react";
import { LayoutGroup, motion } from "framer-motion";
import { Landmark, RotateCcw } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loading, NotAvailable, Reveal, SectionHeader, Stagger, CountUp } from "@/components/primitives";
import { useData } from "@/lib/data";
import { bankColor, hexA } from "@/lib/theme";
import { fmtDate, int } from "@/lib/format";

export default function BanksScreen() {
  const { data, loading, missing } = useData("banks.json");
  const [split, setSplit] = useState(false);
  const [run, setRun] = useState(0);

  useEffect(() => {
    setSplit(false);
    const t = setTimeout(() => setSplit(true), 1100);
    return () => clearTimeout(t);
  }, [run]);

  if (loading) return <Loading />;
  if (missing || !data) return <NotAvailable what="Bank datasets" file="banks.json" />;

  const all = data.banks.flatMap((b) => b.tickers.map((t) => ({ t, b: b.bank_id })));
  const spring = { type: "spring" as const, stiffness: 120, damping: 18 };

  return (
    <Stagger className="grid gap-8">
      <SectionHeader
        eyebrow="Step 2 · Four banks"
        title={
          <>
            One market, <span className="text-gradient">four private vaults</span>
          </>
        }
        subtitle={`Each bank gets one sector, its own 4-year window and its own return transformation, so their data really differ (non-IID). Inputs are ${data.sequence_length}-day return windows; the target is the next day's return.`}
        right={
          <Button variant="glass" size="sm" onClick={() => setRun((r) => r + 1)}>
            <RotateCcw className="h-4 w-4" /> Replay
          </Button>
        }
      />

      <LayoutGroup>
        {/* The shared pool */}
        <Reveal>
          <Card className="flex min-h-[92px] flex-wrap items-center justify-center gap-2.5 px-6 py-5">
            {!split ? (
              all.map(({ t, b }) => (
                <motion.span
                  key={t}
                  layoutId={`tk-${t}`}
                  transition={spring}
                  className="rounded-lg border px-3 py-1 font-mono text-sm"
                  style={{ borderColor: hexA(bankColor(b), 0.35), color: bankColor(b), background: hexA(bankColor(b), 0.07) }}
                >
                  {t}
                </motion.span>
              ))
            ) : (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-muted">
                {int(all.length)} tickers distributed → each bank keeps its own
              </motion.span>
            )}
          </Card>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
          {data.banks.map((b, i) => {
            const c = bankColor(b.bank_id);
            const n = b.n_sequences;
            const total = (n.train ?? 0) + (n.val ?? 0) + (n.test ?? 0);
            return (
              <motion.div
                key={b.bank_id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                whileHover={{ y: -4 }}
              >
                <Card glow={hexA(c, 0.45)} className="h-full overflow-hidden p-6 transition-shadow hover:shadow-glow">
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${c}, transparent)` }} />
                  <div className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full opacity-20 blur-3xl" style={{ background: c }} />
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl border" style={{ borderColor: hexA(c, 0.45), background: hexA(c, 0.12) }}>
                        <Landmark className="h-5 w-5" style={{ color: c }} />
                      </div>
                      <div>
                        <div className="font-display text-xl font-semibold text-white">Bank {b.bank_id}</div>
                        <div className="text-sm" style={{ color: c }}>{b.sector}</div>
                      </div>
                    </div>
                    <div className="text-right font-mono text-xs text-muted">
                      {fmtDate(b.period[0])}
                      <br />→ {fmtDate(b.period[1])}
                    </div>
                  </div>

                  <div className="mt-5 flex min-h-[74px] flex-wrap content-start gap-2">
                    {split &&
                      b.tickers.map((t) => (
                        <motion.span
                          key={t}
                          layoutId={`tk-${t}`}
                          transition={spring}
                          className="rounded-lg border px-2.5 py-1 font-mono text-[0.8rem]"
                          style={{ borderColor: hexA(c, 0.35), color: c, background: hexA(c, 0.08) }}
                        >
                          {t}
                        </motion.span>
                      ))}
                  </div>

                  <div className="mt-2 rounded-xl border border-white/[0.06] bg-ink-950/40 px-4 py-3 text-sm text-slate-300">
                    {b.description}
                  </div>

                  <div className="mt-5">
                    <div className="flex items-baseline justify-between">
                      <span className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted">Samples</span>
                      <span className="font-mono text-2xl text-white tabular-nums">
                        <CountUp value={total} />
                      </span>
                    </div>
                    <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-white/[0.06]">
                      {(["train", "val", "test"] as const).map((k, j) => (
                        <motion.div
                          key={k}
                          initial={{ width: 0 }}
                          animate={{ width: `${total ? ((n[k] ?? 0) / total) * 100 : 0}%` }}
                          transition={{ delay: 0.6 + i * 0.1 + j * 0.1, duration: 0.8 }}
                          style={{ background: hexA(c, [0.9, 0.55, 0.3][j]) }}
                        />
                      ))}
                    </div>
                    <div className="mt-2 flex justify-between font-mono text-xs text-muted">
                      <span>train {int(n.train)}</span>
                      <span>val {int(n.val)}</span>
                      <span>test {int(n.test)}</span>
                    </div>
                  </div>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </LayoutGroup>
    </Stagger>
  );
}
