/**
 * Tailwind theme derived from docs/design/tokens.css (ADR-027).
 * Colors reference CSS custom properties so the dark theme works by flipping
 * data-theme on <html> — no Tailwind dark-mode class duplication.
 * Never hardcode a hex, radius, or spacing value in a component.
 */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: { DEFAULT: "var(--surface)", 2: "var(--surface-2)" },
        border: { DEFAULT: "var(--border)", strong: "var(--border-strong)" },
        text: { DEFAULT: "var(--text)", 2: "var(--text-2)", 3: "var(--text-3)" },
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          soft: "var(--accent-soft)",
          on: "var(--on-accent)",
        },
        qualify: { DEFAULT: "var(--qualify)", soft: "var(--qualify-soft)" },
        nearmiss: { DEFAULT: "var(--nearmiss)", soft: "var(--nearmiss-soft)" },
        below: { DEFAULT: "var(--below)", soft: "var(--below-soft)" },
        danger: { DEFAULT: "var(--danger)", soft: "var(--danger-soft)" },
      },
      fontFamily: {
        display: "var(--font-display)",
        body: "var(--font-body)",
        mono: "var(--font-mono)",
      },
      fontSize: {
        display: "var(--fs-display)",
        h2: "var(--fs-h2)",
        body: "var(--fs-body)",
        control: "var(--fs-control)",
        small: "var(--fs-small)",
        caption: "var(--fs-caption)",
        label: "var(--fs-label)",
        tick: "var(--fs-tick)",
      },
      borderRadius: {
        card: "var(--r-card)",
        control: "var(--r-control)",
        pill: "var(--r-pill)",
      },
      spacing: {
        1: "var(--s1)",
        2: "var(--s2)",
        3: "var(--s3)",
        4: "var(--s4)",
        5: "var(--s5)",
        6: "var(--s6)",
        7: "var(--s7)",
        8: "var(--s8)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "250ms",
      },
    },
  },
  plugins: [],
};
