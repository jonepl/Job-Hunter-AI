# Design Rules — Job Hunter AI Web

Read before touching anything under `web/src/`. Values live in
`docs/design/tokens.css`; this file is *why* and *how*. Source: Job Hunter AI
Design System v1.0.

---

## Principles

1. **Color is never decorative.** Semantic colors are reserved for score state and
   run status. If a color isn't carrying meaning, it shouldn't be there.
2. **Borders, not shadows, define surfaces.** No drop shadows on cards or panels.
3. **One primary action per view.** Exactly one `btn-primary`. Everything else is
   secondary, ghost, or danger.
4. **Numbers are mono.** Scores, costs, cron expressions, token counts, timestamps
   — IBM Plex Mono. Numbers in mono read as measured, not styled.
5. **Every visual decision serves one question:** is this job above or below your
   threshold?

## Non-negotiables

- **Never hardcode a hex, radius, or spacing value.** Use the CSS custom properties
  from `tokens.css`, surfaced through the Tailwind theme.
- **Focus rings are always visible on keyboard navigation** — 2px, accent color,
  2px offset. Do not remove or suppress `:focus-visible`.
- **Motion budget:** transitions ≤ 250ms, `ease-out`, and only on `background` and
  `border-color`. Never animate layout or opacity by default.
- **`prefers-reduced-motion` is respected** — already handled in `tokens.css`;
  don't reintroduce unconditional transitions.
- **No browser storage** (`localStorage` / `sessionStorage`) for domain/app data —
  React Query's in-memory cache only. **One exception (ADR-037): the theme UI
  preference** persists in `localStorage` (key `theme`), read synchronously by a guard
  in `index.html` before first paint. Navigation state (screen, Settings section,
  Search rail selection) lives in the **URL**, not storage. Nothing else may use
  browser storage.

---

## The threshold rail — the signature component

Every score visualization carries a tick at the active threshold. The rail appears
in cards, tables, and the detail pane, so the product's core rule is legible
everywhere. Build it once as `<ThresholdRail>`; never re-implement.

**Three fill states, not two:**

| State | Condition | Fill | Chip background |
|---|---|---|---|
| `qualify` | `score >= threshold` | `--qualify` | `--qualify-soft` |
| `nearmiss` | inside the near-miss band, below threshold | `--nearmiss` | `--nearmiss-soft` |
| `below` | beneath the near-miss band | `--below` | `--below-soft` |

Green means qualifying, amber means near-miss, gray means below.

Geometry: 10px track, `--r-pill` radius, `--surface-2` background. Tick is a 2px
`--text` bar at 55% opacity, overhanging 5px top and bottom, with the threshold
value as a `--fs-tick` mono label above it.

**`<ScoreChip>`** pairs with it: mono, 600 weight, pill radius, a 6px `currentColor`
dot, and the same three states. Renders `92 · Qualifying`, `71 · Near-miss`,
`48 · Below`.

> **✓ Resolved (ADR-033) — the near-miss band boundary.** The band is a
> **fixed-width offset below the active threshold**: `NEAR_MISS_BAND` (default `15`),
> backend-owned. `nearMissFloor = threshold − NEAR_MISS_BAND`. A job is `nearmiss`
> when `nearMissFloor ≤ score < threshold`, `qualify` when `score ≥ threshold`,
> `below` otherwise. The backend returns `threshold` **and** `nearMissFloor` **per
> job** (threshold is per-profile, stored on the evaluation row); `<ThresholdRail>`
> reads the job's own values and **never** a global threshold. This one rule also
> feeds the email near-miss cards, the CSV, and the zero-results suggested threshold,
> replacing the old floor-the-lowest-of-five rule.

---

## Component vocabulary

| Component | Notes |
|---|---|
| `<ThresholdRail>` | Above. Reused everywhere a score appears. |
| `<ScoreChip>` | Three states, mono, dot + value + label. |
| Buttons | `primary` (accent bg) · `secondary` (surface + strong border) · `ghost` (transparent, accent text) · `danger` (transparent, danger border/text). Buttons name what they do — "Run search now", not "Submit". |
| `<StatusPill>` | Nine job statuses. Visual grouping per `ui-spec.md` §4. |
| Run status dots | 8px dot + label: running (`--accent`), delivered (`--qualify`), zero results (`--nearmiss`), failed (`--danger`). |
| `<ProviderBadges>` | Uppercase mono, 11px, `--ls-badge` tracking, `--surface-2` bg, `--r-control`. **A set** — a job can be seen on several platforms. |
| Skill pills | `have` → `--accent-soft` bg + `--accent` text. `miss` → `--surface-2` bg, `--text-3`, **strikethrough**. |
| Cards / panels | `--surface`, 1px `--border`, `--r-card`. No shadow. |
| Data table | Mono uppercase `th` at `--fs-label`, `--text-3`. Numeric cells `td.num` in mono, colored by score state. |
| Form fields | 13px 600 label, `--bg` input on `--border-strong`, `--r-control`, `--fs-caption` hint in `--text-3`. Cron and other data inputs use `--font-mono`. |

---

## Tailwind wiring

`tokens.css` is imported once, then mapped. Colors reference the CSS variables so
the dark theme works by flipping `data-theme` on `<html>` — no Tailwind dark-mode
class duplication.

```js
// tailwind.config.js
export default {
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
        qualify:  { DEFAULT: "var(--qualify)",  soft: "var(--qualify-soft)" },
        nearmiss: { DEFAULT: "var(--nearmiss)", soft: "var(--nearmiss-soft)" },
        below:    { DEFAULT: "var(--below)",    soft: "var(--below-soft)" },
        danger:   { DEFAULT: "var(--danger)",   soft: "var(--danger-soft)" },
      },
      fontFamily: {
        display: "var(--font-display)",
        body:    "var(--font-body)",
        mono:    "var(--font-mono)",
      },
      fontSize: {
        display: "var(--fs-display)",
        h1:      "var(--fs-h1)",
        h2:      "var(--fs-h2)",
        h3:      "var(--fs-h3)",
        body:    "var(--fs-body)",
        control: "var(--fs-control)",
        small:   "var(--fs-small)",
        caption: "var(--fs-caption)",
        label:   "var(--fs-label)",
        tick:    "var(--fs-tick)",
      },
      borderRadius: {
        card:    "var(--r-card)",
        control: "var(--r-control)",
        pill:    "var(--r-pill)",
      },
      spacing: {
        1: "var(--s1)", 2: "var(--s2)", 3: "var(--s3)", 4: "var(--s4)",
        5: "var(--s5)", 6: "var(--s6)", 7: "var(--s7)", 8: "var(--s8)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "250ms",
      },
    },
  },
};
```

Fonts load from Google Fonts: Bricolage Grotesque (500/600/700), Inter (400/500/600),
IBM Plex Mono (400/500/600).

---

## Dark mode — decide before W1

The design system ships a **complete dark palette**, but `ui-spec.md` never mentions
dark mode and no screen mockup shows it. Two coherent positions:

- **Ship it.** The tokens already exist; cost is a `data-theme` toggle, persisting
  the choice (in React state, *not* localStorage), and testing both palettes. Low
  marginal cost *if* every component uses tokens from day one.
- **Defer it.** Keep the dark block in `tokens.css` as a reservation. Cost of adding
  later is near zero — *provided* no component ever hardcodes a color.

Either way the discipline is identical: **use the tokens.** Decide explicitly rather
than discovering at W6 that half the components have literal hexes.
