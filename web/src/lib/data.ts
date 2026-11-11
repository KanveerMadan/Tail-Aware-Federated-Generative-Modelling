import { create } from "zustand";
import { useEffect } from "react";
import type { DataFile, DataFiles } from "./types";

type Entry<K extends DataFile> = { status: "loading" } | { status: "ok"; data: DataFiles[K] } | { status: "missing" };

interface DataState {
  entries: Partial<{ [K in DataFile]: Entry<K> }>;
  load: (f: DataFile) => void;
}

const base = import.meta.env.BASE_URL.endsWith("/") ? import.meta.env.BASE_URL : import.meta.env.BASE_URL + "/";

export const useDataStore = create<DataState>((set, get) => ({
  entries: {},
  load: (file) => {
    if (get().entries[file]) return;
    set((s) => ({ entries: { ...s.entries, [file]: { status: "loading" } } }));
    fetch(`${base}data/${file}`, { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        const ct = r.headers.get("content-type") ?? "";
        if (ct.includes("text/html")) throw new Error("not json");
        return r.json();
      })
      .then((json) => {
        const ok = json && typeof json === "object" && json.available !== false;
        set((s) => ({ entries: { ...s.entries, [file]: ok ? { status: "ok", data: json } : { status: "missing" } } }));
      })
      .catch(() => set((s) => ({ entries: { ...s.entries, [file]: { status: "missing" } } })));
  },
}));

/** Load one exported JSON file. Returns { data, loading, missing }. Never throws. */
export function useData<K extends DataFile>(file: K) {
  const entry = useDataStore((s) => s.entries[file]) as Entry<K> | undefined;
  const load = useDataStore((s) => s.load);
  useEffect(() => load(file), [file, load]);
  return {
    data: entry?.status === "ok" ? entry.data : undefined,
    loading: !entry || entry.status === "loading",
    missing: entry?.status === "missing",
  };
}

export const ALL_FILES: DataFile[] = [
  "manifest.json", "settings.json", "source.json", "prices.json", "banks.json", "federated.json",
  "results.json", "predictions.json", "masking.json", "summary.json", "code.json",
];
