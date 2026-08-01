import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  /* Severity/priority colour classes are referenced dynamically (via
     SEVERITY_CONFIG[sev].dot etc.), so Tailwind's JIT can't always see them in
     source and skips generating some (e.g. bg-sev-high never compiled → the
     high segment of the severity meter and risk bars rendered invisible).
     Safelisting guarantees every severity colour class always exists. */
  safelist: [
    "bg-sev-critical", "bg-sev-high", "bg-sev-medium", "bg-sev-low", "bg-sev-info",
    "text-sev-critical", "text-sev-high", "text-sev-medium", "text-sev-low", "text-sev-info",
    "bg-sev-critical-bg", "bg-sev-high-bg", "bg-sev-medium-bg", "bg-sev-low-bg", "bg-sev-info-bg",
    "border-sev-critical-border", "border-sev-high-border", "border-sev-medium-border",
    "border-sev-low-border", "border-sev-info-border",
    "bg-success", "text-success", "bg-success-bg", "border-success-border",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        /* "The Lens" ink ramp. Overrides Tailwind's default `slate` so the ~159
           legacy `slate-*` utilities across pages read correctly on the dark
           ink ground. INVERTED lightness: slate-50 is now near-white text,
           slate-900 is a near-black surface — so `text-slate-900` stays high
           contrast (now light-on-dark) and `bg-slate-50` becomes a dim surface.
           Single ink hue family (240°). */
        slate: {
          50: "hsl(44 20% 94%)",   /* brightest text */
          100: "hsl(44 16% 88%)",
          200: "hsl(240 8% 78%)",
          300: "hsl(240 8% 66%)",
          400: "hsl(240 8% 56%)",  /* muted text */
          500: "hsl(240 8% 48%)",
          600: "hsl(240 10% 34%)",
          700: "hsl(240 12% 22%)", /* borders */
          800: "hsl(240 14% 15%)", /* elevated surface */
          900: "hsl(240 16% 10%)", /* card surface */
          950: "hsl(240 18% 7%)",  /* ground */
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          bg: "hsl(var(--success-bg))",
          border: "hsl(var(--success-border))",
        },
        /* Semantic severity scale — first-class, shared everywhere. */
        sev: {
          critical: "hsl(var(--sev-critical))",
          "critical-bg": "hsl(var(--sev-critical-bg))",
          "critical-border": "hsl(var(--sev-critical-border))",
          high: "hsl(var(--sev-high))",
          "high-bg": "hsl(var(--sev-high-bg))",
          "high-border": "hsl(var(--sev-high-border))",
          medium: "hsl(var(--sev-medium))",
          "medium-bg": "hsl(var(--sev-medium-bg))",
          "medium-border": "hsl(var(--sev-medium-border))",
          low: "hsl(var(--sev-low))",
          "low-bg": "hsl(var(--sev-low-bg))",
          "low-border": "hsl(var(--sev-low-border))",
          info: "hsl(var(--sev-info))",
          "info-bg": "hsl(var(--sev-info-bg))",
          "info-border": "hsl(var(--sev-info-border))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "calc(var(--radius) + 4px)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        glow: "var(--shadow-glow)",
      },
      transitionTimingFunction: {
        "out-quint": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", ...fontFamily.sans],
        mono: ["var(--font-geist-mono)", ...fontFamily.mono],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "rise": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "shimmer": {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "rise": "rise var(--dur, 190ms) var(--ease-out) both",
        "fade-in": "fade-in var(--dur, 190ms) var(--ease-out) both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
