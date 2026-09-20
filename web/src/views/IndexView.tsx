import {
  useState, useEffect, useRef, useCallback, useMemo, useId,
} from 'react';
import * as d3Scale from 'd3-scale';
import * as d3Shape from 'd3-shape';
import * as d3Array from 'd3-array';
import { api, type IndexPoint, type Relative, type Run } from '../api';
import {
  recomputeIndex, maxDeviation,
  DEFAULT_LEAD_WEIGHTS, DEFAULT_ROUTE_WEIGHTS,
  ROUTES,
} from '../lib/indexMath';
import WeightBar from '../components/WeightBar';
import RecordStrip from '../components/RecordStrip';

type Freq = 'daily' | 'weekly' | 'monthly';
type RouteId = typeof ROUTES[number];

const ROUTE_COLORS: Record<string, string> = {
  'DEL-BOM': 'var(--route-blue)',
  'DEL-BLR': 'var(--route-mag)',
  'BOM-BLR': 'var(--route-teal)',
};

const CHART_H = 360;
const MARGIN = { top: 24, right: 120, bottom: 40, left: 52 };

/* ── helpers ──────────────────────────────────────────────────────────── */

function fmtNum(n: number | null, dp = 2): string {
  if (n == null) return '—';
  return n.toFixed(dp);
}

function parseUTC(s: string): Date {
  return new Date(s + 'T00:00:00Z');
}

function fmtDate(s: string): string {
  return parseUTC(s).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', timeZone: 'UTC',
  });
}

function fmtDateShort(s: string): string {
  return parseUTC(s).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', timeZone: 'UTC',
  });
}

function fmtPeriod(s: string, freq: Freq): string {
  const d = parseUTC(s);
  if (freq === 'daily') return fmtDate(s);
  if (freq === 'weekly') {
    return `the week of ${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', timeZone: 'UTC' })}`;
  }
  return d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' });
}

function dayLabel(d: number): string {
  return d === 1 ? '1 day' : `${d} days`;
}

/* ── headline sentence (§5.1) ─────────────────────────────────────────── */
function makeHeadline(
  current: IndexPoint | null,
  prev: IndexPoint | null,
  freq: Freq,
  routePoints: Record<string, IndexPoint[]>,
  routeWeights: Record<string, number>,
): string {
  if (!current || current.level == null) return '';

  if (!prev || prev.level == null) {
    return `The index is ${fmtNum(current.level)} (base = 100). ${
      current.is_synthetic ? 'All data shown is synthetic.' : ''
    }`;
  }

  const pct = ((current.level - prev.level) / prev.level) * 100;
  const absChange = Math.abs(pct);

  // "Mostly on ROUTE" logic
  let routePart = 'across all routes';
  const contributions: Record<string, number> = {};
  for (const route of ROUTES) {
    const rPts = routePoints[route];
    if (!rPts) continue;
    const rCurr = rPts.find(p => p.date === current.date);
    const rPrev = rPts.find(p => p.date === prev.date);
    if (rCurr?.level != null && rPrev?.level != null) {
      const w = routeWeights[route] ?? 0;
      contributions[route] = w * ((rCurr.level - rPrev.level) / rPrev.level);
    }
  }
  const absSum = Object.values(contributions).reduce((s, v) => s + Math.abs(v), 0);
  if (absSum > 0) {
    const [topRoute, topVal] = Object.entries(contributions).reduce(
      (best, cur) => Math.abs(cur[1]) > Math.abs(best[1]) ? cur : best,
    );
    if (Math.abs(topVal) / absSum >= 0.6) {
      routePart = `on ${topRoute}`;
    }
  }

  let firstSentence: string;
  if (absChange < 0.05) {
    firstSentence = `Fares were unchanged ${freq === 'daily' ? 'on' : 'in'} ${fmtPeriod(current.date, freq)}.`;
  } else {
    const verb = pct > 0 ? 'rose' : 'fell';
    const prep = freq === 'daily' ? 'on' : 'in';
    firstSentence = `Fares ${verb} ${absChange.toFixed(1)}% ${prep} ${fmtPeriod(current.date, freq)}, mostly ${routePart}.`;
  }

  return firstSentence;
}

/* ── nudge labels to avoid overlap ───────────────────────────────────── */
function nudgeLabels(
  labels: { id: string; y: number }[],
  minGap = 16,
): Record<string, number> {
  const sorted = [...labels].sort((a, b) => a.y - b.y);
  const result: Record<string, number> = {};
  for (let i = 0; i < sorted.length; i++) {
    result[sorted[i].id] = sorted[i].y;
    if (i > 0 && result[sorted[i].id] - result[sorted[i - 1].id] < minGap) {
      result[sorted[i].id] = result[sorted[i - 1].id] + minGap;
    }
  }
  return result;
}

/* ── props ────────────────────────────────────────────────────────────── */
interface Props {
  selectedDate: string | null;
  onSelectDate: (d: string | null) => void;
}

/* ══════════════════════════════════════════════════════════════════════ */
export default function IndexView({ selectedDate, onSelectDate }: Props) {
  const [overall, setOverall] = useState<IndexPoint[]>([]);
  const [routeData, setRouteData] = useState<Record<string, IndexPoint[]>>({});
  const [relatives, setRelatives] = useState<Relative[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [freq, setFreq] = useState<Freq>('daily');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Weight-bar state
  const [leadWeights, setLeadWeights] = useState<Record<number, number>>(DEFAULT_LEAD_WEIGHTS);
  const [routeWeightsCustom, setRouteWeightsCustom] = useState<Record<string, number>>(DEFAULT_ROUTE_WEIGHTS);
  const [weightMode, setWeightMode] = useState<'lead' | 'route'>('lead');
  const [weightsChanged, setWeightsChanged] = useState(false);
  const [customPoints, setCustomPoints] = useState<IndexPoint[]>([]);

  // Chart hover state
  const [hoveredRoute, setHoveredRoute] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(900);
  const liveId = useId();

  /* resize observer */
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([e]) => setW(e.contentRect.width));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  /* fetch data */
  useEffect(() => {
    setLoading(true);
    setError(null);

    const routeFetches = ROUTES.map(r =>
      api.index('route', r, freq).then(pts => [r, pts] as const),
    );

    Promise.all([
      api.index('overall', undefined, freq),
      api.relatives(),
      api.runs(),
      ...routeFetches,
    ]).then(([ov, rels, rs, ...rFetches]) => {
      setOverall(ov);
      setRelatives(rels);
      setRuns(rs);
      const rd: Record<string, IndexPoint[]> = {};
      for (const [route, pts] of rFetches) rd[route] = pts;
      setRouteData(rd);
      setLoading(false);
    }).catch(err => {
      setError(`Couldn't load the index. The API at http://localhost:8000/api didn't respond. Start it with make api, then reload.`);
      console.error(err);
      setLoading(false);
    });
  }, [freq]);

  /* recompute when weights change */
  useEffect(() => {
    if (!weightsChanged || relatives.length === 0) {
      setCustomPoints([]);
      return;
    }
    const pts = recomputeIndex(relatives, routeWeightsCustom, leadWeights);
    setCustomPoints(pts);
  }, [leadWeights, routeWeightsCustom, weightsChanged, relatives]);

  /* resolve display points */
  const displayPoints = weightsChanged && customPoints.length > 0 ? customPoints : overall;
  const validOverall = displayPoints.filter(p => p.level != null);

  /* date range */
  const allDates = validOverall.map(p => p.date);
  const latestDate = allDates.at(-1) ?? null;
  const activeDate = selectedDate && allDates.includes(selectedDate)
    ? selectedDate
    : latestDate;

  const activePoint = activeDate
    ? validOverall.find(p => p.date === activeDate) ?? null
    : null;
  const prevPoint = activeDate
    ? validOverall.slice(0, validOverall.findIndex(p => p.date === activeDate)).at(-1) ?? null
    : null;

  /* route active values at selected date */
  const routeActiveValues: Record<string, number | null> = {};
  for (const route of ROUTES) {
    const pts = routeData[route]?.filter(p => p.level != null) ?? [];
    const p = pts.find(pt => pt.date === activeDate);
    routeActiveValues[route] = p?.level ?? null;
  }

  /* sensitivity */
  const sensitivity = useMemo(() => {
    if (!weightsChanged || customPoints.length === 0) return null;
    return maxDeviation(customPoints, overall);
  }, [weightsChanged, customPoints, overall]);

  /* D3 scales */
  const innerW = w - MARGIN.left - MARGIN.right;
  const innerH = CHART_H - MARGIN.top - MARGIN.bottom;

  const xScale = useMemo(() => {
    if (validOverall.length < 2) return null;
    const ext = d3Array.extent(validOverall, p => parseUTC(p.date)) as [Date, Date];
    return d3Scale.scaleTime().domain(ext).range([0, innerW]);
  }, [validOverall, innerW]);

  const yScale = useMemo(() => {
    if (validOverall.length === 0) return null;
    const allLevels = [
      ...validOverall.map(p => p.level!),
      ...Object.values(routeData).flatMap(pts => pts.filter(p => p.level != null).map(p => p.level!)),
      100,
    ];
    const [lo, hi] = d3Array.extent(allLevels) as [number, number];
    const pad = Math.max((hi - lo) * 0.12, 2);
    return d3Scale.scaleLinear().domain([lo - pad, hi + pad]).range([innerH, 0]);
  }, [validOverall, routeData, innerH]);

  const lineGenLinear = useMemo(() => {
    if (!xScale || !yScale) return null;
    return d3Shape.line<IndexPoint>()
      .x(p => xScale(parseUTC(p.date)))
      .y(p => yScale(p.level!))
      .defined(p => p.level != null)
      .curve(d3Shape.curveLinear);
  }, [xScale, yScale]);

  /* x-ticks */
  const xTicks = xScale
    ? xScale.ticks(Math.min(8, validOverall.length)).map(t => ({ val: t, x: xScale(t) }))
    : [];

  /* y-ticks */
  const yTicks = yScale ? yScale.ticks(6).map(t => ({ val: t, y: yScale(t) })) : [];

  /* synthetic band extent */
  const synthPoints = validOverall.filter(p => p.is_synthetic);
  const synthStart = synthPoints.at(0)?.date ?? null;
  const synthEnd = synthPoints.at(-1)?.date ?? null;
  const firstRealDate = validOverall.find(p => !p.is_synthetic)?.date ?? null;

  /* direct labels at right end of lines */
  const labelYs = useMemo(() => {
    if (!yScale || !activeDate) return {};
    const raw: { id: string; y: number }[] = [];
    if (activePoint?.level != null) raw.push({ id: 'overall', y: yScale(activePoint.level) });
    for (const route of ROUTES) {
      const v = routeActiveValues[route];
      if (v != null) raw.push({ id: route, y: yScale(v) });
    }
    return nudgeLabels(raw);
  }, [yScale, activePoint, routeActiveValues, activeDate]);

  /* scrubbing */
  const handlePointerMove = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (!xScale || validOverall.length === 0) return;
    const rect = svgRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left - MARGIN.left;
    const date = xScale.invert(Math.max(0, Math.min(mx, innerW)));
    const nearest = d3Array.least(validOverall, p =>
      Math.abs(parseUTC(p.date).getTime() - date.getTime()),
    );
    if (nearest) onSelectDate(nearest.date);
  }, [xScale, validOverall, innerW, onSelectDate]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<SVGSVGElement>) => {
    if (!activeDate || validOverall.length === 0) return;
    const idx = validOverall.findIndex(p => p.date === activeDate);
    if (e.key === 'ArrowRight' && idx < validOverall.length - 1) {
      onSelectDate(validOverall[idx + 1].date);
      e.preventDefault();
    } else if (e.key === 'ArrowLeft' && idx > 0) {
      onSelectDate(validOverall[idx - 1].date);
      e.preventDefault();
    } else if (e.key === 'Escape') {
      onSelectDate(null);
      e.preventDefault();
    }
  }, [activeDate, validOverall, onSelectDate]);

  /* headline */
  const headline = makeHeadline(activePoint, prevPoint, freq, routeData, DEFAULT_ROUTE_WEIGHTS);

  const baseY = yScale ? yScale(100) : null;

  /* data status sentence */
  const allSynth = validOverall.length > 0 && validOverall.every(p => p.is_synthetic);
  const noneSynth = validOverall.every(p => !p.is_synthetic);
  let statusSentence = '';
  if (validOverall.length === 0) {
    statusSentence = 'No fares collected yet. The first run is scheduled for 05:00 IST.';
  } else if (allSynth) {
    statusSentence = 'All data shown is synthetic. No fares have been collected yet.';
  } else if (!noneSynth && firstRealDate) {
    statusSentence = `Data before ${fmtDateShort(firstRealDate)} is synthetic. Fares were collected from ${fmtDateShort(firstRealDate)}.`;
  }

  /* show dots when ≤ 45 points */
  const showDots = validOverall.length <= 45;

  /* ghost line (default weights) when weights changed */
  const defaultOverallPath = useMemo(() => {
    if (!lineGenLinear || !weightsChanged) return null;
    const defaultPts = overall.filter(p => p.level != null);
    return lineGenLinear(defaultPts);
  }, [lineGenLinear, weightsChanged, overall]);

  const customOverallPath = useMemo(() => {
    if (!lineGenLinear) return null;
    const pts = (weightsChanged && customPoints.length > 0 ? customPoints : overall)
      .filter(p => p.level != null);
    return lineGenLinear(pts);
  }, [lineGenLinear, weightsChanged, customPoints, overall]);

  /* route paths */
  const routePaths = useMemo(() => {
    if (!lineGenLinear) return {};
    const result: Record<string, string | null> = {};
    for (const route of ROUTES) {
      const pts = (routeData[route] ?? []).filter(p => p.level != null);
      result[route] = pts.length > 0 ? lineGenLinear(pts) : null;
    }
    return result;
  }, [lineGenLinear, routeData]);

  const hasSynth = validOverall.some(p => p.is_synthetic);

  /* ── render ──────────────────────────────────────────────────────── */
  return (
    <div className="page">
      {/* Headline sentence (§5.1) */}
      {!loading && !error && activePoint && (
        <div style={{ marginBottom: 'var(--sp-6)' }}>
          <p className="headline">{headline}</p>
          <p style={{
            fontFamily: "'Newsreader Variable', Georgia, serif",
            fontSize: '18px',
            lineHeight: 1.55,
            marginTop: 'var(--sp-2)',
            color: 'var(--ink)',
          }}>
            The index is {fmtNum(activePoint.level)} ({
              overall.at(0)
                ? `${fmtDateShort(overall[0].date)} = 100`
                : 'base = 100'
            }).{' '}
            <span style={{ color: 'var(--ink-2)' }}>{statusSentence}</span>
          </p>
        </div>
      )}

      {error && (
        <div className="error-state">
          <p>{error}</p>
        </div>
      )}

      {/* Frequency toggle */}
      {!loading && !error && (
        <div className="toggle-group" style={{ marginBottom: 'var(--sp-4)' }}>
          {(['daily', 'weekly', 'monthly'] as Freq[]).map((f, i) => (
            <span key={f} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
              {i > 0 && <span className="toggle-sep">|</span>}
              <button
                className="toggle-btn"
                aria-pressed={freq === f}
                onClick={() => setFreq(f)}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Chart */}
      {loading ? (
        <div className="loading">Loading fare data…</div>
      ) : validOverall.length === 0 ? (
        <div className="empty-state">
          No fares collected yet. The first run is scheduled for 05:00 IST.
        </div>
      ) : (
        <figure className="chart-figure">
          <figcaption className="text-secondary" style={{ marginBottom: 'var(--sp-2)' }}>
            {activeDate ? `Showing ${fmtDate(activeDate)}` : 'Hover or use arrow keys to scrub'}
          </figcaption>

          <div className="chart-wrap" ref={wrapRef}>
            {/* aria-live region for scrub readouts */}
            <div
              id={liveId}
              aria-live="polite"
              aria-atomic="true"
              style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}
            >
              {activeDate && activePoint ? (
                `${fmtDate(activeDate)}: overall ${fmtNum(activePoint.level)}, ${
                  ROUTES.map(r => `${r} ${fmtNum(routeActiveValues[r])}`).join(', ')
                }`
              ) : ''}
            </div>

            <svg
              ref={svgRef}
              width={w}
              height={CHART_H}
              role="img"
              aria-label={`APIx fare index chart, ${validOverall.length} data points. Use arrow keys to scrub.`}
              aria-describedby={liveId}
              tabIndex={0}
              style={{ cursor: 'crosshair', outline: 'none' }}
              onPointerMove={handlePointerMove}
              onPointerLeave={() => onSelectDate(null)}
              onKeyDown={handleKeyDown}
            >
              <defs>
                {/* Synthetic hatch pattern */}
                {hasSynth && (
                  <pattern id="synth-hatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
                    <line x1="0" y1="0" x2="0" y2="8" stroke="var(--hatch)" strokeWidth="1.5" opacity="0.35" />
                  </pattern>
                )}
              </defs>

              <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
                {/* Gridlines */}
                {yTicks.map(({ val, y }) => (
                  <line key={val} x1={0} x2={innerW} y1={y} y2={y}
                    stroke="var(--contour)" strokeWidth={1} />
                ))}

                {/* Synthetic band */}
                {hasSynth && xScale && synthStart && synthEnd && (
                  <>
                    <rect
                      x={xScale(parseUTC(synthStart))}
                      y={0}
                      width={Math.max(0, xScale(parseUTC(synthEnd)) - xScale(parseUTC(synthStart)))}
                      height={innerH}
                      fill="url(#synth-hatch)"
                    />
                    <text
                      x={xScale(parseUTC(synthStart)) + 8}
                      y={16}
                      fontSize="var(--t-axis)"
                      fill="var(--hatch)"
                      fontFamily="'B612', monospace"
                    >
                      Synthetic data
                    </text>
                  </>
                )}

                {/* Vertical rule at start of real data */}
                {firstRealDate && !allSynth && xScale && (
                  <line
                    x1={xScale(parseUTC(firstRealDate))}
                    x2={xScale(parseUTC(firstRealDate))}
                    y1={0} y2={innerH}
                    stroke="var(--ink-2)"
                    strokeWidth={1}
                    strokeDasharray="3 3"
                  />
                )}

                {/* Base line at 100 */}
                {baseY != null && (
                  <>
                    <line
                      x1={0} x2={innerW}
                      y1={baseY} y2={baseY}
                      stroke="var(--ink-2)"
                      strokeWidth={1}
                      strokeDasharray="2 4"
                    />
                    <text
                      x={4}
                      y={baseY - 4}
                      fontSize="var(--t-axis)"
                      fill="var(--ink-2)"
                      fontFamily="'B612', monospace"
                    >
                      Base = 100
                    </text>
                  </>
                )}

                {/* Route lines (1.25px) — drawn first */}
                {ROUTES.map((route, ri) => {
                  const path = routePaths[route];
                  if (!path) return null;
                  const opacity = hoveredRoute && hoveredRoute !== route ? 0.25 : 1;
                  return (
                    <path
                      key={route}
                      d={path}
                      fill="none"
                      stroke={ROUTE_COLORS[route]}
                      strokeWidth={1.25}
                      opacity={opacity}
                      className="line-draw"
                      style={{
                        '--draw-delay': `${ri * 120}ms`,
                        '--draw-dur': '800ms',
                      } as React.CSSProperties}
                    />
                  );
                })}

                {/* Ghost line (default weights) */}
                {defaultOverallPath && (
                  <path
                    d={defaultOverallPath}
                    fill="none"
                    stroke="var(--ink-2)"
                    strokeWidth={1.25}
                    strokeDasharray="3 3"
                    opacity={0.5}
                  />
                )}

                {/* Overall line (2.5px, ink) — drawn last */}
                {customOverallPath && (
                  <path
                    d={customOverallPath}
                    fill="none"
                    stroke="var(--ink)"
                    strokeWidth={2.5}
                    className="line-draw"
                    style={{
                      '--draw-delay': `${ROUTES.length * 120}ms`,
                      '--draw-dur': '900ms',
                    } as React.CSSProperties}
                  />
                )}

                {/* Daily dots on overall (≤ 45 pts) */}
                {showDots && xScale && yScale && validOverall.map(p => (
                  p.level != null ? (
                    <circle
                      key={p.date}
                      cx={xScale(parseUTC(p.date))}
                      cy={yScale(p.level)}
                      r={2}
                      fill="var(--ink)"
                    />
                  ) : null
                ))}

                {/* Scrub hairline */}
                {activeDate && xScale && (
                  <line
                    x1={xScale(parseUTC(activeDate))}
                    x2={xScale(parseUTC(activeDate))}
                    y1={0} y2={innerH}
                    stroke="var(--ink)"
                    strokeWidth={1}
                    opacity={0.4}
                    pointerEvents="none"
                  />
                )}

                {/* Y-axis labels */}
                {yTicks.map(({ val, y }) => (
                  <text key={val} x={-8} y={y}
                    textAnchor="end" dominantBaseline="middle"
                    fontSize="var(--t-axis)" fill="var(--ink-2)"
                    fontFamily="'B612', monospace"
                  >
                    {val.toFixed(1)}
                  </text>
                ))}

                {/* X-axis labels */}
                {xTicks.map(({ val, x }) => (
                  <text key={val.getTime()} x={x} y={innerH + 20}
                    textAnchor="middle"
                    fontSize="var(--t-axis)" fill="var(--ink-2)"
                    fontFamily="'B612', monospace"
                  >
                    {fmtDateShort(val.toISOString().slice(0, 10))}
                  </text>
                ))}

                {/* Axis lines */}
                <line x1={0} x2={0} y1={0} y2={innerH} stroke="var(--contour)" />
                <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke="var(--contour)" />

                {/* Direct labels at right end */}
                {activeDate && xScale && yScale && (() => {
                  const labelX = innerW + 8;
                  return (
                    <>
                      {/* Overall label */}
                      {activePoint?.level != null && labelYs['overall'] != null && (
                        <text
                          x={labelX}
                          y={labelYs['overall']}
                          fontSize="var(--t-axis)"
                          fill="var(--ink)"
                          fontFamily="'B612', monospace"
                          fontWeight="700"
                          dominantBaseline="middle"
                        >
                          Overall {fmtNum(activePoint.level, 1)}
                        </text>
                      )}
                      {/* Route labels */}
                      {ROUTES.map(route => {
                        const val = routeActiveValues[route];
                        if (val == null || labelYs[route] == null) return null;
                        return (
                          <text
                            key={route}
                            x={labelX}
                            y={labelYs[route]}
                            fontSize="var(--t-axis)"
                            fill={ROUTE_COLORS[route]}
                            fontFamily="'B612', monospace"
                            dominantBaseline="middle"
                            style={{ cursor: 'pointer' }}
                            onMouseEnter={() => setHoveredRoute(route)}
                            onMouseLeave={() => setHoveredRoute(null)}
                          >
                            {route} {fmtNum(val, 1)}
                          </text>
                        );
                      })}
                    </>
                  );
                })()}
              </g>
            </svg>
          </div>

          {/* Data table (accessibility) */}
          <details className="chart-data-table">
            <summary>Show data as table</summary>
            <table aria-label="Index data">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Overall</th>
                  {ROUTES.map(r => <th key={r}>{r}</th>)}
                  <th>Synthetic</th>
                </tr>
              </thead>
              <tbody>
                {validOverall.slice(-30).map(p => (
                  <tr key={p.date}>
                    <td>{fmtDateShort(p.date)}</td>
                    <td className="font-num">{fmtNum(p.level)}</td>
                    {ROUTES.map(r => (
                      <td key={r} className="font-num">
                        {fmtNum(routeData[r]?.find(rp => rp.date === p.date)?.level ?? null)}
                      </td>
                    ))}
                    <td>{p.is_synthetic ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </figure>
      )}

      {/* WeightBar */}
      {!loading && !error && validOverall.length > 0 && (
        <section className="section">
          <WeightBar
            leadWeights={leadWeights}
            routeWeights={routeWeightsCustom}
            mode={weightMode}
            sensitivity={sensitivity}
            onLeadChange={w => { setLeadWeights(w); setWeightsChanged(true); }}
            onRouteChange={w => { setRouteWeightsCustom(w); setWeightsChanged(true); }}
            onModeChange={setWeightMode}
            onReset={() => {
              setLeadWeights(DEFAULT_LEAD_WEIGHTS);
              setRouteWeightsCustom(DEFAULT_ROUTE_WEIGHTS);
              setWeightsChanged(false);
            }}
          />
        </section>
      )}

      {/* Collection record */}
      {!loading && runs.length > 0 && (
        <section className="section">
          <RecordStrip runs={runs} />
        </section>
      )}
    </div>
  );
}
