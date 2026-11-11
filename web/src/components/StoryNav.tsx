import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/primitives";
import { STEPS } from "@/lib/store";
import { cn } from "@/lib/utils";

export function StoryNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const i = STEPS.findIndex((s) => pathname === `/story/${s.id}`);
  const prev = i > 0 ? STEPS[i - 1] : null;
  const next = i < STEPS.length - 1 ? STEPS[i + 1] : null;

  return (
    <div className="mt-8 flex items-center justify-between gap-6 border-t border-white/[0.06] pt-5">
      <Button variant="ghost" onClick={() => navigate(prev ? `/story/${prev.id}` : "/")}>
        <ChevronLeft className="h-4 w-4" />
        {prev ? prev.label : "Start"}
      </Button>

      <div className="flex items-center gap-2" aria-label="Progress">
        {STEPS.map((s, j) => (
          <button
            key={s.id}
            aria-label={s.label}
            onClick={() => navigate(`/story/${s.id}`)}
            className="group p-1"
          >
            <motion.span
              layout
              className={cn(
                "block h-1.5 rounded-full transition-colors",
                j === i ? "w-8 bg-server" : j < i ? "w-3 bg-white/40 group-hover:bg-white/60" : "w-3 bg-white/12 group-hover:bg-white/30"
              )}
              style={j > i ? { backgroundColor: "rgba(255,255,255,0.12)" } : undefined}
            />
          </button>
        ))}
        <span className="presenter-hide ml-4 hidden items-center gap-1.5 text-xs text-muted md:flex">
          <Kbd>←</Kbd>
          <Kbd>→</Kbd> to navigate
        </span>
      </div>

      {next ? (
        <Button variant="primary" onClick={() => navigate(`/story/${next.id}`)}>
          {next.label}
          <ArrowRight className="h-4 w-4" />
        </Button>
      ) : (
        <Button variant="glass" onClick={() => navigate("/")}>
          Back to start
          <ArrowRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
