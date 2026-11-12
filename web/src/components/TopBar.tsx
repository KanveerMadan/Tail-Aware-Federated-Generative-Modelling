import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Code2, Maximize2, Minimize2, Network } from "lucide-react";
import { STEPS, useUI } from "@/lib/store";
import { Tip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function TopBar({ stepIndex, onPresenter }: { stepIndex: number | null; onPresenter: () => void }) {
  const presenter = useUI((s) => s.presenter);
  const setHoodOpen = useUI((s) => s.setHoodOpen);
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-900/70 backdrop-blur-xl">
      <div className="mx-auto flex h-[68px] max-w-[1680px] items-center gap-6 px-8">
        <Link to="/" className="group flex shrink-0 items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-gradient-to-br from-server/30 to-violet-500/20 shadow-glow">
            <Network className="h-[18px] w-[18px] text-white" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-[0.98rem] font-semibold tracking-tight text-white">Tail-Aware FL</div>
            <div className="text-[0.68rem] uppercase tracking-[0.18em] text-muted">Federated Generative Modelling</div>
          </div>
        </Link>

        {/* Step progress */}
        <div className="flex min-w-0 flex-1 justify-center">
        {stepIndex != null && !presenter && (
        <nav className="hidden min-w-0 items-center justify-center gap-1 lg:flex" aria-label="Walkthrough steps">
          {STEPS.map((s, i) => {
            const active = i === stepIndex;
            const done = stepIndex != null && i < stepIndex;
            return (
              <button
                key={s.id}
                onClick={() => navigate(`/story/${s.id}`)}
                className={cn(
                  "group relative flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[0.78rem] font-medium transition-colors",
                  active ? "text-white" : done ? "text-slate-300 hover:text-white" : "text-slate-500 hover:text-slate-300"
                )}
              >
                {active && (
                  <motion.span
                    layoutId="step-pill"
                    className="absolute inset-0 rounded-lg border border-white/10 bg-white/[0.07]"
                    transition={{ type: "spring", stiffness: 420, damping: 36 }}
                  />
                )}
                <span
                  className={cn(
                    "relative flex h-5 w-5 items-center justify-center rounded-full font-mono text-[0.64rem]",
                    active ? "bg-server text-ink-950" : done ? "bg-white/15 text-white" : "bg-white/[0.06] text-slate-500"
                  )}
                >
                  {i + 1}
                </span>
                <span className="relative hidden xl:inline">{s.short}</span>
              </button>
            );
          })}
        </nav>
        )}
        {presenter && stepIndex != null && (
          <div className="font-mono text-base text-slate-300">
            <span className="text-white">{stepIndex + 1}</span> / {STEPS.length} · {STEPS[stepIndex].label}
          </div>
        )}
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <Tip content="Every number on this site is read from JSON exported from the pipeline outputs. Nothing is fetched or trained in the browser.">
            <div className="flex items-center gap-2 rounded-full border border-better/25 bg-better/[0.07] px-3.5 py-1.5 text-xs font-medium text-better">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-better opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-better" />
              </span>
              Running 100% locally
            </div>
          </Tip>
          {stepIndex != null && (
            <Tip content="Under the hood: command + source for this step">
              <button
                onClick={() => setHoodOpen(true)}
                className="presenter-hide flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-slate-300 transition hover:border-white/20 hover:bg-white/[0.09] hover:text-white"
                aria-label="Under the hood"
              >
                <Code2 className="h-4 w-4" />
              </button>
            </Tip>
          )}
          <button
            onClick={onPresenter}
            className="flex h-9 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3.5 text-sm text-slate-200 transition hover:border-server/40 hover:bg-server/10 hover:text-white"
          >
            {presenter ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            {presenter ? "Exit presenter" : "Presenter mode"}
          </button>
        </div>
      </div>
    </header>
  );
}
