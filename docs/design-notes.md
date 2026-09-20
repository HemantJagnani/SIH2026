# APIx v2 — Design Notes

## 1. Tokens

```css
--vellum:      #F0F2EE;  /* surface */
--ink:         #1A2B3C;  /* text and overall series */
--ink-2:       #4A5A68;  /* secondary text, axes (6:1 on vellum) */
--contour:     #C9D0CB;  /* gridlines, hairlines — never text */
--route-blue:  #2A5FA5;  /* DEL-BOM */
--route-mag:   #B0286A;  /* DEL-BLR */
--route-teal:  #2F7D6D;  /* BOM-BLR */
--hatch:       #A8916A;  /* synthetic hatch lines only */
--assumed:     #8A5600;  /* the word "assumed" in text (5:1) */
--focus:       #B0286A;
```

Direction (up/down) is always encoded in words and signed numbers, never red/green.

## 2. Type scale

| Role | Face | Size / leading |
|---|---|---|
| Headline sentence | Newsreader 400 | clamp(28px, 3.4vw, 44px) / 1.15, max 30ch |
| Prose | Newsreader 400 | 18px / 1.55, max 66ch |
| Reading on chart | B612 700 | 28px / 1.1 |
| UI and labels | B612 400 | 14px / 1.4 |
| Axis text | B612 400 | 12px / 1.3, `--ink-2` |

Two families, clearly different. B612 was designed by Airbus for cockpit displays — its
digits stay unambiguous at a glance. Newsreader provides warmth for prose only.

## 3. Shape rules

- Border-radius: 0, or 2px on interactive controls only.
- No shadows, gradients, blur or glass.
- Active toggle: underline in `--ink`, 2px, offset 4px. No pills.
- Focus ring: 2px `--focus`, 3px offset, always visible.

## 4. Wireframes (adapted)

### Index, desktop (1440)

```
+------------------------------------------------------------------------------+
| APIx      Index   Booking curves   Method               Data through 19 Sep  |
+------------------------------------------------------------------------------+
|                                                                              |
|  Fares fell 0.7% on 19 September,                                            |
|  mostly on DEL-BLR.                                                          |
|  The index is 95.67 (22 July = 100). All data shown is synthetic.            |
|                                                                              |
|  104 |  ╔═══════════════════════════════════════════════╗ ← hatched = synth  |
|      |  ║  /\    /\    /\                     Overall 95.67 ║               |
|  100 +-- ║ - - - - - - - - - - - - - - - - -  DEL-BOM 96.1 ║               |
|      |  ║                                     DEL-BLR 94.9 ║               |
|   92 |  ╚═════════════════════════════════════BOM-BLR 96.4 ╝               |
|      +---+-------+-------+-------+-------+-------+------                    |
|          25 Jul   8 Aug   22 Aug   5 Sep                                     |
|  Daily  Weekly  Monthly                                                      |
|                                                                              |
|  What if the weights were different?          Lead times | Routes             |
|  [ 1 day 25% | 7 days 25% | 15 days 25% | 30 days 25% ]     Reset           |
|  With these weights the index differs from the default by at most 0.6 pts.  |
|                                                                              |
|  Collection record  |||||||||||||||||||||||||||||||||||  60 of 60 runs ok    |
+------------------------------------------------------------------------------+
```

Deviation from brief wireframe: the route-colour legend is omitted in favour of direct
labels at the right end of each line (which the brief §5.2 also requires). The wireframe
was illustrative; direct labels are the authoritative instruction.

### Index, mobile (390)

```
APIx        Index  Curves  Method
-----------------------------------
Fares fell 0.7% on 19 September,
mostly on DEL-BLR.
The index is 95.67 (22 July = 100).
All data shown is synthetic.

[ chart, full width, 55vh ]
Direct labels at right shrink to codes

Daily  Weekly  Monthly

What if the weights were different?
[ 1d | 7d | 15d | 30d ]   Reset
Differs by at most 0.6 points.

Collection record ||||||||||||||||||
60 of 60 runs ok
```

## 5. "Remove wordmark" test

**Question:** If the wordmark "APIx" were removed, would this look like any other analytics dashboard?

**Answer:** No. The distinguishing features are:
- Light vellum paper surface (industry-wide default is dark)
- B612 cockpit font throughout — no analytics tool uses this
- No cards or boxes anywhere; sections divided only by space and rules
- Synthetic-data hatch drawn *inside the chart*, not badged outside
- Direct labels on lines, not a detached legend
- Headline sentence generated from data, not a numeric hero block

The design is legible and purposeful without the wordmark.

## 6. Elements removed

Each step records one decorative element removed per the review protocol (§12):

- **Step 1:** Removed scrollbar custom styling (pure decoration, no information)
- **Step 2:** Removed the "Real" legend entry (no real data exists; only show what exists per §13)
- **Step 3:** Removed the "Normalised weights" duplicate table (the bar itself shows the weights)
- **Step 4:** Removed the "Schedule: 05:00 IST daily" sub-caption from the strip header
- **Step 5:** Removed the route selector pill buttons from Booking curves (routes shown as panels)
- **Step 6:** Removed "Index methodology" panel title (h2 heading does the same job)
- **Step 7:** Removed custom scrollbar from webkit (not visible to most users)

## 7. Deviations from brief

| Brief instruction | Deviation | Reason |
|---|---|---|
| Route selector on Index (§5) | Removed — route lines shown as direct labels on chart | Brief §5.2 says direct labels replace the legend; a separate selector is redundant |
| Ridgeline chart in Lead time (§6) | Changed to three-panel small multiples | Brief §6 explicitly describes "three small panels side by side" — the old view incorrectly implemented a ridgeline |
