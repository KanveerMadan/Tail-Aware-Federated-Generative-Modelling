import * as React from "react";
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/** Segmented control with a sliding highlight. */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  size = "md",
  layoutId,
  className,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: React.ReactNode; color?: string }[];
  size?: "md" | "lg";
  layoutId: string;
  className?: string;
}) {
  return (
    <ToggleGroupPrimitive.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as T)}
      className={cn(
        "relative inline-flex items-center rounded-2xl border border-white/10 bg-ink-850/80 p-1 backdrop-blur",
        className
      )}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <ToggleGroupPrimitive.Item
            key={o.value}
            value={o.value}
            className={cn(
              "relative z-10 rounded-xl font-medium transition-colors duration-200",
              size === "lg" ? "px-7 py-3 text-base" : "px-4 py-1.5 text-sm",
              active ? "text-white" : "text-slate-400 hover:text-slate-200"
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 -z-10 rounded-xl border border-white/10"
                style={{
                  background: o.color
                    ? `linear-gradient(180deg, ${o.color}33, ${o.color}14)`
                    : "rgba(255,255,255,0.09)",
                  boxShadow: o.color ? `0 0 24px -6px ${o.color}88` : undefined,
                }}
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            {o.label}
          </ToggleGroupPrimitive.Item>
        );
      })}
    </ToggleGroupPrimitive.Root>
  );
}
