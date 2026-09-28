# AERIX Index Page Redesign (v4): Brief for Cursor / Antigravity

> How to use: put this in the project root. Tell the agent: "Read APIX_INDEX_PAGE_REDESIGN.md. This replaces the Index page's structure only — Overview, Booking curves, Method, the design tokens and the design-lint script are unchanged. Follow section 6 in order."

---

## 1. Diagnosis: why the Index page looks empty

Look at what's actually on screen by default right now: a headline sentence, one line of inline stats, a row of four tab buttons, and — under the first tab — a single table. **The chart is not visible.** It's one click away, behind a tab labelled "History." So is the lead-time snapshot ("Average price by lead time") and the what-if weight bar ("What if the weights were different?"). You built four reasonable pieces of content and then hid three of them, which is why the page a visitor actually lands on is mostly whitespace and one table.

This also explains the "not much interactivity" feeling. The interactivity (scrubbing, the weight bar) exists in the brief but isn't reachable without clicking through tabs first, so nobody finds it.

**The fix is structural, not decorative:** stop using tabs to gate the primary content of a single page. A tab bar is for switching between genuinely separate views (which is right for the top-level nav: Overview / Index / Booking curves / Method). It's the wrong tool for sections of one view that a visitor should see by scrolling.

---

## 2. New architecture: one page, five sections, no gating tabs

Delete the "Routes / Average price by lead time / History / What if the weights were different?" tab bar. Replace it with a single scrolling page in this order. Every section is always present; nothing is hidden behind a click except the two `<details>` elements noted below.

```
1. Headline + status (kept from v2/v3, unchanged)
2. THE CHART — full width, dominant, visible immediately
3. Route strip — one compact row per route, with a sparkline
4. Lead-time snapshot — today's price by lead window, small multiples
5. What-if weights — the draggable bar, directly below the chart's controls
6. Collection record strip (specified in v2 §5.4, never actually shipped — add it now)
```

Each is detailed below. None of them is a card; they're separated by a plain rule and a heading, in the same voice as the Method page's prose.

---

## 3. Section 2: the chart (make it the page)

This is the single biggest fix. Right now nothing here is visible by default; after this section it is the first thing under the headline.

- **Default view on load:** the overall index line plus all three route lines, full history, daily frequency. No tab click required to see it.
- **Controls live on the chart itself**, as a row of plain text toggles directly above or below the plot — not as a separate nav tab:
  - Frequency: `Daily  Weekly  Monthly`
  - Range: `30d  90d  All`
  - Series: click a route's direct label to solo it (fade the others to 25%); click again to restore all. This replaces "Average price by lead time" living elsewhere — route focus happens right where the routes already are.
- **Annotations, so the chart has something to say.** A flat line with no context is part of why it reads as empty even once it's visible. Add small marks on the x-axis for:
  - The date real collection started (already known: 3 October) — a short vertical tick with the label "Real data starts" pinned at the hatch boundary (this already exists per v2/v3; make sure it's the first thing your eye hits).
  - Any point where the day-over-day change exceeds a threshold (for example ±3%) — a small dot on the line with a one-line tooltip on hover/focus: `12 Aug: +4.1%, mostly DEL-BLR`. Compute this from the relatives you already have; don't hand-author it.
  - If the synthetic generator has festival or demand-bump periods (per the v2 seed-data fix), mark the bump window with a very light vertical band and a small label ("Diwali demand" or whatever the seed's actual event is called) so the chart reads as a real, eventful series instead of noise.
- **Everything else from the v2 brief stays:** straight segments only, hatch band for synthetic dates, direct end-of-line labels, scrubbing with hairline cursor and arrow-key support, `aria-live` readout, the base-100 reference line.

---

## 4. Section 3: route strip (replaces the plain table)

The current table (route, weight, index, lead times, status) is correct information but reads as flat and small. Turn each row into a compact strip with a sparkline, so the page carries more at a glance without adding boxes:

```
DEL-BOM     [small 60-day sparkline, --route-blue]     100.00   +1.9%   live since 3 Oct   weight 35%
DEL-BLR     [small 60-day sparkline, --route-mag]      100.45   +0.4%   synthetic history   weight 35%
BOM-BLR     [small 60-day sparkline, --route-teal]      99.82   -0.2%   synthetic history   weight 30%
```

- One `<svg>` sparkline per row (40–50px tall, no axes, no gridlines — it's a glance object, the real chart above is where you read exact values).
- Clicking a row solos that route on the main chart above and scrolls it into view if needed (reuse the "click a direct label" behaviour from section 3).
- Status text and weight must be pulled from the same source as Method's weights table (this is the fix for the DEL-BOM-at-35%-vs-100% mismatch flagged earlier — one config value, rendered in two places, never typed twice).
- Route order is fixed and identical everywhere in the app (Overview, this strip, Method).

---

## 5. Section 4: lead-time snapshot (small multiples)

This is the content that was called "Average price by lead time." Give it a permanent, visible home instead of a tab:

- One row of three small charts, one per route (stacks on mobile), each showing **today's price at each tracked lead window** (1, 7, 15, 21, 30, 45 days) as a simple dot-and-line plot, x-axis = lead window, y-axis = price.
- Directly under it, one sentence generated from the data: `Booking 1 day ahead costs {x}% more than 30 days ahead on {route}.` (pick the route with the largest gap).
- Link this sentence and the mini-charts to the full Booking curves page: `See the full booking curves →` — this is a legitimate use of an arrow (an in-page link to another view), same rule as the Overview page.
- If a route has no real data yet, the snapshot uses its synthetic series and says so in the same small note style as Booking curves ("DEL-BLR: synthetic history only").

---

## 6. Section 5: what-if weights

Move the weight bar (already specified in the v2 brief, section 5.3) here, always visible, directly under the lead-time snapshot. Nothing about its own design changes — only its location: it stops being a fourth tab and becomes a normal part of the page a visitor scrolls into.

---

## 7. Section 6: collection record strip

This was specified in the v2 brief (§5.4) but isn't present in any screenshot so far — add it now. One line, one tick per run date (ok / partial / failed), with the exceptions written out below it in a sentence, exactly as originally specified. It's a good, quiet way to end the page with evidence of how the pipeline is actually running, rather than ending abruptly after the weights bar.

---

## 8. Two bugs to fix in the same pass (carried over, still open)

1. **Route weights must match everywhere.** Method's route-weights table currently shows only DEL-BOM at 100%, while this page shows 35/35/30. Fix Method's table to list all three routes with the same numbers as the route strip (section 4), sourced from the same place.
2. **Remove the duplicate "Fare in rupees" line** on Booking curves, directly under the unit toggle — it's a leftover render of the selected state.

---

## 9. What "more interactive" means here (so it doesn't turn into decoration)

Every new interactive element must change what's shown, not just move or animate:
- Scrub → readout and headline update (already specified).
- Click a route label or strip row → solo that route on the chart (new).
- Hover/focus an annotation dot → a one-line tooltip with the real number (new).
- Drag a weight divider → chart's overall line recomputes (already specified, now visible without a click).
- Frequency and range toggles → chart redraws (new, replaces the separate "History" tab).

Nothing here should be a hover animation, a card lift, or motion with no informational payload — that would be reintroducing the generic-dashboard feel this project has been deliberately avoiding.

---

## 10. Build order and review

**Step 1.** Remove the four-tab bar. Reorder the page to sections 2–6 above, chart first.
**Step 2.** Move frequency/range/series controls onto the chart itself; wire up soloing from both the chart labels and the route strip.
**Step 3.** Add chart annotations (real-data start, notable-change dots, synthetic event bands) computed from data, not hand-typed.
**Step 4.** Build the route strip with sparklines, sourced from the same weight/status data as Method.
**Step 5.** Build the lead-time snapshot small multiples and its link to Booking curves.
**Step 6.** Move the what-if weight bar into place; add the collection record strip.
**Step 7.** Fix the two carried-over bugs (section 8).

**After every step:** screenshot at 1440x900 and 390x844, and check: is the chart the first thing you see under the headline? Is anything on the page still gated behind a tab that isn't top-level nav? Does every new element change something when you interact with it? Re-run the design-lint script — it should still pass unchanged.

---

## 11. Acceptance checklist

- [ ] The index chart is visible immediately on page load — no tab click required.
- [ ] No tab bar exists on the Index page except the top-level app nav (Overview / Index / Booking curves / Method).
- [ ] Frequency, range, and route-soloing controls live on or beside the chart.
- [ ] The chart carries at least one generated annotation (the real-data-start marker plus any notable-change dots the data produces).
- [ ] The route strip shows a sparkline per route and matches Method's weights table exactly.
- [ ] The lead-time snapshot is visible on the page (not a separate tab) and links to Booking curves.
- [ ] The what-if weight bar is visible on the page without a click.
- [ ] The collection record strip is present at the bottom of the page.
- [ ] Both carried-over bugs (route-weight mismatch, duplicate rupees line) are fixed.
- [ ] The design-lint script still passes; no cards, shadows, or gradients were introduced while adding these sections.
