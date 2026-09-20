/**
 * RecordStrip — a single-line visual record of collection runs.
 * One tick per run date:
 *   filled  = ok
 *   outline = partial
 *   crossed = failed (in --route-mag)
 * Hover / focus shows date + reason as tooltip.
 */
import { useState } from 'react';
import type { Run } from '../api';

function fmtDateShort(s: string): string {
  return new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', timeZone: 'UTC',
  });
}

interface Props {
  runs: Run[];
}

interface Tooltip {
  x: number;
  y: number;
  run: Run;
}

export default function RecordStrip({ runs }: Props) {
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);

  if (runs.length === 0) return null;

  const sorted = [...runs].sort((a, b) => a.run_date.localeCompare(b.run_date));
  const okCount = sorted.filter(r => r.status === 'ok').length;
  const exceptions = sorted.filter(r => r.status !== 'ok');

  return (
    <div className="record-strip">
      <div className="record-strip-row">
        <div className="record-strip-ticks" role="list" aria-label="Collection run history">
          {sorted.map(run => (
            <Tick
              key={run.id}
              run={run}
              onShowTooltip={(x, y, r) => setTooltip({ x, y, run: r })}
              onHideTooltip={() => setTooltip(null)}
            />
          ))}
        </div>
        <span className="record-strip-count font-num">
          {okCount} of {sorted.length} {sorted.length === 1 ? 'run' : 'runs'} ok
        </span>
      </div>

      {/* Exceptions in plain sentences */}
      {exceptions.length > 0 && (
        <div className="record-exceptions">
          {exceptions.map(run => (
            <span key={run.id}>
              {fmtDateShort(run.run_date)}: {run.status}
              {run.notes ? `, ${run.notes}` : ''}
            </span>
          ))}
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div
          role="tooltip"
          style={{
            position: 'fixed',
            left: tooltip.x + 8,
            top: tooltip.y - 32,
            background: 'var(--ink)',
            color: 'var(--vellum)',
            padding: '4px 8px',
            fontSize: 'var(--t-axis)',
            fontFamily: "'B612', monospace",
            fontVariantNumeric: 'tabular-nums',
            pointerEvents: 'none',
            zIndex: 200,
            whiteSpace: 'nowrap',
          }}
        >
          {fmtDateShort(tooltip.run.run_date)}: {tooltip.run.status}
          {tooltip.run.notes ? ` — ${tooltip.run.notes}` : ''}
        </div>
      )}
    </div>
  );
}

interface TickProps {
  run: Run;
  onShowTooltip: (x: number, y: number, run: Run) => void;
  onHideTooltip: () => void;
}

function Tick({ run, onShowTooltip, onHideTooltip }: TickProps) {
  const isOk = run.status === 'ok';
  const isPartial = run.status === 'partial';
  const isFailed = run.status === 'failed';

  const handlePointer = (e: React.PointerEvent) => {
    onShowTooltip(e.clientX, e.clientY, run);
  };

  const handleFocus = (e: React.FocusEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    onShowTooltip(rect.left, rect.top, run);
  };

  return (
    <svg
      className="record-tick"
      role="listitem"
      aria-label={`${run.run_date}: ${run.status}${run.notes ? ` — ${run.notes}` : ''}`}
      tabIndex={0}
      onPointerEnter={handlePointer}
      onPointerMove={handlePointer}
      onPointerLeave={onHideTooltip}
      onFocus={handleFocus}
      onBlur={onHideTooltip}
      viewBox="0 0 10 18"
      style={{ overflow: 'visible' }}
    >
      {isOk && (
        <rect x={3} y={0} width={4} height={18} fill="var(--ink)" />
      )}
      {isPartial && (
        <rect x={3} y={0} width={4} height={18} fill="none" stroke="var(--ink)" strokeWidth={1} />
      )}
      {isFailed && (
        <>
          <rect x={3} y={0} width={4} height={18} fill="none" stroke="var(--route-mag)" strokeWidth={1} />
          <line x1={2} y1={1} x2={8} y2={17} stroke="var(--route-mag)" strokeWidth={1} />
          <line x1={8} y1={1} x2={2} y2={17} stroke="var(--route-mag)" strokeWidth={1} />
        </>
      )}
      {/* Unknown/other: faint */}
      {!isOk && !isPartial && !isFailed && (
        <rect x={3} y={0} width={4} height={18} fill="var(--contour)" />
      )}
    </svg>
  );
}
