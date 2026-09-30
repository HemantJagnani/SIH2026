/**
 * Phase28View — Real Data Index Dashboard
 * Shows the live AERIX score computed from Phase 28 DEL-BOM production data.
 * Displays the formula, lead-time breakdown, stratum sub-indices, source comparison.
 */

import { useState, useEffect, useRef } from 'react';
import { MathBlock } from '../components/MathBlock';

// ── Types ─────────────────────────────────────────────────────────────────────
interface LeadDetail {
  lead_days: number;
  weight: number;
  median_fare_inr: number;
  geometric_mean_fare_inr: number;
  n_itineraries: number;
  min_fare_inr: number;
  max_fare_inr: number;
  contribution_inr: number;
}

interface StratumDetail {
  weighted_price: number;
  index_value: number;
  lead_breakdown: Record<string, { median_fare: number; n_obs: number; weight: number }>;
}

interface SourceDetail {
  weighted_price: number;
  index_value: number;
  total_obs: number;
}

interface AirlineDetail {
  n_obs: number;
  median_fare: number;
  min_fare: number;
  max_fare: number;
}

interface IndexResult {
  meta: {
    route: string;
    base_price_inr: number;
    base_period: string;
    index_reference_period?: string;
    price_reference_period?: string;
    weight_reference_period?: string;
    chain_link_period?: string;
    reference_type?: string;
    experimental_project_reference_price?: number;
    experimental_reference_period?: string;
    reference_price?: number;
    collection_date: string;
    generated_at: string;
    total_observations: number;
    sources: string[];
    lead_times_covered: number[];
    methodology: string;
    formula: string;
    disclaimer: string;
  };
  reference_taxonomy?: Record<string, {
    label: string;
    value?: string;
    reference_type?: string;
    reference_price_inr?: number;
    reference_period?: string;
    formula?: string;
    status: string;
  }>;
  headline: {
    weighted_representative_price_inr: number;
    route_index: number;
    mom_inflation_percent?: number;
    interpretation: string;
    base_price_inr: number;
    reference_index_value?: number;
    experimental_project_reference_price?: number;
    reference_type?: string;
    cpi_airfare_weight_percent?: number;
    cpi_airfare_weight_decimal?: number;
    cpi_airfare_item_code?: string;
    estimated_cpi_contribution_pp?: number;
    cpi_weight_disclaimer?: string;
  };
  lead_time_breakdown: Record<string, LeadDetail>;
  stratum_sub_indices: Record<string, StratumDetail>;
  source_comparison: Record<string, SourceDetail>;
  airline_breakdown: Record<string, AirlineDetail>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const INR = (n: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);

const PCT = (n: number) => `${n.toFixed(1)}%`;

const STRATUM_LABELS: Record<string, string> = {
  STANDARD_SAVER: 'Standard Saver',
  FLEXIBLE_ECONOMY: 'Flexible Economy',
  OTA_EXCLUSIVE: 'OTA Exclusive',
  PREMIUM_UPFRONT: 'Premium Up-front',
};

const STRATUM_DESC: Record<string, string> = {
  STANDARD_SAVER: 'Basic economy — 7 kg cabin, 15 kg check-in, non-refundable',
  FLEXIBLE_ECONOMY: 'Reduced date-change penalty, seat selection included',
  OTA_EXCLUSIVE: 'Aggregator-exclusive promotional fare',
  PREMIUM_UPFRONT: 'Front row / extra legroom, 20 kg check-in, hot meal',
};

const STRATUM_COLOR: Record<string, string> = {
  STANDARD_SAVER: 'var(--route-blue)',
  FLEXIBLE_ECONOMY: 'var(--route-teal)',
  OTA_EXCLUSIVE: 'var(--route-mag)',
  PREMIUM_UPFRONT: 'var(--hatch)',
};

// ── Animated number ───────────────────────────────────────────────────────────
function AnimatedNumber({ value, decimals = 2, prefix = '' }: { value: number; decimals?: number; prefix?: string }) {
  const [display, setDisplay] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const start = 0;
    const end = value;
    const duration = 1200;
    const startTime = performance.now();

    function step(now: number) {
      const t = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(start + (end - start) * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(step);
    }

    rafRef.current = requestAnimationFrame(step);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [value]);

  return <>{prefix}{display.toFixed(decimals)}</>;
}

// ── Gauge ─────────────────────────────────────────────────────────────────────
function IndexGauge({ value }: { value: number }) {
  const pct = Math.min(Math.max(value, 0), 200) / 200;
  const angle = -140 + pct * 280;
  const r = 70;
  const cx = 90, cy = 90;

  const arc = (from: number, to: number, color: string) => {
    const toRad = (deg: number) => (deg * Math.PI) / 180;
    const x1 = cx + r * Math.cos(toRad(from - 90));
    const y1 = cy + r * Math.sin(toRad(from - 90));
    const x2 = cx + r * Math.cos(toRad(to - 90));
    const y2 = cy + r * Math.sin(toRad(to - 90));
    const large = to - from > 180 ? 1 : 0;
    return (
      <path
        d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`}
        fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
      />
    );
  };

  return (
    <svg viewBox="0 0 180 110" style={{ width: 200, height: 120, overflow: 'visible' }} aria-label={`Index gauge: ${value.toFixed(2)}`}>
      {/* Track */}
      {arc(-140, 140, 'var(--contour)')}
      {/* Value arc */}
      {arc(-140, -140 + pct * 280, value > 100 ? 'var(--route-mag)' : 'var(--route-blue)')}
      {/* Needle */}
      <line
        x1={cx} y1={cy}
        x2={cx + (r - 10) * Math.cos(((angle - 90) * Math.PI) / 180)}
        y2={cy + (r - 10) * Math.sin(((angle - 90) * Math.PI) / 180)}
        stroke="var(--ink)" strokeWidth="2" strokeLinecap="round"
        style={{ transformOrigin: `${cx}px ${cy}px`, transition: 'all 1.2s cubic-bezier(0.23, 1, 0.32, 1)' }}
      />
      <circle cx={cx} cy={cy} r={4} fill="var(--ink)" />
      {/* Labels */}
      <text x="20" y="105" fontSize="9" fill="var(--ink-2)">50</text>
      <text x="90" y="22" fontSize="9" fill="var(--ink-2)" textAnchor="middle">100</text>
      <text x="148" y="105" fontSize="9" fill="var(--ink-2)">150</text>
    </svg>
  );
}

// ── Horizontal bar ────────────────────────────────────────────────────────────
function HBar({ value, max, color }: { value: number; max: number; color: string }) {
  return (
    <div style={{ height: 8, background: 'var(--contour)', borderRadius: 4, overflow: 'hidden' }}>
      <div style={{
        height: '100%', width: `${Math.min((value / max) * 100, 100)}%`,
        background: color, borderRadius: 4,
        transition: 'width 1s cubic-bezier(0.23,1,0.32,1)',
      }} />
    </div>
  );
}

// ── Formula block ─────────────────────────────────────────────────────────────
function FormulaBlock({ data }: { data: IndexResult }) {
  const { headline, lead_time_breakdown } = data;
  const leads = Object.entries(lead_time_breakdown).sort((a, b) => a[1].lead_days - b[1].lead_days);
  const n = leads.length;

  return (
    <section style={{ marginTop: 'var(--sp-8)' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-4)', borderBottom: '2px solid var(--ink)', paddingBottom: 'var(--sp-2)' }}>
        Formula Walkthrough — DEL-BOM
      </h2>

      {/* Step 1 */}
      <div className="formula-step">
        <div className="formula-step__label">Step 1 — Representative Route Price</div>
        <MathBlock
          formula="P_{\text{route}} = \sum_{L} w_L \times \text{Median}(\text{fares}_L)"
          caption="For each of the lead-time windows, collect all quoted fares and compute median multiplied by empirical weight."
        />
        <p className="formula-prose">
          For each of the {n} lead-time windows, collect all quoted fares and take the <strong>median</strong>.
          Multiply each median by the lead-time weight (equal weights = 1/{n} each) and sum.
        </p>
        <div className="formula-worked" style={{ overflowX: 'auto' }}>
          <table className="method-table">
            <thead>
              <tr>
                <th>Lead time</th>
                <th>Travel date</th>
                <th className="col-num">Itineraries</th>
                <th className="col-num">Median fare</th>
                <th className="col-num">Weight</th>
                <th className="col-num">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {leads.map(([key, d]) => (
                <tr key={key}>
                  <td className="font-num">{key}</td>
                  <td className="font-num" style={{ color: 'var(--ink-2)' }}>
                    {/* approx travel date */}
                    +{d.lead_days}d
                  </td>
                  <td className="font-num col-num">{d.n_itineraries}</td>
                  <td className="font-num col-num"><strong>{INR(d.median_fare_inr)}</strong></td>
                  <td className="font-num col-num">{PCT(d.weight * 100)}</td>
                  <td className="font-num col-num">{INR(d.contribution_inr)}</td>
                </tr>
              ))}
              <tr style={{ borderTop: '2px solid var(--ink)', fontWeight: 700 }}>
                <td colSpan={5} className="col-num" style={{ textAlign: 'right' }}>Representative Route Price P<sub>route</sub> =</td>
                <td className="font-num col-num" style={{ color: 'var(--route-blue)' }}>
                  {INR(headline.weighted_representative_price_inr)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Step 2 */}
      <div className="formula-step">
        <div className="formula-step__label">Step 2 — Route Index (Experimental Series)</div>
        <MathBlock
          formula="I_{\text{DEL-BOM},t} = \left(\frac{P_{\text{route},t}}{P_{\text{project,reference}}}\right) \times 100"
          caption="Current representative price divided by project reference price (₹6,632.67 from first complete run)."
        />
        <p className="formula-prose">
          Divide the current representative price by the project reference price (₹6,632.67 from first complete production run). 
          <em>Note: This is strictly an experimental project reference, distinct from the official MoSPI CPI 2024 calendar-year price reference.</em>
        </p>
        <div className="formula-calc-row">
          <div className="formula-calc-cell">
            <div className="formula-calc-label">P<sub>route</sub> (today)</div>
            <div className="formula-calc-val">{INR(headline.weighted_representative_price_inr)}</div>
          </div>
          <div className="formula-calc-op">&divide;</div>
          <div className="formula-calc-cell">
            <div className="formula-calc-label">P<sub>project,ref</sub> (2026-09-26)</div>
            <div className="formula-calc-val">{INR(headline.base_price_inr)}</div>
          </div>
          <div className="formula-calc-op">&times; 100 =</div>
          <div className="formula-calc-cell formula-calc-result">
            <div className="formula-calc-label">Route Index</div>
            <div className="formula-calc-val" style={{ color: 'var(--route-blue)', fontSize: 28, fontWeight: 700 }}>
              {headline.route_index.toFixed(2)}
            </div>
          </div>
        </div>
        <p className="formula-prose" style={{ marginTop: 'var(--sp-3)', color: 'var(--ink-2)' }}>
          {headline.interpretation}. An index above 100 indicates upward fare pressure relative to the provisional project reference.
        </p>
      </div>
    </section>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────
export default function Phase28View() {
  const [data, setData] = useState<IndexResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load the pre-computed result JSON directly
    fetch('/aerix_delbom_result.json')
      .then(r => {
        if (!r.ok) return fetch('/apix_delbom_result.json');
        return r;
      })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="page loading">Computing real index…</div>;
  if (error || !data) return (
    <div className="page" style={{ color: 'var(--route-mag)' }}>
      Failed to load index data: {error}.<br />
      Run <code>python scripts/compute_delbom_index.py</code> and copy <code>aerix_delbom_result.json</code> to <code>web/public/</code>.
    </div>
  );

  const { meta, headline, lead_time_breakdown, stratum_sub_indices, source_comparison, airline_breakdown } = data;

  const maxAirlineObs = Math.max(...Object.values(airline_breakdown).map(a => a.n_obs));
  const maxStratum = Math.max(...Object.values(stratum_sub_indices).map(s => s.index_value));

  return (
    <div className="page" style={{ maxWidth: 960 }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 'var(--sp-8)' }}>
        <h1 style={{ fontSize: 'var(--t-headline)', fontWeight: 700, lineHeight: 1.1 }}>
          Real Data Index<br />
          <span style={{ color: 'var(--route-blue)' }}>DEL → BOM</span>
        </h1>
        <p style={{ marginTop: 'var(--sp-2)', color: 'var(--ink-2)', fontSize: 'var(--t-ui)' }}>
          Computed from {meta.total_observations.toLocaleString()} live observations collected {meta.collection_date} &middot;{' '}
          {meta.sources.join(' + ')} &middot; {meta.lead_times_covered.length} lead-time windows
        </p>
        <p style={{ marginTop: 'var(--sp-1)', fontSize: 11, color: 'var(--assumed)', fontStyle: 'italic' }}>
          {meta.disclaimer}
        </p>
      </div>

      {/* ── Headline Score ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '200px 1fr',
        gap: 'var(--sp-8)',
        alignItems: 'center',
        padding: 'var(--sp-6)',
        border: '2px solid var(--ink)',
        marginBottom: 'var(--sp-8)',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <IndexGauge value={headline.route_index} />
          <div style={{ fontSize: 'var(--t-headline)', fontWeight: 700, lineHeight: 1, marginTop: 'var(--sp-2)', color: 'var(--route-blue)' }}>
            <AnimatedNumber value={headline.route_index} decimals={2} />
          </div>
          <div style={{ fontSize: 'var(--t-ui)', color: 'var(--ink-2)', marginTop: 4 }}>AERIX (DEL-BOM)</div>
        </div>
        <div>
          <p style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-3)' }}>
            Fares are at <span style={{ color: 'var(--route-blue)' }}>{headline.route_index.toFixed(1)}%</span> of the project reference price
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--sp-4)' }}>
            {[
              { label: 'Representative price', val: INR(headline.weighted_representative_price_inr) },
              { label: 'Project Reference (POC)', val: INR(headline.base_price_inr) },
              { label: 'Observations used', val: meta.total_observations.toLocaleString() },
            ].map(({ label, val }) => (
              <div key={label} style={{ borderLeft: '2px solid var(--contour)', paddingLeft: 'var(--sp-3)' }}>
                <div style={{ fontSize: 11, color: 'var(--ink-2)', marginBottom: 2 }}>{label}</div>
                <div className="font-num" style={{ fontSize: 16, fontWeight: 700 }}>{val}</div>
              </div>
            ))}
          </div>
          <p style={{ marginTop: 'var(--sp-4)', fontSize: 'var(--t-ui)', color: 'var(--ink-2)' }}>
            Project Ref: {meta.base_period} &middot; Method: {meta.methodology}
          </p>
        </div>
      </div>

      {/* ── Reference Period Taxonomy Notice ── */}
      <div style={{
        background: '#f8fafc',
        border: '1px solid #cbd5e1',
        borderLeft: '4px solid var(--route-blue)',
        padding: 'var(--sp-4)',
        marginBottom: 'var(--sp-8)',
        borderRadius: 4,
      }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>🏛️</span>
          <span>MoSPI CPI 2024 & Eurostat HICP Reference Period Taxonomy</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--sp-3)', marginTop: 'var(--sp-2)' }}>
          <div style={{ background: '#ffffff', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--ink-2)', fontWeight: 600 }}>PROJECT REFERENCE</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--route-blue)' }}>{INR(headline.base_price_inr)} (2026-09-26)</div>
            <div style={{ fontSize: 10, color: '#64748b' }}>Provisional POC anchor</div>
          </div>
          <div style={{ background: '#ffffff', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--ink-2)', fontWeight: 600 }}>MOSPI INDEX REFERENCE</div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>2024 = 100</div>
            <div style={{ fontSize: 10, color: '#64748b' }}>Official revision scale</div>
          </div>
          <div style={{ background: '#ffffff', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--ink-2)', fontWeight: 600 }}>MOSPI PRICE REFERENCE</div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>2024 Annual Average</div>
            <div style={{ fontSize: 10, color: '#d97706' }}>Pending 2024 Actuals</div>
          </div>
          <div style={{ background: '#ffffff', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--ink-2)', fontWeight: 600 }}>MOSPI WEIGHT REFERENCE</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#047857' }}>0.02951%</div>
            <div style={{ fontSize: 10, color: '#64748b' }}>Item: 07.3.3.1.2.01</div>
          </div>
          <div style={{ background: '#ffffff', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 4 }}>
            <div style={{ fontSize: 10, color: 'var(--ink-2)', fontWeight: 600 }}>EUROSTAT LINKING</div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>December y-1</div>
            <div style={{ fontSize: 10, color: '#64748b' }}>Annual recursive chain</div>
          </div>
        </div>
        
        {/* CPI Integration Layer & Contribution Callout */}
        <div style={{ marginTop: 'var(--sp-3)', padding: '10px 14px', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#065f46' }}>
              📊 CPI 2024 Integration Layer (Item Code: 07.3.3.1.2.01 — Passenger transport by air, domestic)
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#047857' }}>
              Airfare Contribution to CPI: {headline.estimated_cpi_contribution_pp !== undefined ? `${headline.estimated_cpi_contribution_pp >= 0 ? '+' : ''}${headline.estimated_cpi_contribution_pp.toFixed(6)} pp` : '+0.000779 pp'}
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#047857' }}>
            CPI Weight: <strong>0.02951%</strong> (Decimal: 0.0002951) &middot; Source: MoSPI CPI 2024 Weights of item CPI 2024 (Annexure 5.3d)
          </div>
          <div style={{ fontSize: 10.5, color: '#065f46', fontStyle: 'italic', borderTop: '1px dashed #6ee7b7', paddingTop: 4, marginTop: 2 }}>
            &ldquo;The MoSPI CPI 2024 airfare expenditure weight is used only for the optional integration of the experimental Airfare Price Index into CPI. It is not used to construct the Airfare Price Index itself.&rdquo;
          </div>
        </div>

        <p style={{ margin: '8px 0 0 0', fontSize: 11, color: '#64748b', fontStyle: 'italic' }}>
          * Institutional distinction: The provisional project reference price ({INR(headline.base_price_inr)}) is an experimental operational anchor and is NOT the official MoSPI calendar-year 2024 price reference.
        </p>
      </div>

      {/* ── Lead-time Breakdown ── */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-4)', borderBottom: '2px solid var(--ink)', paddingBottom: 'var(--sp-2)' }}>
          Lead-time Breakdown
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 'var(--sp-3)' }}>
          {Object.entries(lead_time_breakdown)
            .sort((a, b) => a[1].lead_days - b[1].lead_days)
            .map(([key, d]) => (
              <div key={key} style={{ border: '1px solid var(--contour)', padding: 'var(--sp-3)' }}>
                <div style={{ fontSize: 11, color: 'var(--ink-2)', marginBottom: 'var(--sp-1)' }}>{key}</div>
                <div className="font-num" style={{ fontSize: 16, fontWeight: 700 }}>{INR(d.median_fare_inr)}</div>
                <div style={{ fontSize: 11, color: 'var(--ink-2)', marginTop: 'var(--sp-1)' }}>median</div>
                <div style={{ marginTop: 'var(--sp-2)' }}>
                  <HBar value={d.median_fare_inr} max={10000} color="var(--route-blue)" />
                </div>
                <div style={{ fontSize: 10, color: 'var(--ink-2)', marginTop: 'var(--sp-1)' }}>
                  {d.n_itineraries} itins &middot; w={PCT(d.weight * 100)}
                </div>
                <div style={{ fontSize: 10, color: 'var(--ink-2)' }}>
                  {INR(d.min_fare_inr)} – {INR(d.max_fare_inr)}
                </div>
              </div>
            ))}
        </div>
      </section>

      {/* ── Formula Walkthrough ── */}
      <FormulaBlock data={data} />

      {/* ── Stratum Sub-Indices ── */}
      <section style={{ marginTop: 'var(--sp-8)', marginBottom: 'var(--sp-8)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-4)', borderBottom: '2px solid var(--ink)', paddingBottom: 'var(--sp-2)' }}>
          Fare-Family Stratum Sub-Indices
        </h2>
        <p style={{ fontSize: 'var(--t-ui)', color: 'var(--ink-2)', marginBottom: 'var(--sp-4)' }}>
          Each stratum is an independent homogeneous series. Observations are never mixed across strata.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)' }}>
          {Object.entries(stratum_sub_indices)
            .sort((a, b) => b[1].index_value - a[1].index_value)
            .map(([stratum, d]) => {
              const color = STRATUM_COLOR[stratum] || 'var(--ink)';
              return (
                <div key={stratum} style={{ border: `2px solid ${color}`, padding: 'var(--sp-4)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: 12, color, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {STRATUM_LABELS[stratum] || stratum}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-2)', marginTop: 2 }}>
                        {STRATUM_DESC[stratum]}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="font-num" style={{ fontSize: 22, fontWeight: 700, color }}>{d.index_value.toFixed(2)}</div>
                      <div style={{ fontSize: 11, color: 'var(--ink-2)' }}>index</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 'var(--sp-3)' }}>
                    <HBar value={d.index_value} max={maxStratum * 1.2} color={color} />
                  </div>
                  <div style={{ marginTop: 'var(--sp-2)', fontSize: 11, color: 'var(--ink-2)' }}>
                    Rep. price: {INR(d.weighted_price)} &middot; Base: {INR(meta.base_price_inr)}
                  </div>
                </div>
              );
            })}
        </div>
      </section>

      {/* ── Source Comparison ── */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-4)', borderBottom: '2px solid var(--ink)', paddingBottom: 'var(--sp-2)' }}>
          Source Comparison
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)' }}>
          {Object.entries(source_comparison).map(([src, d]) => {
            const label = src === 'google_flights' ? 'Google Flights' : 'EaseMyTrip';
            const color = src === 'google_flights' ? 'var(--route-blue)' : 'var(--route-mag)';
            return (
              <div key={src} style={{ border: '1px solid var(--contour)', padding: 'var(--sp-4)' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color, marginBottom: 'var(--sp-3)' }}>{label}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--sp-2)' }}>
                  {[
                    { l: 'Index', v: d.index_value.toFixed(2) },
                    { l: 'Rep. price', v: INR(d.weighted_price) },
                    { l: 'Observations', v: d.total_obs.toLocaleString() },
                  ].map(({ l, v }) => (
                    <div key={l}>
                      <div style={{ fontSize: 10, color: 'var(--ink-2)' }}>{l}</div>
                      <div className="font-num" style={{ fontWeight: 700 }}>{v}</div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 'var(--sp-3)' }}>
                  <HBar value={d.index_value} max={120} color={color} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Airline Breakdown ── */}
      <section style={{ marginBottom: 'var(--sp-8)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--sp-4)', borderBottom: '2px solid var(--ink)', paddingBottom: 'var(--sp-2)' }}>
          Airline Breakdown
        </h2>
        <table className="method-table">
          <thead>
            <tr>
              <th>Airline</th>
              <th className="col-num">Observations</th>
              <th className="col-num">Median fare</th>
              <th className="col-num">Min fare</th>
              <th className="col-num">Max fare</th>
              <th style={{ width: 160 }}>Share</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(airline_breakdown).map(([airline, d]) => (
              <tr key={airline}>
                <td style={{ fontWeight: 600 }}>{airline}</td>
                <td className="font-num col-num">{d.n_obs}</td>
                <td className="font-num col-num">{INR(d.median_fare)}</td>
                <td className="font-num col-num" style={{ color: 'var(--route-teal)' }}>{INR(d.min_fare)}</td>
                <td className="font-num col-num" style={{ color: 'var(--route-mag)' }}>{INR(d.max_fare)}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                    <div style={{ flex: 1 }}>
                      <HBar value={d.n_obs} max={maxAirlineObs} color="var(--route-blue)" />
                    </div>
                    <span className="font-num" style={{ fontSize: 10, color: 'var(--ink-2)', minWidth: 36, textAlign: 'right' }}>
                      {((d.n_obs / meta.total_observations) * 100).toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* ── Missing data note ── */}
      <section style={{ border: '1px solid var(--contour)', padding: 'var(--sp-4)', marginBottom: 'var(--sp-8)', fontSize: 'var(--t-ui)' }}>
        <div style={{ fontWeight: 700, marginBottom: 'var(--sp-2)' }}>What's missing (and why it doesn't affect the index)</div>
        <table className="method-table">
          <thead>
            <tr><th>Field</th><th>Needed for Index?</th><th>Status</th><th>Reason</th></tr>
          </thead>
          <tbody>
            {[
              { field: 'total_fare', needed: '✅ YES — core', status: '✅ OBSERVED', reason: 'All 2,432 observations have it' },
              { field: 'base_fare', needed: 'No', status: '❌ NULL', reason: 'Not exposed by any portal (SOURCE_TOTAL_ONLY)' },
              { field: 'taxes / GST', needed: 'No', status: '❌ NULL', reason: 'Bundled inside total_fare, not itemised' },
              { field: 'airport charges', needed: 'No', status: '❌ NULL', reason: 'Not rendered in search DOM (NOT_PRESENT_IN_DOM)' },
              { field: 'cabin_baggage_kg', needed: 'QA only', status: '✅ EMT / ❌ GF', reason: 'GF does not expose baggage in listing view' },
            ].map(r => (
              <tr key={r.field}>
                <td><code>{r.field}</code></td>
                <td>{r.needed}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{r.status}</td>
                <td style={{ color: 'var(--ink-2)' }}>{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ marginTop: 'var(--sp-3)', color: 'var(--ink-2)' }}>
          Per NSC Non-Fabrication Policy: NULL fields remain NULL. No backward calculation from total_fare is performed.
        </p>
      </section>

    </div>
  );
}
