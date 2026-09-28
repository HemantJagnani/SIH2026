/**
 * WeightBar — High-precision interactive weight allocation matrix.
 *
 * Provides both interactive draggable dividers and quick-step controls (+/- 1% and 5%).
 * Weights are strictly normalized to 100%, with real-time recalculation of the
 * main index chart. Fully accessible via keyboard and screen readers.
 */
import { useRef, useCallback, useEffect, useState } from 'react';
import { DGCA_TOP60_ROUTES } from '../data/dgcaTop60';

const LEAD_DAYS = [1, 7, 15, 21, 30, 45] as const;

const SEGMENT_COLORS_LEAD: Record<number, string> = {
  1:  '#2A5FA5',
  7:  '#2F7D6D',
  15: '#8A6D3B',
  21: '#E65100', // MoSPI Official Checkpoint
  30: '#B0286A',
  45: '#5C4382',
};

const DYNAMIC_PALETTE = [
  '#2A5FA5', '#B0286A', '#2F7D6D', '#E65100', '#6A1B9A',
  '#00838F', '#2E7D32', '#C2185B', '#1565C0', '#F57F17',
  '#4527A0', '#00695C', '#D84315', '#37474F',
];

function getRouteColor(route: string, idx: number): string {
  if (route === 'DEL-BOM' || route === 'BOM-DEL') return '#2A5FA5';
  if (route === 'DEL-BLR' || route === 'BLR-DEL') return '#B0286A';
  if (route === 'BOM-BLR' || route === 'BLR-BOM') return '#2F7D6D';
  if (route === 'DEL-CCU' || route === 'CCU-DEL') return '#E65100';
  if (route === 'BLR-HYD' || route === 'HYD-BLR') return '#6A1B9A';
  return DYNAMIC_PALETTE[idx % DYNAMIC_PALETTE.length];
}

const LEAD_DESCRIPTIONS: Record<number, string> = {
  1: 'Spot / Departure - 1d (5.09%)',
  7: 'Short-range / 1 week (13.50%)',
  15: 'Mid-range / Fortnight (14.91%)',
  21: 'MoSPI Checkpoint / 3 weeks (15.19%)',
  30: 'Standard Advance / 1 month (25.88%)',
  45: 'Long-range / 45 days (25.43%)',
};

function getRouteDescription(key: string): string {
  const match = DGCA_TOP60_ROUTES.find(r => r.route_id === key);
  if (match) {
    return `${match.origin} ⇄ ${match.destination} (${match.dgca_share_percent.toFixed(2)}% DGCA share)`;
  }
  return `${key} Corridor`;
}

function dayLabel(d: number): string {
  return d === 1 ? '1 day' : `${d} days`;
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

interface Props {
  leadWeights: Record<number, number>;
  routeWeights: Record<string, number>;
  mode: 'lead' | 'route';
  sensitivity: { maxDev: number; maxDate: string | null } | null;
  onLeadChange: (w: Record<number, number>) => void;
  onRouteChange: (w: Record<string, number>) => void;
  onModeChange: (m: 'lead' | 'route') => void;
  onReset: () => void;
}

/** Renormalise so values sum to 1. */
function renorm(raw: Record<string | number, number>): Record<string | number, number> {
  const total = Object.values(raw).reduce((s, v) => s + v, 0);
  if (total === 0) return raw;
  const out: Record<string | number, number> = {};
  for (const [k, v] of Object.entries(raw)) out[k] = v / total;
  return out;
}

function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)); }
function snap(v: number) { return Math.round(v * 100) / 100; }

export default function WeightBar({
  leadWeights, routeWeights, mode, sensitivity,
  onLeadChange, onRouteChange, onModeChange, onReset,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [activeDivider, setActiveDivider] = useState<number | null>(null);

  const routeKeys = Object.keys(routeWeights);
  const keys: (string | number)[] = mode === 'lead'
    ? [...LEAD_DAYS]
    : routeKeys;

  const weights = mode === 'lead' ? leadWeights : routeWeights;
  const colors = (k: string | number) => {
    if (mode === 'lead') return SEGMENT_COLORS_LEAD[k as number] ?? '#2A5FA5';
    const idx = keys.indexOf(k);
    return getRouteColor(String(k), idx >= 0 ? idx : 0);
  };

  const segLabel = (k: string | number) =>
    mode === 'lead' ? dayLabel(k as number) : String(k);

  const segSub = (k: string | number) =>
    mode === 'lead' ? LEAD_DESCRIPTIONS[k as number] : getRouteDescription(String(k));

  const getWeightsArr = useCallback(() => keys.map(k => weights[k] ?? 0), [keys, weights]);

  // Drag state
  const dragRef = useRef<{
    divIdx: number;
    startX: number;
    startWeights: number[];
    trackW: number;
  } | null>(null);

  const handleDividerPointerDown = useCallback((
    e: React.PointerEvent, divIdx: number,
  ) => {
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setActiveDivider(divIdx);
    dragRef.current = {
      divIdx,
      startX: e.clientX,
      startWeights: getWeightsArr(),
      trackW: trackRef.current?.getBoundingClientRect().width ?? 800,
    };
  }, [getWeightsArr]);

  useEffect(() => {
    function onMove(e: PointerEvent) {
      if (!dragRef.current) return;
      const { divIdx, startX, startWeights, trackW } = dragRef.current;
      const dx = e.clientX - startX;
      const delta = snap(clamp(dx / trackW, -0.99, 0.99));

      const left = startWeights[divIdx];
      const right = startWeights[divIdx + 1];

      const move = clamp(delta, -left + 0.02, right - 0.02);

      const next = [...startWeights];
      next[divIdx] = snap(clamp(left + move, 0.02, 0.98));
      next[divIdx + 1] = snap(clamp(right - move, 0.02, 0.98));

      const newWeights: Record<string | number, number> = {};
      keys.forEach((k, i) => { newWeights[k] = next[i]; });
      const normed = renorm(newWeights);

      if (mode === 'lead') {
        const w: Record<number, number> = {};
        for (const [k, v] of Object.entries(normed)) w[Number(k)] = v;
        onLeadChange(w);
      } else {
        const w: Record<string, number> = {};
        for (const [k, v] of Object.entries(normed)) w[k] = v;
        onRouteChange(w);
      }
    }

    function onUp() {
      dragRef.current = null;
      setActiveDivider(null);
    }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [mode, keys, onLeadChange, onRouteChange]);

  // Stepper adjustments (+/- 1% or 5%)
  const handleStep = (targetKey: string | number, delta: number) => {
    const arr = getWeightsArr();
    const idx = keys.indexOf(targetKey);
    if (idx === -1) return;

    const curVal = arr[idx];
    const nextVal = clamp(curVal + delta, 0.03, 0.92);
    const diff = nextVal - curVal;
    if (Math.abs(diff) < 0.002) return;

    const otherIndices = keys.map((_, i) => i).filter(i => i !== idx);
    const otherTotal = otherIndices.reduce((sum, i) => sum + arr[i], 0);
    if (otherTotal <= 0) return;

    const nextArr = [...arr];
    nextArr[idx] = nextVal;
    otherIndices.forEach(i => {
      const share = arr[i] / otherTotal;
      nextArr[i] = Math.max(0.02, arr[i] - diff * share);
    });

    const newWeights: Record<string | number, number> = {};
    keys.forEach((k, i) => { newWeights[k] = nextArr[i]; });
    const normed = renorm(newWeights);

    if (mode === 'lead') {
      const w: Record<number, number> = {};
      for (const [k, v] of Object.entries(normed)) w[Number(k)] = v;
      onLeadChange(w);
    } else {
      const w: Record<string, number> = {};
      for (const [k, v] of Object.entries(normed)) w[String(k)] = v;
      onRouteChange(w);
    }
  };

  // Keyboard navigation on divider handles
  const handleDividerKey = useCallback((
    e: React.KeyboardEvent, divIdx: number,
  ) => {
    const step = e.shiftKey ? 0.05 : 0.01;
    const arr = getWeightsArr();
    let move = 0;
    if (e.key === 'ArrowLeft') { move = -step; e.preventDefault(); }
    else if (e.key === 'ArrowRight') { move = step; e.preventDefault(); }
    else return;

    const left = arr[divIdx];
    const right = arr[divIdx + 1];
    const clamped = clamp(move, -left + 0.02, right - 0.02);
    const next = [...arr];
    next[divIdx] = snap(left + clamped);
    next[divIdx + 1] = snap(right - clamped);

    const newWeights: Record<string | number, number> = {};
    keys.forEach((k, i) => { newWeights[k] = next[i]; });
    const normed = renorm(newWeights);

    if (mode === 'lead') {
      const w: Record<number, number> = {};
      for (const [k, v] of Object.entries(normed)) w[Number(k)] = v;
      onLeadChange(w);
    } else {
      const w: Record<string, number> = {};
      for (const [k, v] of Object.entries(normed)) w[k] = v;
      onRouteChange(w);
    }
  }, [mode, keys, getWeightsArr, onLeadChange, onRouteChange]);

  const weightsArr = getWeightsArr();

  // Sensitivity analysis status
  const devValue = sensitivity ? sensitivity.maxDev : 0;
  const isBenchmark = devValue < 0.05;
  const formattedDate = sensitivity?.maxDate
    ? new Date(sensitivity.maxDate + 'T00:00:00Z').toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        timeZone: 'UTC',
      })
    : '22 September';

  return (
    <div className="weight-clean-container">
      {/* ── 1. Clean Toolbar (Controls without duplicate title) ── */}
      <div className="weight-clean-toolbar">
        <div className="weight-clean-meta">
          <span className="weight-clean-indicator-dot" />
          <span className="weight-clean-meta-title">
            {mode === 'route'
              ? `Route Basket Allocation (${keys.length} Corridors)`
              : `Lead Time Windows (${keys.length} Advance Tiers)`}
          </span>
          <span className="weight-clean-badge font-num">100% Balanced</span>
        </div>

        <div className="weight-clean-actions">
          <div className="weight-clean-switcher" role="tablist" aria-label="Weight dimension switch">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'lead'}
              className={`weight-switcher-btn${mode === 'lead' ? ' active' : ''}`}
              onClick={() => onModeChange('lead')}
            >
              Lead times
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'route'}
              className={`weight-switcher-btn${mode === 'route' ? ' active' : ''}`}
              onClick={() => onModeChange('route')}
            >
              Routes
            </button>
          </div>

          <button
            type="button"
            className="weight-clean-reset-btn"
            onClick={onReset}
            title="Reset weights to MoSPI baseline default"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* ── 2. Unified Multi-Segment Bar ── */}
      <div
        ref={trackRef}
        className="weight-clean-track"
        role="group"
        aria-label="Interactive weight allocation track"
      >
        {weightsArr.map((w, i) => {
          const left = weightsArr.slice(0, i).reduce((s, v) => s + v, 0) * 100;
          const width = w * 100;
          const key = keys[i];
          const col = colors(key);

          return (
            <div
              key={String(key)}
              className="weight-clean-segment"
              style={{
                left: `${left}%`,
                width: `${width}%`,
                backgroundColor: col,
              }}
              title={`${segLabel(key)}: ${pct(w)}`}
            >
              {width > 14 ? (
                <div className="weight-clean-segment-content">
                  <span className="weight-clean-segment-name">{segLabel(key)}</span>
                  <span className="weight-clean-segment-pct font-num">{pct(w)}</span>
                </div>
              ) : width > 7 ? (
                <span className="weight-clean-segment-pct font-num">{pct(w)}</span>
              ) : null}
            </div>
          );
        })}

        {/* Tactile Divider Handles */}
        {keys.slice(0, -1).map((key, divIdx) => {
          const left = weightsArr.slice(0, divIdx + 1).reduce((s, v) => s + v, 0) * 100;
          const leftW = weightsArr[divIdx];
          const rightW = weightsArr[divIdx + 1];
          const isDragging = activeDivider === divIdx;

          return (
            <div
              key={`div-${String(key)}`}
              className={`weight-clean-divider${isDragging ? ' dragging' : ''}`}
              style={{ left: `${left}%` }}
              role="slider"
              aria-label={`Adjust weight between ${segLabel(keys[divIdx])} and ${segLabel(keys[divIdx + 1])}`}
              aria-valuenow={Math.round(leftW * 100)}
              aria-valuemin={2}
              aria-valuemax={Math.round((leftW + rightW) * 100) - 2}
              tabIndex={0}
              onPointerDown={e => handleDividerPointerDown(e, divIdx)}
              onKeyDown={e => handleDividerKey(e, divIdx)}
            >
              <div className="divider-pill">
                <span className="divider-grip-dot" />
                <span className="divider-grip-dot" />
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 3. Cleaner Weight Breakdown Cards (with Steppers) ── */}
      <div className="weight-clean-cards-grid">
        {keys.map((k, i) => {
          const col = colors(k);
          const w = weightsArr[i];
          const percentage = Math.round(w * 100);

          return (
            <div key={String(k)} className="weight-clean-card">
              <div className="weight-clean-card-header">
                <div className="weight-clean-card-title-group">
                  <span className="weight-card-dot" style={{ backgroundColor: col }} />
                  <span className="weight-card-title">{segLabel(k)}</span>
                  {mode === 'lead' && k === 21 && (
                    <span style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      letterSpacing: '0.03em',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'rgba(230, 81, 0, 0.12)',
                      color: '#E65100',
                      border: '1px solid rgba(230, 81, 0, 0.28)',
                      marginLeft: '6px',
                      display: 'inline-flex',
                      alignItems: 'center',
                    }}>
                      MoSPI Checkpoint
                    </span>
                  )}
                </div>
                <div className="weight-card-steppers">
                  <button
                    type="button"
                    className="weight-card-step-btn"
                    onClick={(e) => handleStep(k, e.shiftKey ? -0.05 : -0.01)}
                    title="Decrease weight by 1% (Shift for 5%)"
                    aria-label={`Decrease ${segLabel(k)} weight`}
                  >
                    -
                  </button>
                  <span className="weight-card-value font-num">{percentage}%</span>
                  <button
                    type="button"
                    className="weight-card-step-btn"
                    onClick={(e) => handleStep(k, e.shiftKey ? 0.05 : 0.01)}
                    title="Increase weight by 1% (Shift for 5%)"
                    aria-label={`Increase ${segLabel(k)} weight`}
                  >
                    +
                  </button>
                </div>
              </div>

              <div className="weight-clean-card-sub">{segSub(k)}</div>

              <div className="weight-card-meter">
                <div
                  className="weight-card-meter-fill"
                  style={{ width: `${percentage}%`, backgroundColor: col }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 4. Sensitivity Callout ── */}
      <div className="weight-clean-sensitivity">
        <div className="sensitivity-icon-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 3" />
          </svg>
        </div>
        <div className="sensitivity-text-wrap">
          {isBenchmark ? (
            <p className="sensitivity-lead">
              Weights match the <strong>MoSPI Baseline</strong>. The index tracks the certified benchmark trajectory with 0.0 pt deviation.
            </p>
          ) : (
            <p className="sensitivity-lead">
              With these weights the index differs from default by at most{' '}
              <strong>{devValue.toFixed(1)} points</strong> on {formattedDate}.
            </p>
          )}
        </div>
        <div className="sensitivity-badge-wrap">
          <span className={`sensitivity-pill ${isBenchmark ? 'benchmark' : devValue < 2.0 ? 'low' : 'moderate'}`}>
            {isBenchmark ? 'MoSPI Baseline' : devValue < 2.0 ? 'Low Sensitivity' : 'Moderate Sensitivity'}
          </span>
        </div>
      </div>
    </div>
  );
}
