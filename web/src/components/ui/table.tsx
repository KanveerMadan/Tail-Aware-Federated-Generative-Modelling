import * as React from "react";
import { cn } from "@/lib/utils";

export const Table = ({ className, ...p }: React.HTMLAttributes<HTMLTableElement>) => (
  <div className="relative w-full overflow-auto">
    <table className={cn("w-full caption-bottom border-separate border-spacing-0 text-sm", className)} {...p} />
  </div>
);
export const TableHeader = ({ className, ...p }: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <thead className={cn("[&_th]:sticky [&_th]:top-0 [&_th]:z-10", className)} {...p} />
);
export const TableBody = ({ className, ...p }: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <tbody className={cn("[&_tr:last-child_td]:border-0", className)} {...p} />
);
export const TableRow = ({ className, ...p }: React.HTMLAttributes<HTMLTableRowElement>) => (
  <tr className={cn("group transition-colors hover:bg-white/[0.035]", className)} {...p} />
);
export const TableHead = ({ className, ...p }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
  <th
    className={cn(
      "h-11 border-b border-white/10 bg-ink-850/95 px-4 text-left align-middle text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-muted backdrop-blur",
      className
    )}
    {...p}
  />
);
export const TableCell = ({ className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
  <td className={cn("border-b border-white/[0.05] px-4 py-3 align-middle", className)} {...p} />
);
