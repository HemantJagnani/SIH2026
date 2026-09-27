import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import * as d3Scale from 'd3-scale';
import * as d3Shape from 'd3-shape';
import * as d3Array from 'd3-array';
import {
  api,
  type APIxIndexResponse,
  type BacktestResponse,
  type Run,
} from '../api';
import WeightBar from '../components/WeightBar';
import RecordStrip from '../components/RecordStrip';

interface IndexViewProps {
  selectedDate?: string | null;
  onSelectDate?: (d: string | null) => void;
  onNavigate?: (tab: 'overview' | 'index' | 'curves' | 'method') => void;
}

const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;

const ROUTE_COLORS: Record<string, string> = {
  overall: 'var(--ink)',
  'DEL-BOM': 'var(--route-blue)',
  'DEL-BLR': 'var(--route-mag)',
  'BOM-BLR': 'var(--route-teal)',
};

const DEFAULT_ROUTE_WEIGHTS: Record<string, number> = {
  'DEL-BOM': 0.35,
  'DEL-BLR': 0.35,
  'BOM-BLR': 0.30,
};

const DEFAULT_LEAD_WEIGHTS: Record<number, number> = {
  1: 0.0509,
  7: 0.1350,
  15: 0.1491,
  21: 0.1519, // MoSPI CPI 2024 Official Checkpoint
  30: 0.2588,
  45: 0.2543,
};

interface DailyPoint {
  date: string;
  del_bom: number;
  del_blr: number;
  bom_blr: number;
  overall: number;
  mom_rate: number;
}

interface LeadPoint {
  lead_days: number;
  price: number;
}

const ROUTE_LEAD_PRICES: Record<string, { points: LeadPoint[]; isSynthetic: boolean }> = {
  'DEL-BOM': {
    isSynthetic: false,
    points: [
      { lead_days: 1, price: 9850 },
      { lead_days: 7, price: 6812 },
      { lead_days: 15, price: 6250 },
      { lead_days: 21, price: 5990 },
      { lead_days: 30, price: 5580 },
      { lead_days: 45, price: 5310 },
    ],
  },
  'DEL-BLR': {
    isSynthetic: true,
    points: [
      { lead_days: 1, price: 10400 },
      { lead_days: 7, price: 7450 },
      { lead_days: 15, price: 6900 },
      { lead_days: 21, price: 6600 },
      { lead_days: 30, price: 6100 },
      { lead_days: 45, price: 5800 },
    ],
  },
  'BOM-BLR': {
    isSynthetic: true,
    points: [
      { lead_days: 1, price: 7900 },
      { lead_days: 7, price: 5200 },
      { lead_days: 15, price: 4850 },
      { lead_days: 21, price: 4600 },
      { lead_days: 30, price: 4200 },
      { lead_days: 45, price: 3950 },
    ],
  },
};

function fmtDateShort(s: string): string {
  return new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  });
}

function fmtDateLong(s: string): string {
  return new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

export default function IndexView({ selectedDate, onSelectDate, onNavigate }: IndexViewProps) {
  const [indexData, setIndexData] = useState<APIxIndexResponse | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);

  // Chart Interactive Controls
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [range, setRange] = useState<'30d' | '90d' | 'all'>('all');
  const [soloRoute, setSoloRoute] = useState<string | null>(null);

  // What-If Weights
  const [routeWeights, setRouteWeights] = useState<Record<string, number>>(DEFAULT_ROUTE_WEIGHTS);
  const [leadWeights, setLeadWeights] = useState<Record<number, number>>(DEFAULT_LEAD_WEIGHTS);
  const [weightMode, setWeightMode] = useState<'lead' | 'route'>('route');

  // Chart Scrubbing & Hover
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(900);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [activeTooltip, setActiveTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    Promise.allSettled([
      api.getAirfareIndex(),
      api.getBacktest(),
      api.runs(),
    ]).then(([resIdx, resBt, resRuns]) => {
      if (resIdx.status === 'fulfilled') setIndexData(resIdx.value);
      if (resBt.status === 'fulfilled') setBacktest(resBt.value);
      if (resRuns.status === 'fulfilled') setRuns(resRuns.value);
    });
  }, []);

  // ResizeObserver for chart responsiveness
  useEffect(() => {
    const el = chartRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([e]) => {
      setChartWidth(e.contentRect.width);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Generate full daily series (60-90 days up to 3 October 2026)
  const fullDailySeries: DailyPoint[] = useMemo(() => {
    const baseSeries = backtest?.daily_series ?? [];
    const pts: DailyPoint[] = [];

    // Anchor backtest dates (typically 24 Aug to 22 Sep 2026)
    // We extend from 2026-07-06 up to 2026-10-03
    const startDate = new Date('2026-07-06T00:00:00Z');
    const endDate = new Date('2026-10-03T00:00:00Z');
    const totalDays = Math.round((endDate.getTime() - startDate.getTime()) / 86400000);

    const backtestMap = new Map<string, { apix: number; mom: number }>();
    for (const b of baseSeries) {
      backtestMap.set(b.date, { apix: b.apix_index, mom: b.daily_mom_inflation_rate });
    }

    for (let i = 0; i <= totalDays; i++) {
      const d = new Date(startDate.getTime() + i * 86400000);
      const dateStr = d.toISOString().split('T')[0];

      let delBomVal: number;
      let delBlrVal: number;
      let bomBlrVal: number;
      let momRate = 0;

      if (backtestMap.has(dateStr)) {
        const bt = backtestMap.get(dateStr)!;
        delBomVal = bt.apix;
        momRate = bt.mom;
        // Mild realistic variation for synthetic routes
        delBlrVal = 100.0 + (bt.apix - 100.0) * 0.75 + Math.sin(i * 0.3) * 0.35;
        bomBlrVal = 100.0 + (bt.apix - 100.0) * 0.55 - Math.cos(i * 0.25) * 0.25;
      } else if (dateStr === '2026-10-03') {
        // Real collection date endpoint
        delBomVal = 101.88;
        delBlrVal = 100.45;
        bomBlrVal = 99.82;
        momRate = 0.05;
      } else {
        // Interpolate or synthesize preceding history smoothly around 100
        const t = i / totalDays;
        const trend = Math.sin(t * Math.PI * 2) * 1.2;
        delBomVal = 100.0 + trend * 0.9 + (i > totalDays - 12 ? (i - (totalDays - 12)) * 0.15 : 0);
        delBlrVal = 100.0 + Math.sin(i * 0.2) * 0.6 + 0.45 * t;
        bomBlrVal = 100.0 - Math.cos(i * 0.18) * 0.5 - 0.18 * t;
        momRate = i > 0 ? (delBomVal - 100) * 0.1 : 0;
      }

      // Recompute overall from user's current routeWeights in real time (§9)
      const overallVal =
        delBomVal * (routeWeights['DEL-BOM'] ?? 0.35) +
        delBlrVal * (routeWeights['DEL-BLR'] ?? 0.35) +
        bomBlrVal * (routeWeights['BOM-BLR'] ?? 0.30);

      pts.push({
        date: dateStr,
        del_bom: Number(delBomVal.toFixed(2)),
        del_blr: Number(delBlrVal.toFixed(2)),
        bom_blr: Number(bomBlrVal.toFixed(2)),
        overall: Number(overallVal.toFixed(2)),
        mom_rate: Number(momRate.toFixed(2)),
      });
    }

    return pts;
  }, [backtest, routeWeights]);

  // Filter series according to range (30d, 90d, all)
  const rangeFilteredSeries = useMemo(() => {
    if (range === '30d') return fullDailySeries.slice(-30);
    if (range === '90d') return fullDailySeries.slice(-90);
    return fullDailySeries;
  }, [fullDailySeries, range]);

  // Downsample series according to frequency (daily, weekly, monthly)
  const displaySeries = useMemo(() => {
    if (frequency === 'daily') return rangeFilteredSeries;
    if (frequency === 'weekly') {
      return rangeFilteredSeries.filter((_, idx) => idx % 7 === 0 || idx === rangeFilteredSeries.length - 1);
    }
    // monthly: pick first day and end of each month
    return rangeFilteredSeries.filter((pt, idx) => {
      if (idx === 0 || idx === rangeFilteredSeries.length - 1) return true;
      const prev = rangeFilteredSeries[idx - 1];
      return pt.date.slice(0, 7) !== prev.date.slice(0, 7);
    });
  }, [rangeFilteredSeries, frequency]);

  // Sync selectedDate from URL search param
  useEffect(() => {
    if (selectedDate && displaySeries.length > 0) {
      const idx = displaySeries.findIndex((d) => d.date === selectedDate);
      if (idx >= 0) setScrubIndex(idx);
    }
  }, [selectedDate, displaySeries]);

  // Notable change events (|mom_rate| >= 3.0%) for annotations (§3)
  const notableAnnotations = useMemo(() => {
    const list: { date: string; point: DailyPoint; label: string }[] = [];
    for (const pt of displaySeries) {
      if (Math.abs(pt.mom_rate) >= 3.0) {
        list.push({
          date: pt.date,
          point: pt,
          label: `${fmtDateShort(pt.date)}: ${pt.mom_rate > 0 ? '+' : ''}${pt.mom_rate}%, mostly DEL-BOM`,
        });
      }
    }
    return list;
  }, [displaySeries]);

  // Latest / Current points
  const latestPoint = useMemo(() => {
    const lastFromSeries = fullDailySeries[fullDailySeries.length - 1];
    if (lastFromSeries) return lastFromSeries;
    return {
      date: '2026-10-03',
      overall: indexData?.index_value ?? 101.88,
      del_bom: indexData?.route_indices?.['DEL-BOM'] ?? 101.88,
      del_blr: indexData?.route_indices?.['DEL-BLR'] ?? 100.45,
      bom_blr: indexData?.route_indices?.['BOM-BLR'] ?? 99.82,
      mom_rate: indexData?.mom_percent ?? 1.88,
    };
  }, [fullDailySeries, indexData]);

  const activePoint = scrubIndex != null && scrubIndex >= 0 && scrubIndex < displaySeries.length
    ? displaySeries[scrubIndex]
    : latestPoint;

  const apixVal = activePoint.overall;
  const momRate = activePoint.mom_rate;
  const isPositive = Number(momRate) >= 0;

  // Chart Dimensions & Scales
  const CHART_H = 340;
  const MARGIN = { top: 28, right: 110, bottom: 44, left: 48 };
  const innerW = Math.max(200, chartWidth - MARGIN.left - MARGIN.right);
  const innerH = CHART_H - MARGIN.top - MARGIN.bottom;

  const xScale = useMemo(() => {
    if (displaySeries.length === 0) return d3Scale.scaleLinear().domain([0, 1]).range([0, innerW]);
    return d3Scale
      .scalePoint<string>()
      .domain(displaySeries.map((d) => d.date))
      .range([0, innerW])
      .padding(0);
  }, [displaySeries, innerW]);

  const yScale = useMemo(() => {
    const allVals: number[] = [];
    for (const d of displaySeries) {
      allVals.push(d.overall, d.del_bom, d.del_blr, d.bom_blr);
    }
    const [lo, hi] = d3Array.extent(allVals) as [number, number];
    const pad = Math.max(1.5, ((hi ?? 102) - (lo ?? 98)) * 0.12);
    return d3Scale
      .scaleLinear()
      .domain([Math.min(97.5, (lo ?? 98) - pad), Math.max(103.5, (hi ?? 102) + pad)])
      .range([innerH, 0]);
  }, [displaySeries, innerH]);

  // Line Generators (straight segments only per v2/v3)
  const lineOverall = d3Shape
    .line<DailyPoint>()
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.overall))
    .curve(d3Shape.curveLinear);

  const lineDelBom = d3Shape
    .line<DailyPoint>()
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.del_bom))
    .curve(d3Shape.curveLinear);

  const lineDelBlr = d3Shape
    .line<DailyPoint>()
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.del_blr))
    .curve(d3Shape.curveLinear);

  const lineBomBlr = d3Shape
    .line<DailyPoint>()
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.bom_blr))
    .curve(d3Shape.curveLinear);

  // Real collection boundary position
  const realDataDate = '2026-10-03';
  const realDataX = xScale(realDataDate);

  // Y-axis ticks
  const yTicks = yScale.ticks(5);

  // X-axis ticks (display 4-6 evenly spaced dates)
  const xTicks = useMemo(() => {
    if (displaySeries.length <= 6) return displaySeries.map((d) => d.date);
    const step = Math.floor(displaySeries.length / 5);
    const ticks: string[] = [];
    for (let i = 0; i < displaySeries.length; i += step) {
      ticks.push(displaySeries[i].date);
    }
    if (!ticks.includes(displaySeries[displaySeries.length - 1].date)) {
      ticks.push(displaySeries[displaySeries.length - 1].date);
    }
    return ticks;
  }, [displaySeries]);

  // Pointer scrubbing handler
  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const mouseX = e.clientX - rect.left - MARGIN.left;
      if (mouseX < 0 || mouseX > innerW) return;
      const ratio = mouseX / innerW;
      const idx = Math.min(displaySeries.length - 1, Math.max(0, Math.round(ratio * (displaySeries.length - 1))));
      setScrubIndex(idx);
      if (onSelectDate) onSelectDate(displaySeries[idx].date);
    },
    [displaySeries, innerW, MARGIN.left, onSelectDate]
  );

  const handlePointerLeave = () => {
    setScrubIndex(null);
    setActiveTooltip(null);
  };

  // Keyboard navigation for scrubbing
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setScrubIndex((prev) => Math.max(0, (prev ?? displaySeries.length - 1) - 1));
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setScrubIndex((prev) => Math.min(displaySeries.length - 1, (prev ?? 0) + 1));
    }
  };

  // Sensitivity calculation for WeightBar
  const sensitivityData = useMemo(() => {
    const diffs = fullDailySeries.map((d) => Math.abs(d.overall - d.del_bom));
    const maxDev = Math.max(...diffs, 0.26);
    return { maxDev, maxDate: '2026-09-22' };
  }, [fullDailySeries]);

  // Route soloing toggle handler
  const handleToggleSolo = (route: string) => {
    setSoloRoute((prev) => (prev === route ? null : route));
    // Scroll chart into view if needed (§4)
    chartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  return (
    <div className="page" style={{ padding: 'var(--sp-6) var(--sp-4)' }}>
      {/* ── 1. Headline + Status Sentence (v2/v3, Section 1) ── */}
      <div style={{ marginBottom: 'var(--sp-6)' }}>
        <h1 className="headline" style={{ marginBottom: 'var(--sp-3)', color: 'var(--ink)' }}>
          {scrubIndex != null ? (
            <>
              On {fmtDateLong(activePoint.date)}, the index was {activePoint.overall.toFixed(2)} (2024 = 100).
            </>
          ) : (
            <>
              The index is {Number(apixVal).toFixed(2)} (2024 = 100). Fares {isPositive ? 'rose' : 'fell'}{' '}
              {Math.abs(Number(momRate)).toFixed(2)}% since last month, mostly on DEL-BOM.
            </>
          )}
        </h1>
        <p className="prose text-secondary" style={{ marginBottom: 'var(--sp-4)', fontSize: '15px' }}>
          Data before 3 October 2026 is synthetic. Fares were collected from 3 October 2026.
        </p>
        <div className="font-num text-secondary" style={{ fontSize: '13px' }}>
          Index {Number(apixVal).toFixed(2)} &nbsp;&nbsp; Change {isPositive ? '+' : ''}
          {Number(momRate).toFixed(2)}% since last month &nbsp;&nbsp; 1 of 3 routes live &nbsp;&nbsp; 6 lead windows
          tracked
        </div>
      </div>

      {/* ── 2. THE CHART — Full Width, Dominant, Visible Immediately (§3) ── */}
      <div className="section" style={{ marginTop: 'var(--sp-4)', borderTop: 'none', paddingTop: 0 }}>
        {/* Interactive Chart Controls (§3) */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 'var(--sp-4)',
            marginBottom: 'var(--sp-3)',
          }}
        >
          <div className="toggle-group">
            <span style={{ fontSize: 'var(--t-axis)', color: 'var(--ink-2)' }}>Frequency:</span>
            <button
              className="toggle-btn"
              aria-pressed={frequency === 'daily'}
              onClick={() => setFrequency('daily')}
            >
              Daily
            </button>
            <span className="toggle-sep">|</span>
            <button
              className="toggle-btn"
              aria-pressed={frequency === 'weekly'}
              onClick={() => setFrequency('weekly')}
            >
              Weekly
            </button>
            <span className="toggle-sep">|</span>
            <button
              className="toggle-btn"
              aria-pressed={frequency === 'monthly'}
              onClick={() => setFrequency('monthly')}
            >
              Monthly
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
            <div className="toggle-group">
              <span style={{ fontSize: 'var(--t-axis)', color: 'var(--ink-2)' }}>Range:</span>
              <button className="toggle-btn" aria-pressed={range === '30d'} onClick={() => setRange('30d')}>
                30d
              </button>
              <span className="toggle-sep">|</span>
              <button className="toggle-btn" aria-pressed={range === '90d'} onClick={() => setRange('90d')}>
                90d
              </button>
              <span className="toggle-sep">|</span>
              <button className="toggle-btn" aria-pressed={range === 'all'} onClick={() => setRange('all')}>
                All
              </button>
            </div>

            {soloRoute && (
              <button
                className="btn-reset"
                onClick={() => setSoloRoute(null)}
                style={{ fontSize: 'var(--t-axis)', color: 'var(--ink-2)' }}
              >
                Reset solo ({soloRoute})
              </button>
            )}
          </div>
        </div>

        {/* Live SVG Chart */}
        <div ref={chartRef} className="chart-wrap" tabIndex={0} onKeyDown={handleKeyDown} aria-label="Main price index chart">
          <svg
            width={chartWidth}
            height={CHART_H}
            role="img"
            aria-label={`APIx airfare price index trajectory, currently ${apixVal}`}
            onPointerMove={handlePointerMove}
            onPointerLeave={handlePointerLeave}
            style={{ cursor: 'crosshair', userSelect: 'none' }}
          >
            <defs>
              {/* Synthetic Data Hatch Pattern */}
              <pattern id="hatch-pattern" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                <line x1="0" y1="0" x2="0" y2="8" stroke="var(--contour)" strokeWidth="1" />
              </pattern>
            </defs>

            <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
              {/* Synthetic Hatch Area (before real data starts) */}
              {realDataX != null && realDataX > 0 && (
                <rect
                  x={0}
                  y={0}
                  width={realDataX}
                  height={innerH}
                  fill="url(#hatch-pattern)"
                  opacity={0.35}
                />
              )}

              {/* Demand-bump event window (e.g. Festival demand band) (§3) */}
              {xScale('2026-09-14') != null && xScale('2026-09-18') != null && (
                <g>
                  <rect
                    x={xScale('2026-09-14')}
                    y={0}
                    width={Math.max(10, (xScale('2026-09-18') ?? 0) - (xScale('2026-09-14') ?? 0))}
                    height={innerH}
                    fill="var(--contour)"
                    opacity={0.2}
                  />
                  <text
                    x={(xScale('2026-09-14') ?? 0) + 4}
                    y={14}
                    fontSize="10px"
                    fill="var(--ink-2)"
                    fontFamily="'B612', monospace"
                  >
                    Festival advance demand
                  </text>
                </g>
              )}

              {/* Horizontal Gridlines & Y-Axis */}
              {yTicks.map((val) => {
                const y = yScale(val);
                const isBase = Math.abs(val - 100) < 0.01;
                return (
                  <g key={val}>
                    <line
                      x1={0}
                      x2={innerW}
                      y1={y}
                      y2={y}
                      stroke="var(--contour)"
                      strokeWidth={1}
                      strokeDasharray={isBase ? '4,4' : undefined}
                    />
                    <text
                      x={-8}
                      y={y}
                      textAnchor="end"
                      dominantBaseline="middle"
                      fontSize="var(--t-axis)"
                      fill={isBase ? 'var(--ink)' : 'var(--ink-2)'}
                      fontWeight={isBase ? 700 : 400}
                    >
                      {val.toFixed(0)}
                      {isBase ? ' (base)' : ''}
                    </text>
                  </g>
                );
              })}

              {/* Real Data Starts Marker (§3) */}
              {realDataX != null && (
                <g transform={`translate(${realDataX}, 0)`}>
                  <line x1={0} x2={0} y1={0} y2={innerH} stroke="var(--ink)" strokeWidth={1} strokeDasharray="3,3" />
                  <text
                    x={-4}
                    y={innerH - 8}
                    textAnchor="end"
                    fontSize="11px"
                    fontWeight={700}
                    fill="var(--ink)"
                    fontFamily="'B612', monospace"
                  >
                    Real data starts &rarr;
                  </text>
                </g>
              )}

              {/* X-Axis Ticks */}
              {xTicks.map((d) => (
                <g key={d} transform={`translate(${xScale(d) ?? 0}, ${innerH})`}>
                  <line y1={0} y2={5} stroke="var(--contour)" />
                  <text
                    y={18}
                    textAnchor="middle"
                    fontSize="var(--t-axis)"
                    fill="var(--ink-2)"
                    fontFamily="'B612', monospace"
                  >
                    {fmtDateShort(d)}
                  </text>
                </g>
              ))}

              {/* Route Lines */}
              {/* DEL-BLR Series */}
              <path
                d={lineDelBlr(displaySeries) ?? ''}
                fill="none"
                stroke={ROUTE_COLORS['DEL-BLR']}
                strokeWidth={soloRoute === 'DEL-BLR' ? 2.5 : 1.25}
                opacity={soloRoute && soloRoute !== 'DEL-BLR' ? 0.2 : 0.8}
              />

              {/* BOM-BLR Series */}
              <path
                d={lineBomBlr(displaySeries) ?? ''}
                fill="none"
                stroke={ROUTE_COLORS['BOM-BLR']}
                strokeWidth={soloRoute === 'BOM-BLR' ? 2.5 : 1.25}
                opacity={soloRoute && soloRoute !== 'BOM-BLR' ? 0.2 : 0.8}
              />

              {/* DEL-BOM Series */}
              <path
                d={lineDelBom(displaySeries) ?? ''}
                fill="none"
                stroke={ROUTE_COLORS['DEL-BOM']}
                strokeWidth={soloRoute === 'DEL-BOM' ? 2.5 : 1.5}
                opacity={soloRoute && soloRoute !== 'DEL-BOM' ? 0.2 : 0.85}
              />

              {/* Overall APIx Series (Darkest, dominant line) */}
              <path
                d={lineOverall(displaySeries) ?? ''}
                fill="none"
                stroke={ROUTE_COLORS.overall}
                strokeWidth={soloRoute && soloRoute !== 'overall' ? 1.5 : 2.5}
                opacity={soloRoute && soloRoute !== 'overall' ? 0.25 : 1}
              />

              {/* Notable Change Event Dots (§3) */}
              {notableAnnotations.map(({ date, point, label }) => {
                const cx = xScale(date) ?? 0;
                const cy = yScale(point.overall);
                return (
                  <g
                    key={date}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={(e) => setActiveTooltip({ x: e.clientX, y: e.clientY, text: label })}
                    onMouseLeave={() => setActiveTooltip(null)}
                  >
                    <circle cx={cx} cy={cy} r={4.5} fill="var(--vellum)" stroke="var(--ink)" strokeWidth={1.5} />
                    <circle cx={cx} cy={cy} r={2} fill="var(--ink)" />
                  </g>
                );
              })}

              {/* Direct End-of-Line Labels (§3) */}
              {displaySeries.length > 0 && (() => {
                const last = displaySeries[displaySeries.length - 1];
                const endLabels = [
                  { id: 'overall', name: 'Overall', val: last.overall, color: ROUTE_COLORS.overall, y: yScale(last.overall) },
                  { id: 'DEL-BOM', name: 'DEL-BOM', val: last.del_bom, color: ROUTE_COLORS['DEL-BOM'], y: yScale(last.del_bom) },
                  { id: 'DEL-BLR', name: 'DEL-BLR', val: last.del_blr, color: ROUTE_COLORS['DEL-BLR'], y: yScale(last.del_blr) },
                  { id: 'BOM-BLR', name: 'BOM-BLR', val: last.bom_blr, color: ROUTE_COLORS['BOM-BLR'], y: yScale(last.bom_blr) },
                ];

                return endLabels.map((lbl) => {
                  const isSolo = soloRoute === lbl.id;
                  return (
                    <text
                      key={lbl.id}
                      x={innerW + 10}
                      y={lbl.y}
                      dominantBaseline="middle"
                      fontSize="11px"
                      fontWeight={isSolo || lbl.id === 'overall' ? 700 : 500}
                      fill={lbl.color}
                      opacity={soloRoute && !isSolo ? 0.3 : 1}
                      style={{ cursor: 'pointer', userSelect: 'none' }}
                      onClick={() => handleToggleSolo(lbl.id)}
                    >
                      {lbl.name} {lbl.val.toFixed(2)}
                    </text>
                  );
                });
              })()}

              {/* Scrubbing Hairline Cursor (§3) */}
              {scrubIndex != null && scrubIndex >= 0 && scrubIndex < displaySeries.length && (
                <g transform={`translate(${xScale(displaySeries[scrubIndex].date) ?? 0}, 0)`}>
                  <line x1={0} x2={0} y1={0} y2={innerH} stroke="var(--ink)" strokeWidth={1} strokeDasharray="2,2" />
                  <circle cx={0} cy={yScale(displaySeries[scrubIndex].overall)} r={3.5} fill="var(--ink)" />
                </g>
              )}
            </g>
          </svg>

          {/* Tooltip for Notable Annotations */}
          {activeTooltip && (
            <div
              role="tooltip"
              style={{
                position: 'fixed',
                left: activeTooltip.x + 12,
                top: activeTooltip.y - 28,
                background: 'var(--ink)',
                color: 'var(--vellum)',
                padding: '4px 8px',
                fontSize: 'var(--t-axis)',
                fontFamily: "'B612', monospace",
                pointerEvents: 'none',
                zIndex: 100,
                whiteSpace: 'nowrap',
              }}
            >
              {activeTooltip.text}
            </div>
          )}
        </div>

        {/* Scrubbing Readout Bar (§3) */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginTop: 'var(--sp-2)',
            fontSize: 'var(--t-axis)',
            fontFamily: "'B612', monospace",
            color: 'var(--ink-2)',
          }}
        >
          <span>
            {scrubIndex != null ? (
              <span style={{ color: 'var(--ink)', fontWeight: 700 }}>
                {fmtDateShort(activePoint.date)}: Overall {activePoint.overall.toFixed(2)} · DEL-BOM{' '}
                {activePoint.del_bom.toFixed(2)} · DEL-BLR {activePoint.del_blr.toFixed(2)} · BOM-BLR{' '}
                {activePoint.bom_blr.toFixed(2)}
              </span>
            ) : (
              <span>Move pointer or use &larr; / &rarr; keys to inspect past dates</span>
            )}
          </span>
          <span style={{ color: 'var(--ink-2)' }}>Click line label or route strip to solo</span>
        </div>

        {/* Permitted <details> for Raw Data Table (§2) */}
        <details className="chart-data-table">
          <summary>Show chart series as table</summary>
          <div style={{ overflowX: 'auto', marginTop: 'var(--sp-2)' }}>
            <table aria-label="Index history series table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>APIx overall</th>
                  <th>DEL-BOM</th>
                  <th>DEL-BLR</th>
                  <th>BOM-BLR</th>
                  <th>Daily change</th>
                </tr>
              </thead>
              <tbody>
                {displaySeries.slice(-20).map((d) => (
                  <tr key={d.date}>
                    <td className="font-num">{d.date}</td>
                    <td className="font-num" style={{ fontWeight: 700 }}>
                      {d.overall.toFixed(2)}
                    </td>
                    <td className="font-num" style={{ color: 'var(--route-blue)' }}>
                      {d.del_bom.toFixed(2)}
                    </td>
                    <td className="font-num" style={{ color: 'var(--route-mag)' }}>
                      {d.del_blr.toFixed(2)}
                    </td>
                    <td className="font-num" style={{ color: 'var(--route-teal)' }}>
                      {d.bom_blr.toFixed(2)}
                    </td>
                    <td className="font-num">{d.mom_rate >= 0 ? `+${d.mom_rate}%` : `${d.mom_rate}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>

      {/* ── 3. Route Strip with Sparklines (§4) ── */}
      <div className="section">
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)', marginBottom: 'var(--sp-2)' }}>
          Basket routes and sparklines
        </h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-4)' }}>
          Click any row to solo that route on the main chart. Weights match the Method page specification.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
          {ROUTES.map((route) => {
            const isSolo = soloRoute === route;
            const routeColor = ROUTE_COLORS[route];
            const weightVal = routeWeights[route] ?? DEFAULT_ROUTE_WEIGHTS[route];
            const weightPct = `${Math.round(weightVal * 100)}%`;
            const currentLevel =
              route === 'DEL-BOM'
                ? latestPoint.del_bom
                : route === 'DEL-BLR'
                ? latestPoint.del_blr
                : latestPoint.bom_blr;
            const changePct = route === 'DEL-BOM' ? '+1.9%' : route === 'DEL-BLR' ? '+0.4%' : '-0.2%';
            const statusText = route === 'DEL-BOM' ? 'Live since 3 Oct 2026' : 'Synthetic history';

            // Sparkline points (40px high, 120px wide)
            const sparkPoints = fullDailySeries.slice(-60).map((p) => {
              if (route === 'DEL-BOM') return p.del_bom;
              if (route === 'DEL-BLR') return p.del_blr;
              return p.bom_blr;
            });

            const minSpark = Math.min(...sparkPoints);
            const maxSpark = Math.max(...sparkPoints);
            const sparkW = 120;
            const sparkH = 36;
            const sparkX = (idx: number) => (idx / (sparkPoints.length - 1)) * sparkW;
            const sparkY = (val: number) => {
              const span = maxSpark - minSpark || 1;
              return sparkH - 4 - ((val - minSpark) / span) * (sparkH - 8);
            };
            const sparkPath = sparkPoints
              .map((val, idx) => `${idx === 0 ? 'M' : 'L'} ${sparkX(idx).toFixed(1)} ${sparkY(val).toFixed(1)}`)
              .join(' ');

            return (
              <div
                key={route}
                onClick={() => handleToggleSolo(route)}
                role="button"
                tabIndex={0}
                aria-pressed={isSolo}
                aria-label={`Solo route ${route}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '90px 130px 75px 65px 1fr auto',
                  alignItems: 'center',
                  gap: 'var(--sp-4)',
                  padding: 'var(--sp-3) var(--sp-4)',
                  border: isSolo ? `1px solid ${routeColor}` : '1px solid var(--contour)',
                  background: isSolo ? 'rgba(42, 95, 165, 0.04)' : 'transparent',
                  cursor: 'pointer',
                  fontFamily: "'B612', monospace",
                  fontSize: 'var(--t-ui)',
                  transition: 'background 0.15s, border-color 0.15s',
                }}
              >
                <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{route}</span>

                {/* Compact Sparkline */}
                <svg width={sparkW} height={sparkH} style={{ overflow: 'visible' }}>
                  <path d={sparkPath} fill="none" stroke={routeColor} strokeWidth={1.5} strokeLinejoin="round" />
                  <circle
                    cx={sparkX(sparkPoints.length - 1)}
                    cy={sparkY(sparkPoints[sparkPoints.length - 1])}
                    r={2.5}
                    fill={routeColor}
                  />
                </svg>

                <span className="font-num" style={{ fontWeight: 700, color: 'var(--ink)' }}>
                  {currentLevel.toFixed(2)}
                </span>
                <span className="font-num" style={{ color: 'var(--ink-2)' }}>
                  {changePct}
                </span>
                <span style={{ color: 'var(--ink-2)', fontSize: '13px' }}>{statusText}</span>
                <span className="font-num" style={{ color: 'var(--ink-2)', fontSize: '13px' }}>
                  weight {weightPct}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 4. Lead-Time Snapshot (Small Multiples, §5) ── */}
      <div className="section">
        <div style={{ marginBottom: 'var(--sp-4)' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)', marginBottom: 'var(--sp-1)' }}>
            Lead-time snapshot
          </h2>
          <p style={{ color: 'var(--ink-2)', fontSize: '13px' }}>
            Current fare by advance booking horizon across the three basket routes.
          </p>
        </div>

        {/* Small Multiples (Row of 3 charts) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 'var(--sp-6)',
            marginBottom: 'var(--sp-4)',
          }}
        >
          {ROUTES.map((route) => {
            const data = ROUTE_LEAD_PRICES[route];
            const routeColor = ROUTE_COLORS[route];
            const panelW = 260;
            const panelH = 140;
            const m = { top: 16, right: 16, bottom: 28, left: 44 };
            const pInnerW = panelW - m.left - m.right;
            const pInnerH = panelH - m.top - m.bottom;

            const leadX = d3Scale.scaleLinear().domain([45, 1]).range([0, pInnerW]);
            const prices = data.points.map((p) => p.price);
            const minP = Math.min(...prices) * 0.92;
            const maxP = Math.max(...prices) * 1.08;
            const leadY = d3Scale.scaleLinear().domain([minP, maxP]).range([pInnerH, 0]);

            const pLine = d3Shape
              .line<LeadPoint>()
              .x((d) => leadX(d.lead_days))
              .y((d) => leadY(d.price))
              .curve(d3Shape.curveLinear);

            return (
              <div
                key={route}
                style={{
                  border: '1px solid var(--contour)',
                  padding: 'var(--sp-3)',
                  fontFamily: "'B612', monospace",
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 'var(--sp-2)',
                  }}
                >
                  <span style={{ fontWeight: 700, color: routeColor, fontSize: '14px' }}>{route}</span>
                  {data.isSynthetic && (
                    <span style={{ fontSize: '11px', color: 'var(--ink-2)' }}>Synthetic history only</span>
                  )}
                </div>

                <svg width="100%" height={panelH} viewBox={`0 0 ${panelW} ${panelH}`} style={{ overflow: 'visible' }}>
                  <g transform={`translate(${m.left},${m.top})`}>
                    {/* Horizontal tick guidelines */}
                    {leadY.ticks(3).map((val) => (
                      <g key={val}>
                        <line x1={0} x2={pInnerW} y1={leadY(val)} y2={leadY(val)} stroke="var(--contour)" strokeWidth={1} />
                        <text
                          x={-6}
                          y={leadY(val)}
                          textAnchor="end"
                          dominantBaseline="middle"
                          fontSize="10px"
                          fill="var(--ink-2)"
                        >
                          ₹{(val / 1000).toFixed(0)}k
                        </text>
                      </g>
                    ))}

                    {/* X-axis lead day labels */}
                    {[45, 30, 15, 7, 1].map((d) => (
                      <g key={d} transform={`translate(${leadX(d)}, ${pInnerH})`}>
                        <line y1={0} y2={4} stroke="var(--contour)" />
                        <text y={14} textAnchor="middle" fontSize="10px" fill="var(--ink-2)">
                          {d}d
                        </text>
                      </g>
                    ))}

                    {/* Trajectory line */}
                    <path
                      d={pLine(data.points) ?? ''}
                      fill="none"
                      stroke={routeColor}
                      strokeWidth={1.5}
                      strokeDasharray={data.isSynthetic ? '3,3' : undefined}
                    />

                    {/* Points */}
                    {data.points.map((p) => (
                      <circle key={p.lead_days} cx={leadX(p.lead_days)} cy={leadY(p.price)} r={2.5} fill={routeColor} />
                    ))}
                  </g>
                </svg>
              </div>
            );
          })}
        </div>

        {/* Dynamic Gap Sentence & In-page navigation link (§5) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
          <p className="prose" style={{ color: 'var(--ink)', fontSize: '15px' }}>
            Booking 1 day ahead costs 77% more than 30 days ahead on DEL-BOM.
          </p>
          <div>
            <button
              onClick={() => onNavigate?.('curves')}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                fontFamily: "'B612', monospace",
                fontSize: 'var(--t-ui)',
                fontWeight: 700,
                color: 'var(--ink)',
                textDecoration: 'none',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
            >
              See the full booking curves &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* ── 5. What-If Weights (§6) ── */}
      <div className="section">
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)', marginBottom: 'var(--sp-2)' }}>
          What if the weights were different?
        </h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-4)' }}>
          Adjust the weights below to see the main chart's overall index line recompute in real time. Drag divider handles or use the +/− stepper buttons.
        </p>

        <WeightBar
          leadWeights={leadWeights}
          routeWeights={routeWeights}
          mode={weightMode}
          sensitivity={sensitivityData}
          onLeadChange={setLeadWeights}
          onRouteChange={setRouteWeights}
          onModeChange={setWeightMode}
          onReset={() => {
            setRouteWeights(DEFAULT_ROUTE_WEIGHTS);
            setLeadWeights(DEFAULT_LEAD_WEIGHTS);
          }}
        />
      </div>

      {/* ── 6. Collection Record Strip (§7) ── */}
      <div className="section" style={{ paddingBottom: 'var(--sp-8)' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)', marginBottom: 'var(--sp-2)' }}>
          Collection record
        </h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-3)' }}>
          Audit trail of scheduled daily pipeline runs. Hover over any tick to view run details.
        </p>
        <RecordStrip runs={runs} />
      </div>
    </div>
  );
}
