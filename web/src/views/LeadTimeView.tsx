import { useState, useEffect, useRef, useMemo } from 'react';
import * as d3Scale from 'd3-scale';
import * as d3Shape from 'd3-shape';
import * as d3Array from 'd3-array';
import { api, type LeadCurve } from '../api';

const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'];
const RIDGE_H = 60;       // height per day strip
const CHART_W_FRACTION = 0.95;
const MARGIN = { top: 16, right: 32, bottom: 48, left: 80 };
const LEAD_DAYS = [30, 15, 7, 1];

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function fmt(n: number) {
  return n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

export default function LeadTimeView() {
  const [curves, setCurves] = useState<LeadCurve[]>([]);
  const [route, setRoute] = useState('DEL-BOM');
  const [loading, setLoading] = useState(true);
  const [hoverDate, setHoverDate] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(700);

  useEffect(() => {
    if (!wrapRef.current) return;
    const obs = new ResizeObserver(([e]) => setW(e.contentRect.width));
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    setLoading(true);
    api.leadCurve(route).then(data => {
      setCurves(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [route]);

  const innerW = w - MARGIN.left - MARGIN.right;
  const totalH = MARGIN.top + curves.length * RIDGE_H + MARGIN.bottom;

  // Scales
  const xScale = useMemo(() => {
    return d3Scale.scaleLinear().domain([30, 1]).range([0, innerW]);
  }, [innerW]);

  const allPrices = curves.flatMap(c => c.points.map(p => p.price));
  const [priceMin, priceMax] = allPrices.length > 0
    ? d3Array.extent(allPrices) as [number, number]
    : [0, 10000];

  // Each strip gets its own y-scale (0 → priceMax), positioned at its row
  const priceScale = d3Scale.scaleLinear()
    .domain([priceMin * 0.9, priceMax * 1.05])
    .range([RIDGE_H - 4, 0]);

  const areaGen = d3Shape.area<{ lead_days: number; price: number }>()
    .x(p => xScale(p.lead_days))
    .y0(RIDGE_H)
    .y1(p => priceScale(p.price))
    .curve(d3Shape.curveMonotoneX);

  const lineGen = d3Shape.line<{ lead_days: number; price: number }>()
    .x(p => xScale(p.lead_days))
    .y(p => priceScale(p.price))
    .curve(d3Shape.curveMonotoneX);

  const xTicks = [30, 15, 7, 1];

  return (
    <div className="page">
      <h1 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, marginBottom: 'var(--space-4)' }}>
        Lead time curves
      </h1>
      <p className="text-muted text-italic" style={{ marginBottom: 'var(--space-6)', maxWidth: '60ch', lineHeight: 1.6 }}>
        Each line shows the price curve from 30 to 1 days before departure on a single observation day.
        A rising stack means fares are increasing; steepening curves signal scarcity near departure.
      </p>

      <div className="route-selector" style={{ marginBottom: 'var(--space-6)' }} role="group" aria-label="Route">
        {ROUTES.map(r => (
          <button
            key={r}
            className={`route-btn${route === r ? ' active' : ''}`}
            onClick={() => setRoute(r)}
          >
            {r}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">Loading lead-time data…</div>
      ) : curves.length === 0 ? (
        <div className="empty-state">
          <p>No lead-time data collected yet for {route}.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="panel__header">
            <span className="panel__title">Booking curves by observation date — {route}</span>
            <span style={{ fontSize: 'var(--text-xs)' }}>
              {curves.length} observation days
            </span>
          </div>

          <div className="ridgeline-wrap" ref={wrapRef}>
            <svg
              width={w}
              height={totalH}
              role="img"
              aria-label={`Ridgeline chart for ${route} showing ${curves.length} booking curves`}
            >
              {/* X axis */}
              <g transform={`translate(${MARGIN.left},${MARGIN.top + curves.length * RIDGE_H})`}>
                <line x1={0} x2={innerW} y1={0} y2={0} stroke="var(--col-border)" />
                {xTicks.map(t => (
                  <g key={t} transform={`translate(${xScale(t)},0)`}>
                    <line y1={0} y2={5} stroke="var(--col-border)" />
                    <text
                      y={18}
                      textAnchor="middle"
                      fontSize={10}
                      fill="var(--col-ink-muted)"
                      fontFamily="inherit"
                    >
                      {t}d
                    </text>
                  </g>
                ))}
                <text
                  x={innerW / 2}
                  y={36}
                  textAnchor="middle"
                  fontSize={10}
                  fill="var(--col-ink-muted)"
                  fontFamily="inherit"
                >
                  Days before departure
                </text>
              </g>

              {/* Ridgeline strips (oldest at bottom) */}
              {[...curves].reverse().map((curve, i) => {
                const pts = curve.points
                  .filter(p => LEAD_DAYS.includes(p.lead_days))
                  .sort((a, b) => b.lead_days - a.lead_days);

                const yOffset = MARGIN.top + (curves.length - 1 - i) * RIDGE_H;
                const isHover = hoverDate === curve.obs_date;
                const col = curve.is_synthetic ? 'var(--col-synthetic)' : 'var(--col-primary)';

                return (
                  <g
                    key={curve.obs_date}
                    transform={`translate(${MARGIN.left},${yOffset})`}
                    onMouseEnter={() => setHoverDate(curve.obs_date)}
                    onMouseLeave={() => setHoverDate(null)}
                    style={{ cursor: 'pointer' }}
                    aria-label={`Observation date ${curve.obs_date}`}
                  >
                    {/* Area fill */}
                    {pts.length > 0 && (
                      <path
                        d={areaGen(pts) ?? ''}
                        fill={col}
                        opacity={isHover ? 0.3 : 0.12}
                      />
                    )}
                    {/* Line */}
                    {pts.length > 0 && (
                      <path
                        d={lineGen(pts) ?? ''}
                        fill="none"
                        stroke={col}
                        strokeWidth={isHover ? 2 : 1.2}
                        opacity={0.9}
                      />
                    )}
                    {/* Date label */}
                    <text
                      x={-8}
                      y={RIDGE_H / 2}
                      textAnchor="end"
                      dominantBaseline="middle"
                      fontSize={9}
                      fill={isHover ? 'var(--col-ink)' : 'var(--col-ink-muted)'}
                      fontFamily="inherit"
                    >
                      {fmtDate(curve.obs_date)}
                    </text>

                    {/* Hover price readout */}
                    {isHover && pts.map(p => (
                      <g key={p.lead_days} transform={`translate(${xScale(p.lead_days)},${priceScale(p.price)})`}>
                        <circle r={3} fill={col} />
                        <text
                          x={4}
                          y={-4}
                          fontSize={9}
                          fill="var(--col-ink)"
                          fontFamily="inherit"
                        >
                          ₹{fmt(p.price)}
                        </text>
                      </g>
                    ))}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Synthetic legend */}
          {curves.some(c => c.is_synthetic) && (
            <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--col-ink-muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 2, background: 'var(--col-primary)', display: 'inline-block' }} />
                Real
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 2, background: 'var(--col-synthetic)', display: 'inline-block' }} />
                Synthetic — not collected fares
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
