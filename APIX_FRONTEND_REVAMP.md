# APIx Frontend Revamp (v2): Brief for Cursor / Antigravity

> How to use: put this file in the project root. Tell the agent: "Read APIX_FRONTEND_REVAMP.md. Follow section 12 in order. Do not write UI code until section 12, step 0 is done. After each step, show screenshots and wait for my go-ahead."
>
> This replaces the visual layer of `web/` completely. The API, the data types and the honesty rules stay. Everything you can see (layout, colour, type, components, chart styling, copy) is rewritten.

---

## 1. Why the current UI reads as AI-made

Read this so you know what not to reproduce. Each point is visible in the current build.

**Whole app**
- Near-black navy surface, one blue accent, one purple secondary. This is the default "dark analytics dashboard" look.
- Every block is the same rounded, bordered box with the same padding. Hierarchy comes only from text size.
- Pill-shaped nav tabs and pill filter buttons. Default browser range sliders. The wordmark colours one letter ("API" and a blue "x").
- Grey italic serif captions sit on top of a sans UI. They clash and are hard to read against the dark surface.
- Small grey text on dark has low contrast throughout.

**Index screen**
- The hero is a big number, a tiny label and a floating delta. That is the default hero for any metrics page. A fall is coloured blue, which carries no meaning, and no words explain what happened.
- Lines are drawn with a smoothing curve. The data is one value per day, so smoothing draws values that never existed.
- The legend shows a "Real" line although no real data exists. Synthetic status is a purple pill, not something the chart itself shows.
- The weights panel is four default sliders and a duplicate "Normalised weights" table. It also prints "1 days".

**Lead time screen**
- It is not a ridgeline. The ridges do not overlap, share no visible scale and have no axes, and the plot fills only the left half of its box. Sixty near-identical shapes give no way to read a price.
- There are visible steps at the 15-day and 7-day marks. They come from how the synthetic prices are generated.

**Method screen**
- It shows raw config keys (`nonstop_only`, `price_statistic`), which is the system's vocabulary, not the reader's.
- "Lead Level" and "Route Level (same)" describe one step twice, in Title Case.
- Amber pill badges label assumptions, and the limitations are a quote-style list with a left rule.

**Run log**
- Sixty identical rows (`ok / synthetic / 12 / 0`) say one thing sixty times.

---

## 2. What stays and what goes

**Keep:** the API client and types, routing, the TypeScript recompute of the index (fix it if wrong), the three views and their purposes, the labelling of synthetic data, and the weights-recompute feature.

**Replace:** all CSS, layout, components, chart styling, icons, copy and the design tokens. Delete unused UI dependencies. No component library (shadcn, MUI, Chakra, Radix Themes) and no framework default palette.

Views after the revamp (renamed in plain words): **Index**, **Booking curves**, **Method**.

---

## 3. Direction: "chart paper"

**Reference (use it, don't imitate it):** aeronautical sectional charts and cockpit display typography. Charts are printed in two or three inks on pale paper, with direct labels on the features and no legends or boxes. Cockpit type is designed so digits stay unambiguous at a glance. That is exactly what an index page needs.

Consequences for the design:
- **The chart is the page.** There is no hero block above it. The current reading is annotated on the chart, and a plain sentence states what happened.
- **Direct labels, not legends.** Series are named at the end of their lines.
- **No cards.** Sections are separated by space and headings. A rule appears only where it encodes something (for example the boundary between synthetic and real data).
- **Light paper, two inks and a mark.** It is deliberately not dark mode.

Spend the boldness in one place: **the linked scrubbing between charts** (section 7.2). Everything else stays quiet.

### 3.1 Tokens

```css
:root {
  --vellum:      #F0F2EE;  /* surface */
  --ink:         #1A2B3C;  /* text and the overall series */
  --ink-2:       #4A5A68;  /* secondary text, axes (6:1 on vellum) */
  --contour:     #C9D0CB;  /* gridlines and hairlines, never text */
  --route-blue:  #2A5FA5;  /* DEL-BOM */
  --route-mag:   #B0286A;  /* DEL-BLR */
  --route-teal:  #2F7D6D;  /* BOM-BLR */
  --hatch:       #A8916A;  /* synthetic-data hatch lines only */
  --assumed:     #8A5600;  /* the word "assumed" in text (5:1) */
  --focus:       #B0286A;
}
```

Direction (up or down) is shown by words and signed numbers, never by red or green. Route colours are categorical, and every series is also named by a direct label.

### 3.2 Type

Two families, clearly different:
- **B612** (designed by Airbus for cockpit displays): everything in the interface and every number. Weights 400 and 700 only. `npm i @fontsource/b612`.
- **Newsreader** (variable): the headline sentence and explanatory prose only. `npm i @fontsource-variable/newsreader`.

Check that B612's digits align in columns (`font-variant-numeric: tabular-nums`). If they do not, use B612 Mono for numeric table columns only, never for labels.

Scale (set as variables, use nothing else):
| Role | Face | Size and line-height |
|---|---|---|
| Headline sentence | Newsreader 400 | clamp(28px, 3.4vw, 44px) / 1.15, max-width 30ch |
| Prose | Newsreader 400 | 18px / 1.55, max-width 66ch |
| Reading on chart | B612 700 | 28px / 1.1 |
| UI and labels | B612 400 | 14px / 1.4 |
| Axis text | B612 400 | 12px / 1.3, `--ink-2` |

Forbidden: all-caps labels, tracked-out text, italics, an accent colour or style on one word of a headline.

### 3.3 Shape

- Border radius: 0, or 2px on interactive controls. Nothing else.
- No shadows, gradients, blur or glass.
- Toggles are text buttons with `aria-pressed`. The active one is underlined in `--ink` (2px, offset 4px). No pills.
- Focus: 2px `--focus` outline, 3px offset, always visible.

---

## 4. Layout

Content column max-width 1200px, left-aligned text, generous vertical space. The header is a single line.

### 4.1 Index, desktop (1440 wide)

```
+------------------------------------------------------------------------------+
| APIx      Index   Booking curves   Method               Data through 19 Sep  |
+------------------------------------------------------------------------------+
|                                                                              |
|  Fares fell 0.7% on 19 September,                                            |
|  mostly on DEL-BLR.                                                          |
|  The index is 95.67 (22 July = 100). All data shown is synthetic.            |
|                                                                              |
|  104 |  hatched band = synthetic dates                                       |
|      |     /\    /\    /\                                       Overall 95.67|
|  100 +- - - - - - - - - - - - - - - - - - - - - - - - - - - - - DEL-BOM 96.1|
|      |                                                          DEL-BLR 94.9|
|   92 |                                                          BOM-BLR 96.4|
|      +-----+-------+-------+-------+-------+-------+------                  |
|          25 Jul   8 Aug   22 Aug   5 Sep                                     |
|  Daily  Weekly  Monthly                                                      |
|                                                                              |
|  What if the weights were different?          Lead times | Routes            |
|  [ 1 day 25% | 7 days 25% | 15 days 25% | 30 days 25% ]      Reset           |
|  With these weights the index differs from the default by at most 0.6 points.|
|                                                                              |
|  Collection record   |||||||||||||||||||||||||||||||||||   60 of 60 runs ok  |
+------------------------------------------------------------------------------+
```

### 4.2 Index, mobile (390 wide)

```
APIx        Index  Curves  Method
-----------------------------------
Fares fell 0.7% on 19 September,
mostly on DEL-BLR.
The index is 95.67 (22 July = 100).
All data shown is synthetic.

[ chart, full width, 55vh, labels at
  line ends shrink to route codes ]
Daily  Weekly  Monthly

What if the weights were different?
[ 1d | 7d | 15d | 30d ]   Reset
Differs by at most 0.6 points.

Collection record ||||||||||||||
60 of 60 runs ok
```

The agent may change these wireframes if it can justify a better arrangement in `docs/design-notes.md`, but must keep the chart-first structure and the absence of cards.

---

## 5. Index view

### 5.1 Headline sentence (generated from data, template-based)
Reflects the selected date (default: latest).
- Format: `Fares {rose|fell} {x.x}% on {d MMMM}, {mostly on ROUTE|across all routes}.`
- If the absolute change rounds to 0.0: `Fares were unchanged on {d MMMM}.`
- For weekly and monthly frequency: `Fares rose 1.4% in the week of 7 September.` and `... in September.`
- "Mostly on ROUTE": compute each route's contribution `w_j * (R_j - 1)`. If one route's absolute contribution is at least 60% of the sum of absolute contributions, name it. Otherwise say "across all routes".
- The line under it: `The index is 95.67 (22 July = 100).` Then the data status sentence (section 8).

### 5.2 IndexChart (hand-built SVG, D3 scales and shapes)
- Series: overall (2.5px, `--ink`) and one thin line (1.25px) per route in its colour.
- **Straight segments only** (`curveLinear`). At 45 visible points or fewer, draw a small dot for each daily value on the overall line.
- Null levels (low coverage) break the line. They are not interpolated.
- A base line at 100 in `--ink-2`, 1px, labelled at its left end: "Base = 100 (22 July)".
- Horizontal gridlines in `--contour`, 1px. No vertical gridlines. Y domain from the visible data, padded, and always including 100.
- Dates parsed as UTC so labels never shift a day.
- **Synthetic data is part of the chart:** dates with `is_synthetic` sit on a diagonal hatch (`<pattern>` in `--hatch`, low opacity), with the text "Synthetic data" written once inside the band. When real rows exist, a vertical line marks "Fares collected from here". The legend, the pill and the badge are gone.
- **Direct labels** at the right end of each line: name and latest value, with a minimum vertical gap of 16px between labels (sort by y and nudge).
- **Scrub:** moving the pointer or pressing the left and right arrow keys sets `selectedDate`. A hairline cursor follows it, the end-of-line values become the values at that date, and the headline sentence updates. Escape returns to the latest date. Make the chart focusable and announce the readout in an `aria-live="polite"` region.
- Hovering a route label fades the other lines to 25% opacity. That is a response to an action, so it is allowed.

### 5.3 What-if weights (WeightBar)
Replaces the four sliders and the normalised table.
- **One horizontal bar split into segments**, one per lead window (1, 7, 15, 30 days) or one per route. Dragging the divider between two segments moves weight from one neighbour to the other, so weights always sum to 100%. Snap to 1%.
- Each divider is `role="slider"` with `aria-valuenow`, and supports Left and Right (1%) and Shift plus arrows (5%).
- Segment labels sit under the bar: `1 day 25%`, `7 days 25%` (correct singular and plural).
- A text toggle "Lead times | Routes" switches which set is edited. "Reset" restores the defaults.
- On the chart, the default-weight overall line stays as a thin `--ink-2` line ("Default weights") while the recomputed line is the thick `--ink` line. Show the ghost only when the weights differ.
- Under the bar, one sentence with the sensitivity result: `With these weights the index differs from the default by at most 0.6 points (on 3 September).` This sentence is the point of the feature.
- Recompute in the browser from `/api/relatives`. Write the maths in `src/lib/indexMath.ts` exactly as the Python (bands to lead windows by geometric mean, lead windows to route by weighted geometric mean, routes to overall by weighted arithmetic mean, chained from 100, weights renormalised over what is present).
- **Parity test (vitest):** with the default weights, the recomputed levels equal the API's `level` values to 1e-6, using a saved fixture.

### 5.4 Collection record strip
A single-line strip, one tick per run date. Tick = `--ink` for ok, an open outline for partial, a crossed tick in `--route-mag` for failed. Hover or focus gives the date and the reason. To the right: `60 of 60 runs ok.` If there are exceptions, list only those below the strip, in plain sentences (`12 September: partial, DEL-BLR 15 days page blocked`).

---

## 6. Booking curves view

Purpose: show what a traveller pays for booking early versus late, and how that has moved.

- Title and one sentence of prose: `Each line is one day's fares, from 30 days before departure to the day before. Darker lines are more recent.`
- Text toggle: `Fare in rupees | Indexed to 30 days = 100`. Indexed is the default so routes with different price levels compare by shape.
- **Three small panels side by side (stacked on mobile), one per route, sharing one y scale** in the current mode. X runs toward departure: 30 days out on the left, 1 day out on the right, with ticks at the four lead windows. Y has visible tick labels.
- One thin line per observation day, coloured on a single-hue ramp from `#C9D6E6` (oldest) to `--ink` (latest). The latest day is 2.5px. Straight segments between the four lead windows, with a dot at each.
- Hovering or scrubbing highlights one day and shows a readout: `12 August: ₹4,180 at 30 days, ₹8,940 at 1 day`.
- **The selected date is shared with the Index view** (kept in the URL as `?d=2026-09-12`). Scrubbing on Index moves the highlighted line here.
- Below the panels, one line chart: **late-booking premium**, meaning how much more a fare 1 day out costs than 30 days out, per route over time, with direct labels. Compute it client-side from `/api/lead-curve`.
- If the data has fewer than 5 observation days, show the panels with what exists and say so in a sentence.

---

## 7. Method view

Prose first, in Newsreader, 66ch wide. No table of config keys.

1. **What this measures.** Two or three sentences: displayed fares for a fixed set of flights, not what travellers paid.
2. **How the index is built,** in plain steps (this is a real sequence, so a numbered list is right):
   1. Each flight group (route, days ahead, departure time band) is priced at its cheapest nonstop economy fare each day.
   2. Each group's price is compared with its previous price. The change is a ratio.
   3. Ratios for the departure bands within a lead window are combined with a geometric mean.
   4. Lead windows are combined into a route with a weighted geometric mean.
   5. Routes are combined into the overall figure with a weighted average, and the result is chained forward from 100.
3. **A worked example from the latest day,** computed live from the API. Take the route with the largest contribution and show its actual numbers: the band ratios, the geometric mean, the lead-window ratios, the route ratio, and its contribution to the day's change. This is the trust device of the page.
4. **Rules used,** as a two-column definition list in plain words:
   | Label | Value |
   |---|---|
   | Fare class | Economy |
   | Flights counted | Nonstop only |
   | Price used for each group | Lowest fare |
   | Unusual fares | Kept in the index and flagged |
5. **Weights.** Two small tables (routes, lead windows). The word `assumed` in `--assumed` appears in a column where the weight is an assumption, with one footnote: `Route weights are placeholders until replaced with passenger shares from DGCA city-pair data. Lead-window weights are equal by assumption; the what-if bar on the Index page shows how much they matter.` No badges.
6. **Limits,** written as short paragraphs, not a bulleted list with a left rule:
   - Displayed fares, not paid fares.
   - A short real history cannot be compared with monthly official series; validation rests on the synthetic recovery test.
   - One source only; production would use data-sharing agreements.
   - Day-over-day changes include weekday effects because the departure date moves each day.
7. **Collection record,** the full table, inside a `<details>` element titled "All runs".

---

## 8. Copy

Sentence case, plain verbs, specific, no filler, no marketing language. Names are what an analyst would say.

| Situation | Text |
|---|---|
| All data synthetic | `All data shown is synthetic. No fares have been collected yet.` |
| Mixed | `Data before 20 September is synthetic. Fares were collected from 20 September.` |
| Empty (no rows) | `No fares collected yet. The first run is scheduled for 05:00 IST.` |
| API down | `Couldn't load the index. The API at {url} didn't respond. Start it with make api, then reload.` |
| Low coverage day | `No index for 12 September: only 40% of fare groups had prices (minimum 50%).` |
| Header status | `Data through 19 Sep 2026` |
| Counts | Use a helper: `1 day`, `7 days`. Never `1 days`. |

Do not use middle-dot separated strings, arrows on links or buttons, or `WORD: fragment` labels. Errors do not apologise. An action keeps one name everywhere ("Reset" stays "Reset").

---

## 9. Motion

- One orchestrated moment at page load: the lines draw in from left to right over about 900ms, route lines first and the overall line last.
- After that, motion only answers actions: scrubbing, hovering a label, dragging a weight (the recomputed line eases over about 120ms), switching frequency.
- Respect `prefers-reduced-motion` (no draw-in, no easing).
- No fade-and-slide on sections, no hover lift, no animated counters.

---

## 10. Accessibility and responsive floor

- Contrast at least 4.5:1 for text. Never use colour alone to carry meaning (labels and words always accompany colour).
- Every chart sits in a `<figure>` with a text summary and a `<details>` "Show data as table".
- Full keyboard use: nav, toggles, chart scrub, weight dividers, the record strip.
- Works at 390px wide without horizontal page scroll. Tap targets at least 40px.
- Semantic landmarks (`header`, `nav`, `main`), one `h1` per view, correct heading order.

---

## 11. Design lint (add it, and run it in `make test`)

Save as `scripts/design-lint.sh`. It fails when the UI drifts back to generic defaults.

```bash
#!/usr/bin/env bash
# Fails if the frontend drifts back to generic defaults.
cd "$(dirname "$0")/../web/src" || exit 1
bad=0
check() {
  if grep -RIn -E "$1" . >/dev/null 2>&1; then
    echo "FAIL: $2"; grep -RIn -E "$1" . | head -5; bad=1
  fi
}
check "linear-gradient|radial-gradient|conic-gradient"  "no gradients"
check "backdrop-filter"                                  "no glass effects"
check "box-shadow"                                       "no shadows"
check "text-transform:[[:space:]]*uppercase"             "no all-caps labels"
check "letter-spacing:[[:space:]]*0?\.[1-9]"             "no tracked-out text"
check "border-radius:[[:space:]]*([3-9]|[1-9][0-9])px"   "radius above 2px"
check "border-radius:[[:space:]]*[0-9.]+rem"             "radius in rem"
check "curveBasis|curveCatmullRom|curveMonotone|curveCardinal|curveNatural" "no smoothed curves"
check "font-style:[[:space:]]*italic"                    "no italics"
check "className=[\"'][^\"']*\bcard\b"                   "no card components"
check "→|·"                                              "no arrows or middle dots in UI text"
exit $bad
```

---

## 12. Build order and review protocol

**Step 0. Audit and plan (no UI code).** List the current components and delete the old styles. Write `docs/design-notes.md` with the tokens, the type scale, the two wireframes as adapted, and any deviation from this brief with a reason. Then answer in the file: "If I removed the wordmark, would this look like any other dashboard?" If yes, revise.

**Step 1. Shell.** Fonts, tokens, header, nav, the headline sentence with real data.

**Step 2. IndexChart.** Hatch, direct labels, base line, scrubbing, headline updating.

**Step 3. WeightBar and recompute,** with the parity test.

**Step 4. Collection record strip.**

**Step 5. Booking curves,** including the shared selected date.

**Step 6. Method page** with the live worked example.

**Step 7. Polish.** Responsive, accessibility, `scripts/design-lint.sh` passing.

**After every step, review:**
1. Take screenshots of each view at 1440x900, 1024x768 and 390x844 (use the browser tool).
2. Squint test: what is the one memorable element? Is everything else quiet?
3. Is any block a box or card? Is any element decoration that encodes nothing?
4. Does any text fail contrast? Does any label use system vocabulary?
5. Fix, then remove one decorative element and record which in `docs/design-notes.md`.

---

## 13. Data problems that make the UI look fake (fix in `seed_synthetic.py`)

These are visible in the current screenshots and no styling will hide them.

- **The weekly wave repeats identically** every week, so the index looks like a sine wave. Reduce the weekday effect, add autocorrelated noise, and add three or four irregular demand bumps of 3 to 7 days with different heights.
- **The booking curves have steps** near 15 and 7 days out. Generate the lead-time curve as a smooth, monotone function of lead time (for example a price multiplier of `1 + a * exp(-lead / tau)`, with route-specific `a` and `tau`) plus per-quote noise.
- **Every run is `ok`.** Seed two or three partial runs and one failed run so the record strip and the low-coverage state have something to show.
- **The legend showed a "Real" series with no real data.** Draw only what exists.
- Keep a fixed random seed for reproducibility, but do not let the seed produce a fixed pattern.

---

## 14. Acceptance checklist

- [ ] `scripts/design-lint.sh` passes.
- [ ] No cards, shadows, gradients, pills or dark theme anywhere.
- [ ] The chart is the first thing on the page, and a generated sentence states what happened.
- [ ] Synthetic data is marked inside the chart (hatch band and label), not by a badge.
- [ ] Lines are straight segments with visible daily points.
- [ ] Scrubbing updates the headline, the readout and, on Booking curves, the highlighted day.
- [ ] The weight bar keeps weights at 100%, works with the keyboard, and reports the sensitivity result in a sentence.
- [ ] The TypeScript recompute matches the API levels at default weights (parity test).
- [ ] Booking curves have a shared visible y scale, axes and a date ramp; the layout fills its container.
- [ ] The Method page has no raw config keys and includes a live worked example.
- [ ] The collection record is a strip, with exceptions written out.
- [ ] Works at 390px, with keyboard only, and with reduced motion.
- [ ] `docs/design-notes.md` records the plan, deviations and the one element removed.
