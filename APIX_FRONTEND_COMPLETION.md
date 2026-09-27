# APIx Frontend Completion Plan (v3): Master Brief for Cursor / Antigravity

> How to use: put this in the project root. Tell the agent: "Read APIX_FRONTEND_COMPLETION.md end to end before changing anything. Follow section 9 in order. Show screenshots after each step and wait for my go-ahead."
>
> This is a **completion and correction** pass, not another restyle. The visual language from the v2 revamp (light "chart paper" surface, B612 + Newsreader, route colours, no cards/shadows/gradients) is working and must not change. What's broken is the **information architecture, the honesty of some labels, and unfinished states**. Section 1 says what to keep untouched.

---

## 1. Keep this exactly as it is

- The vellum/ink/route-colour palette and the two typefaces.
- Flat surfaces with no cards, shadows, gradients or pills.
- The Method page's prose-first writing (the numbered "how the index is built" list and the "what this measures" paragraph read well — keep that voice everywhere else too).
- The general instinct to write real sentences instead of dashboard jargon.

Nothing below asks for a new colour, a new font, or a new visual texture. It asks to finish the site, fix the parts that overclaim or break, and add the landing page.

---

## 2. What's actually wrong (grounded in the current build)

Read this section before touching code. Each item points at something visible right now.

### 2.1 It claims things that aren't true
The Index page header shows two badges: **"CPI 2024 COMPATIBLE"** and **"MoSPI T+21 ALIGNED"**. Neither is true. This is an independent hackathon prototype with one live route and mostly synthetic history. It has not been evaluated for CPI-2024 compatibility, and "MoSPI T+21 aligned" invents an official alignment that doesn't exist. This is the single most damaging thing in the current build: a judge or a real economist who notices this stops trusting everything else on the page, and a fabricated compliance claim is worse for the pitch than the honest limitations in the Method page. **Delete both badges. Do not replace them with a softer version of the same claim.**

### 2.2 It's overclaiming through jargon, not just badges
Tab labels: "Route Matrix & Weights", "Lead-Time Yield Curves", "30-Day Historical Backtest", **"Sensitivity Analysis (§63)"**, **"Observations Explorer (122)"**. The `(§63)` is a fake legal-style citation to nothing. The `(122)` is a raw row count doing duty as a label. "Yield curves" is bond-market vocabulary borrowed for its authority, not because it's the right term. This is the same failure mode as the badges: reaching for the appearance of institutional rigor instead of being plainly correct. Fix throughout: name things for what they do, in lowercase sentence case, with no invented reference numbers.

### 2.3 The hero regressed to a stat-card dashboard
The v2 brief replaced the metric-tile hero with a generated sentence. It's back: four bordered boxes with all-caps micro-labels ("ALL-INDIA APIX LEVEL", "MOM INFLATION RATE", "MONITORED NETWORK", "ADVANCE-PURCHASE HORIZONS") and big numbers. This is a card grid with a hairline border, which is exactly the pattern the lint script in the v2 brief exists to catch, and the labels are all-caps, which that brief also forbids. **These are not new problems to solve — they're a specific instruction being un-done. Re-apply it.**

### 2.4 The basket is inconsistent with itself
The route table (Image 1) lists one route, DEL-BOM, at a DGCA weight of 35.0% in the "MONITORED NETWORK" tile but 100% in the route table underneath it, and the page separately says "1 Routes" (grammatically wrong) while the project's stated basket is three routes. The Data page shows real quotes for DEL-BOM only. **Decide the actual state of each route and show it truthfully everywhere at once**: DEL-BOM has real data, DEL-BLR and BOM-BLR do not yet. Every view must say the same thing about this.

### 2.5 The one-real-route nav link looks like an ad
"Real Data → DEL-BOM" sits in the top nav, bold and coloured, styled like a promotional callout rather than a plain nav item. It's also the only thing in the header that uses an arrow, which the design-lint script already forbids elsewhere. Fold this information into the page content instead of a shouting nav item (see 5.2 and 8).

### 2.6 Booking curves break instead of degrading
DEL-BOM shows one dot and a malformed floating label ("22 Sept: 7d 9399" with no currency symbol or full stop). DEL-BLR and BOM-BLR render completely empty panels with axes that go nowhere. A y-axis spanning 9394 to 9402 for a single point is also mis-scaled: a lone value shouldn't produce a tight, arbitrary-looking range. This page needs a real **empty-state and thin-data design**, not just a note above the charts (see 6).

### 2.7 The Method page mislabels an assumption as a measurement
The lead-window weights table shows six windows (1, 7, 15, 21, 30, 45 days) at 17% each, status **"measured"**. Equal 17% splits are an assumption, not something measured. This is the same honesty failure as 2.1 in miniature: a guess wearing the label of a fact. It directly contradicts the correct sentence right below the table ("Lead-window weights are equal by assumption"). Fix the status column to say `assumed`, styled the way the v2 brief specified, and make sure no table anywhere claims a number is measured when it's a default.

### 2.8 The Data page is new, unspecified, and its numbers don't look real
A "Data" tab now exists (it wasn't in the v2 brief) showing 122 raw rows from `google_flights`. Two problems:
- **It has no obs/scrape date column**, only a travel date (`2026-10-03` on every visible row) and departure/arrival times. Without an observation date, lead time can't be computed and this table can't be told apart from a printed timetable.
- **The fares repeat identically across many rows**: every Air India nonstop shows either ₹6314 or ₹6425 regardless of departure time, every IndiGo nonstop shows ₹6474, every IndiGo one-stop shows ₹6083. Real per-flight fares vary flight to flight. If the collector is actually returning one templated price per carrier/stop-count rather than per-flight prices, that's a data problem to fix at the source, not a frontend problem — but the frontend must not present templated numbers as if they were 122 independent observations. See section 8 and section 7 for what to do about this.

### 2.9 There is no way to arrive at the site
Every screenshot lands directly on a working view. There's no page that says what APIx is, who it's for, and what's real versus synthetic before the visitor is looking at a chart. Section 4 specifies it.

### 2.10 Small formatting things to sweep up while in each file
- "1 Routes" → pluralise correctly, or better, say "DEL-BOM (2 of 3 routes not yet collecting)".
- Table header cells match the all-caps ban already in force elsewhere ("ALL-INDIA APIX LEVEL" etc.) — sentence case only, everywhere, no exceptions.
- The malformed booking-curve label needs a fixed format: `{date} — {lead}d before departure: ₹{price}` with correct spacing and punctuation, or omitted entirely when there's nothing to show.

---

## 3. Information architecture (the fix for 2.2, 2.5, 2.8, 2.9)

Flat, five items, plain words, no nested tab bars layered on top of a page:

```
APIx        Overview   Index   Booking curves   Method
```

- **Overview** (new — this is the landing page, section 4). Default route for first-time visits.
- **Index**: the headline sentence, the chart, the what-if weight bar, the collection record. The route table from Image 1 moves here as a plain table under the chart (see 5.2), not a separate sub-tab.
- **Booking curves**: as in the v2 brief, fixed per section 6.
- **Method**: prose, worked example, rules, weights, limits (as already mostly working), plus the raw observations table folded in as a `<details>` at the very bottom (see section 8) — not a top-level nav item, because it's supporting evidence for the method, not a destination on its own.

Delete "Data" and "Real Data → DEL-BOM" as separate nav entries. Nothing is lost: the raw table moves under Method, and the real-vs-synthetic fact moves into the Overview and Index copy where a reader actually needs it.

---

## 4. Overview (new landing page)

Purpose: a first-time visitor understands in one screen what this is, who would use it, what's real right now, and where to go next. It is not a marketing page. No stat-tile hero, no badges, no hype copy.

### 4.1 Structure

```
+--------------------------------------------------------------------+
| APIx        Overview   Index   Booking curves   Method              |
+--------------------------------------------------------------------+
|                                                                      |
|  APIx                                                                |
|  A daily airfare price index for Indian domestic routes,             |
|  built the way the CPI is built.                                     |
|                                                                      |
|  [ small static index sketch: a short chained line from 100,         |
|    hand-drawn scale, no numbers — decorative, not a real chart ]     |
|                                                                      |
|  Prices for the same flights move by 200 to 400 percent in a         |
|  single day depending on how far ahead you book. Official inflation  |
|  data mostly can't see that. APIx tracks a fixed set of routes and   |
|  booking windows every day and turns the changes into one number,    |
|  using the same kind of method behind India's Consumer Price Index.  |
|                                                                      |
|  Where the data stands today                                         |
|  DEL-BOM     collecting real fares since 3 October 2026               |
|  DEL-BLR     not yet collecting — shown with synthetic history        |
|  BOM-BLR     not yet collecting — shown with synthetic history        |
|                                                                      |
|  This is a hackathon prototype, not an official statistic. See        |
|  Method for what it does and doesn't measure.                        |
|                                                                      |
|  See today's index →  Read the method →                              |
|                                                                      |
+--------------------------------------------------------------------+
```

(The two links at the bottom are the only acceptable use of an arrow in the whole app: outbound in-page links to another view, not decoration. Use `→` nowhere else.)

### 4.2 Rules
- The route-status list is generated from the same data the Index and Data views use — never hand-typed, so it can't drift out of sync with reality again (this is what caused 2.4).
- The opening paragraph states the real motivating fact (200–400% intraday variation) without inventing an official endorsement. It should sound like the background section of the problem statement, in plain words, not like ad copy.
- The small chart sketch is genuinely decorative (no axis values, no claim to be real data) and must be labelled as such in alt text: "Illustrative sketch, not real data."
- No badges, no logos of MoSPI/RBI/DGCA (using a government body's mark implies endorsement it doesn't have).
- This page must fit one screen at 1440x900 without scrolling for the text; the two links are always visible.

---

## 5. Index page fixes

### 5.1 Remove the stat-tile hero (2.3)
Replace the four boxes with the generated headline sentence from the v2 brief (`Fares {rose|fell} {x.x}% on {date}, mostly on {route}.` / `The index is {level} ({base date} = 100).`) plus the data-status sentence (v2 §8). If you want the four facts (level, change, route count, lead windows) visible at a glance, put them as a single inline line of plain text under the headline, separated by two spaces, not boxes and not caps: `Index 100.00   Change +1.88% since last month   1 of 3 routes live   6 lead windows tracked`. No borders, no fill, no icons.

### 5.2 Fold the route table in, and make it tell the truth (2.4)
Keep the table, but:
- Show all three configured routes, always, in the same order everywhere in the app.
- For a route with no real quotes yet, the Index column still shows its synthetic-based value, and the status column says `Synthetic history` instead of `Published`. For DEL-BOM, once real collection has started, the status says `Live since 3 Oct 2026`. No `PUBLISHED` pill — plain text in the status column, in `--ink-2`, not colour-coded as a badge.
- The DGCA weight column shows the same placeholder weights as the Method page's weights table (2.7 applies here too — if these are placeholders, they must say so in every place they appear, not just on Method).

### 5.3 Retitle the tabs (2.2)
- "Route Matrix & Weights" → "Routes"
- "Lead-Time Yield Curves" → this content is the same job as the Booking curves page; either remove this tab and link to Booking curves, or, if it's genuinely a different view (a route-by-route average price at each lead window, as a static snapshot rather than a curve over time), call it "Average price by lead time" and say in one sentence how it differs from Booking curves.
- "30-Day Historical Backtest" → "History" (or fold into the main chart's date range — a 60-day chart already exists, so check whether this tab is really a duplicate before renaming it).
- "Sensitivity Analysis (§63)" → "What if the weights were different?" — and this should just be the what-if weight bar from the v2 brief, in place, not a separate tab. If it's already a separate feature from the weight bar, merge them; two different sensitivity-analysis UIs is a sign one is redundant.
- "Observations Explorer (122)" → remove as a tab; this is the raw data, which belongs under Method per section 3.

### 5.4 Remove the nav callout (2.5)
Delete "Real Data → DEL-BOM" from the header entirely. Its information now lives in the Overview route-status list (4.1) and the Index data-status sentence (v2 §8, e.g. "Data before 3 October is synthetic. Fares were collected from 3 October."). The header keeps only "Data through {date}" as before.

---

## 6. Booking curves fixes (2.6)

- **Minimum-range rule:** when a panel has fewer than 2 real points, don't compute a tight auto-scaled range from the single value. Use a fixed default y-range appropriate to the route's typical fare level (from `config.yaml` or from the synthetic series for that route) so the panel looks like a normal chart with room in it, with the one real point marked distinctly (a filled dot with a ring around it) against a faint synthetic reference line for context if synthetic history exists for that route.
- **Explicit empty state per panel:** when a route/window combination has zero quotes at all, don't render empty axes. Show the axes greyed out with one centred sentence inside the plot area: `No fares collected yet for DEL-BLR.` This is a real state, and it should look like a designed empty state, not a broken chart.
- **Fix the floating label format:** `{date} · {lead}d before departure: ₹{price}` in the same font and size as other chart annotations, positioned so it never overlaps the axis, and only rendered when there is a value to show.
- **Say the true coverage once, above all three panels**, not per panel: `DEL-BOM: 1 day of real fares collected. DEL-BLR and BOM-BLR: synthetic history only.` This replaces the generic "fewer than 5 observation days" note with the specific truth per route.

---

## 7. Data quality note for the pipeline (2.8, second half)

This is outside the frontend, but the frontend depends on it, so record it here:

- If the live source currently assigns one fare per (carrier, stop-count) rather than a genuinely per-flight or per-search-instant fare, that's worth fixing in the scraper before the demo, because a reviewer who opens the raw table (which the frontend now surfaces, per section 8) will notice the repetition immediately, as you just did.
- Add an explicit `observed_at` (scrape timestamp) to every stored quote if it isn't already there in the pipeline (Phase 5's `pipeline.run(date)` should be writing this). The frontend cannot show a correct lead time without it.
- If templated per-class pricing is a known, temporary limitation of the current scraper, say so as a one-line caveat on the Method page's limitations list ("Fares are currently recorded per carrier and stop-count rather than per individual flight") rather than letting the raw table imply more precision than exists.

---

## 8. Raw observations, folded into Method

Replace the standalone "Data" page with a `<details>` block at the bottom of Method, titled `All recorded fares (122)` (the count is fine here, inside a label that already explains what it's a count of — the problem in 2.2 was using a bare number as the whole tab name).

Table columns, in this order: **Observed** (scrape date/time), **Travel date**, **Lead (days)**, **Route**, **Airline**, **Departs**, **Arrives**, **Stops**, **Fare**. Add "Observed" and "Lead (days)" even if you have to backfill them from the run log's date, so the table can actually support a lead-time claim. Keep it collapsed by default; it's evidence for someone who wants to check the method, not a page anyone lands on.

---

## 9. Build order and review protocol

**Step 0.** Update `docs/design-notes.md` with the IA change (section 3) and a short "why" for each deletion (badges, `(§63)`, the extra tabs, the Data nav item). Get this reviewed before touching JSX.

**Step 1.** Delete the CPI/MoSPI badges and the stat-tile hero on Index; restore the generated headline sentence (5.1).

**Step 2.** Rebuild the nav to the four flat items (section 3); remove "Real Data → DEL-BOM"; move the raw table under Method as a `<details>` (section 8) with the added columns.

**Step 3.** Fix the route table (5.2) and retitle or merge the remaining Index tabs (5.3).

**Step 4.** Fix the Method weights table's status column (`assumed`, not `measured`) and double check every other table in the app for the same mistake.

**Step 5.** Build the Overview / landing page (section 4), generated from live route status.

**Step 6.** Fix Booking curves: minimum-range rule, empty states, label format, one true coverage sentence (section 6).

**Step 7.** File the pipeline note from section 7 as a task (or fix it now if you own that code too), and add the one-line caveat to Method's limitations if the templated-pricing issue isn't fixed before the demo.

**After every step:**
1. Screenshot at 1440x900 and 390x844.
2. Read every visible label out loud — literally — and ask: is this true right now, in this build, with this data? If a label claims something the data doesn't back up (a status, a compliance badge, a "measured" tag, a route count), fix the label or fix the data before moving on.
3. Re-run the section 11 lint script from the v2 brief (gradients, shadows, all-caps, tracked text, radius, smoothed curves, cards, arrows/middle-dots). It should still pass — this plan doesn't touch tokens or components that would break it.

---

## 10. Acceptance checklist

- [ ] No badge, tab name, or table cell claims official compatibility, alignment, or "measured" status that the data doesn't support.
- [ ] Nav is four flat items: Overview, Index, Booking curves, Method. No nested tab bar duplicates the same content under a fancier name.
- [ ] The Overview page exists, fits one screen, states the real per-route data status generated from live data, and carries no logos or badges.
- [ ] Index shows the generated headline sentence, not a stat-tile hero.
- [ ] The route table lists all three routes with statuses that are true and consistent with the Overview page and the Method page.
- [ ] Booking curves never show a broken, mis-scaled, or blank-looking chart: every panel is either real data, real-plus-synthetic-for-context, or a designed empty state with a sentence.
- [ ] The raw-observations table lives under Method inside a `<details>`, includes an observation date and computed lead time for every row, and is not a top-level nav destination.
- [ ] Every occurrence of route weights or lead-window weights, anywhere in the app, is labelled consistently as placeholder/assumed or as truly measured — never both for the same number.
- [ ] The design-lint script from the v2 brief still passes.
- [ ] `docs/design-notes.md` records what was removed in this pass and why.
