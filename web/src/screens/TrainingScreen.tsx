import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Cpu, Merge, RefreshCw, Send, Server } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Loading, NotAvailable, Reveal, SectionHeader, Stagger } from "@/components/primitives";
import { useData } from "@/lib/data";
import { BANK_COLORS, SERVER_COLOR, hexA } from "@/lib/theme";
import { cn } from "@/lib/utils";

const PHASE_MS = 2300;

export default function TrainingScreen() {
  const { data: settings, loading, missing } = useData("settings.json");
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setPhase((p) => (p + 1) % 4), PHASE_MS);
    return () => clearInterval(t);
  }, []);

  if (loading) return <Loading />;
  if (missing || !settings) return <NotAvailable what="Settings" file="settings.json" />;

  const cfg = settings.config;
  const phases = [
    { icon: <Cpu className="h-5 w-5" />, t: "1 · Train locally", d: `Each bank runs ${cfg.training.local_epochs} epochs of Adam (lr ${cfg.training.lr}) on its own windows, with ${cfg.training.loss_type} loss. FedProx adds μ/2·‖w − w_global‖² (μ = ${cfg.federated.mu}) to stay close to the global model.` },
    { icon: <Send className="h-5 w-5" />, t: "2 · Send masked update", d: "Each bank sends n_i · w_i plus a pairwise random mask. Its raw data never leave the bank." },
    { icon: <Merge className="h-5 w-5" />, t: "3 · Combine", d: "The server adds the four masked updates: the masks cancel, and dividing by Σ n_i gives the FedAvg weighted mean." },
    { icon: <RefreshCw className="h-5 w-5" />, t: "4 · Send back", d: `The new global model goes back to every bank. Repeat for ${cfg.federated.n_rounds} rounds.` },
  ];

  // Layout (percent of the stage)
  const banks = [0, 1, 2, 3].map((i) => ({ x: 12, y: 14 + i * 24 }));
  const server = { x: 82, y: 50 };

  return (
    <Stagger className="grid gap-8">
      <SectionHeader
        eyebrow="Step 4 · How training works"
        title={
          <>
            Train locally, <span className="text-gradient">combine centrally</span>
          </>
        }
        subtitle={`A ${cfg.model.n_layers}-layer Transformer (${cfg.model.embed_dim}-dim, ${cfg.model.n_heads} heads) predicts tomorrow's return from the last ${cfg.data.sequence_length} days. One loop of four steps is one federated round.`}
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_1fr]">
        <Reveal>
          <Card className="relative h-[480px] overflow-hidden">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              {banks.map((b, i) => (
                <line key={i} x1={b.x + 7} y1={b.y} x2={server.x - 7} y2={server.y} stroke={hexA(BANK_COLORS[i], 0.5)} strokeWidth={1.5} vectorEffect="non-scaling-stroke" className={phase === 1 || phase === 3 ? "edge-flow" : ""} />
              ))}
            </svg>

            {banks.map((b, i) => {
              const c = BANK_COLORS[i];
              return (
                <div key={i} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${b.x}%`, top: `${b.y}%` }}>
                  <motion.div
                    animate={phase === 0 ? { boxShadow: [`0 0 0px ${c}`, `0 0 34px ${c}`, `0 0 0px ${c}`] } : { boxShadow: `0 0 0px ${c}` }}
                    transition={{ duration: 1.1, repeat: phase === 0 ? Infinity : 0 }}
                    className="flex w-[150px] items-center gap-3 rounded-2xl border bg-ink-900/90 px-4 py-3"
                    style={{ borderColor: hexA(c, 0.5) }}
                  >
                    <div className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
                    <div>
                      <div className="font-display text-sm font-semibold text-white">Bank {i}</div>
                      <div className="font-mono text-[0.68rem] text-muted">{phase === 0 ? "training…" : phase === 3 ? "receiving" : "idle"}</div>
                    </div>
                  </motion.div>
                </div>
              );
            })}

            <div className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${server.x}%`, top: `${server.y}%` }}>
              <motion.div
                animate={phase === 2 ? { scale: [1, 1.08, 1] } : { scale: 1 }}
                transition={{ duration: 0.8, repeat: phase === 2 ? Infinity : 0 }}
                className="flex h-[140px] w-[140px] flex-col items-center justify-center rounded-3xl border bg-ink-900/90"
                style={{ borderColor: hexA(SERVER_COLOR, 0.6), boxShadow: `0 0 ${phase === 2 ? 60 : 30}px -10px ${SERVER_COLOR}` }}
              >
                <Server className="h-8 w-8 text-server" />
                <div className="mt-2 font-display text-sm font-semibold text-white">Server</div>
                <div className="font-mono text-[0.68rem] text-muted">{phase === 2 ? "Σ masked / Σ n" : "global model"}</div>
              </motion.div>
            </div>

            {/* packets */}
            <AnimatePresence>
              {(phase === 1 || phase === 3) &&
                banks.map((b, i) => {
                  const from = phase === 1 ? { x: b.x + 7, y: b.y } : { x: server.x - 7, y: server.y };
                  const to = phase === 1 ? { x: server.x - 7, y: server.y } : { x: b.x + 7, y: b.y };
                  const c = phase === 1 ? BANK_COLORS[i] : SERVER_COLOR;
                  return (
                    <motion.div
                      key={`${phase}-${i}`}
                      className="absolute h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                      style={{ background: c, boxShadow: `0 0 18px 4px ${c}` }}
                      initial={{ left: `${from.x}%`, top: `${from.y}%`, opacity: 0, scale: 0.4 }}
                      animate={{ left: `${to.x}%`, top: `${to.y}%`, opacity: [0, 1, 1, 0], scale: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 1.6, delay: i * 0.12, ease: "easeInOut" }}
                    />
                  );
                })}
            </AnimatePresence>
          </Card>
        </Reveal>

        <div className="grid gap-4">
          {phases.map((p, i) => (
            <Reveal key={p.t}>
              <button onClick={() => setPhase(i)} className="w-full text-left">
                <Card
                  className={cn("p-5 transition-all duration-300", phase === i ? "border-server/40" : "opacity-60 hover:opacity-90")}
                  style={phase === i ? { boxShadow: `0 0 40px -14px ${SERVER_COLOR}` } : undefined}
                >
                  <div className={cn("flex items-center gap-3 font-display text-lg font-semibold", phase === i ? "text-white" : "text-slate-300")}>
                    <span className={phase === i ? "text-server" : "text-slate-500"}>{p.icon}</span>
                    {p.t}
                  </div>
                  <p className="mt-2 text-[0.95rem] leading-relaxed text-slate-300">{p.d}</p>
                  {phase === i && (
                    <motion.div className="mt-3 h-0.5 rounded-full bg-server" initial={{ width: "0%" }} animate={{ width: "100%" }} transition={{ duration: PHASE_MS / 1000, ease: "linear" }} />
                  )}
                </Card>
              </button>
            </Reveal>
          ))}
        </div>
      </div>
    </Stagger>
  );
}
