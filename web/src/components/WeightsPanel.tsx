import { useState } from 'react';

interface Props {
  leadWeights: Record<number, number>;
  onChange: (w: Record<number, number>) => void;
  onToggle: (active: boolean) => void;
  active: boolean;
}

const LEAD_DAYS = [1, 7, 15, 30];

/** Renormalise weights so they sum to 1, keeping all positive. */
function normalise(weights: Record<number, number>): Record<number, number> {
  const total = Object.values(weights).reduce((s, v) => s + v, 0);
  if (total === 0) return weights;
  const out: Record<number, number> = {};
  for (const [k, v] of Object.entries(weights)) {
    out[Number(k)] = v / total;
  }
  return out;
}

export default function WeightsPanel({ leadWeights, onChange, onToggle, active }: Props) {
  // Raw slider values (0–100 ints)
  const [sliders, setSliders] = useState<Record<number, number>>(() =>
    Object.fromEntries(LEAD_DAYS.map(d => [d, Math.round(leadWeights[d] * 100)]))
  );

  function handleSlider(day: number, val: number) {
    const next = { ...sliders, [day]: val };
    setSliders(next);
    const raw: Record<number, number> = {};
    for (const [k, v] of Object.entries(next)) raw[Number(k)] = v / 100;
    onChange(normalise(raw));
  }

  const normalised = normalise(Object.fromEntries(LEAD_DAYS.map(d => [d, sliders[d] / 100])));

  return (
    <div className="panel">
      <div className="panel__header">
        <span className="panel__title">Weights panel</span>
        <button
          onClick={() => onToggle(!active)}
          style={{
            padding: '2px 10px',
            borderRadius: 3,
            border: '1px solid var(--col-border)',
            background: active ? 'rgba(91,156,246,0.1)' : 'transparent',
            color: active ? 'var(--col-primary)' : 'var(--col-ink-muted)',
            fontFamily: 'inherit',
            fontSize: 'var(--text-xs)',
            cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {active ? 'Using custom' : 'Apply'}
        </button>
      </div>

      <p className="text-muted text-italic" style={{ fontSize: 'var(--text-xs)', marginBottom: 'var(--space-4)', lineHeight: 1.5 }}>
        Adjust lead-time weights and the index recomputes in the browser.
        These are assumptions — the default is equal weight across all windows.
      </p>

      <div className="weights-panel" role="group" aria-label="Lead-time weight controls">
        {LEAD_DAYS.map(day => (
          <div className="weight-row" key={day}>
            <label htmlFor={`weight-${day}`} style={{ textAlign: 'right' }}>
              {day}d
            </label>
            <input
              id={`weight-${day}`}
              type="range"
              min={0}
              max={100}
              step={1}
              value={sliders[day]}
              onChange={e => handleSlider(day, parseInt(e.target.value))}
              aria-label={`Weight for ${day} days before departure`}
            />
            <span className="weight-val font-num">
              {(normalised[day] * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--col-surface)', borderRadius: 4, fontSize: 'var(--text-xs)', color: 'var(--col-ink-muted)' }}>
        <div style={{ marginBottom: 'var(--space-1)', fontWeight: 500, color: 'var(--col-ink)' }}>
          Normalised weights
        </div>
        {LEAD_DAYS.map(d => (
          <div key={d} style={{ display: 'flex', justifyContent: 'space-between', fontVariantNumeric: 'tabular-nums' }}>
            <span>{d} days</span>
            <span>{(normalised[d] * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--col-ink-muted)' }}>
        Route weights (DGCA-placeholder): DEL-BOM 50% · DEL-BLR 30% · BOM-BLR 20%
      </div>
    </div>
  );
}
