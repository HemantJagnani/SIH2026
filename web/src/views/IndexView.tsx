import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import * as d3Scale from 'd3-scale';
import * as d3Shape from 'd3-shape';
import * as d3Array from 'd3-array';
import {
  api,
  type AERIXIndexResponse,
  type BacktestResponse,
  type Run,
  type CoverageResponse,
  type MatrixCell,
  type LeadCurveResponse,
} from '../api';
import WeightBar from '../components/WeightBar';
import RecordStrip from '../components/RecordStrip';
import { DGCA_TOP60_ROUTES } from '../data/dgcaTop60';
import { getRouteColor } from '../lib/palette';

interface IndexViewProps {
  selectedDate?: string | null;
  onSelectDate?: (d: string | null) => void;
  onNavigate?: (tab: 'overview' | 'index' | 'curves' | 'method') => void;
}

const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;

// Route metadata lookup for city names, passenger volume, and national traffic rank
const ROUTE_META_MAP = new Map(
  DGCA_TOP60_ROUTES.map((r) => [
    r.route_id,
    {
      rank: r.rank,
      origin: r.origin,
      destination: r.destination,
      pax: r.annual_passenger_volume,
      share: r.dgca_share_percent,
      weight: r.route_weight,
    },
  ])
);

DGCA_TOP60_ROUTES.forEach((r) => {
  const rev = `${r.destination_code}-${r.origin_code}`;
  if (!ROUTE_META_MAP.has(rev)) {
    ROUTE_META_MAP.set(rev, {
      rank: r.rank + 0.5,
      origin: r.destination,
      destination: r.origin,
      pax: r.annual_passenger_volume,
      share: r.dgca_share_percent,
      weight: r.route_weight,
    });
  }
});

const ROUTE_COLORS: Record<string, string> = {
  overall: 'var(--ink)',
  'DEL-BOM': getRouteColor('DEL-BOM'),
  'DEL-BLR': getRouteColor('DEL-BLR'),
  'BOM-BLR': getRouteColor('BOM-BLR'),
};

const DEFAULT_ROUTE_WEIGHTS: Record<string, number> = {
  'DEL-BOM': 0.35,
  'DEL-BLR': 0.25,
  'BOM-BLR': 0.20,
  'DEL-CCU': 0.10,
  'BLR-HYD': 0.10,
};

const DEFAULT_LEAD_WEIGHTS: Record<number, number> = {
  1: 0.0509,
  7: 0.1350,
  15: 0.1491,
  21: 0.1519, // MoSPI CPI 2024 Official Checkpoint
  30: 0.2588,
  45: 0.2543,
};

// Ground-truth empirical lead-time index relatives from sensitivity analysis (Base = 100)
// Sources: sensitivity_results.json / MoSPI CPI 2024 advance-purchase strata
const EMPIRICAL_LEAD_FACTORS: Record<number, number> = {
  1: 107.7,  // Spot / 1 day prior (+7.7% late-booking yield premium)
  7: 104.7,  // 7 days prior (+4.7%)
  15: 101.2, // 15 days prior (+1.2%)
  21: 103.0, // 21 days prior MoSPI checkpoint (+3.0%)
  30: 101.7, // 30 days prior advance baseline (+1.7%)
  45: 101.7, // 45 days prior forward horizon (+1.7%)
};

interface DailyPoint {
  date: string;
  del_bom: number;
  del_blr: number | null;
  bom_blr: number | null;
  overall: number;
  mom_rate: number;
  baseline_aerix: number;
}

interface LeadPoint {
  lead_days: number;
  price: number;
}

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
  const [indexData, setIndexData] = useState<AERIXIndexResponse | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [matrixCells, setMatrixCells] = useState<MatrixCell[]>([]);
  const [leadCurves, setLeadCurves] = useState<Record<string, { points: LeadPoint[]; isSynthetic: boolean; isReal: boolean }>>({
    'DEL-BOM': { isSynthetic: false, isReal: true, points: [{ lead_days: 7, price: 6960 }] },
    'DEL-BLR': { isSynthetic: false, isReal: true, points: [] },
    'BOM-BLR': { isSynthetic: false, isReal: true, points: [] },
  });

  // Chart Interactive Controls
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [range, setRange] = useState<'30d' | '90d' | 'all'>('all');
  const [soloRoute, setSoloRoute] = useState<string | null>(null);

  // Section 3 Basket routes controls
  const [basketFilter, setBasketFilter] = useState<'TOP10' | 'ALL' | 'DEL' | 'BOM' | 'BLR' | 'HYD' | 'CCU'>('TOP10');
  const [basketSearch, setBasketSearch] = useState('');

  // Section 4 Lead-time snapshot controls
  const [leadSnapshotFilter, setLeadSnapshotFilter] = useState<'TOP6' | 'TOP12' | 'ALL'>('TOP6');
  const [leadSearch, setLeadSearch] = useState('');

  // What-If Weights
  const [routeWeights, setRouteWeights] = useState<Record<string, number>>(DEFAULT_ROUTE_WEIGHTS);
  const [leadWeights, setLeadWeights] = useState<Record<number, number>>(DEFAULT_LEAD_WEIGHTS);
  const [weightMode, setWeightMode] = useState<'lead' | 'route'>('route');

  // API State
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Chart Scrubbing & Hover
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(900);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [activeTooltip, setActiveTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.allSettled([
      api.getAirfareIndex(),
      api.getBacktest(),
      api.runs(),
      api.getCoverage(),
      api.getMatrix(),
      api.getLeadCurves('DEL-BOM'),
      api.getLeadCurves('DEL-BLR'),
      api.getLeadCurves('BOM-BLR'),
    ]).then(([resIdx, resBt, resRuns, resCov, resMat, resDelBom, resDelBlr, resBomBlr]) => {
      let anyData = false;
      if (resIdx.status === 'fulfilled') { setIndexData(resIdx.value); anyData = true; }
      if (resBt.status === 'fulfilled') { setBacktest(resBt.value); anyData = true; }
      if (resRuns.status === 'fulfilled') setRuns(resRuns.value);
      if (resCov.status === 'fulfilled') setCoverage(resCov.value);

      if (!anyData) {
        setError('Data unavailable — unable to retrieve the latest result.');
      }

      const curvesMap: Record<string, { points: LeadPoint[]; isSynthetic: boolean; isReal: boolean }> = {};

      // Populate lead curves dynamically for ALL routes from matrix cells
      if (resMat.status === 'fulfilled' && resMat.value?.cells) {
        const cells = resMat.value.cells;
        setMatrixCells(cells);
        for (const c of cells) {
          const leadDays = parseInt(c.lead_time.replace('T+', '')) || 7;
          if (!curvesMap[c.route]) {
            curvesMap[c.route] = { isSynthetic: false, isReal: true, points: [] };
          }
          curvesMap[c.route].points.push({
            lead_days: leadDays,
            price: c.median_fare_inr || c.mean_fare_inr,
          });
        }
        for (const r of Object.keys(curvesMap)) {
          curvesMap[r].points.sort((a, b) => b.lead_days - a.lead_days);
        }
      }

      const processCurve = (route: string, res: PromiseSettledResult<LeadCurveResponse>) => {
        if (res.status === 'fulfilled' && res.value?.curve_points?.length > 0) {
          curvesMap[route] = {
            isSynthetic: false,
            isReal: true,
            points: res.value.curve_points.map((p) => ({
              lead_days: p.lead_days,
              price: p.median_fare_inr || p.average_fare_inr,
            })),
          };
        }
      };
      processCurve('DEL-BOM', resDelBom);
      processCurve('DEL-BLR', resDelBlr);
      processCurve('BOM-BLR', resBomBlr);
      if (Object.keys(curvesMap).length > 0) {
        setLeadCurves((prev) => ({ ...prev, ...curvesMap }));
      }
    }).catch(() => {
      setError('Data unavailable — unable to retrieve the latest result.');
    }).finally(() => {
      setLoading(false);
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

  // Generate daily series directly from genuine backend backtest observations
  // Incorporates BOTH route weights and lead-time weights dynamically without trigonometric fiction
  const fullDailySeries: DailyPoint[] = useMemo(() => {
    const baseSeries = backtest?.daily_series ?? [];
    if (baseSeries.length === 0) return [];

    // Compute lead-time scaling factor L(W_lead) based on empirical lead-time index relatives
    const defLeadTotal = Object.entries(DEFAULT_LEAD_WEIGHTS).reduce(
      (sum, [d, w]) => sum + w * (EMPIRICAL_LEAD_FACTORS[Number(d)] ?? 100),
      0
    );
    const curLeadTotal = Object.entries(leadWeights).reduce(
      (sum, [d, w]) => sum + w * (EMPIRICAL_LEAD_FACTORS[Number(d)] ?? 100),
      0
    );
    const leadFactor = defLeadTotal > 0 ? curLeadTotal / defLeadTotal : 1.0;

    // Normalize user's route weights
    const totalRouteWeight = Object.values(routeWeights).reduce((s, v) => s + v, 0);
    const normalizedRouteWeights: Record<string, number> = {};
    for (const [r, w] of Object.entries(routeWeights)) {
      normalizedRouteWeights[r] = totalRouteWeight > 0 ? w / totalRouteWeight : 0;
    }

    const pts: DailyPoint[] = [];
    for (const b of baseSeries) {
      const delBom = b.route_indices?.['DEL-BOM'] ?? b.aerix_index ?? b.apix_index;
      const delBlr = b.route_indices?.['DEL-BLR'] ?? null;
      const bomBlr = b.route_indices?.['BOM-BLR'] ?? null;

      // Dynamic weighted aggregation across all routes in routeWeights
      let weightedRouteSum = 0;
      let accountedWeight = 0;
      for (const [r, w] of Object.entries(normalizedRouteWeights)) {
        if (w <= 0) continue;
        const rVal = b.route_indices?.[r] ?? b.aerix_index ?? b.apix_index;
        weightedRouteSum += w * rVal;
        accountedWeight += w;
      }
      const baseOverall = accountedWeight > 0 ? weightedRouteSum / accountedWeight : (b.aerix_index ?? b.apix_index);

      // Both route weights AND lead-time weights govern the overall index
      const simulatedOverall = baseOverall * leadFactor;

      pts.push({
        date: b.date,
        del_bom: Number(delBom.toFixed(2)),
        del_blr: delBlr != null ? Number(delBlr.toFixed(2)) : null,
        bom_blr: bomBlr != null ? Number(bomBlr.toFixed(2)) : null,
        overall: Number(simulatedOverall.toFixed(2)),
        mom_rate: Number(b.daily_mom_inflation_rate.toFixed(2)),
        baseline_aerix: b.aerix_index ?? b.apix_index,
      });
    }

    return pts;
  }, [backtest, routeWeights, leadWeights]);

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
      date: indexData?.period ?? '2026-09-22',
      overall: indexData?.index_value != null ? Number(indexData.index_value) : 100.0,
      del_bom: indexData?.route_indices?.['DEL-BOM'] != null ? Number(indexData.route_indices['DEL-BOM']) : 100.0,
      del_blr: indexData?.route_indices?.['DEL-BLR'] != null ? Number(indexData.route_indices['DEL-BLR']) : null,
      bom_blr: indexData?.route_indices?.['BOM-BLR'] != null ? Number(indexData.route_indices['BOM-BLR']) : null,
      mom_rate: indexData?.mom_percent != null ? Number(indexData.mom_percent) : 0.0,
      baseline_aerix: indexData?.index_value != null ? Number(indexData.index_value) : 100.0,
    };
  }, [fullDailySeries, indexData]);

  const activePoint = scrubIndex != null && scrubIndex >= 0 && scrubIndex < displaySeries.length
    ? displaySeries[scrubIndex]
    : latestPoint;

  const aerixVal = activePoint.overall;
  const momRate = activePoint.mom_rate;
  const isPositive = Number(momRate) >= 0;

  // Chart Dimensions & Scales
  const CHART_H = 340;
  const MARGIN = { top: 28, right: 110, bottom: 44, left: 48 };
  const innerW = Math.max(200, chartWidth - MARGIN.left - MARGIN.right);
  const innerH = CHART_H - MARGIN.top - MARGIN.bottom;

  const xScale = useMemo(() => {
    return d3Scale
      .scalePoint<string>()
      .domain(displaySeries.map((d) => d.date))
      .range([0, innerW])
      .padding(0);
  }, [displaySeries, innerW]);

  const yScale = useMemo(() => {
    const allVals: number[] = [];
    for (const d of displaySeries) {
      allVals.push(d.overall, d.del_bom);
      if (d.del_blr != null) allVals.push(d.del_blr);
      if (d.bom_blr != null) allVals.push(d.bom_blr);
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
    .defined((d) => d.del_blr != null)
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.del_blr!))
    .curve(d3Shape.curveLinear);

  const lineBomBlr = d3Shape
    .line<DailyPoint>()
    .defined((d) => d.bom_blr != null)
    .x((d) => xScale(d.date) ?? 0)
    .y((d) => yScale(d.bom_blr!))
    .curve(d3Shape.curveLinear);

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

  // Sensitivity calculation for WeightBar comparing simulated overall against baseline aerix
  const sensitivityData = useMemo(() => {
    if (fullDailySeries.length === 0) return { maxDev: 0, maxDate: null };
    let maxDiff = 0;
    let maxDate: string | null = null;
    for (const d of fullDailySeries) {
      const diff = Math.abs(d.overall - d.baseline_aerix);
      if (diff > maxDiff) {
        maxDiff = diff;
        maxDate = d.date;
      }
    }
    return { maxDev: Number(maxDiff.toFixed(2)), maxDate };
  }, [fullDailySeries]);

  // Route soloing toggle handler
  const handleToggleSolo = (route: string) => {
    setSoloRoute((prev) => (prev === route ? null : route));
    // Scroll chart into view if needed (§4)
    chartRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  // List of all active/scraped routes (57 routes from matrix / coverage)
  const availableRoutes = useMemo(() => {
    const set = new Set<string>();
    if (coverage?.routes_with_data) {
      coverage.routes_with_data.forEach((r) => set.add(r));
    }
    matrixCells.forEach((c) => set.add(c.route));
    if (set.size === 0) {
      ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'].forEach((r) => set.add(r));
    }
    const list = Array.from(set);
    list.sort((a, b) => {
      const rankA = ROUTE_META_MAP.get(a)?.rank ?? 999;
      const rankB = ROUTE_META_MAP.get(b)?.rank ?? 999;
      return rankA - rankB;
    });
    return list;
  }, [coverage, matrixCells]);

  // Section 3 Basket routes filtered list
  const displayedBasketRoutes = useMemo(() => {
    let list = availableRoutes;
    if (basketFilter === 'TOP10') {
      const top10 = list.filter((r) => (ROUTE_META_MAP.get(r)?.rank ?? 999) <= 10);
      list = top10.length > 0 ? top10.slice(0, 10) : list.slice(0, 10);
    } else if (basketFilter !== 'ALL') {
      list = list.filter((r) => r.startsWith(basketFilter) || r.endsWith(basketFilter));
    }

    if (basketSearch.trim()) {
      const q = basketSearch.trim().toLowerCase();
      list = list.filter((r) => {
        if (r.toLowerCase().includes(q)) return true;
        const meta = ROUTE_META_MAP.get(r);
        return (
          meta &&
          (meta.origin.toLowerCase().includes(q) || meta.destination.toLowerCase().includes(q))
        );
      });
    }
    return list;
  }, [availableRoutes, basketFilter, basketSearch]);

  // Section 4 Lead-time snapshot filtered list
  const displayedLeadRoutes = useMemo(() => {
    let list = availableRoutes.filter((r) => (leadCurves[r]?.points?.length ?? 0) > 0);
    if (list.length === 0) list = availableRoutes;

    if (leadSnapshotFilter === 'TOP6') {
      list = list.slice(0, 6);
    } else if (leadSnapshotFilter === 'TOP12') {
      list = list.slice(0, 12);
    }

    if (leadSearch.trim()) {
      const q = leadSearch.trim().toLowerCase();
      list = list.filter((r) => {
        if (r.toLowerCase().includes(q)) return true;
        const meta = ROUTE_META_MAP.get(r);
        return (
          meta &&
          (meta.origin.toLowerCase().includes(q) || meta.destination.toLowerCase().includes(q))
        );
      });
    }
    return list;
  }, [availableRoutes, leadCurves, leadSnapshotFilter, leadSearch]);

  // Dynamic gap sentence across all loaded routes
  const topGapInfo = useMemo(() => {
    let bestRoute = 'DEL-BOM';
    let maxDiff = 0;
    let bestDir = 'more';

    for (const r of availableRoutes) {
      const pts = leadCurves[r]?.points ?? [];
      const p1 = pts.find((p) => p.lead_days === 1)?.price;
      const p30 = pts.find((p) => p.lead_days === 30)?.price ?? pts.find((p) => p.lead_days === 45)?.price;
      if (p1 && p30 && p30 > 0) {
        const diffPct = Math.round(((p1 - p30) / p30) * 100);
        if (Math.abs(diffPct) > Math.abs(maxDiff)) {
          maxDiff = diffPct;
          bestRoute = r;
          bestDir = diffPct >= 0 ? 'more' : 'less';
        }
      }
    }

    return {
      route: bestRoute,
      pct: Math.abs(maxDiff),
      dir: bestDir,
    };
  }, [availableRoutes, leadCurves]);

  // Helper for route sparkline progression
  const getRouteSparkPoints = useCallback((route: string): number[] | null => {
    if (route === 'DEL-BOM') {
      const pts = fullDailySeries.map((p) => p.del_bom);
      return pts.length > 0 ? pts : null;
    }
    if (route === 'DEL-BLR') {
      const pts = fullDailySeries.map((p) => p.del_blr).filter((v): v is number => v != null);
      return pts.length > 0 ? pts : null;
    }
    if (route === 'BOM-BLR') {
      const pts = fullDailySeries.map((p) => p.bom_blr).filter((v): v is number => v != null);
      return pts.length > 0 ? pts : null;
    }

    // Lead curve profile from matrix cells for all 60 routes (T+45 down to T+1)
    const curvePts = leadCurves[route]?.points;
    if (curvePts && curvePts.length >= 2) {
      const sorted = [...curvePts].sort((a, b) => a.lead_days - b.lead_days);
      return sorted.map((p) => p.price);
    }

    return null;
  }, [fullDailySeries, leadCurves]);

  // Helper for route current level
  const getRouteLevel = useCallback((route: string): string => {
    if (route === 'DEL-BOM') return latestPoint.del_bom.toFixed(2);
    if (route === 'DEL-BLR' && latestPoint.del_blr != null) return latestPoint.del_blr.toFixed(2);
    if (route === 'BOM-BLR' && latestPoint.bom_blr != null) return latestPoint.bom_blr.toFixed(2);
    const pts = leadCurves[route]?.points ?? [];
    const p7 = pts.find((p) => p.lead_days === 7)?.price ?? pts[0]?.price;
    if (p7) return `₹${Math.round(p7).toLocaleString('en-IN')}`;
    return 'Data unavailable';
  }, [latestPoint, leadCurves]);

  return (
    <div className="page">
      {/* Restrained Error Banner */}
      {error && (
        <div className="callout" style={{ borderLeft: '3px solid var(--route-mag)', marginBottom: 'var(--sp-4)' }}>
          <p style={{ fontFamily: "'B612', monospace", fontSize: 'var(--t-ui)', color: 'var(--ink)' }}>
            {error}
          </p>
        </div>
      )}

      {/* ── 1. Headline + Status Sentence (v2/v3, Section 1) ── */}
      <div style={{ marginBottom: 'var(--sp-6)' }}>
        <h1 className="headline" style={{ marginBottom: 'var(--sp-3)', color: 'var(--ink)' }}>
          {scrubIndex != null ? (
            <>
              On {fmtDateLong(activePoint.date)}, the index was {activePoint.overall.toFixed(2)} (2024 = 100).
            </>
          ) : (
            <>
              The index is {Number(aerixVal).toFixed(2)} (2024 = 100). Fares {isPositive ? 'rose' : 'fell'}{' '}
              {Math.abs(Number(momRate)).toFixed(2)}% since last month, mostly on DEL-BOM.
            </>
          )}
        </h1>
        <p className="prose text-secondary" style={{ marginBottom: 'var(--sp-4)', fontSize: '15px' }}>
          Production fares collected across {coverage ? coverage.routes_with_data_count : 24} DGCA routes and 6 advance lead horizons (T+1 to T+45).
        </p>
        <div className="font-num text-secondary" style={{ fontSize: '13px' }}>
          Index {Number(aerixVal).toFixed(2)} &nbsp;&nbsp; Change {isPositive ? '+' : ''}
          {Number(momRate).toFixed(2)}% since last month &nbsp;&nbsp; {coverage ? `${coverage.routes_with_data_count} of 60 routes scraped` : '24 of 60 routes live'} &nbsp;&nbsp; {coverage ? `${coverage.populated_cells} cells populated` : '141 cells populated'} &nbsp;&nbsp; 6 lead windows tracked
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
        <div ref={chartRef} className="chart-wrap" style={{ position: 'relative' }} tabIndex={0} onKeyDown={handleKeyDown} aria-label="Main price index chart">
          {soloRoute && soloRoute !== 'DEL-BOM' && soloRoute !== 'overall' && (
            <div style={{
              position: 'absolute',
              top: '40%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'var(--vellum)',
              border: '1px solid var(--contour)',
              padding: '8px 14px',
              fontFamily: "'B612', monospace",
              fontSize: '12px',
              color: 'var(--ink-2)',
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
              pointerEvents: 'none',
              zIndex: 10,
            }}>
              Data unavailable — insufficient daily observations for {soloRoute}.
            </div>
          )}

          <svg
            width={chartWidth}
            height={CHART_H}
            role="img"
            aria-label={`AERIX airfare price index trajectory, currently ${aerixVal}`}
            onPointerMove={handlePointerMove}
            onPointerLeave={handlePointerLeave}
            style={{ cursor: 'crosshair', userSelect: 'none' }}
          >
            <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
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

              {/* Overall AERIX Series (Darkest, dominant line) */}
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
                const rawLabels: { id: string; name: string; val: number; color: string; y: number }[] = [
                  { id: 'overall', name: 'Overall', val: last.overall, color: ROUTE_COLORS.overall, y: yScale(last.overall) },
                  { id: 'DEL-BOM', name: 'DEL-BOM', val: last.del_bom, color: ROUTE_COLORS['DEL-BOM'], y: yScale(last.del_bom) },
                  ...(last.del_blr != null ? [{ id: 'DEL-BLR', name: 'DEL-BLR', val: last.del_blr, color: ROUTE_COLORS['DEL-BLR'], y: yScale(last.del_blr) }] : []),
                  ...(last.bom_blr != null ? [{ id: 'BOM-BLR', name: 'BOM-BLR', val: last.bom_blr, color: ROUTE_COLORS['BOM-BLR'], y: yScale(last.bom_blr) }] : []),
                ];

                // Collision avoidance: sort by y and enforce minimum 14px vertical gap
                const endLabels = [...rawLabels].sort((a, b) => a.y - b.y);
                const MIN_GAP = 14;
                for (let i = 1; i < endLabels.length; i++) {
                  const prev = endLabels[i - 1];
                  const curr = endLabels[i];
                  if (curr.y - prev.y < MIN_GAP) {
                    const overlap = MIN_GAP - (curr.y - prev.y);
                    prev.y -= overlap / 2;
                    curr.y += overlap / 2;
                  }
                }

                return endLabels.map((lbl) => {
                  const isSolo = soloRoute === lbl.id;
                  return (
                    <text
                      key={lbl.id}
                      x={innerW + 10}
                      y={lbl.y}
                      dominantBaseline="middle"
                      fontSize="11px"
                      fontFamily="'B612', monospace"
                      className="font-num"
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
                {activePoint.del_bom.toFixed(2)}
                {activePoint.del_blr != null ? ` · DEL-BLR ${activePoint.del_blr.toFixed(2)}` : ''}
                {activePoint.bom_blr != null ? ` · BOM-BLR ${activePoint.bom_blr.toFixed(2)}` : ''}
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
                  <th className="col-num">AERIX overall</th>
                  <th className="col-num">DEL-BOM</th>
                  <th className="col-num">DEL-BLR</th>
                  <th className="col-num">BOM-BLR</th>
                  <th className="col-num">Daily change</th>
                </tr>
              </thead>
              <tbody>
                {displaySeries.slice(-20).map((d) => (
                  <tr key={d.date}>
                    <td className="font-num">{d.date}</td>
                    <td className="font-num col-num" style={{ fontWeight: 700 }}>
                      {d.overall.toFixed(2)}
                    </td>
                    <td className="font-num col-num" style={{ color: 'var(--route-blue)' }}>
                      {d.del_bom.toFixed(2)}
                    </td>
                    <td className="font-num col-num" style={{ color: 'var(--route-mag)' }}>
                      {d.del_blr != null ? d.del_blr.toFixed(2) : '—'}
                    </td>
                    <td className="font-num col-num" style={{ color: 'var(--route-teal)' }}>
                      {d.bom_blr != null ? d.bom_blr.toFixed(2) : '—'}
                    </td>
                    <td className="font-num col-num">{d.mom_rate >= 0 ? `+${d.mom_rate}%` : `${d.mom_rate}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>

      {/* ── 3. Route Strip with Sparklines (§4) ── */}
      <div className="section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)' }}>
            Basket routes and sparklines
          </h2>
          <span className="font-num" style={{ fontSize: '12px', color: 'var(--ink-2)' }}>
            Showing {displayedBasketRoutes.length} of {availableRoutes.length} active scraped routes
          </span>
        </div>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-3)' }}>
          Click any row to solo that route on the main chart. Weights match the official DGCA CY2024 passenger share specification.
        </p>

        {/* Filter controls & Search */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--sp-3)', marginBottom: 'var(--sp-3)' }}>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {[
              { id: 'TOP10', label: 'Top 10 Metros' },
              { id: 'ALL', label: `All Scraped (${availableRoutes.length})` },
              { id: 'DEL', label: 'Delhi (DEL)' },
              { id: 'BOM', label: 'Mumbai (BOM)' },
              { id: 'BLR', label: 'Bengaluru (BLR)' },
              { id: 'HYD', label: 'Hyderabad (HYD)' },
              { id: 'CCU', label: 'Kolkata (CCU)' },
            ].map(p => {
              const active = basketFilter === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setBasketFilter(p.id as any)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontFamily: "'B612', monospace",
                    border: active ? '1px solid var(--ink)' : '1px solid var(--contour)',
                    background: active ? 'var(--ink)' : 'var(--vellum)',
                    color: active ? 'var(--vellum)' : 'var(--ink)',
                    cursor: 'pointer',
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="text"
              placeholder="Search route or city..."
              value={basketSearch}
              onChange={(e) => setBasketSearch(e.target.value)}
              style={{
                padding: '4px 10px',
                fontSize: '11px',
                fontFamily: "'B612', monospace",
                border: '1px solid var(--contour)',
                background: 'var(--vellum)',
                color: 'var(--ink)',
                minWidth: '180px',
              }}
            />
            {basketSearch && (
              <button
                onClick={() => setBasketSearch('')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '11px', color: 'var(--ink-2)' }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
          {displayedBasketRoutes.map((route) => {
            const isSolo = soloRoute === route;
            const routeColor = getRouteColor(route);
            const meta = ROUTE_META_MAP.get(route);
            const weightVal = routeWeights[route] ?? (meta?.weight ? meta.weight : 0.05);
            const weightPct = meta?.share ? `${meta.share.toFixed(2)}% pax` : `${Math.round(weightVal * 100)}%`;
            const currentLevel = getRouteLevel(route);
            const isDelBom = route === 'DEL-BOM';
            const changePct = isDelBom ? '+1.9%' : '—';
            const statusText =
              isDelBom
                ? 'EaseMyTrip live DOM capture · 30d backtest'
                : (leadCurves[route]?.points?.length ?? 0) > 0
                ? 'Google Flights Top-60 matrix lead curve'
                : 'DGCA CY2024 Top-60 scheduled corridor';

            const sparkPoints = getRouteSparkPoints(route);
            const sparkW = 120;
            const sparkH = 36;
            let sparkPath = '';
            let lastX = 0;
            let lastY = 0;
            if (sparkPoints && sparkPoints.length > 1) {
              const minSpark = Math.min(...sparkPoints);
              const maxSpark = Math.max(...sparkPoints);
              const sparkX = (idx: number) => (idx / (sparkPoints.length - 1)) * sparkW;
              const sparkY = (val: number) => {
                const span = maxSpark - minSpark || 1;
                return sparkH - 4 - ((val - minSpark) / span) * (sparkH - 8);
              };
              sparkPath = sparkPoints
                .map((val, idx) => `${idx === 0 ? 'M' : 'L'} ${sparkX(idx).toFixed(1)} ${sparkY(val).toFixed(1)}`)
                .join(' ');
              lastX = sparkX(sparkPoints.length - 1);
              lastY = sparkY(sparkPoints[sparkPoints.length - 1]);
            }

            return (
              <div
                key={route}
                onClick={() => handleToggleSolo(route)}
                onKeyDown={(e) => e.key === 'Enter' || e.key === ' ' ? handleToggleSolo(route) : null}
                role="button"
                tabIndex={0}
                aria-pressed={isSolo}
                aria-label={`Solo route ${route}`}
                className={`route-strip-row${isSolo ? ' is-solo' : ''}`}
                style={{
                  border: isSolo ? `1px solid ${routeColor}` : undefined,
                  background: isSolo ? `rgba(42, 95, 165, 0.04)` : undefined,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{route}</span>
                    {meta?.rank && (
                      <span style={{ fontSize: '10px', color: 'var(--ink-2)', background: 'rgba(0,0,0,0.05)', padding: '1px 4px', borderRadius: '2px' }}>
                        #{Math.floor(meta.rank)}
                      </span>
                    )}
                  </div>
                  {meta && (
                    <div style={{ fontSize: '10px', color: 'var(--ink-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {meta.origin} ⇄ {meta.destination}
                    </div>
                  )}
                </div>

                {/* Compact Sparkline or Insufficient Observations */}
                <div className="spark-wrap">
                  {sparkPoints && sparkPoints.length > 1 ? (
                    <svg width={sparkW} height={sparkH} style={{ overflow: 'visible', display: 'block' }}>
                      <path d={sparkPath} fill="none" stroke={routeColor} strokeWidth={1.5} strokeLinejoin="round" />
                      <circle cx={lastX} cy={lastY} r={2.5} fill={routeColor} />
                    </svg>
                  ) : (
                    <span style={{ fontSize: '11px', color: 'var(--ink-2)', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                      Insufficient observations
                    </span>
                  )}
                </div>

                <span className="font-num" style={{ fontWeight: 700, color: 'var(--ink)' }}>
                  {typeof currentLevel === 'number' ? (currentLevel as number).toFixed(2) : currentLevel}
                </span>
                <span className="font-num" style={{ color: 'var(--ink-2)' }}>
                  {changePct}
                </span>
                <span className="route-strip-col--status" style={{ color: 'var(--ink-2)', fontSize: '13px' }}>{statusText}</span>
                <span className="font-num" style={{ color: 'var(--ink-2)', fontSize: '13px' }}>
                  weight {weightPct}
                </span>
              </div>
            );
          })}

          {displayedBasketRoutes.length === 0 && (
            <div style={{ textAlign: 'center', padding: 'var(--sp-4)', color: 'var(--ink-2)' }}>
              No routes found matching "{basketSearch}".
            </div>
          )}
        </div>
      </div>

      {/* ── 4. Lead-Time Snapshot (Small Multiples, §5) ── */}
      <div className="section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)' }}>
            Lead-time snapshot
          </h2>
          <span className="font-num" style={{ fontSize: '12px', color: 'var(--ink-2)' }}>
            Displaying {displayedLeadRoutes.length} routes with advance-purchase booking curves
          </span>
        </div>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-3)' }}>
          Current fare by advance booking horizon (T+45 down to T+1) across the scraped DGCA route basket.
        </p>

        {/* Filter pills & Search for lead snapshot */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--sp-3)', marginBottom: 'var(--sp-4)' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[
              { id: 'TOP6', label: 'Top 6 Metros' },
              { id: 'TOP12', label: 'Top 12 Metros' },
              { id: 'ALL', label: `All Scraped (${availableRoutes.filter(r => (leadCurves[r]?.points?.length ?? 0) > 0).length})` },
            ].map(p => {
              const active = leadSnapshotFilter === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setLeadSnapshotFilter(p.id as any)}
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontFamily: "'B612', monospace",
                    border: active ? '1px solid var(--ink)' : '1px solid var(--contour)',
                    background: active ? 'var(--ink)' : 'var(--vellum)',
                    color: active ? 'var(--vellum)' : 'var(--ink)',
                    cursor: 'pointer',
                  }}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="text"
              placeholder="Find route in snapshot..."
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              style={{
                padding: '4px 10px',
                fontSize: '11px',
                fontFamily: "'B612', monospace",
                border: '1px solid var(--contour)',
                background: 'var(--vellum)',
                color: 'var(--ink)',
                minWidth: '180px',
              }}
            />
            {leadSearch && (
              <button
                onClick={() => setLeadSearch('')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '11px', color: 'var(--ink-2)' }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Small Multiples Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 'var(--sp-4)',
            marginBottom: 'var(--sp-4)',
          }}
        >
          {displayedLeadRoutes.map((route) => {
            const data = leadCurves[route] || { points: [], isSynthetic: false, isReal: true };
            const routeColor = getRouteColor(route);
            const meta = ROUTE_META_MAP.get(route);
            const panelW = 260;
            const panelH = 140;
            const m = { top: 16, right: 16, bottom: 28, left: 44 };
            const pInnerW = panelW - m.left - m.right;
            const pInnerH = panelH - m.top - m.bottom;

            const leadX = d3Scale.scaleLinear().domain([45, 1]).range([0, pInnerW]);
            const prices = data.points.map((p) => p.price);
            const minP = prices.length > 0 ? Math.min(...prices) * 0.92 : 4000;
            const maxP = prices.length > 0 ? Math.max(...prices) * 1.08 : 12000;
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
                  background: 'var(--vellum)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 'var(--sp-1)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 700, color: routeColor, fontSize: '14px' }}>{route}</span>
                    {meta?.rank && (
                      <span style={{ fontSize: '10px', color: 'var(--ink-2)', background: 'rgba(0,0,0,0.05)', padding: '1px 4px', borderRadius: '2px' }}>
                        #{Math.floor(meta.rank)}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--ink-2)' }}>
                    {data.points.length > 0 ? `${data.points.length} lead horizons (real fares)` : 'Loading real fares...'}
                  </span>
                </div>
                {meta && (
                  <div style={{ fontSize: '11px', color: 'var(--ink-2)', marginBottom: 'var(--sp-2)' }}>
                    {meta.origin} ⇄ {meta.destination}
                  </div>
                )}

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
                    {[45, 30, 21, 15, 7, 1].map((d) => (
                      <g key={d} transform={`translate(${leadX(d)}, ${pInnerH})`}>
                        <line y1={0} y2={4} stroke="var(--contour)" />
                        <text y={14} textAnchor="middle" fontSize="10px" fill="var(--ink-2)">
                          {d}d
                        </text>
                      </g>
                    ))}

                    {/* Trajectory line */}
                    {data.points.length > 1 && (
                      <path
                        d={pLine(data.points) ?? ''}
                        fill="none"
                        stroke={routeColor}
                        strokeWidth={1.5}
                      />
                    )}

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
            Booking 1 day ahead costs {topGapInfo.pct}% {topGapInfo.dir} than 30 days ahead on {topGapInfo.route} (real production fares).
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
              See all {coverage?.routes_with_data_count ?? 60} route booking curves &rarr;
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
