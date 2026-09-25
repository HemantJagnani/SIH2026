/**
 * BookingCurvesView (replaces LeadTimeView)
 *
 * Three small panels side by side, one per route, sharing one y scale.
 * X runs 30 → 1 (departure). Lines are one per observation day.
 * Single-hue ramp: #C9D6E6 (oldest) → --ink (latest).
 * Shared selectedDate with Index view (URL ?d=…).
 * Late-booking premium chart below.
 */
import { useState, useEffect, useMemo, useRef, useId } from 'react';
import * as d3Scale from 'd3-scale';
import * as d3Shape from 'd3-shape';
import * as d3Array from 'd3-array';
import { api, type LeadCurve } from '../api';

const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;
const LEAD_DAYS = [30, 15, 7, 1] as const;
const PANEL_H = 220;
const MARGIN = { top: 16, right: 16, bottom: 48, left: 56 };
const PREMIUM_H = 160;

type Mode = 'rupees' | 'indexed';

const ROUTE_COLORS: Record<string, string> = {
  'DEL-BOM': 'var(--route-blue)',
  'DEL-BLR': 'var(--route-mag)',
  'BOM-BLR': 'var(--route-teal)',
};

function parseUTC(s: string): Date {
  return new Date(s + 'T00:00:00Z');
}

function fmtDateShort(s: string): string {
  return parseUTC(s).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', timeZone: 'UTC',
  });
}

function fmtRupee(n: number): string {
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
}

/** Interpolate between two hex colours */
function lerpColor(t: number): string {
  // oldest: #C9D6E6 → newest: #1A2B3C (var(--ink))
  const r0 = 0xC9, g0 = 0xD6, b0 = 0xE6;
  const r1 = 0x1A, g1 = 0x2B, b1 = 0x3C;
  const r = Math.round(r0 + (r1 - r0) * t);
  const g = Math.round(g0 + (g1 - g0) * t);
  const b = Math.round(b0 + (b1 - b0) * t);
  return `rgb(${r},${g},${b})`;
}

/** Index a curve's points to 30 days = 100 */
function indexCurve(
  points: { lead_days: number; price: number }[],
): { lead_days: number; price: number }[] {
  const base = points.find(p => p.lead_days === 30)?.price ?? null;
  if (!base || base === 0) return points;
  return points.map(p => ({ ...p, price: (p.price / base) * 100 }));
}

/** Compute late-booking premium = price at 1d / price at 30d */
function computePremium(
  curve: LeadCurve,
  mode: Mode,
): number | null {
  const pts = mode === 'indexed' ? indexCurve(curve.points) : curve.points;
  const p1 = pts.find(p => p.lead_days === 1)?.price;
  const p30 = pts.find(p => p.lead_days === 30)?.price;
  if (p1 == null || p30 == null || p30 === 0) return null;
  return (p1 / p30 - 1) * 100;
}

interface Props {
  selectedDate: string | null;
  onSelectDate: (d: string | null) => void;
}

interface PanelProps {
  route: string;
  curves: LeadCurve[];
  mode: Mode;
  sharedYScale: d3Scale.ScaleLinear<number, number> | null;
  selectedDate: string | null;
  onSelectDate: (d: string | null) => void;
  panelW: number;
}

function RoutePanel({
  route, curves, mode, sharedYScale, selectedDate, onSelectDate, panelW,
}: PanelProps) {
  const innerW = panelW - MARGIN.left - MARGIN.right;
  const innerH = PANEL_H - MARGIN.top - MARGIN.bottom;
  const liveId = useId();

  const xScale = useMemo(() => (
    d3Scale.scaleLinear().domain([30, 1]).range([0, innerW])
  ), [innerW]);

  const sorted = useMemo(() => (
    [...curves].sort((a, b) => a.obs_date.localeCompare(b.obs_date))
  ), [curves]);

  const n = sorted.length;

  const lineGen = useMemo(() => {
    if (!sharedYScale) return null;
    return d3Shape.line<{ lead_days: number; price: number }>()
      .x(p => xScale(p.lead_days))
      .y(p => sharedYScale(p.price))
      .defined(p => p.price != null)
      .curve(d3Shape.curveLinear);
  }, [xScale, sharedYScale]);

  if (!sharedYScale || !lineGen) return null;

  const yTicks = sharedYScale.ticks(4).map(t => ({ val: t, y: sharedYScale(t) }));

  // Find highlighted curve
  const highlightedIdx = selectedDate
    ? sorted.findIndex(c => c.obs_date === selectedDate)
    : n - 1;

  return (
    <div>
      <div className="booking-panel-title" style={{ color: ROUTE_COLORS[route] }}>{route}</div>
      <div style={{ position: 'relative' }}>
        <div id={liveId} aria-live="polite" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
          {highlightedIdx >= 0 ? `${route} ${fmtDateShort(sorted[highlightedIdx].obs_date)}` : ''}
        </div>
        <svg
          width={panelW}
          height={PANEL_H}
          role="img"
          aria-label={`${route} booking curves, ${curves.length} observation days`}
          aria-describedby={liveId}
        >
          <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
            {/* Gridlines */}
            {yTicks.map(({ val, y }) => (
              <line key={val} x1={0} x2={innerW} y1={y} y2={y}
                stroke="var(--contour)" strokeWidth={1} />
            ))}

            {/* Lead-day tick markers */}
            {LEAD_DAYS.map(d => (
              <g key={d} transform={`translate(${xScale(d)},${innerH})`}>
                <line y1={0} y2={4} stroke="var(--contour)" />
                <text y={16} textAnchor="middle"
                  fontSize="var(--t-axis)" fill="var(--ink-2)"
                  fontFamily="'B612', monospace"
                >
                  {d}d
                </text>
              </g>
            ))}
            <text
              x={innerW / 2} y={innerH + 34}
              textAnchor="middle"
              fontSize="var(--t-axis)" fill="var(--ink-2)"
              fontFamily="'B612', monospace"
            >
              Days before departure →
            </text>

            {/* Y-axis */}
            {yTicks.map(({ val, y }) => (
              <text key={val} x={-8} y={y}
                textAnchor="end" dominantBaseline="middle"
                fontSize="var(--t-axis)" fill="var(--ink-2)"
                fontFamily="'B612', monospace"
              >
                {mode === 'indexed' ? val.toFixed(0) : Math.round(val).toLocaleString('en-IN')}
              </text>
            ))}

            {/* Axis lines */}
            <line x1={0} x2={0} y1={0} y2={innerH} stroke="var(--contour)" />
            <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke="var(--contour)" />

            {/* Curves (oldest → newest) */}
            {sorted.map((curve, i) => {
              const t = n <= 1 ? 1 : i / (n - 1);
              const isLatest = i === n - 1;
              const isHighlighted = i === highlightedIdx;
              const pts = mode === 'indexed' ? indexCurve(curve.points) : curve.points;
              const sortedPts = [...pts]
                .filter(p => LEAD_DAYS.includes(p.lead_days as typeof LEAD_DAYS[number]))
                .sort((a, b) => b.lead_days - a.lead_days);

              if (sortedPts.length === 0) return null;
              const path = lineGen(sortedPts);
              if (!path) return null;

              return (
                <g key={curve.obs_date}
                  style={{ cursor: 'pointer' }}
                  onClick={() => onSelectDate(isHighlighted ? null : curve.obs_date)}
                  aria-label={`${fmtDateShort(curve.obs_date)}`}
                >
                  <path
                    d={path}
                    fill="none"
                    stroke={lerpColor(t)}
                    strokeWidth={isLatest || isHighlighted ? 2.5 : 1}
                    opacity={isHighlighted ? 1 : isLatest ? 0.9 : 0.6}
                  />
                  {/* Dots at lead-day ticks */}
                  {(isLatest || isHighlighted) && sortedPts.map(p => (
                    <circle
                      key={p.lead_days}
                      cx={xScale(p.lead_days)}
                      cy={sharedYScale(p.price)}
                      r={2.5}
                      fill={lerpColor(t)}
                    />
                  ))}
                </g>
              );
            })}

            {/* Highlighted readout */}
            {highlightedIdx >= 0 && sorted[highlightedIdx] && (() => {
              const curve = sorted[highlightedIdx];
              const pts = mode === 'indexed' ? indexCurve(curve.points) : curve.points;
              const relevant = pts.filter(p => LEAD_DAYS.includes(p.lead_days as typeof LEAD_DAYS[number]));
              return (
                <text
                  x={innerW}
                  y={-4}
                  textAnchor="end"
                  fontSize="var(--t-axis)"
                  fill="var(--ink)"
                  fontFamily="'B612', monospace"
                >
                  {fmtDateShort(curve.obs_date)}: {
                    relevant.sort((a,b) => b.lead_days - a.lead_days).map(p =>
                      `${p.lead_days}d ${mode === 'indexed' ? p.price.toFixed(0) : fmtRupee(p.price)}`
                    ).join('  ')
                  }
                </text>
              );
            })()}
          </g>
        </svg>
      </div>
    </div>
  );
}

export default function BookingCurvesView({ selectedDate, onSelectDate }: Props) {
  const [allCurves, setAllCurves] = useState<Record<string, LeadCurve[]>>({});
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<Mode>('indexed');
  const panelRef = useRef<HTMLDivElement>(null);
  const [panelW, setPanelW] = useState(300);

  useEffect(() => {
    const el = panelRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([e]) => {
      const w = e.contentRect.width;
      setPanelW(Math.max(160, Math.floor((w - 48) / 3)));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all(
      ROUTES.map(r => api.leadCurve(r).then(curves => [r, curves] as const))
    ).then(results => {
      const data: Record<string, LeadCurve[]> = {};
      for (const [r, curves] of results) data[r] = curves;
      setAllCurves(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Shared y scale across all three panels
  const sharedYScale = useMemo(() => {
    const allPrices: number[] = [];
    for (const route of ROUTES) {
      for (const curve of allCurves[route] ?? []) {
        const pts = mode === 'indexed' ? indexCurve(curve.points) : curve.points;
        for (const p of pts) {
          if (LEAD_DAYS.includes(p.lead_days as typeof LEAD_DAYS[number])) {
            allPrices.push(p.price);
          }
        }
      }
    }
    if (allPrices.length === 0) return null;
    const [lo, hi] = d3Array.extent(allPrices) as [number, number];
    const pad = (hi - lo) * 0.1 || 5;
    const innerH = PANEL_H - MARGIN.top - MARGIN.bottom;
    return d3Scale.scaleLinear()
      .domain([lo - pad, hi + pad])
      .range([innerH, 0]);
  }, [allCurves, mode]);

  // Late-booking premium
  const premiumData = useMemo(() => {
    const data: Record<string, { date: string; premium: number }[]> = {};
    for (const route of ROUTES) {
      data[route] = (allCurves[route] ?? [])
        .map(c => ({ date: c.obs_date, premium: computePremium(c, mode) ?? 0 }))
        .filter(d => d.premium !== null)
        .sort((a, b) => a.date.localeCompare(b.date));
    }
    return data;
  }, [allCurves, mode]);

  const hasSynth = ROUTES.some(r =>
    (allCurves[r] ?? []).some(c => c.is_synthetic)
  );

  const totalCurves = ROUTES.reduce((s, r) => s + (allCurves[r]?.length ?? 0), 0);
  const minCurves = ROUTES.reduce((s, r) => Math.min(s, allCurves[r]?.length ?? 0), Infinity);

  return (
    <div className="page">
      <h1>Booking curves</h1>
      <p className="prose" style={{ marginBottom: 'var(--sp-6)', color: 'var(--ink)' }}>
        Each line is one day's fares, from 30 days before departure to the day before. Darker lines are more recent.
      </p>

      {hasSynth && (
        <p style={{ fontSize: 'var(--t-ui)', color: 'var(--ink-2)', marginBottom: 'var(--sp-4)' }}>
          All data shown is synthetic. No fares have been collected yet.
        </p>
      )}

      {/* Mode toggle */}
      <div className="toggle-group" style={{ marginBottom: 'var(--sp-4)' }}>
        <button
          className="toggle-btn"
          aria-pressed={mode === 'rupees'}
          onClick={() => setMode('rupees')}
        >
          Fare in rupees
        </button>
        <span className="toggle-sep">|</span>
        <button
          className="toggle-btn"
          aria-pressed={mode === 'indexed'}
          onClick={() => setMode('indexed')}
        >
          Indexed to 30 days = 100
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading booking curves…</div>
      ) : totalCurves === 0 ? (
        <div className="empty-state">
          No fare data collected yet for any route.
        </div>
      ) : (
        <>
          {minCurves < 5 && (
            <p style={{ fontSize: 'var(--t-ui)', color: 'var(--ink-2)', marginBottom: 'var(--sp-4)' }}>
              Fewer than 5 observation days available — showing what exists.
            </p>
          )}

          {/* Three panels */}
          <figure className="chart-figure">
            <figcaption style={{ marginBottom: 'var(--sp-3)', fontSize: 'var(--t-axis)', color: 'var(--ink-2)' }}>
              {mode === 'indexed' ? 'Indexed: 30 days before departure = 100' : 'Fare in rupees'}
              {selectedDate && ` · Highlighted: ${fmtDateShort(selectedDate)}`}
            </figcaption>
            <div className="booking-panels" ref={panelRef}>
              {ROUTES.map(route => (
                <RoutePanel
                  key={route}
                  route={route}
                  curves={allCurves[route] ?? []}
                  mode={mode}
                  sharedYScale={sharedYScale}
                  selectedDate={selectedDate}
                  onSelectDate={onSelectDate}
                  panelW={panelW}
                />
              ))}
            </div>
            <details className="chart-data-table">
              <summary>Show data as table</summary>
              <p style={{ marginTop: 'var(--sp-2)', fontSize: 'var(--t-axis)', color: 'var(--ink-2)' }}>
                Showing latest observation day per route.
              </p>
              {ROUTES.map(route => {
                const curves = allCurves[route] ?? [];
                const latest = curves.at(-1);
                if (!latest) return null;
                const pts = mode === 'indexed' ? indexCurve(latest.points) : latest.points;
                return (
                  <table key={route} aria-label={`${route} latest fares`} style={{ marginTop: 'var(--sp-2)' }}>
                    <thead>
                      <tr>
                        <th>{route} — {fmtDateShort(latest.obs_date)}</th>
                        {LEAD_DAYS.map(d => <th key={d}>{d}d</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Price</td>
                        {LEAD_DAYS.map(d => {
                          const p = pts.find(pt => pt.lead_days === d);
                          return (
                            <td key={d} className="font-num">
                              {p ? (mode === 'indexed' ? p.price.toFixed(1) : fmtRupee(p.price)) : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    </tbody>
                  </table>
                );
              })}
            </details>
          </figure>

          {/* Late-booking premium chart */}
          {Object.values(premiumData).some(d => d.length > 0) && (
            <section className="section">
              <h2>Late-booking premium</h2>
              <p className="prose" style={{ marginBottom: 'var(--sp-4)', color: 'var(--ink-2)', fontSize: 'var(--t-ui)' }}>
                How much more a fare costs 1 day before departure compared to 30 days out, per route.
              </p>
              <PremiumChart premiumData={premiumData} />
            </section>
          )}
        </>
      )}
    </div>
  );
}

/** Small line chart for late-booking premium per route */
function PremiumChart({ premiumData }: { premiumData: Record<string, { date: string; premium: number }[]> }) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(800);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new ResizeObserver(([e]) => setW(e.contentRect.width));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const M = { top: 12, right: 80, bottom: 32, left: 48 };
  const innerW = w - M.left - M.right;
  const innerH = PREMIUM_H - M.top - M.bottom;

  const allDates = [...new Set(
    Object.values(premiumData).flatMap(d => d.map(p => p.date))
  )].sort();

  if (allDates.length < 2) return null;

  const xScale = d3Scale.scaleTime()
    .domain([parseUTC(allDates[0]), parseUTC(allDates.at(-1)!)])
    .range([0, innerW]);

  const allPremiums = Object.values(premiumData).flatMap(d => d.map(p => p.premium));
  const [lo, hi] = d3Array.extent(allPremiums) as [number, number];
  const pad = (hi - lo) * 0.15 || 2;
  const yScale = d3Scale.scaleLinear()
    .domain([lo - pad, hi + pad])
    .range([innerH, 0]);

  const lineGen = d3Shape.line<{ date: string; premium: number }>()
    .x(p => xScale(parseUTC(p.date)))
    .y(p => yScale(p.premium))
    .curve(d3Shape.curveLinear);

  const yTicks = yScale.ticks(4).map(t => ({ val: t, y: yScale(t) }));
  const xTicks = xScale.ticks(5).map(t => ({ val: t, x: xScale(t) }));

  const ROUTE_COLORS_MAP: Record<string, string> = {
    'DEL-BOM': 'var(--route-blue)',
    'DEL-BLR': 'var(--route-mag)',
    'BOM-BLR': 'var(--route-teal)',
  };

  return (
    <div ref={ref}>
      <svg width={w} height={PREMIUM_H} role="img" aria-label="Late-booking premium by route">
        <g transform={`translate(${M.left},${M.top})`}>
          {yTicks.map(({ val, y }) => (
            <line key={val} x1={0} x2={innerW} y1={y} y2={y}
              stroke="var(--contour)" strokeWidth={1} />
          ))}
          {yTicks.map(({ val, y }) => (
            <text key={val} x={-8} y={y}
              textAnchor="end" dominantBaseline="middle"
              fontSize="var(--t-axis)" fill="var(--ink-2)"
              fontFamily="'B612', monospace"
            >
              {val.toFixed(0)}%
            </text>
          ))}
          {xTicks.map(({ val, x }) => (
            <text key={val.getTime()} x={x} y={innerH + 20}
              textAnchor="middle"
              fontSize="var(--t-axis)" fill="var(--ink-2)"
              fontFamily="'B612', monospace"
            >
              {val.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })}
            </text>
          ))}

          {Object.entries(premiumData).map(([route, data]) => {
            if (data.length < 2) return null;
            const path = lineGen(data);
            if (!path) return null;
            const last = data.at(-1)!;
            return (
              <g key={route}>
                <path d={path} fill="none" stroke={ROUTE_COLORS_MAP[route]} strokeWidth={1.5} />
                <text
                  x={innerW + 6}
                  y={yScale(last.premium)}
                  dominantBaseline="middle"
                  fontSize="var(--t-axis)"
                  fill={ROUTE_COLORS_MAP[route]}
                  fontFamily="'B612', monospace"
                >
                  {route}
                </text>
              </g>
            );
          })}

          <line x1={0} x2={0} y1={0} y2={innerH} stroke="var(--contour)" />
          <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke="var(--contour)" />
        </g>
      </svg>
    </div>
  );
}
