import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Lock, Network, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/primitives";
import { useData } from "@/lib/data";
import { STEPS } from "@/lib/store";
import { BANK_COLORS, SERVER_COLOR } from "@/lib/theme";
import { int } from "@/lib/format";

const ease = [0.22, 1, 0.36, 1] as const;

// Project name as presented (second line gets the gradient)
const TITLE_LINES = ["Tail-Aware Federated Generative Modelling", "of Financial Markets"];
const PROJECT_NAME = "Tail-Aware Federated Generative Modelling";

export default function Landing() {
  const navigate = useNavigate();
  const { data: settings } = useData("settings.json");
  const { data: prices } = useData("prices.json");
  const { data: source } = useData("source.json");
  const { data: fed } = useData("federated.json");

  const nRounds = fed?.strategies.fedprox?.n_rounds ?? fed?.strategies.fedavg?.n_rounds;

  const facts = [
    prices && { k: "Tickers", v: int(prices.n_tickers) },
    prices && { k: "Trading days", v: int(prices.n_trading_days) },
    settings && { k: "Banks", v: int(settings.config.data.n_banks) },
    nRounds != null && { k: "Federated rounds", v: int(nRounds) },
    settings?.n_parameters != null && { k: "Model parameters", v: int(settings.n_parameters) },
  ].filter(Boolean) as { k: string; v: string }[];

  return (
    <section className="relative mx-auto flex min-h-[calc(100vh-68px)] max-w-[1680px] flex-col justify-center px-8 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease }}
        className="mb-8 flex flex-wrap items-center gap-3"
      >
        <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-sm text-slate-300 backdrop-blur">
          <Network className="h-4 w-4 text-server" />
          {PROJECT_NAME}
        </span>
        {source && (
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-sm text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-better" />
            {source.kind === "real" ? "Real market data · Yahoo Finance" : source.kind === "synthetic" ? "Synthetic market data" : "Data source recorded"}
          </span>
        )}
      </motion.div>

      <h1 className="font-display text-[clamp(2.5rem,4.2vw,4.75rem)] font-semibold leading-[1.06] tracking-[-0.035em] text-white">
        {TITLE_LINES.map((line, li) => {
          const offset = TITLE_LINES.slice(0, li).reduce((n, l) => n + l.split(" ").length, 0);
          return (
            <span key={li} className="block">
              {line.split(" ").map((w, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, y: 40, filter: "blur(10px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ duration: 0.9, delay: 0.15 + (offset + i) * 0.07, ease }}
                  className={li === TITLE_LINES.length - 1 ? "text-gradient mr-[0.25em] inline-block pb-[0.08em]" : "mr-[0.25em] inline-block"}
                >
                  {w}
                </motion.span>
              ))}
            </span>
          );
        })}
      </h1>

      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.75, ease }}
        className="mt-8 max-w-3xl text-xl leading-relaxed text-slate-300 presenter:text-2xl"
      >
        Four banks train one shared Transformer on stock returns, without ever sharing their raw data, and the server only
        sees scrambled updates.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.9, ease }}
        className="mt-12 flex flex-wrap items-center gap-5"
      >
        <Button size="lg" variant="primary" onClick={() => navigate(`/story/${STEPS[0].id}`)}>
          Start the walkthrough <ArrowRight className="h-5 w-5" />
        </Button>
        <Button size="lg" variant="glass" onClick={() => navigate("/story/rounds")}>
          Jump to federated rounds
        </Button>
        <span className="presenter-hide flex items-center gap-2 text-sm text-muted">
          or press <Kbd>→</Kbd>
        </span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.1 }}
        className="mt-20 flex flex-wrap items-end justify-between gap-10"
      >
        <dl className="flex flex-wrap gap-x-12 gap-y-6">
          {facts.map((f) => (
            <div key={f.k}>
              <dt className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-muted">{f.k}</dt>
              <dd className="mt-2 font-mono text-3xl text-white tabular-nums">{f.v}</dd>
            </div>
          ))}
        </dl>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            {BANK_COLORS.map((c, i) => (
              <motion.div
                key={c}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 1.2 + i * 0.08, type: "spring", stiffness: 300, damping: 18 }}
                className="flex h-11 w-11 items-center justify-center rounded-xl border"
                style={{ borderColor: `${c}55`, background: `${c}14`, boxShadow: `0 0 24px -8px ${c}` }}
              >
                <Lock className="h-4 w-4" style={{ color: c }} />
              </motion.div>
            ))}
          </div>
          <div className="h-px w-14 bg-gradient-to-r from-white/30 to-server" />
          <div
            className="flex h-12 w-12 items-center justify-center rounded-2xl border"
            style={{ borderColor: `${SERVER_COLOR}66`, background: `${SERVER_COLOR}18`, boxShadow: `0 0 30px -6px ${SERVER_COLOR}` }}
          >
            <ShieldCheck className="h-5 w-5 text-server" />
          </div>
          {settings?.team && <div className="ml-4 text-sm text-muted">{settings.team}</div>}
        </div>
      </motion.div>
    </section>
  );
}
