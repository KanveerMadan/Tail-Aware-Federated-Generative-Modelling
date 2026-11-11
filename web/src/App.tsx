import { useCallback, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { useHotkeys } from "react-hotkeys-hook";
import { Backdrop } from "@/components/Backdrop";
import { TopBar } from "@/components/TopBar";
import { Hood } from "@/components/Hood";
import { StoryNav } from "@/components/StoryNav";
import { TooltipProvider } from "@/components/ui/tooltip";
import { STEPS, useUI } from "@/lib/store";
import { cn } from "@/lib/utils";
import Landing from "@/screens/Landing";
import DataScreen from "@/screens/DataScreen";
import BanksScreen from "@/screens/BanksScreen";
import ProblemScreen from "@/screens/ProblemScreen";
import TrainingScreen from "@/screens/TrainingScreen";
import RoundsScreen from "@/screens/RoundsScreen";
import MaskingScreen from "@/screens/MaskingScreen";
import ResultsScreen from "@/screens/ResultsScreen";
import PredictScreen from "@/screens/PredictScreen";
import TakeawaysScreen from "@/screens/TakeawaysScreen";

const SCREENS: Record<string, () => JSX.Element> = {
  data: DataScreen,
  banks: BanksScreen,
  problem: ProblemScreen,
  training: TrainingScreen,
  rounds: RoundsScreen,
  masking: MaskingScreen,
  results: ResultsScreen,
  predict: PredictScreen,
  takeaways: TakeawaysScreen,
};

function stepIndexFromPath(path: string): number | null {
  const m = path.match(/^\/story\/([^/]+)/);
  if (!m) return null;
  const i = STEPS.findIndex((s) => s.id === m[1]);
  return i >= 0 ? i : null;
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const presenter = useUI((s) => s.presenter);
  const setPresenter = useUI((s) => s.setPresenter);
  const hoodOpen = useUI((s) => s.hoodOpen);
  const stepIndex = stepIndexFromPath(location.pathname);
  const onLanding = location.pathname === "/";

  const go = useCallback(
    (delta: number) => {
      if (stepIndex == null) {
        if (delta > 0) navigate(`/story/${STEPS[0].id}`);
        return;
      }
      const next = stepIndex + delta;
      if (next < 0) navigate("/");
      else if (next < STEPS.length) navigate(`/story/${STEPS[next].id}`);
    },
    [stepIndex, navigate]
  );

  const enterPresenter = useCallback(() => {
    setPresenter(true);
    document.documentElement.requestFullscreen?.().catch(() => undefined);
    if (onLanding) navigate(`/story/${STEPS[0].id}`);
  }, [setPresenter, onLanding, navigate]);

  const exitPresenter = useCallback(() => {
    setPresenter(false);
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => undefined);
  }, [setPresenter]);

  // Presenter mode scales every rem-based size up a notch
  useEffect(() => {
    document.documentElement.classList.toggle("presenter-root", presenter);
  }, [presenter]);

  // Leaving fullscreen with the browser's own Esc also leaves presenter mode
  useEffect(() => {
    const onChange = () => {
      if (!document.fullscreenElement && useUI.getState().presenter) setPresenter(false);
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, [setPresenter]);

  const opts = { enabled: !hoodOpen, preventDefault: true };
  useHotkeys("right, pagedown", () => go(1), opts, [go]);
  useHotkeys("space", () => go(1), { ...opts, enabled: !hoodOpen && presenter }, [go, presenter]);
  useHotkeys("left, pageup", () => go(-1), opts, [go]);
  useHotkeys("escape", () => presenter && exitPresenter(), { enabled: presenter }, [presenter, exitPresenter]);

  return (
    <TooltipProvider delayDuration={150}>
      <div className={cn("relative min-h-screen", presenter && "presenter")}>
        <Backdrop network={onLanding} />
        <TopBar stepIndex={stepIndex} onPresenter={presenter ? exitPresenter : enterPresenter} />
        <AnimatePresence mode="wait">
          <motion.main
            key={location.pathname}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
          >
            <Routes location={location}>
              <Route path="/" element={<Landing />} />
              <Route path="/story/:step" element={<StoryPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.main>
        </AnimatePresence>
        {stepIndex != null && <Hood stepId={STEPS[stepIndex].id} />}
      </div>
    </TooltipProvider>
  );
}

function StoryPage() {
  const { step } = useParams();
  const Screen = step ? SCREENS[step] : undefined;
  if (!Screen) return <Navigate to="/" replace />;
  return (
    <div className="mx-auto flex min-h-[calc(100vh-68px)] max-w-[1680px] flex-col px-8 pb-6 pt-8 presenter:pt-10">
      <div className="flex-1">
        <Screen />
      </div>
      <StoryNav />
    </div>
  );
}
