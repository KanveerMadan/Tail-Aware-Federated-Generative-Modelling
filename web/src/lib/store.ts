import { create } from "zustand";

export interface StepDef {
  id: string;
  label: string;
  short: string;
}

export const STEPS: StepDef[] = [
  { id: "data", label: "The data", short: "Data" },
  { id: "banks", label: "Four banks", short: "Banks" },
  { id: "problem", label: "The problem", short: "Problem" },
  { id: "training", label: "How training works", short: "Training" },
  { id: "rounds", label: "Federated rounds", short: "Rounds" },
  { id: "masking", label: "Scrambling updates", short: "Masking" },
  { id: "results", label: "Results", short: "Results" },
  { id: "predict", label: "Predict a stock", short: "Predict" },
  { id: "takeaways", label: "Honest takeaways", short: "Takeaways" },
];

interface UIState {
  presenter: boolean;
  setPresenter: (v: boolean) => void;
  hoodOpen: boolean;
  setHoodOpen: (v: boolean) => void;
  roundsStrategy: "fedavg" | "fedprox";
  setRoundsStrategy: (s: "fedavg" | "fedprox") => void;
}

export const useUI = create<UIState>((set) => ({
  presenter: false,
  setPresenter: (presenter) => set({ presenter }),
  hoodOpen: false,
  setHoodOpen: (hoodOpen) => set({ hoodOpen }),
  roundsStrategy: "fedprox",
  setRoundsStrategy: (roundsStrategy) => set({ roundsStrategy }),
}));
