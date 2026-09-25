/**
 * WeightBar — drag-divider horizontal bar for weight allocation.
 *
 * One bar split into segments per lead window (or per route).
 * Dragging the divider between two segments moves weight from one to the other.
 * Weights always sum to 100%. Snap to 1%.
 * Keyboard: Left/Right = 1%, Shift+Arrow = 5%.
 */
import { useState, useRef, useCallback, useId, useEffect } from 'react';

const LEAD_DAYS = [1, 7, 15, 30] as const;
const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;

const SEGMENT_COLORS_LEAD: Record<number, string> = {
  1:  '#2A5FA5',
  7:  '#2F7D6D',
  15: '#B0286A',
  30: '#A8916A',
};

const SEGMENT_COLORS_ROUTE: Record<string, string> = {
  'DEL-BOM': '#2A5FA5',
  'DEL-BLR': '#B0286A',
  'BOM-BLR': '#2F7D6D',
};

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

  // Internal % weights (0–1) as array for the current mode
  const keys: (string | number)[] = mode === 'lead'
    ? [...LEAD_DAYS]
    : [...ROUTES];

  const weights = mode === 'lead' ? leadWeights : routeWeights;
  const colors = mode === 'lead'
    ? (k: string | number) => SEGMENT_COLORS_LEAD[k as number]
    : (k: string | number) => SEGMENT_COLORS_ROUTE[k as string];

  const segLabel = (k: string | number) =>
    mode === 'lead' ? dayLabel(k as number) : String(k);

  // Drag state
  const dragRef = useRef<{
    divIdx: number;
    startX: number;
    startWeights: number[];   // FIXED: snapshot of actual weight values at pointer-down
    trackW: number;
  } | null>(null);

  const getWeightsArr = () => keys.map(k => weights[k] ?? 0);

  const handleDividerPointerDown = useCallback((
    e: React.PointerEvent, divIdx: number,
  ) => {
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = {
      divIdx,
      startX: e.clientX,
      startWeights: keys.map(k => weights[k] ?? 0),  // snapshot values, not keys
      trackW: trackRef.current?.getBoundingClientRect().width ?? 800,
    };
  }, [keys, weights]);

  useEffect(() => {
    function onMove(e: PointerEvent) {
      if (!dragRef.current) return;
      const { divIdx, startX, startWeights, trackW } = dragRef.current;
      const dx = e.clientX - startX;
      // delta relative to the SNAPSHOT at drag-start — no drift accumulation
      const delta = snap(clamp(dx / trackW, -0.99, 0.99));

      const left0 = startWeights[divIdx];
      const right0 = startWeights[divIdx + 1];
      const move = clamp(delta, -left0 + 0.01, right0 - 0.01);

      const next = [...startWeights];
      next[divIdx]     = snap(clamp(left0  + move, 0.01, 0.99));
      next[divIdx + 1] = snap(clamp(right0 - move, 0.01, 0.99));

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

    function onUp() { dragRef.current = null; }

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [mode, keys, weights, onLeadChange, onRouteChange]);

  // Keyboard on dividers
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
    const clamped = clamp(move, -left + 0.01, right - 0.01);
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
  }, [mode, keys, weights, onLeadChange, onRouteChange]);

  // Sensitivity sentence
  let sensitivityText = '';
  if (sensitivity) {
    const { maxDev, maxDate } = sensitivity;
    if (maxDev < 0.05) {
      sensitivityText = 'With these weights the index is within 0.0 points of the default.';
    } else {
      const datePart = maxDate
        ? ` (on ${new Date(maxDate + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', timeZone: 'UTC' })})`
        : '';
      sensitivityText = `With these weights the index differs from the default by at most ${maxDev.toFixed(1)} points${datePart}.`;
    }
  }

  const weightsArr = getWeightsArr();
  const buttonId1 = useId();
  const buttonId2 = useId();

  return (
    <div className="weight-bar-section">
      <div className="weight-bar-controls">
        <span className="weight-bar-label">What if the weights were different?</span>
        <div className="toggle-group" style={{ marginLeft: 'auto' }}>
          <button
            id={buttonId1}
            className="toggle-btn"
            aria-pressed={mode === 'lead'}
            onClick={() => onModeChange('lead')}
          >
            Lead times
          </button>
          <span className="toggle-sep">|</span>
          <button
            id={buttonId2}
            className="toggle-btn"
            aria-pressed={mode === 'route'}
            onClick={() => onModeChange('route')}
          >
            Routes
          </button>
          <button className="btn-reset" onClick={onReset} style={{ marginLeft: 'var(--sp-4)' }}>
            Reset
          </button>
        </div>
      </div>

      {/* Bar track */}
      <div
        ref={trackRef}
        className="weight-bar-track"
        role="group"
        aria-label="Weight allocation bar"
      >
        {weightsArr.map((w, i) => {
          const left = weightsArr.slice(0, i).reduce((s, v) => s + v, 0) * 100;
          const width = w * 100;
          const key = keys[i];
          const col = colors(key);
          return (
            <div
              key={String(key)}
              className="weight-bar-segment"
              style={{
                left: `${left}%`,
                width: `${width}%`,
                background: col,
              }}
            >
              <span className="weight-bar-segment-label">
                {width > 8 ? pct(w) : ''}
              </span>
            </div>
          );
        })}

        {/* Dividers between segments */}
        {keys.slice(0, -1).map((key, divIdx) => {
          const left = weightsArr.slice(0, divIdx + 1).reduce((s, v) => s + v, 0) * 100;
          const leftW = weightsArr[divIdx];
          const rightW = weightsArr[divIdx + 1];
          return (
            <div
              key={`div-${String(key)}`}
              className="weight-bar-divider"
              style={{ left: `${left}%` }}
              role="slider"
              aria-label={`Divider between ${segLabel(keys[divIdx])} and ${segLabel(keys[divIdx + 1])}`}
              aria-valuenow={Math.round(leftW * 100)}
              aria-valuemin={1}
              aria-valuemax={Math.round((leftW + rightW) * 100) - 1}
              tabIndex={0}
              onPointerDown={e => handleDividerPointerDown(e, divIdx)}
              onKeyDown={e => handleDividerKey(e, divIdx)}
            />
          );
        })}
      </div>

      {/* Captions */}
      <div className="weight-bar-captions">
        {keys.map((k, i) => (
          <div
            key={String(k)}
            className="weight-bar-caption-item"
            style={{ width: `${weightsArr[i] * 100}%` }}
          >
            {segLabel(k)} {pct(weightsArr[i])}
          </div>
        ))}
      </div>

      {/* Sensitivity sentence */}
      {sensitivityText && (
        <p className="weight-sensitivity">{sensitivityText}</p>
      )}
    </div>
  );
}
