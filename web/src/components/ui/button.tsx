import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-server/60 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-900 disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-r from-server via-fuchsia-400 to-violet-400 text-ink-950 shadow-[0_10px_40px_-10px_rgba(244,114,182,0.7)] hover:shadow-[0_14px_50px_-8px_rgba(244,114,182,0.9)] hover:-translate-y-0.5 active:translate-y-0",
        glass:
          "border border-white/10 bg-white/[0.04] text-slate-100 backdrop-blur-md hover:bg-white/[0.09] hover:border-white/20",
        ghost: "text-slate-300 hover:text-white hover:bg-white/[0.06]",
        outline: "border border-white/15 text-slate-200 hover:border-white/30 hover:bg-white/[0.04]",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-5 text-[0.95rem]",
        lg: "h-14 px-8 text-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "glass", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";
