import * as React from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import CountUpLib from "react-countup";
import { DatabaseZap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

export const rise: Variants = {
  hidden: { opacity: 0, y: 22, filter: "blur(6px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

/** Wrap a screen's content: staggered fade/slide of each direct <Reveal>. */
export function Stagger({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div variants={stagger} initial="hidden" animate="show" className={className}>
      {children}
    </motion.div>
  );
}

export function Reveal({ children, className, delay }: { children: React.ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div variants={rise} className={className} transition={delay ? { delay } : undefined}>
      {children}
    </motion.div>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  right,
  className,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div variants={rise} className={cn("flex flex-wrap items-end justify-between gap-6", className)}>
      <div className="max-w-4xl">
        {eyebrow && (
          <div className="mb-3 flex items-center gap-3 text-[0.78rem] font-semibold uppercase tracking-[0.22em] text-server/90">
            <span className="h-px w-8 bg-gradient-to-r from-server to-transparent" />
            {eyebrow}
          </div>
        )}
        <h1 className="font-display text-display font-semibold text-white">{title}</h1>
        {subtitle && <p className="mt-4 max-w-3xl text-lg leading-relaxed text-slate-300/90 presenter:text-xl">{subtitle}</p>}
      </div>
      {right && <div className="flex items-center gap-3">{right}</div>}
    </motion.div>
  );
}

export function CountUp({
  value,
  decimals = 0,
  duration = 1.6,
  formatter,
  className,
}: {
  value: number;
  decimals?: number;
  duration?: number;
  formatter?: (v: number) => string;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <CountUpLib
      end={value}
      decimals={decimals}
      duration={reduce ? 0 : duration}
      separator=","
      preserveValue
      formattingFn={formatter}
      className={className}
    />
  );
}

export function StatCard({
  label,
  value,
  hint,
  accent = "#F472B6",
  icon,
  className,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: string;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div variants={rise} whileHover={{ y: -3 }} transition={{ type: "spring", stiffness: 300, damping: 24 }} className={className}>
      <Card className="group h-full overflow-hidden px-6 py-5 transition-colors hover:border-white/15">
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-25 blur-3xl transition-opacity group-hover:opacity-45"
          style={{ background: accent }}
        />
        <div className="flex items-center gap-2 text-[0.72rem] font-semibold uppercase tracking-[0.16em] text-muted">
          {icon && <span style={{ color: accent }}>{icon}</span>}
          {label}
        </div>
        <div className="mt-3 font-mono text-[2.1rem] font-medium leading-none tracking-tight text-white tabular-nums">{value}</div>
        {hint && <div className="mt-3 text-sm text-slate-400">{hint}</div>}
      </Card>
    </motion.div>
  );
}

export function ChartPanel({
  title,
  subtitle,
  right,
  children,
  className,
  footer,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
}) {
  return (
    <motion.div variants={rise} className={className}>
      <Card className="h-full">
        <div className="flex flex-wrap items-start justify-between gap-4 px-6 pt-5">
          <div>
            <h3 className="font-display text-lg font-semibold tracking-tight text-white">{title}</h3>
            {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          </div>
          {right && <div className="flex flex-wrap items-center gap-2">{right}</div>}
        </div>
        <div className="px-3 pb-3 pt-2">{children}</div>
        {footer && <div className="border-t border-white/[0.06] px-6 py-3 text-xs text-muted">{footer}</div>}
      </Card>
    </motion.div>
  );
}

export function NotAvailable({ what, file, className, compact }: { what: string; file?: string; className?: string; compact?: boolean }) {
  return (
    <motion.div variants={rise} initial="hidden" animate="show" className={className}>
      <Card className={cn("flex flex-col items-center justify-center text-center", compact ? "px-6 py-8" : "px-10 py-16")}>
        <div className="relative mb-5">
          <div className="absolute inset-0 rounded-full bg-server/20 blur-2xl" />
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
            <DatabaseZap className="h-6 w-6 text-server" />
          </div>
        </div>
        <div className="font-display text-xl font-semibold text-white">{what} not available yet</div>
        <p className="mt-2 max-w-md text-sm text-muted">
          This view only shows numbers exported from the pipeline.
          {file && (
            <>
              {" "}
              Expected <span className="font-mono text-slate-300">web/public/data/{file}</span>.
            </>
          )}
        </p>
        <code className="mt-5 rounded-lg border border-white/10 bg-ink-950/70 px-4 py-2 font-mono text-xs text-slate-300">
          bash scripts/run_demo.sh &amp;&amp; python scripts/export_web_data.py
        </code>
      </Card>
    </motion.div>
  );
}

export function Loading({ className }: { className?: string }) {
  return (
    <div className={cn("grid gap-6", className)}>
      <div className="h-16 w-2/3 animate-shimmer rounded-2xl bg-[linear-gradient(90deg,rgba(255,255,255,0.03),rgba(255,255,255,0.08),rgba(255,255,255,0.03))] bg-[length:200%_100%]" />
      <div className="h-80 animate-shimmer rounded-2xl bg-[linear-gradient(90deg,rgba(255,255,255,0.03),rgba(255,255,255,0.08),rgba(255,255,255,0.03))] bg-[length:200%_100%]" />
    </div>
  );
}

export function Dot({ color, className }: { color: string; className?: string }) {
  return <span className={cn("inline-block h-2.5 w-2.5 rounded-full", className)} style={{ background: color, boxShadow: `0 0 12px ${color}` }} />;
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-white/15 bg-white/[0.05] px-1.5 font-mono text-[0.7rem] text-slate-300">
      {children}
    </kbd>
  );
}
