# APIx Frontend: Design Plan

## Reference

**Aeronautical Sectional Charts** — the instrument the pilot uses to read terrain, airways and navigation data at a glance. Characteristics: a quiet, functional ground colour (pale blue-grey for controlled airspace, tan for terrain), dense information at different scales, numbered airways, thin lines encoding distance and bearing, and a total absence of decoration.

The interface derives from this visual language: a calm surface, purposeful ink, one data layer dominant at a time.

---

## Palette

| Name | Hex | Role |
|---|---|---|
| `--col-surface` | `#0f1117` | Page background (night airspace) |
| `--col-paper` | `#171b24` | Panel/card surface |
| `--col-border` | `#252c3a` | Dividers, chart axes |
| `--col-ink` | `#e8eaf2` | Body text, labels |
| `--col-ink-muted` | `#6b7280` | Secondary labels, metadata |
| `--col-primary` | `#5b9cf6` | Main data line (VFR blue) |
| `--col-compare` | `#f6955b` | Comparison / second route (warm orange) |
| `--col-alert` | `#f6c25b` | Low coverage, anomaly warning (amber) |
| `--col-synthetic` | `#7c6af6` | Synthetic data line (violet — distinct from real) |

All six roles checked for contrast ≥ 4.5:1 against `--col-surface`.

---

## Typography

**Two families, maximally different:**

| Family | Use | Setting |
|---|---|---|
| IBM Plex Sans Condensed (400, 500) | Labels, numbers, axes, nav, metadata | `font-variant-numeric: tabular-nums` |
| Newsreader (400 italic) | Annotations only, body description text, empty states | Italic for voice |

Type scale:
- `--text-xs`: 11px — axis ticks, metadata
- `--text-sm`: 13px — labels, table rows
- `--text-base`: 15px — body, nav
- `--text-lg`: 20px — panel headers
- `--text-xl`: 28px — index reading
- `--text-2xl`: 48px — today's index (dominant number)

Lines ≤ 72 characters. Tabular numerals everywhere.

---

## Layout Concept

```
┌─────────────────────────────────────────────────────────────────┐
│  APIx  Fare Index  ·  [Index] [Lead time] [Method]              │  nav bar
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   TODAY'S INDEX   101.23     ▲ 0.38%    Coverage 89%           │  hero strip (compact)
│   Synthetic data shown — clearly labelled                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                                                                 │
│   [  MAIN INDEX CHART — hand-built SVG, full width  ]          │  dominant
│   Crosshair readout, low-coverage shading, synth hatching       │
│                                                                 │
│                                                                 │
├──────────────────────────┬──────────────────────────────────────┤
│  Routes (small multiples)│  Weights panel                      │
│  DEL-BOM  ───────────    │  Adjust lead-time weights           │
│  DEL-BLR  ───────────    │  [sliders] → index recomputes       │
│  BOM-BLR  ───────────    │  in browser from /api/relatives     │
└──────────────────────────┴──────────────────────────────────────┘
```

Mobile (390 px): nav collapses to hamburger; hero strip single column; chart full-width; small multiples stacked; weights panel below.

---

## The Signature Element

**Ridgeline of booking curves** on the Lead-time view:

- Y-axis: observation date (oldest at bottom)
- X-axis: days-to-departure (30 → 1, right = nearer)
- Each horizontal slice = one observation day's price-vs-lead curve
- Curves stacked in date order; the stack lifts when fares rise
- Filled with a semi-transparent primary colour; where a date is synthetic, the fill changes to the synthetic violet
- Pointer scrub selects a date and shows the curve's values in a callout

This visualisation makes the two key patterns visible at once: whether fares are rising or falling, and whether the lead-time curve is steepening (scarcity) or flattening (oversupply).

---

## Principles

1. **Information first.** The chart is the page; the UI chrome is minimal.
2. **One dominant element per view.** Index view: the line chart. Lead view: the ridgeline. Method view: the data table + formula text.
3. **Colour encodes meaning.** Primary blue = real index. Violet = synthetic. Amber = warning (low coverage, anomaly). Orange = comparison. No colour-only distinctions — hatching or labels always back them up.
4. **Motion answers actions only.** The index line draws in on first load (single orchestrated moment). After that: hover crosshair, route selector toggle, weights slider redraw. All respecting `prefers-reduced-motion`.
5. **Typography is the personality.** IBM Plex Sans Condensed's compressed, legible numerals give the dashboard a professional instrument feel without the clichés of monospace decoration.
6. **Honesty.** Synthetic rows clearly labelled with "Synthetic" badge. Empty states say what happened and what to do. Coverage percentages shown in context, not hidden.

---

## Avoid-list Check

- ❌ Cream + serif + terracotta → using dark ground + condensed sans
- ❌ Neon on near-black → primary is steel blue, not acid
- ❌ Newspaper look with hairlines → functional axes only
- ❌ Rounded cards with grey shadow → `--col-paper` panels with `--col-border` edges, no box-shadow
- ❌ Gradient text, glassmorphism → none
- ❌ Row of four identical stat tiles → compact hero strip only
- ❌ ALL-CAPS eyebrows, middle-dot meta, arrows on links → sentence case throughout
- ❌ Numbered markers → no
- ❌ Fade-and-slide-up on every section → one draw-in animation, then nothing
- ❌ Emoji or icon walls → no icons except a focus-ring indicator
- ❌ Monospace everywhere → IBM Plex Sans Condensed, not monospace
- ❌ Marketing copy → "Fare index", "Lead time", "Coverage"
