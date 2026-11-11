import { useEffect, useRef } from "react";
import { BANK_COLORS, SERVER_COLOR } from "@/lib/theme";

/** Fixed background: slow grid, radial glows and (optionally) a drifting node network. */
export function Backdrop({ network = false }: { network?: boolean }) {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-ink-900" />
      <div
        className="absolute inset-0 animate-grid-pan bg-grid-faint opacity-60 [background-size:64px_64px]"
        style={{ maskImage: "radial-gradient(ellipse 80% 70% at 50% 40%, black 30%, transparent 80%)" }}
      />
      <div className="absolute -left-40 -top-40 h-[640px] w-[640px] rounded-full bg-violet-600/20 blur-[140px]" />
      <div className="absolute -right-40 top-1/4 h-[560px] w-[560px] rounded-full bg-cyan-500/10 blur-[140px]" />
      <div className="absolute bottom-[-280px] left-1/3 h-[620px] w-[620px] rounded-full bg-pink-500/10 blur-[160px]" />
      {network && <NetworkCanvas />}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(5,8,15,0.75))]" />
    </div>
  );
}

interface P {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  c: string;
}

/** Lightweight 2D canvas: ~70 drifting nodes linked when close. */
function NetworkCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const palette = [...BANK_COLORS, SERVER_COLOR, "#94A3B8", "#94A3B8"];
    let w = 0;
    let h = 0;
    let raf = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const pts: P[] = [];
    // Deterministic pseudo-random so every load looks the same
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    for (let i = 0; i < 70; i++) {
      pts.push({
        x: rnd() * w,
        y: rnd() * h,
        vx: (rnd() - 0.5) * 0.25,
        vy: (rnd() - 0.5) * 0.25,
        r: 1.2 + rnd() * 2.2,
        c: palette[Math.floor(rnd() * palette.length)],
      });
    }
    const link = 150;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of pts) {
        if (!reduce) {
          p.x += p.vx;
          p.y += p.vy;
        }
        if (p.x < -20) p.x = w + 20;
        if (p.x > w + 20) p.x = -20;
        if (p.y < -20) p.y = h + 20;
        if (p.y > h + 20) p.y = -20;
      }
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const a = pts[i];
          const b = pts[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < link) {
            ctx.strokeStyle = `rgba(148,163,184,${0.16 * (1 - d / link)})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      for (const p of pts) {
        ctx.fillStyle = p.c;
        ctx.globalAlpha = 0.75;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 0.12;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);
  return <canvas ref={ref} className="absolute inset-0 h-full w-full opacity-70" />;
}
