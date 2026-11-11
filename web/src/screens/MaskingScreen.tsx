import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Eye, EyeOff, Landmark, Server, Sigma } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Segmented } from "@/components/ui/toggle-group";
import { Loading, NotAvailable, Reveal, SectionHeader, Stagger } from "@/components/primitives";
import { useData } from "@/lib/data";
import { BANK_COLORS, SERVER_COLOR, hexA } from "@/lib/theme";
import { int, sci, sciShort } from "@/lib/format";

type View = "bank" | "server";

const fmtSigned = (v: number, digits: number) => {
  const a = Math.abs(v);
  const s = a !== 0 && (a >= 1e5 || a < 1e-3) ? a.toExponential(digits - 1) : a.toFixed(digits);
  return `${v < 0 ? "−" : "+"}${s}`;
};

/** Number that scrambles its digits for a moment whenever its value changes. */
function Scramble({ value, digits, className }: { value: number; digits: number; className?: string }) {
  const final = fmtSigned(value, digits);
  const [text, setText] = useState(final);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      setText(final);
      return;
    }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setText(final);
      return;
    }
    let n = 0;
    const id = setInterval(() => {
      n++;
      if (n > 14) {
        clearInterval(id);
        setText(final);
        return;
      }
      setText(final.replace(/[0-9]/g, () => String(Math.floor(Math.random() * 10))));
    }, 45);
    return () => clearInterval(id);
  }, [final]);
  return <span className={className}>{text}</span>;
}

export default function MaskingScreen() {
  const { data, loading, missing } = useData("masking.json");
  const [view, setView] = useState<View>("bank");

  if (loading) return <Loading />;
  if (missing || !data) return <NotAvailable what="Masking example" file="masking.json" />;

  const server = view === "server";
  const labels = data.value_labels;

  return (
    <Stagger className="grid gap-7">
      <SectionHeader
        eyebrow="Step 6 · Scrambling updates"
        title={
          <>
            What the server <span className="text-gradient">actually sees</span>
          </>
        }
        subtitle={`Real weights from each bank's trained model (${data.n_values_shown} of ${data.n_values_total} output-layer values shown), masked with the project's own pairwise masker for round ${data.server_round}. Each bank sends n_i·w_i plus masks of scale ${sci(data.mask_scale, 1)} that cancel in the sum.`}
        right={
          <Segmented<View>
            layoutId="mask-view"
            size="lg"
            value={view}
            onChange={setView}
            options={[
              { value: "bank", label: <span className="flex items-center gap-2"><Eye className="h-4 w-4" /> Bank's view</span>, color: BANK_COLORS[0] },
              { value: "server", label: <span className="flex items-center gap-2"><EyeOff className="h-4 w-4" /> Server's view</span>, color: SERVER_COLOR },
            ]}
          />
        }
      />

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        {data.banks.map((b) => {
          const c = BANK_COLORS[b.bank_id];
          const values = server ? b.masked : b.real;
          return (
            <Reveal key={b.bank_id}>
              <motion.div whileHover={{ y: -3 }}>
                <Card glow={hexA(server ? SERVER_COLOR : c, 0.4)} className="overflow-hidden p-5 transition-shadow hover:shadow-glow">
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${server ? SERVER_COLOR : c}, transparent)` }} />
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Landmark className="h-[18px] w-[18px]" style={{ color: c }} />
                      <span className="font-display text-lg font-semibold text-white">Bank {b.bank_id}</span>
                    </div>
                    <span className="font-mono text-xs text-muted">n = {int(b.num_examples)}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {server ? "received: n·w + Σ masks" : "real weights w (output layer)"}
                  </div>
                  <div className="mt-4 grid gap-1.5">
                    {values.map((v, k) => (
                      <div key={k} className="flex items-baseline justify-between rounded-lg bg-ink-950/40 px-3 py-1.5">
                        <span className="font-mono text-[0.72rem] text-slate-500">{labels[k]}</span>
                        <Scramble
                          value={v}
                          digits={server ? 1 : 4}
                          className={`font-mono tabular-nums ${server ? "text-[1.15rem] text-server" : "text-[1rem] text-white"}`}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 text-xs text-muted">
                    {server ? (
                      <>masked update is <span className="font-mono text-slate-300">{b.masked_rel_distance.toFixed(0)}×</span> its real size away from n·w</>
                    ) : (
                      <>only this bank knows these values</>
                    )}
                  </div>
                </Card>
              </motion.div>
            </Reveal>
          );
        })}
      </div>

      <Reveal>
        <Card className="overflow-hidden p-6" glow={hexA("#4ADE80", 0.35)}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-server/40 bg-server/10">
                {server ? <Server className="h-5 w-5 text-server" /> : <Sigma className="h-5 w-5 text-server" />}
              </div>
              <div>
                <div className="font-display text-xl font-semibold text-white">Combined model update: Σ (n·w + masks) ÷ Σ n</div>
                <div className="text-sm text-muted">Σ n = {int(data.total_examples)} · identical in both views</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant="success" className="px-4 py-1.5 text-sm">
                <CheckCircle2 className="h-4 w-4" /> exact match
              </Badge>
              <span className="font-mono text-sm text-slate-300">max |difference| = {sciShort(data.max_abs_diff_avg, 2)}</span>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            {data.plain_avg.map((v, k) => (
              <div key={k} className="rounded-xl border border-white/[0.06] bg-ink-950/50 px-4 py-3">
                <div className="font-mono text-[0.72rem] text-slate-500">{labels[k]}</div>
                <div className="mt-1 font-mono text-lg text-white tabular-nums">{fmtSigned(server ? data.masked_avg[k] : v, 5)}</div>
              </div>
            ))}
          </div>
          <p className="mt-5 text-lg text-slate-200 presenter:text-xl">
            The server gets the correct total but never sees any single bank's real update.
          </p>
        </Card>
      </Reveal>
    </Stagger>
  );
}
