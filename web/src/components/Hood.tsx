import { Highlight, themes } from "prism-react-renderer";
import { FileCode2, Terminal } from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useData } from "@/lib/data";
import { useUI } from "@/lib/store";

/** "Under the hood" drawer: the real command and source for the current step (from code.json). */
export function Hood({ stepId }: { stepId: string }) {
  const open = useUI((s) => s.hoodOpen);
  const setOpen = useUI((s) => s.setHoodOpen);
  const { data } = useData("code.json");
  const step = data?.steps[stepId];

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent aria-describedby={undefined}>
        <div className="border-b border-white/[0.06] px-8 pb-6 pt-8">
          <div className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.2em] text-server">Under the hood</div>
          <SheetTitle>{step?.title ?? "Source not available"}</SheetTitle>
          <SheetDescription className="mt-2">Exact code from the repository, extracted by scripts/export_web_data.py.</SheetDescription>
        </div>
        {step ? (
          <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-hidden px-8 py-6">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted">
                <Terminal className="h-3.5 w-3.5" /> Command
              </div>
              <pre className="overflow-x-auto rounded-xl border border-white/10 bg-ink-950/80 px-4 py-3 font-mono text-[0.82rem] text-emerald-300">
                <span className="select-none text-slate-500">$ </span>
                {step.command}
              </pre>
            </div>
            <div className="flex min-h-0 flex-1 flex-col">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted">
                <FileCode2 className="h-3.5 w-3.5" />
                <span className="font-mono normal-case tracking-normal text-slate-300">{step.file}</span>
                <span className="text-slate-500">· {step.symbols.join(", ")}</span>
              </div>
              <div className="min-h-0 flex-1 overflow-auto rounded-xl border border-white/10 bg-ink-950/80">
                <Highlight theme={themes.nightOwl} code={step.code || "# source not found"} language="python">
                  {({ tokens, getLineProps, getTokenProps }) => (
                    <pre className="px-4 py-4 font-mono text-[0.78rem] leading-relaxed">
                      {tokens.map((line, i) => (
                        <div key={i} {...getLineProps({ line })} className="table-row">
                          <span className="table-cell select-none pr-4 text-right text-slate-600">{i + 1}</span>
                          <span className="table-cell">
                            {line.map((token, k) => (
                              <span key={k} {...getTokenProps({ token })} />
                            ))}
                          </span>
                        </div>
                      ))}
                    </pre>
                  )}
                </Highlight>
              </div>
            </div>
          </div>
        ) : (
          <div className="px-8 py-10 text-sm text-muted">code.json is not available. Run python scripts/export_web_data.py.</div>
        )}
      </SheetContent>
    </Sheet>
  );
}
