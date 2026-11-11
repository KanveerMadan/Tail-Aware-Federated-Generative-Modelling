import { useEffect, useMemo, useRef, useState } from "react";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import {
  ReactFlow,
  Handle,
  Position,
  getStraightPath,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { CheckCircle2, Landmark, Pause, Play, Server, SkipBack, SkipForward, TriangleAlert } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Segmented } from "@/components/ui/toggle-group";
import { Chart, axisBase, tooltipBase } from "@/components/Chart";
import { ChartPanel, Loading, NotAvailable, Reveal, SectionHeader, Stagger } from "@/components/primitives";
import { useData } from "@/lib/data";
import { useUI } from "@/lib/store";
import { BANK_COLORS, MODEL_COLORS, SERVER_COLOR, hexA } from "@/lib/theme";
import { int, num } from "@/lib/format";
import type { RoundRow } from "@/lib/types";

type Phase = "idle" | "up" | "combine" | "down";
const BASE_MS: Record<Exclude<Phase, "idle">, number> = { up: 1300, combine: 800, down: 1300 };

// ------------------------------------------------------------------ nodes

type BankData = { bank: number; sector: string; n: number | null; active: boolean };
type ServerData = { phase: Phase; round: number };
type BankNodeT = Node<BankData, "bank">;
type ServerNodeT = Node<ServerData, "server">;

const centerHandle = { top: "50%", left: "50%", transform: "translate(-50%,-50%)", width: 1, height: 1, minWidth: 0, minHeight: 0, border: 0 };

function BankNode({ data }: NodeProps<BankNodeT>) {
  const c = BANK_COLORS[data.bank];
  return (
    <motion.div
      animate={{ boxShadow: data.active ? `0 0 46px -6px ${c}` : `0 0 22px -12px ${c}` }}
      className="relative w-[200px] rounded-2xl border bg-ink-900/95 px-4 py-3.5 backdrop-blur"
      style={{ borderColor: hexA(c, data.active ? 0.85 : 0.45) }}
    >
      <Handle type="source" position={Position.Top} style={centerHandle} isConnectable={false} />
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl" style={{ background: hexA(c, 0.16) }}>
          <Landmark className="h-[18px] w-[18px]" style={{ color: c }} />
        </div>
        <div className="min-w-0">
          <div className="font-display text-[0.95rem] font-semibold text-white">Bank {data.bank}</div>
          <div className="truncate text-xs" style={{ color: c }}>{data.sector}</div>
        </div>
      </div>
      {data.n != null && <div className="mt-2 font-mono text-[0.7rem] text-muted">n = {int(data.n)} examples</div>}
    </motion.div>
  );
}

function ServerNode({ data }: NodeProps<ServerNodeT>) {
  const combining = data.phase === "combine";
  return (
    <div className="relative">
      <motion.div
        className="absolute inset-0 rounded-[28px]"
        animate={combining ? { scale: [1, 1.35], opacity: [0.55, 0] } : { scale: 1, opacity: 0 }}
        transition={{ duration: 0.9, repeat: combining ? Infinity : 0 }}
        style={{ background: SERVER_COLOR, filter: "blur(12px)" }}
      />
      <motion.div
        animate={{ scale: combining ? [1, 1.06, 1] : 1 }}
        transition={{ duration: 0.8, repeat: combining ? Infinity : 0 }}
        className="relative flex h-[150px] w-[150px] flex-col items-center justify-center rounded-[28px] border bg-ink-900/95"
        style={{ borderColor: hexA(SERVER_COLOR, 0.75), boxShadow: `0 0 50px -10px ${SERVER_COLOR}` }}
      >
        <Handle type="target" position={Position.Top} style={centerHandle} isConnectable={false} />
        <Server className="h-8 w-8 text-server" />
        <div className="mt-2 font-display font-semibold text-white">Server</div>
        <div className="mt-0.5 font-mono text-[0.7rem] text-muted">
          {combining ? "Σ masked ÷ Σ n" : data.round > 0 ? `global model r${data.round}` : "initial model"}
        </div>
      </motion.div>
    </div>
  );
}

// ------------------------------------------------------------------ edges with packets

type PacketData = { bank: number; phase: Phase; tick: number; duration: number };
type PacketEdgeT = Edge<PacketData, "packet">;

function PacketEdge({ sourceX, sourceY, targetX, targetY, data }: EdgeProps<PacketEdgeT>) {
  const [path] = getStraightPath({ sourceX, sourceY, targetX, targetY });
  const ref = useRef<SVGPathElement>(null);
  const progress = useMotionValue(0);
  const opacity = useMotionValue(0);
  const point = (p: number) => {
    const el = ref.current;
    if (!el) return { x: sourceX, y: sourceY };
    const len = el.getTotalLength();
    return el.getPointAtLength(Math.max(0, Math.min(1, p)) * len);
  };
  const cx = useTransform(progress, (p) => point(p).x);
  const cy = useTransform(progress, (p) => point(p).y);
  const phase = data?.phase ?? "idle";
  const c = BANK_COLORS[data?.bank ?? 0];
  const color = phase === "down" ? SERVER_COLOR : c;

  useEffect(() => {
    if (phase !== "up" && phase !== "down") {
      opacity.set(0);
      return;
    }
    const dur = (data?.duration ?? 1300) / 1000;
    const delay = (data?.bank ?? 0) * 0.08;
    const [from, to] = phase === "up" ? [0, 1] : [1, 0];
    progress.set(from);
    const a1 = animate(progress, to, { duration: dur * 0.9, delay, ease: [0.45, 0, 0.25, 1] });
    const a2 = animate(opacity, [0, 1, 1, 0], { duration: dur * 0.9, delay, times: [0, 0.12, 0.85, 1] });
    return () => {
      a1.stop();
      a2.stop();
    };
  }, [phase, data?.tick, data?.duration, data?.bank, progress, opacity]);

  const active = phase === "up" || phase === "down";
  return (
    <g>
      <path ref={ref} d={path} fill="none" stroke={hexA(c, 0.18)} strokeWidth={2} />
      <path d={path} fill="none" stroke={hexA(color, active ? 0.65 : 0.22)} strokeWidth={1.5} className="edge-flow" />
      <motion.circle cx={cx} cy={cy} r={14} fill={color} style={{ opacity, filter: "blur(8px)" }} />
      <motion.circle cx={cx} cy={cy} r={6.5} fill={color} style={{ opacity }} />
      <motion.circle cx={cx} cy={cy} r={2.6} fill="#fff" style={{ opacity }} />
    </g>
  );
}

const nodeTypes = { bank: BankNode, server: ServerNode };
const edgeTypes = { packet: PacketEdge };

// ------------------------------------------------------------------ screen

export default function RoundsScreen() {
  const { data: fed, loading, missing } = useData("federated.json");
  const { data: banks } = useData("banks.json");
  const strategy = useUI((s) => s.roundsStrategy);
  const setStrategy = useUI((s) => s.setRoundsStrategy);

  const runs = fed?.strategies ?? {};
  const available = (["fedavg", "fedprox"] as const).filter((k) => runs[k]);
  const key = runs[strategy] ? strategy : available[0];
  const run = key ? runs[key] : undefined;
  const nRounds = run?.rounds.length ?? 0;

  const [round, setRound] = useState(0); // completed rounds shown
  const [phase, setPhase] = useState<Phase>("idle");
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1.5);
  const [tick, setTick] = useState(0);

  // restart when the strategy changes
  useEffect(() => {
    setRound(0);
    setPhase("idle");
    setPlaying(true);
  }, [key]);

  // round state machine: idle -> up -> combine -> down -> (round+1) -> up ...
  useEffect(() => {
    if (!playing || !run) return;
    if (round >= nRounds && phase === "idle") {
      setPlaying(false);
      return;
    }
    const next: Record<Phase, Phase> = { idle: "up", up: "combine", combine: "down", down: "idle" };
    const wait = phase === "idle" ? 250 / speed : BASE_MS[phase] / speed;
    const t = setTimeout(() => {
      if (phase === "down") setRound((r) => Math.min(nRounds, r + 1));
      if (phase === "idle") setTick((x) => x + 1);
      setPhase(next[phase]);
    }, wait);
    return () => clearTimeout(t);
  }, [playing, phase, round, nRounds, speed, run]);

  // Training examples per bank (= the FedAvg weight n_i each client reports)
  const examples = banks?.banks.map((b) => b.n_sequences.train ?? null);
  const sectors = banks?.banks.map((b) => b.sector ?? "") ?? [];

  const nodes: Node[] = useMemo(() => {
    const pos = [
      { x: 30, y: 30 },
      { x: 650, y: 30 },
      { x: 30, y: 330 },
      { x: 650, y: 330 },
    ];
    return [
      ...pos.map((p, i) => ({
        id: `b${i}`,
        type: "bank",
        position: p,
        draggable: false,
        selectable: false,
        data: { bank: i, sector: sectors[i] ?? "", n: examples?.[i] ?? null, active: phase === "up" || phase === "down" },
      })),
      { id: "server", type: "server", position: { x: 365, y: 170 }, draggable: false, selectable: false, data: { phase, round } },
    ];
  }, [phase, round, sectors.join("|"), examples?.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  const edges: Edge[] = useMemo(
    () =>
      [0, 1, 2, 3].map((i) => ({
        id: `e${i}`,
        source: `b${i}`,
        target: "server",
        type: "packet",
        data: { bank: i, phase, tick, duration: (phase === "down" ? BASE_MS.down : BASE_MS.up) / speed },
      })),
    [phase, tick, speed]
  );

  if (loading) return <Loading />;
  if (missing || !fed || !run || !key) return <NotAvailable what="Federated history" file="federated.json" />;

  const shown: RoundRow[] = run.rounds.slice(0, round);
  const current = run.rounds[Math.max(0, round - 1)];
  const other = key === "fedavg" ? runs.fedprox : runs.fedavg;
  const otherKey = key === "fedavg" ? "fedprox" : "fedavg";
  const ok = current && current.n_results === run.n_clients && !current.n_failures;
  const allOk = run.rounds.every((r) => r.n_results === run.n_clients && !r.n_failures && !r.eval_n_failures);
  const color = MODEL_COLORS[key];
  const label = key === "fedavg" ? "FedAvg" : "FedProx";

  const chart = {
    animationDurationUpdate: 450,
    grid: { left: 64, right: 22, top: 46, bottom: 44 },
    legend: { top: 4, left: 8, textStyle: { color: "#CBD5E1" }, icon: "roundRect", itemWidth: 14, itemHeight: 4 },
    tooltip: { ...tooltipBase, trigger: "axis" as const, valueFormatter: (v: unknown) => (v == null ? "—" : num(Number(v), 4)) },
    xAxis: { type: "value" as const, min: 1, max: nRounds, interval: Math.max(1, Math.round(nRounds / 10)), name: "round", nameLocation: "middle" as const, nameGap: 28, ...axisBase, splitLine: { show: false } },
    yAxis: { type: "value" as const, scale: true, ...axisBase, axisLabel: { ...axisBase.axisLabel, formatter: (v: number) => v.toFixed(3) } },
    series: [
      {
        name: `${label} val loss`, type: "line" as const, smooth: true, symbol: "circle", symbolSize: 7,
        lineStyle: { width: 3, color }, itemStyle: { color },
        areaStyle: { color: { type: "linear" as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: hexA(color, 0.25) }, { offset: 1, color: hexA(color, 0) }] } },
        data: shown.map((r) => [r.round, r.val_loss]),
      },
      {
        name: `${label} train loss`, type: "line" as const, smooth: true, showSymbol: false,
        lineStyle: { width: 2, color: hexA(color, 0.55), type: "dashed" as const }, itemStyle: { color: hexA(color, 0.55) },
        data: shown.map((r) => [r.round, r.train_loss]),
      },
      ...(other
        ? [{
            name: `${otherKey === "fedavg" ? "FedAvg" : "FedProx"} val loss`, type: "line" as const, smooth: true, showSymbol: false,
            lineStyle: { width: 1.5, color: hexA(MODEL_COLORS[otherKey], 0.45) }, itemStyle: { color: hexA(MODEL_COLORS[otherKey], 0.45) },
            data: other.rounds.slice(0, round).map((r) => [r.round, r.val_loss]),
          }]
        : []),
    ],
  };

  return (
    <Stagger className="grid gap-6">
      <SectionHeader
        eyebrow="Step 5 · Federated rounds"
        title={
          <>
            {nRounds} rounds of <span className="text-gradient">masked updates</span>
          </>
        }
        subtitle={`Replayed from the real ${label} run (${run.run_id}). Each round: ${run.n_clients} banks send masked updates, the server combines them, the new global model goes back.`}
        right={
          <Segmented
            layoutId="rounds-strategy"
            size="lg"
            value={key}
            onChange={(v) => setStrategy(v)}
            options={available.map((k) => ({ value: k, label: k === "fedavg" ? "FedAvg" : `FedProx · μ=${runs[k]?.mu ?? "?"}`, color: MODEL_COLORS[k] }))}
          />
        }
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.08fr_1fr]">
        <Reveal>
          <Card className="relative h-[540px] overflow-hidden">
            <div className="absolute left-5 top-4 z-10 flex items-center gap-3">
              <div className="rounded-xl border border-white/10 bg-ink-950/70 px-4 py-2 font-mono text-lg text-white backdrop-blur">
                Round <span className="text-server">{Math.max(1, Math.min(nRounds, phase === "idle" ? round : round + 1))}</span> / {nRounds}
              </div>
              <motion.div
                key={`${phase}-${round}`}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs uppercase tracking-[0.14em] text-slate-300"
              >
                {phase === "up" ? "banks → server · masked" : phase === "combine" ? "server combining" : phase === "down" ? "global model → banks" : round >= nRounds ? "done" : "ready"}
              </motion.div>
            </div>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              fitView
              fitViewOptions={{ padding: 0.12 }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              panOnDrag={false}
              zoomOnScroll={false}
              zoomOnPinch={false}
              zoomOnDoubleClick={false}
              preventScrolling={false}
              proOptions={{ hideAttribution: true }}
            />
          </Card>
        </Reveal>

        <div className="grid gap-5">
          <ChartPanel
            title="Loss per round"
            subtitle="Normalised loss, weighted over the 4 banks · solid = validation, dashed = training"
            right={
              current && round > 0 ? (
                <div className="font-mono text-sm text-slate-300">
                  val <span style={{ color }}>{num(current.val_loss, 4)}</span>
                </div>
              ) : undefined
            }
          >
            <Chart option={chart} height={300} />
          </ChartPanel>

          <Reveal>
            <Card className="p-5">
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="glass" size="icon" aria-label="Previous round" onClick={() => { setPlaying(false); setPhase("idle"); setRound((r) => Math.max(0, r - 1)); }}>
                  <SkipBack className="h-4 w-4" />
                </Button>
                <Button
                  variant="primary"
                  className="w-[132px]"
                  onClick={() => {
                    if (round >= nRounds) { setRound(0); setPhase("idle"); }
                    setPlaying((p) => !p || round >= nRounds);
                  }}
                >
                  {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {playing ? "Pause" : round >= nRounds ? "Replay" : "Play"}
                </Button>
                <Button variant="glass" size="icon" aria-label="Next round" onClick={() => { setPlaying(false); setPhase("idle"); setRound((r) => Math.min(nRounds, r + 1)); }}>
                  <SkipForward className="h-4 w-4" />
                </Button>
                <div className="ml-auto flex min-w-[240px] items-center gap-4">
                  <span className="text-xs uppercase tracking-[0.14em] text-muted">Speed</span>
                  <Slider value={[speed]} min={0.5} max={4} step={0.25} onValueChange={(v) => setSpeed(v[0])} className="w-36" />
                  <span className="w-12 font-mono text-sm text-white">{speed.toFixed(2).replace(/0$/, "")}×</span>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-3">
                {round > 0 && current ? (
                  <>
                    <span className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm ${ok ? "border-better/30 bg-better/10 text-better" : "border-worse/30 bg-worse/10 text-worse"}`}>
                      {ok ? <CheckCircle2 className="h-4 w-4" /> : <TriangleAlert className="h-4 w-4" />}
                      Round {current.round}: {current.n_results} results · {current.n_failures ?? 0} failures
                    </span>
                    {current.eval_n_results != null && (
                      <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-sm text-slate-300">
                        evaluate: {String(current.eval_n_results)} results · {String(current.eval_n_failures ?? 0)} failures
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-sm text-muted">Press play to replay the run round by round.</span>
                )}
                <span className={`ml-auto inline-flex items-center gap-2 text-sm ${allOk ? "text-better" : "text-worse"}`}>
                  {allOk ? <CheckCircle2 className="h-4 w-4" /> : <TriangleAlert className="h-4 w-4" />}
                  {allOk ? `All ${nRounds} rounds complete, 0 failures` : "Some rounds had failures"}
                </span>
              </div>
              <div className="mt-4 flex gap-1">
                {run.rounds.map((r, i) => (
                  <div
                    key={r.round}
                    className="h-1.5 flex-1 rounded-full transition-colors duration-300"
                    style={{ background: i < round ? (r.n_failures ? "#F87171" : color) : "rgba(255,255,255,0.08)" }}
                  />
                ))}
              </div>
            </Card>
          </Reveal>
        </div>
      </div>
    </Stagger>
  );
}
