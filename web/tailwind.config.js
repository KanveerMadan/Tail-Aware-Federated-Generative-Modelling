import animate from "tailwindcss-animate";
import plugin from "tailwindcss/plugin";
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1600px" } },
    extend: {
      colors: {
        ink: {
          950: "#05080F",
          900: "#070B14",
          850: "#0A0F1C",
          800: "#0D1424",
          700: "#131C31",
          600: "#1C2741",
          500: "#2A3757",
        },
        bank: {
          0: "#22D3EE",
          1: "#A78BFA",
          2: "#FBBF24",
          3: "#34D399",
        },
        server: "#F472B6",
        better: "#4ADE80",
        worse: "#F87171",
        muted: "#8B97B1",
        line: "rgba(255,255,255,0.08)",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui"],
        sans: ['"Inter"', "ui-sans-serif", "system-ui"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        hero: ["clamp(3rem, 5.4vw, 6.25rem)", { lineHeight: "1.02", letterSpacing: "-0.035em" }],
        display: ["clamp(2.25rem, 3.2vw, 3.6rem)", { lineHeight: "1.06", letterSpacing: "-0.03em" }],
      },
      spacing: { 18: "4.5rem", 22: "5.5rem", 30: "7.5rem" },
      borderRadius: { "2xl": "1.25rem", "3xl": "1.75rem" },
      boxShadow: {
        glass: "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 30px 80px -30px rgba(0,0,0,0.75), 0 12px 32px -12px rgba(0,0,0,0.55)",
        glow: "0 0 0 1px rgba(255,255,255,0.08), 0 0 40px -6px var(--glow, rgba(244,114,182,0.45))",
        lift: "0 24px 60px -20px rgba(0,0,0,0.8)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
      },
      keyframes: {
        "pulse-dot": { "0%,100%": { opacity: "1", transform: "scale(1)" }, "50%": { opacity: ".55", transform: "scale(.82)" } },
        "grid-pan": { from: { backgroundPosition: "0 0, 0 0" }, to: { backgroundPosition: "64px 64px, 64px 64px" } },
        shimmer: { from: { backgroundPosition: "-200% 0" }, to: { backgroundPosition: "200% 0" } },
        "slide-in-right": { from: { transform: "translateX(100%)" }, to: { transform: "translateX(0)" } },
        "slide-out-right": { from: { transform: "translateX(0)" }, to: { transform: "translateX(100%)" } },
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-out": { from: { opacity: "1" }, to: { opacity: "0" } },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.8s ease-in-out infinite",
        "grid-pan": "grid-pan 18s linear infinite",
        shimmer: "shimmer 3s linear infinite",
        "sheet-in": "slide-in-right 380ms cubic-bezier(.22,1,.36,1)",
        "sheet-out": "slide-out-right 260ms ease-in",
        "fade-in": "fade-in 240ms ease-out",
        "fade-out": "fade-out 200ms ease-in",
      },
    },
  },
  plugins: [animate, plugin(({ addVariant }) => { addVariant("presenter", ".presenter &"); })],
};
