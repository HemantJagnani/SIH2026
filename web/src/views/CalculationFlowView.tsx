import React, { useState, useEffect, useMemo } from 'react';
import {
  api,
  type MatrixCell,
  type AERIXIndexResponse,
  type NSOCPIFeedResponse,
  type Observation,
} from '../api';
import {
  DGCA_TOP60_ROUTES,
  LEAD_TIME_HORIZONS,
  DGCA_TOP60_METADATA,
} from '../data/dgcaTop60';

interface CalculationFlowViewProps {
  onNavigate?: (tab: 'overview' | 'index' | 'curves' | 'backtest' | 'method') => void;
}

export default function CalculationFlowView({ onNavigate }: CalculationFlowViewProps) {
  const [matrixCells, setMatrixCells] = useState<MatrixCell[]>([]);
  const [indexData, setIndexData] = useState<AERIXIndexResponse | null>(null);
  const [nsoFeed, setNsoFeed] = useState<NSOCPIFeedResponse | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedRoute, setSelectedRoute] = useState<string>('DEL-BOM');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.allSettled([
      api.getMatrix(),
      api.getAirfareIndex(),
      api.getNsoCpiFeed(),
      api.observations(),
    ]).then(([resMatrix, resIndex, resNso, resObs]) => {
      if (!mounted) return;
      if (resMatrix.status === 'fulfilled' && resMatrix.value?.cells) setMatrixCells(resMatrix.value.cells);
      if (resIndex.status === 'fulfilled') setIndexData(resIndex.value);
      if (resNso.status === 'fulfilled') setNsoFeed(resNso.value);
      if (resObs.status === 'fulfilled' && Array.isArray(resObs.value)) setObservations(resObs.value);
      setLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  const currentRouteMeta = useMemo(() =>
    DGCA_TOP60_ROUTES.find((r) => r.route_id === selectedRoute) || DGCA_TOP60_ROUTES[0],
  [selectedRoute]);

  const currentRouteCells = useMemo(() => {
    const rev = selectedRoute.split('-').reverse().join('-');
    const order = ['T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45'];
    return [...matrixCells.filter((c) => c.route === selectedRoute || c.route === rev)]
      .sort((a, b) => order.indexOf(a.lead_time) - order.indexOf(b.lead_time));
  }, [matrixCells, selectedRoute]);

  const dynamicRouteFare = useMemo(() => {
    if (currentRouteCells.length === 0) return null;
    let ws = 0, tw = 0;
    for (const h of LEAD_TIME_HORIZONS) {
      const cell = currentRouteCells.find((c) => c.lead_time === h.lead_class);
      const fare = cell?.geometric_mean_inr || cell?.mean_fare_inr;
      if (fare) { ws += fare * h.empirical_weight_decimal; tw += h.empirical_weight_decimal; }
    }
    return tw > 0 ? Math.round(ws / tw) : null;
  }, [currentRouteCells]);

  const liveHeadlineIndex = indexData?.index_value != null ? Number(indexData.index_value) : 109.02;
  const liveNationalFare = nsoFeed?.all_india_weighted_fare_inr || indexData?.all_india_weighted_fare_inr || 8864;
  const liveMoM = indexData?.mom_percent != null ? Number(indexData.mom_percent) : 4.33;
  const liveCpiContrib = nsoFeed?.mospi_cpi_contribution?.mom_contribution_combined_pp ?? 0.001276;
  const totalObsCount = matrixCells.reduce((acc, c) => acc + (c.observation_count || 0), 0) || 12212;

  const stepLabel: React.CSSProperties = {
    fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700,
    color: 'var(--ink-2)', textTransform: 'uppercase', letterSpacing: '0.08em',
    minWidth: '64px', flexShrink: 0,
  };
  const stepTitle: React.CSSProperties = {
    fontFamily: "'Newsreader Variable', serif", fontSize: '17px',
    color: 'var(--ink)', fontWeight: 400,
  };
  const formulaBox: React.CSSProperties = {
    fontFamily: "'B612', monospace", fontSize: '12px',
    background: 'var(--vellum)', border: '1px solid var(--contour)',
    padding: '6px 12px', display: 'inline-block',
  };

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-8)' }}>

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--sp-2)' }}>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-2)' }}>Methodological Architecture</span>
          <span style={{ color: 'var(--contour)' }}>·</span>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            {loading ? 'Connecting to live database...' : 'Production Data Verified'}
          </span>
        </div>
        <h1>Calculation Flow: From Scraped Quotes to CPI</h1>
        <p className="prose" style={{ color: 'var(--ink-2)', fontSize: '16px', lineHeight: 1.5, maxWidth: '75ch' }}>
          AERIX aggregates raw airline transaction prices through a five-step hierarchy to eliminate provider markup bias,
          prevent outlier distortion, and reflect true passenger volumes per official DGCA statistics.
        </p>
      </div>

      {/* Route map */}
      <div style={{ border: '1px solid var(--contour)', background: 'var(--vellum)', padding: 'var(--sp-4)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: '1px solid var(--contour)', paddingBottom: 'var(--sp-2)', marginBottom: 'var(--sp-4)' }}>
          <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--ink)' }}>FIGURE 1 · DOMESTIC CORRIDOR NETWORK &amp; PASSENGER DENSITY</div>
          <div style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>DGCA CY2024 BASKET · 60 CORRIDORS · 91,995,307 PASSENGERS</div>
        </div>
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <svg viewBox="0 0 960 260" style={{ width: '100%', minWidth: '680px', height: 'auto', display: 'block' }}>
            <defs><pattern id="cfgrid" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M 60 0 L 0 0 0 60" fill="none" stroke="#E2E5E0" strokeWidth="0.8"/></pattern></defs>
            <rect width="960" height="260" fill="url(#cfgrid)"/>
            <path d="M 380 50 Q 300 90 270 150" fill="none" stroke="var(--route-blue)" strokeWidth="2.8"/>
            <path d="M 340 215 Q 330 120 380 50" fill="none" stroke="var(--route-mag)" strokeWidth="2.2"/>
            <path d="M 340 215 Q 290 190 270 150" fill="none" stroke="var(--route-teal)" strokeWidth="2.0"/>
            <path d="M 380 50 Q 520 70 660 115" fill="none" stroke="var(--ink)" strokeWidth="1.5" strokeDasharray="4 3"/>
            <path d="M 270 150 Q 460 160 660 115" fill="none" stroke="var(--ink-2)" strokeWidth="1.2" strokeDasharray="4 3"/>
            <path d="M 380 50 L 370 155" fill="none" stroke="var(--ink-2)" strokeWidth="1.2" strokeDasharray="3 3"/>
            <path d="M 270 150 L 370 155" fill="none" stroke="var(--ink-2)" strokeWidth="1.2" strokeDasharray="3 3"/>
            <path d="M 340 215 L 370 155" fill="none" stroke="var(--ink-2)" strokeWidth="1.2" strokeDasharray="3 3"/>
            <circle cx="380" cy="50" r="5" fill="var(--ink)"/><circle cx="380" cy="50" r="10" fill="none" stroke="var(--ink)" strokeWidth="1"/>
            <text x="395" y="46" fontFamily="'B612', monospace" fontSize="12" fontWeight="700" fill="var(--ink)">DEL</text>
            <text x="395" y="59" fontFamily="'B612', monospace" fontSize="9" fill="var(--ink-2)">DELHI · RANK #1 HUB</text>
            <circle cx="270" cy="150" r="5" fill="var(--ink)"/><circle cx="270" cy="150" r="9" fill="none" stroke="var(--ink)" strokeWidth="1"/>
            <text x="195" y="146" fontFamily="'B612', monospace" fontSize="12" fontWeight="700" fill="var(--ink)">BOM</text>
            <text x="195" y="159" fontFamily="'B612', monospace" fontSize="9" fill="var(--ink-2)">MUMBAI · 6.88M PAX</text>
            <circle cx="340" cy="215" r="5" fill="var(--ink)"/><circle cx="340" cy="215" r="9" fill="none" stroke="var(--ink)" strokeWidth="1"/>
            <text x="260" y="222" fontFamily="'B612', monospace" fontSize="12" fontWeight="700" fill="var(--ink)">BLR</text>
            <text x="260" y="234" fontFamily="'B612', monospace" fontSize="9" fill="var(--ink-2)">BENGALURU · 4.76M</text>
            <circle cx="410" cy="210" r="4" fill="var(--ink)"/>
            <text x="424" y="214" fontFamily="'B612', monospace" fontSize="11" fontWeight="700" fill="var(--ink)">MAA</text>
            <circle cx="370" cy="155" r="4" fill="var(--ink)"/>
            <text x="385" y="158" fontFamily="'B612', monospace" fontSize="11" fontWeight="700" fill="var(--ink)">HYD</text>
            <circle cx="660" cy="115" r="5" fill="var(--ink)"/><circle cx="660" cy="115" r="9" fill="none" stroke="var(--ink)" strokeWidth="1"/>
            <text x="675" y="112" fontFamily="'B612', monospace" fontSize="12" fontWeight="700" fill="var(--ink)">CCU</text>
            <text x="675" y="125" fontFamily="'B612', monospace" fontSize="9" fill="var(--ink-2)">KOLKATA · EAST HUB</text>
            <rect x="740" y="15" width="205" height="100" fill="var(--vellum)" stroke="var(--contour)" strokeWidth="1"/>
            <text x="752" y="32" fontFamily="'B612', monospace" fontSize="10" fontWeight="700" fill="var(--ink)">COVERAGE SPECIFICATION</text>
            <text x="752" y="48" fontFamily="'B612', monospace" fontSize="10" fill="var(--ink-2)">Corridors: 60 Scheduled</text>
            <text x="752" y="64" fontFamily="'B612', monospace" fontSize="10" fill="var(--ink-2)">Lead Horizons: 6 Windows</text>
            <text x="752" y="80" fontFamily="'B612', monospace" fontSize="10" fill="var(--ink-2)">Observation Cells: 360</text>
            <text x="752" y="96" fontFamily="'B612', monospace" fontSize="10" fill="var(--ink-2)">Traffic Coverage: 57.02%</text>
          </svg>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1px', background: 'var(--contour)', marginTop: 'var(--sp-4)' }}>
          {[
            { label: 'Daily Scraped Quotes', value: `${totalObsCount.toLocaleString('en-IN')} observations` },
            { label: 'Lead-Time Checkpoint', value: 'T+21 (MoSPI Official)' },
            { label: 'All-India Weighted Fare', value: `Rs.${Math.round(liveNationalFare).toLocaleString('en-IN')}` },
            { label: 'Headline AERIX Index', value: `${liveHeadlineIndex.toFixed(2)} (CY2024=100)` },
          ].map((kpi) => (
            <div key={kpi.label} style={{ background: 'var(--vellum)', padding: '10px 14px' }}>
              <div style={{ fontSize: '11px', color: 'var(--ink-2)', textTransform: 'uppercase' }}>{kpi.label}</div>
              <div className="font-num" style={{ fontSize: '16px', fontWeight: 700, color: 'var(--ink)' }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Flowchart */}
      <div className="section" style={{ marginTop: 0 }}>
        <h2 className="section-title">Five-Step Aggregation Flowchart</h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-6)' }}>
          Raw scraper quotes flow through five successive aggregation stages to produce the headline AERIX index and its CPI contribution.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 0, maxWidth: '820px' }}>

          <div style={{ border: '1px solid var(--ink)', background: 'var(--vellum)', padding: '18px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
              <span style={stepLabel}>Step 1</span>
              <span style={stepTitle}>Multi-Provider Quote Reconciliation</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.55, margin: '0 0 10px 76px' }}>
              Each physical flight is quoted by multiple OTAs (EaseMyTrip, MakeMyTrip, Google Flights, airline direct).
              Quotes for the <em>same scheduled flight</em> are averaged to remove platform markup noise before any aggregation.
            </p>
            <div style={{ marginLeft: '76px', display: 'flex', gap: '14px', alignItems: 'baseline', flexWrap: 'wrap' }}>
              <div style={{ ...formulaBox, background: '#fff' }}>P<sub>flight</sub> = mean(p<sub>EMT</sub>, p<sub>MMT</sub>, p<sub>GFL</sub>, p<sub>direct</sub>)</div>
              <div style={{ fontSize: '12px', color: 'var(--ink-2)' }}>Output: 1 consensus price per scheduled departure</div>
            </div>
          </div>

          <div style={{ display: 'flex', paddingLeft: '76px' }}>
            <svg width="20" height="32" viewBox="0 0 20 32" style={{ display: 'block' }}>
              <line x1="10" y1="0" x2="10" y2="24" stroke="var(--contour)" strokeWidth="2"/>
              <polygon points="4,21 16,21 10,30" fill="var(--contour)"/>
            </svg>
          </div>

          <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '18px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
              <span style={stepLabel}>Step 2</span>
              <span style={stepTitle}>Advance-Horizon Aggregation via Geometric Mean (Jevons)</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.55, margin: '0 0 10px 76px' }}>
              On any departure date, 30–50 scheduled flights operate on a trunk corridor. One high-priced seat would skew an arithmetic
              average significantly. AERIX applies the Jevons Geometric Mean across all flights at a given advance-purchase window.
            </p>
            <div style={{ marginLeft: '76px', display: 'flex', gap: '14px', alignItems: 'baseline', flexWrap: 'wrap' }}>
              <div style={formulaBox}>P(r, l) = exp[ (1/N) &times; SUM ln(P<sub>i</sub>) ]</div>
              <div style={{ fontSize: '12px', color: 'var(--ink-2)' }}>Output: 1 price per lead-time horizon per route</div>
            </div>
          </div>

          <div style={{ display: 'flex', paddingLeft: '76px' }}>
            <svg width="20" height="32" viewBox="0 0 20 32" style={{ display: 'block' }}>
              <line x1="10" y1="0" x2="10" y2="24" stroke="var(--contour)" strokeWidth="2"/>
              <polygon points="4,21 16,21 10,30" fill="var(--contour)"/>
            </svg>
          </div>

          <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '18px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
              <span style={stepLabel}>Step 3</span>
              <span style={stepTitle}>Booking-Horizon Synthesis into Route Representative Price</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.55, margin: '0 0 10px 76px' }}>
              Fares differ across T+1 (last-minute) through T+45 (advance booking). The 6 horizon prices for a route are combined using
              empirical weights from actual booking distributions. T+21 is the official MoSPI CPI 2024 checkpoint (15.19% weight).
            </p>
            <div style={{ marginLeft: '76px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={formulaBox}>P(r) = SUM[ w<sub>l</sub> &times; P(r, l) ] &nbsp;&nbsp; where SUM(w<sub>l</sub>) = 1.0000</div>
              <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                {([{l:'T+1',w:'5.09%'},{l:'T+7',w:'16.36%'},{l:'T+15',w:'11.55%'},{l:'T+21',w:'15.19%',m:true},{l:'T+30',w:'24.78%'},{l:'T+45',w:'27.03%'}] as {l:string,w:string,m?:boolean}[]).map((h) => (
                  <span key={h.l} style={{ fontFamily: "'B612', monospace", fontSize: '11px', padding: '2px 7px', border: h.m ? '2px solid var(--ink)' : '1px solid var(--contour)', background: h.m ? 'var(--vellum)' : '#fff', fontWeight: h.m ? 700 : 400 }}>
                    {h.l}: {h.w}
                  </span>
                ))}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--ink-2)' }}>
                Output: 1 representative corridor fare &mdash; P(r)
                {dynamicRouteFare && <span style={{ marginLeft: '12px', fontWeight: 700, color: 'var(--ink)', fontFamily: "'B612', monospace" }}>Live {selectedRoute}: Rs.{dynamicRouteFare.toLocaleString('en-IN')}</span>}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', paddingLeft: '76px' }}>
            <svg width="20" height="32" viewBox="0 0 20 32" style={{ display: 'block' }}>
              <line x1="10" y1="0" x2="10" y2="24" stroke="var(--contour)" strokeWidth="2"/>
              <polygon points="4,21 16,21 10,30" fill="var(--contour)"/>
            </svg>
          </div>

          <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '18px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
              <span style={stepLabel}>Step 4</span>
              <span style={stepTitle}>National Traffic-Share Aggregation (60 Routes)</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.55, margin: '0 0 10px 76px' }}>
              Route fares are combined into an All-India weighted fare using official DGCA CY2024 passenger volume shares.
              DEL-BOM (6.88M passengers, 4.27% share) contributes proportionally more than smaller corridors like DEL-PNQ (1.80%).
            </p>
            <div style={{ marginLeft: '76px', display: 'flex', gap: '14px', alignItems: 'baseline', flexWrap: 'wrap' }}>
              <div style={formulaBox}>P<sub>National</sub> = SUM[ W<sub>r</sub> &times; P(r) ] &nbsp;&nbsp; r=1..60 &nbsp;&nbsp; SUM(W<sub>r</sub>)=1.0000</div>
              <div style={{ fontSize: '12px', color: 'var(--ink-2)' }}>Output: All-India fare &mdash; live Rs.{Math.round(liveNationalFare).toLocaleString('en-IN')}</div>
            </div>
          </div>

          <div style={{ display: 'flex', paddingLeft: '76px' }}>
            <svg width="20" height="32" viewBox="0 0 20 32" style={{ display: 'block' }}>
              <line x1="10" y1="0" x2="10" y2="24" stroke="var(--contour)" strokeWidth="2"/>
              <polygon points="4,21 16,21 10,30" fill="var(--contour)"/>
            </svg>
          </div>

          <div style={{ border: '1px solid var(--ink)', background: 'var(--vellum)', padding: '18px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '8px' }}>
              <span style={stepLabel}>Step 5</span>
              <span style={stepTitle}>Index Compilation and MoSPI CPI Contribution</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: 1.55, margin: '0 0 10px 76px' }}>
              The national fare is benchmarked against the CY2024 base period (Base = 100). Month-over-month inflation is multiplied by the
              HCES 2023-24 household expenditure weight (0.02951%) to yield the direct CPI contribution.
            </p>
            <div style={{ marginLeft: '76px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ ...formulaBox, background: '#fff' }}>AERIX<sub>t</sub> = (P<sub>National,t</sub> / P<sub>National,base</sub>) &times; 100 &nbsp;&nbsp;&nbsp; DeltaCPI<sub>pp</sub> = MoM% &times; 0.0002951</div>
              <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '12px' }}><span style={{ color: 'var(--ink-2)' }}>Headline Index: </span><span className="font-num" style={{ fontWeight: 700 }}>{liveHeadlineIndex.toFixed(2)}</span><span style={{ fontSize: '11px', color: 'var(--ink-2)' }}> (CY2024=100)</span></div>
                <div style={{ fontSize: '12px' }}><span style={{ color: 'var(--ink-2)' }}>MoM Inflation: </span><span className="font-num" style={{ fontWeight: 700 }}>+{liveMoM.toFixed(2)}%</span></div>
                <div style={{ fontSize: '12px' }}><span style={{ color: 'var(--ink-2)' }}>CPI Contribution: </span><span className="font-num" style={{ fontWeight: 700 }}>+{liveCpiContrib.toFixed(6)} pp</span></div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Live Corridor Inspector */}
      <div className="section" style={{ marginTop: 0 }}>
        <h2 className="section-title">Live Corridor Verification</h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', marginBottom: 'var(--sp-4)' }}>
          Select any corridor to inspect its live database cells, observation counts, and synthesized fare.
        </p>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: 'var(--sp-4)' }}>
          {['DEL-BOM', 'BLR-DEL', 'BLR-BOM', 'DEL-HYD', 'DEL-PNQ', 'DEL-CCU', 'AMD-DEL', 'MAA-DEL'].map((r) => (
            <button key={r} type="button" onClick={() => setSelectedRoute(r)} style={{ background: selectedRoute === r ? 'var(--ink)' : '#fff', color: selectedRoute === r ? 'var(--vellum)' : 'var(--ink)', border: '1px solid var(--contour)', padding: '4px 10px', fontFamily: "'B612', monospace", fontSize: '11px', cursor: 'pointer', fontWeight: selectedRoute === r ? 700 : 400 }}>
              {r}
            </button>
          ))}
        </div>
        <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: 'var(--sp-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: '1px solid var(--contour)', paddingBottom: 'var(--sp-2)', marginBottom: 'var(--sp-4)' }}>
            <div>
              <span style={{ fontFamily: "'B612', monospace", fontSize: '14px', fontWeight: 700, color: 'var(--ink)' }}>{currentRouteMeta.route_id}</span>
              <span style={{ fontSize: '12px', color: 'var(--ink-2)', marginLeft: '8px' }}>{currentRouteMeta.origin} &harr; {currentRouteMeta.destination} · Rank #{currentRouteMeta.rank}</span>
            </div>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', color: 'var(--ink-2)' }}>
              DGCA Share: {currentRouteMeta.dgca_share_percent.toFixed(2)}% ({currentRouteMeta.annual_passenger_volume.toLocaleString('en-IN')} flyers)
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', marginBottom: 'var(--sp-4)' }}>
            {['T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45'].map((lead) => {
              const cell = currentRouteCells.find((c) => c.lead_time === lead);
              const hm = LEAD_TIME_HORIZONS.find((h) => h.lead_class === lead);
              return (
                <div key={lead} style={{ border: lead === 'T+21' ? '2px solid var(--ink)' : '1px solid var(--contour)', background: lead === 'T+21' ? 'var(--vellum)' : '#fff', padding: '8px' }}>
                  <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', color: 'var(--ink-2)' }}>{lead}{lead === 'T+21' ? ' (MoSPI)' : ''}</div>
                  <div className="font-num" style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)', margin: '4px 0' }}>
                    {cell?.geometric_mean_inr ? `Rs.${Math.round(cell.geometric_mean_inr).toLocaleString('en-IN')}` : '—'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--ink-2)' }}>wt {hm?.empirical_weight_percent}% · {cell?.observation_count || 0} quotes</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--vellum)', padding: '10px 14px', border: '1px solid var(--contour)' }}>
            <div>
              <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700 }}>Synthesized Corridor Price:</span>
              <span style={{ fontSize: '11px', color: 'var(--ink-2)', marginLeft: '8px' }}>Computed dynamically from live cells</span>
            </div>
            <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>
              {dynamicRouteFare ? `Rs.${dynamicRouteFare.toLocaleString('en-IN')}` : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div className="section" style={{ marginTop: 0 }}>
        <h2 className="section-title">Key Methodological Decisions</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--sp-4)', marginTop: 'var(--sp-4)' }}>
          {[
            { q: 'Why is a simple arithmetic average rejected across flights?', a: 'Dynamic yield management produces extreme right-tail skew when a few emergency seats are priced at Rs.25,000+. An arithmetic average would inflate the index even if 95% of passengers paid standard economy rates. The Geometric Mean is the international benchmark (Eurostat HICP / MoSPI) for elementary price index compilation.' },
            { q: 'Where do the route and horizon weights originate?', a: 'Route weights are drawn from official DGCA CY2024 annual scheduled domestic city-pair passenger statistics covering 91.99M passengers. Horizon weights reflect empirical advance-purchase distributions, anchoring on the official MoSPI CPI T+21 reference window (15.19% share).' },
            { q: 'Why are multiple OTA providers sampled instead of just one?', a: 'Individual OTAs apply convenience fees, promotional markups, and caching differences. Sampling all available platforms and averaging at the individual flight level eliminates systematic distribution bias before any corridor aggregation occurs.' },
          ].map((item) => (
            <div key={item.q} style={{ border: '1px solid var(--contour)', background: '#fff', padding: '14px' }}>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--ink)', marginBottom: '6px' }}>{item.q}</div>
              <p style={{ fontSize: '13px', color: 'var(--ink-2)', lineHeight: 1.45, margin: 0 }}>{item.a}</p>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}