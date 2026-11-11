import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ban, Landmark, Lock, LockOpen, Scale, ShieldAlert, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Loading, NotAvailable, Reveal, SectionHeader, Stagger } from "@/components/primitives";
import { useData } from "@/lib/data";
import { bankColor, hexA } from "@/lib/theme";
import { int } from "@/lib/format";

export default function ProblemScreen() {
  const { data, loading, missing } = useData("banks.json");
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLocked(true), 700);
    return () => clearTimeout(t);
  }, []);

  if (loading) return <Loading />;
  if (missing || !data) return <NotAvailable what="Bank datasets" file="banks.json" />;

  return (
    <Stagger className="grid gap-10">
      <SectionHeader
        eyebrow="Step 3 · The problem"
        title={
          <>
            Banks can't share raw data, <br />
            <span className="text-gradient">but want a better model.</span>
          </>
        }
        subtitle="Client positions and trading histories are confidential and regulated. Each bank alone has a small, biased slice of the market."
      />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        {data.banks.map((b, i) => {
          const c = bankColor(b.bank_id);
          return (
            <motion.div key={b.bank_id} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
              <Card className="relative h-[230px] overflow-hidden p-6">
                <div className="flex items-center gap-3">
                  <Landmark className="h-5 w-5" style={{ color: c }} />
                  <span className="font-display text-lg font-semibold text-white">Bank {b.bank_id}</span>
                  <span className="text-sm" style={{ color: c }}>{b.sector}</span>
                </div>
                <div className="mt-4 font-mono text-sm text-muted">{int(b.n_sequences.train)} training windows</div>

                {/* Vault door */}
                <div className="absolute inset-x-6 bottom-6 top-[96px] flex items-center justify-center">
                  <motion.div
                    className="relative flex h-full w-full items-center justify-center rounded-2xl border"
                    animate={{
                      borderColor: locked ? hexA(c, 0.6) : "rgba(255,255,255,0.08)",
                      background: locked ? hexA(c, 0.1) : "rgba(255,255,255,0.02)",
                      boxShadow: locked ? `0 0 40px -10px ${c}, inset 0 0 30px -16px ${c}` : "0 0 0 0 transparent",
                    }}
                    transition={{ delay: 0.15 * i, duration: 0.6 }}
                  >
                    {/* bars that slide shut */}
                    {[0, 1, 2].map((k) => (
                      <motion.div
                        key={k}
                        className="absolute left-0 h-[2px] rounded-full"
                        style={{ top: `${28 + k * 22}%`, background: hexA(c, 0.55) }}
                        initial={{ width: "0%" }}
                        animate={{ width: locked ? "100%" : "0%" }}
                        transition={{ delay: 0.25 + 0.15 * i + k * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                      />
                    ))}
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={locked ? "l" : "u"}
                        initial={{ scale: 0.4, rotate: -30, opacity: 0 }}
                        animate={{ scale: 1, rotate: 0, opacity: 1 }}
                        exit={{ scale: 0.4, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 260, damping: 15, delay: locked ? 0.4 + 0.15 * i : 0 }}
                        className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full border bg-ink-900"
                        style={{ borderColor: hexA(c, 0.6) }}
                      >
                        {locked ? <Lock className="h-6 w-6" style={{ color: c }} /> : <LockOpen className="h-6 w-6 text-slate-500" />}
                      </motion.div>
                    </AnimatePresence>
                  </motion.div>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {[
          { icon: <Ban className="h-5 w-5" />, t: "Pooling is off the table", d: "A central dataset of every bank's history would be a privacy, legal and competitive non-starter.", c: "#F87171" },
          { icon: <ShieldAlert className="h-5 w-5" />, t: "Alone, each model is narrow", d: "One sector, one time window: a local model never sees the regimes other banks lived through.", c: "#FBBF24" },
          { icon: <Sparkles className="h-5 w-5" />, t: "Goal: share learning, not data", d: "Send only model updates, scrambled so the server learns the combined model and nothing about any single bank.", c: "#4ADE80" },
        ].map((x, i) => (
          <Reveal key={x.t}>
            <motion.div whileHover={{ y: -3 }}>
              <Card className="h-full p-6">
                <div className="flex items-center gap-3" style={{ color: x.c }}>
                  {x.icon}
                  <span className="font-display text-lg font-semibold text-white">{x.t}</span>
                </div>
                <p className="mt-3 text-[0.98rem] leading-relaxed text-slate-300">{x.d}</p>
                {i === 2 && (
                  <div className="mt-4 inline-flex items-center gap-2 text-sm text-better">
                    <Scale className="h-4 w-4" /> Federated learning + secure aggregation
                  </div>
                )}
              </Card>
            </motion.div>
          </Reveal>
        ))}
      </div>
    </Stagger>
  );
}
