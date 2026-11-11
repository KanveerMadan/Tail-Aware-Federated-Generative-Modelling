import { motion } from "framer-motion";
import { CheckCircle2, Dices, KeyRound, Scale, ShieldCheck, Target, TrendingDown, TriangleAlert } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Loading, NotAvailable, Reveal, SectionHeader, Stagger } from "@/components/primitives";
import { useData } from "@/lib/data";
import { BETTER, WORSE } from "@/lib/theme";
import { int, sci, sciShort, signedPct } from "@/lib/format";

interface Item {
  icon: JSX.Element;
  title: string;
  body: string;
  stat?: string;
  statLabel?: string;
}

function Column({ title, tone, items }: { title: string; tone: "good" | "limit"; items: Item[] }) {
  const c = tone === "good" ? BETTER : WORSE;
  return (
    <div className="grid content-start gap-4">
      <Reveal>
        <div className="flex items-center gap-3 font-display text-2xl font-semibold text-white">
          {tone === "good" ? <CheckCircle2 className="h-6 w-6" style={{ color: c }} /> : <TriangleAlert className="h-6 w-6" style={{ color: c }} />}
          {title}
        </div>
      </Reveal>
      {items.map((it) => (
        <Reveal key={it.title}>
          <motion.div whileHover={{ y: -3 }}>
            <Card className="flex items-start gap-5 p-6">
              <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border" style={{ borderColor: `${c}44`, background: `${c}12`, color: c }}>
                {it.icon}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-display text-lg font-semibold text-white">{it.title}</div>
                <p className="mt-1.5 text-[0.98rem] leading-relaxed text-slate-300">{it.body}</p>
              </div>
              {it.stat && (
                <div className="shrink-0 text-right">
                  <div className="font-mono text-2xl tabular-nums text-white">{it.stat}</div>
                  {it.statLabel && <div className="mt-1 text-xs text-muted">{it.statLabel}</div>}
                </div>
              )}
            </Card>
          </motion.div>
        </Reveal>
      ))}
    </div>
  );
}

export default function TakeawaysScreen() {
  const { data: summary, loading, missing } = useData("summary.json");
  const { data: masking } = useData("masking.json");
  const { data: settings } = useData("settings.json");
  const { data: fed } = useData("federated.json");

  if (loading) return <Loading />;
  if (missing || !summary) return <NotAvailable what="Summary" file="summary.json" />;

  const bf = summary.best_federated;
  const name = bf === "fedavg" ? "FedAvg" : bf === "fedprox" ? "FedProx" : "Federated";
  const mse = bf ? summary.comparisons.mse?.[bf] : undefined;
  const var95 = bf ? summary.comparisons.var_95_error?.[bf] : undefined;
  const rounds = summary.rounds ?? {};
  const totalRounds = Object.values(rounds).reduce((a, r) => a + (r?.n_rounds ?? 0), 0);
  const totalFailures = Object.values(rounds).reduce((a, r) => a + (r?.total_failures ?? 0), 0);
  const allComplete = Object.values(rounds).every((r) => r?.all_results);
  const nClients = fed?.strategies.fedavg?.n_clients ?? fed?.strategies.fedprox?.n_clients;

  const good: Item[] = [];
  if (mse?.vs_centralized_pct != null) {
    good.push({
      icon: <Scale className="h-5 w-5" />,
      title: `${name} matches centralized, without pooling data`,
      body: `Pooled test MSE is within ${Math.abs(mse.vs_centralized_pct).toFixed(1)}% of a model trained on all banks' data in one place (${mse.vs_centralized_pct <= 0 ? "slightly better" : "slightly worse"}). No bank ever sent a single return.`,
      stat: signedPct(mse.vs_centralized_pct),
      statLabel: "MSE vs centralized",
    });
  }
  if (masking) {
    good.push({
      icon: <ShieldCheck className="h-5 w-5" />,
      title: "The masking simulation works",
      body: `Masked updates sum to the true weighted average (max difference ${sci(masking.max_abs_diff_avg, 2)}), while each single masked update is about ${Math.round(Math.min(...masking.banks.map((b) => b.masked_rel_distance)))}× its own size away from the real value.`,
      stat: sciShort(masking.max_abs_diff_avg, 2),
      statLabel: "max |error|",
    });
  }
  if (totalRounds > 0) {
    good.push({
      icon: <CheckCircle2 className="h-5 w-5" />,
      title: allComplete && totalFailures === 0 ? "Every round completed cleanly" : "Some rounds were incomplete",
      body: `${int(totalRounds)} federated rounds across FedAvg and FedProx, each with ${nClients ?? "all"} results and ${int(totalFailures)} failures in total. The run stops loudly if a bank drops out.`,
      stat: `${int(totalFailures)}`,
      statLabel: "failures",
    });
  }

  const limits: Item[] = [];
  if (mse?.vs_local_ensemble_pct != null && var95?.vs_local_ensemble_pct != null) {
    const both = mse.vs_local_ensemble_pct >= 0 && var95.vs_local_ensemble_pct >= 0;
    limits.push({
      icon: <Target className="h-5 w-5" />,
      title: both ? "It doesn't beat the local ensemble" : "No clear win over the local ensemble",
      body: `Against each bank's own local model: MSE ${signedPct(mse.vs_local_ensemble_pct)}, but VaR(95) error ${signedPct(var95.vs_local_ensemble_pct)}. Specialised local models still capture each bank's tails better.`,
      stat: signedPct(var95.vs_local_ensemble_pct),
      statLabel: "VaR(95) err vs local",
    });
  }
  if (mse?.vs_zero_pct != null) {
    const cz = summary.comparisons.mse?.centralized_vs_zero_pct;
    limits.push({
      icon: <TrendingDown className="h-5 w-5" />,
      title: "Gain over predicting 0 is modest",
      body: `Always predicting a 0% return is a hard baseline for daily returns. ${name} lowers MSE by ${Math.abs(mse.vs_zero_pct).toFixed(1)}%${cz != null ? `, centralized by ${Math.abs(cz).toFixed(1)}%` : ""}: useful signal, not a crystal ball.`,
      stat: signedPct(mse.vs_zero_pct),
      statLabel: "MSE vs predict-0",
    });
  }
  limits.push({
    icon: <Dices className="h-5 w-5" />,
    title: "Single seed, single run",
    body: `Every number here comes from one run (random_seed = ${settings?.config.random_seed ?? "?"}). Differences of a few percent between models may be noise; repeated seeds would be needed for confidence intervals.`,
  });
  limits.push({
    icon: <KeyRound className="h-5 w-5" />,
    title: "Masking is a simulation",
    body: "Pairwise seeds are handed out by the launch script: no real key exchange, no dropout recovery, real-valued masks, and protection only against an honest-but-curious server (see docs/threat_model.md).",
  });

  return (
    <Stagger className="grid gap-8">
      <SectionHeader
        eyebrow="Step 9 · Honest takeaways"
        title={
          <>
            What worked, <span className="text-gradient">what didn't</span>
          </>
        }
        subtitle="Every number on this slide is computed from the exported results, not typed in."
      />
      <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
        <Column title="What works" tone="good" items={good} />
        <Column title="Limitations" tone="limit" items={limits} />
      </div>
    </Stagger>
  );
}
