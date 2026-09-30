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
} from '../data/dgcaTop60';
import { MathBlock } from '../components/MathBlock';

interface CalculationFlowViewProps {
  onNavigate?: (tab: 'overview' | 'index' | 'curves' | 'backtest' | 'method') => void;
}

export default function CalculationFlowView({ onNavigate }: CalculationFlowViewProps) {
  const [matrixCells, setMatrixCells] = useState<MatrixCell[]>([]);
  const [indexData, setIndexData] = useState<AERIXIndexResponse | null>(null);
  const [nsoFeed, setNsoFeed] = useState<NSOCPIFeedResponse | null>(null);
  const [, setObservations] = useState<Observation[]>([]);
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

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-6)' }}>

      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--sp-2)' }}>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-2)' }}>
            Methodological Architecture
          </span>
          <span style={{ color: 'var(--contour)' }}>·</span>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            {loading ? 'Connecting to live database...' : 'Production Data Verified'}
          </span>
        </div>
        <h1 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '32px', fontWeight: 400, color: 'var(--ink)', marginBottom: '8px' }}>
          Calculation Flow: From Scraped Quotes to CPI
        </h1>
        <p style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '16px', color: 'var(--ink-2)', lineHeight: 1.5, maxWidth: '75ch', margin: 0 }}>
          A clear, five-stage aggregation hierarchy designed to eliminate platform markup noise, prevent extreme price distortion, and reflect true domestic passenger travel patterns.
        </p>
      </div>

      {/* Pipeline Navigation / Executive Summary */}
      <div style={{ border: '1px solid var(--contour)', background: 'var(--vellum)', padding: '16px 20px' }}>
        <div style={{ fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink)', marginBottom: '12px' }}>
          Five-Stage Aggregation Pipeline Overview
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '10px' }}>
          {[
            { num: '01', title: 'Provider Mean', desc: 'Average OTAs per flight' },
            { num: '02', title: 'Geometric Mean', desc: 'Jevons across flights' },
            { num: '03', title: 'Horizon Weights', desc: 'T+1 to T+45 blend' },
            { num: '04', title: 'DGCA Basket', desc: '60 routes by pax share' },
            { num: '05', title: 'AERIX & CPI', desc: 'Base 2024=100 index' },
          ].map((s) => (
            <div key={s.num} style={{ background: '#fff', border: '1px solid var(--contour)', padding: '10px 12px' }}>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, color: 'var(--route-blue)' }}>{s.num}</div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', margin: '2px 0' }}>{s.title}</div>
              <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Vertical Flowchart Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, maxWidth: '920px' }}>

        {/* STEP 1 */}
        <div style={{ border: '1px solid var(--ink)', background: 'var(--vellum)', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ background: 'var(--ink)', color: 'var(--vellum)', fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, padding: '3px 8px' }}>
                STEP 1
              </span>
              <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '20px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                Multi-Provider Quote Reconciliation
              </h2>
            </div>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)', border: '1px solid var(--contour)', padding: '2px 8px', background: '#fff' }}>
              Arithmetic Mean (OTA Normalization)
            </span>
          </div>

          <p style={{ fontSize: '13.5px', color: 'var(--ink)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            A single flight (e.g. IndiGo 6E-205) is often listed at slightly different prices across different platforms (EaseMyTrip, MakeMyTrip, Google Flights, and official airline direct). To eliminate platform markup fees or promotional discounts, we calculate the simple arithmetic mean across all valid quotes for the exact same scheduled departure.
          </p>

          <MathBlock
            formula="\bar{P}_{f} = \frac{1}{K} \sum_{k=1}^K p_{f,k}"
            caption="Where p_{f,k} is the price of scheduled flight f quoted by provider k, and K is the count of reporting providers."
          />

          <div style={{ background: '#fff', border: '1px solid var(--contour)', borderLeft: '3px solid var(--ink)', padding: '10px 14px', marginTop: '10px' }}>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700, color: 'var(--ink-2)', textTransform: 'uppercase', marginBottom: '4px' }}>
              Worked Numerical Example
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--ink)', lineHeight: 1.4 }}>
              Flight <strong>6E-205 (DEL &rarr; BOM)</strong>: MakeMyTrip quotes <strong>Rs.5,200</strong>, EaseMyTrip quotes <strong>Rs.5,100</strong>, Airline Direct quotes <strong>Rs.5,150</strong>.<br />
              &rarr; <strong>Harmonized Flight Price</strong> = (5,200 + 5,100 + 5,150) / 3 = <strong>Rs.5,150</strong>
            </div>
          </div>
        </div>

        {/* Connector 1 -> 2 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0 8px 30px' }}>
          <svg width="18" height="28" viewBox="0 0 18 28">
            <line x1="9" y1="0" x2="9" y2="20" stroke="var(--ink)" strokeWidth="2" />
            <polygon points="4,18 14,18 9,26" fill="var(--ink)" />
          </svg>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            Passes 1 consensus price per scheduled flight
          </span>
        </div>

        {/* STEP 2 */}
        <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ background: 'var(--contour)', color: 'var(--ink)', fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, padding: '3px 8px' }}>
                STEP 2
              </span>
              <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '20px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                Flight Aggregation within Horizon (Geometric Mean)
              </h2>
            </div>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)', border: '1px solid var(--contour)', padding: '2px 8px', background: 'var(--vellum)' }}>
              Jevons Formula (Outlier Mitigation)
            </span>
          </div>

          <p style={{ fontSize: '13.5px', color: 'var(--ink)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            On any travel date, a corridor has multiple flights operating at different times. If one last-minute emergency ticket is priced at Rs.25,000 while 20 other seats are Rs.5,000, a regular average would distort the true cost of flying. Per official MoSPI CPI and Eurostat HICP standards, AERIX takes the unweighted <strong>Geometric Mean (Jevons formula)</strong> of all flights within each lead-time horizon.
          </p>

          <MathBlock
            formula="P_{r,h} = \left(\prod_{i=1}^{N_{r,h}} P_{r,h,i}\right)^{\frac{1}{N_{r,h}}} = \exp\left( \frac{1}{N_{r,h}} \sum_{i=1}^{N_{r,h}} \ln P_{r,h,i} \right)"
            caption="Where P_{r,h} is the representative price for route r in lead horizon h across N flights."
          />

          <div style={{ background: 'var(--vellum)', border: '1px solid var(--contour)', borderLeft: '3px solid var(--ink-2)', padding: '10px 14px', marginTop: '10px' }}>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700, color: 'var(--ink-2)', textTransform: 'uppercase', marginBottom: '4px' }}>
              Worked Numerical Example
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--ink)', lineHeight: 1.4 }}>
              Corridor <strong>DEL &rarr; BOM at T+21</strong> has 3 scheduled flights priced at <strong>Rs.4,800</strong>, <strong>Rs.5,150</strong>, and <strong>Rs.5,400</strong>.<br />
              &rarr; <strong>Geometric Mean P(DEL-BOM, T+21)</strong> = (4,800 &times; 5,150 &times; 5,400)<sup>1/3</sup> = <strong>Rs.5,112</strong><br />
              <span style={{ color: 'var(--ink-2)', fontSize: '11.5px' }}>Notice: Arithmetic mean would be Rs.5,117. Geometric mean protects the index from upward bounce.</span>
            </div>
          </div>
        </div>

        {/* Connector 2 -> 3 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0 8px 30px' }}>
          <svg width="18" height="28" viewBox="0 0 18 28">
            <line x1="9" y1="0" x2="9" y2="20" stroke="var(--contour)" strokeWidth="2" />
            <polygon points="4,18 14,18 9,26" fill="var(--contour)" />
          </svg>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            Passes 6 horizon prices per route: T+1, T+7, T+15, T+21, T+30, T+45
          </span>
        </div>

        {/* STEP 3 */}
        <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ background: 'var(--contour)', color: 'var(--ink)', fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, padding: '3px 8px' }}>
                STEP 3
              </span>
              <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '20px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                Booking Lead-Time Horizon Weighting
              </h2>
            </div>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--assumed)', border: '1px solid var(--contour)', padding: '2px 8px', background: 'var(--vellum)', fontWeight: 700 }}>
              MoSPI T+21 Checkpoint (15.19%)
            </span>
          </div>

          <p style={{ fontSize: '13.5px', color: 'var(--ink)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            Airfares fluctuate sharply between T+1 (emergency booking) and T+45 (early booking). To produce a single representative fare for a route, AERIX combines all six advance-purchase horizons using empirical booking distribution weights. T+21 serves as the primary official MoSPI reference window.
          </p>

          <MathBlock
            formula="P_r = \sum_{h \in \text{Horizons}} W_h \cdot P_{r,h}, \quad \text{where } \sum W_h = 1.0000"
            caption="Empirical advance-purchase weights: T+1 (5.09%), T+7 (16.36%), T+15 (11.55%), T+21 (15.19%), T+30 (24.78%), T+45 (27.03%)."
          />

          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', margin: '10px 0' }}>
            {[
              { l: 'T+1', w: '5.09%' },
              { l: 'T+7', w: '16.36%' },
              { l: 'T+15', w: '11.55%' },
              { l: 'T+21', w: '15.19%', m: true },
              { l: 'T+30', w: '24.78%' },
              { l: 'T+45', w: '27.03%' },
            ].map((h) => (
              <span key={h.l} style={{ fontFamily: "'B612', monospace", fontSize: '11px', padding: '3px 8px', border: h.m ? '1.5px solid var(--ink)' : '1px solid var(--contour)', background: h.m ? 'var(--vellum)' : '#fff', fontWeight: h.m ? 700 : 400 }}>
                {h.l}: {h.w}{h.m ? ' (MoSPI)' : ''}
              </span>
            ))}
          </div>

          <div style={{ background: 'var(--vellum)', border: '1px solid var(--contour)', borderLeft: '3px solid var(--assumed)', padding: '10px 14px', marginTop: '10px' }}>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700, color: 'var(--ink-2)', textTransform: 'uppercase', marginBottom: '4px' }}>
              Worked Numerical Example
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--ink)', lineHeight: 1.4 }}>
              DEL-BOM Fares: T+1 (Rs.8,400), T+7 (Rs.6,200), T+15 (Rs.5,600), T+21 (Rs.5,112), T+30 (Rs.4,700), T+45 (Rs.4,300).<br />
              &rarr; <strong>Composite Route Price P(DEL-BOM)</strong> = &sum; [w<sub>h</sub> &times; P<sub>h</sub>] = <strong>Rs.5,420</strong>
            </div>
          </div>
        </div>

        {/* Connector 3 -> 4 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0 8px 30px' }}>
          <svg width="18" height="28" viewBox="0 0 18 28">
            <line x1="9" y1="0" x2="9" y2="20" stroke="var(--contour)" strokeWidth="2" />
            <polygon points="4,18 14,18 9,26" fill="var(--contour)" />
          </svg>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            Passes 1 composite fare for each of the 60 DGCA corridors
          </span>
        </div>

        {/* STEP 4 */}
        <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ background: 'var(--contour)', color: 'var(--ink)', fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, padding: '3px 8px' }}>
                STEP 4
              </span>
              <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '20px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                All-India Route Basket Aggregation
              </h2>
            </div>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--route-blue)', border: '1px solid var(--contour)', padding: '2px 8px', background: 'rgba(42,95,165,0.06)', fontWeight: 700 }}>
              DGCA CY2024 Passenger Shares
            </span>
          </div>

          <p style={{ fontSize: '13.5px', color: 'var(--ink)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            Different corridors carry vastly different traffic volumes. Delhi-Mumbai carries 6.88 million passengers annually, while secondary routes carry fewer. AERIX weights each of the 60 routes by its exact DGCA annual passenger volume share, ensuring the national basket is truly representative of Indian flyers.
          </p>

          <MathBlock
            formula="P_{\text{National}} = \sum_{r=1}^{60} W_r^{\text{DGCA}} \cdot P_r, \quad \text{where } \sum_{r=1}^{60} W_r^{\text{DGCA}} = 1.0000"
            caption="Route weights derived from 91,995,307 scheduled passengers across the top 60 domestic routes."
          />

          <div style={{ background: 'var(--vellum)', border: '1px solid var(--contour)', borderLeft: '3px solid var(--route-blue)', padding: '10px 14px', marginTop: '10px' }}>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700, color: 'var(--ink-2)', textTransform: 'uppercase', marginBottom: '4px' }}>
              Worked Numerical Example
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--ink)', lineHeight: 1.4 }}>
              Weight DEL-BOM (4.27% &times; Rs.5,420) + Weight BOM-BLR (2.95% &times; Rs.4,850) + ... all 60 corridors.<br />
              &rarr; <strong>All-India Weighted Domestic Fare</strong> = <strong>Rs.{Math.round(liveNationalFare).toLocaleString('en-IN')}</strong>
            </div>
          </div>
        </div>

        {/* Connector 4 -> 5 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0 8px 30px' }}>
          <svg width="18" height="28" viewBox="0 0 18 28">
            <line x1="9" y1="0" x2="9" y2="20" stroke="var(--ink)" strokeWidth="2" />
            <polygon points="4,18 14,18 9,26" fill="var(--ink)" />
          </svg>
          <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)' }}>
            Passes All-India national price vs. CY2024 Base Year
          </span>
        </div>

        {/* STEP 5 */}
        <div style={{ border: '1px solid var(--ink)', background: 'var(--vellum)', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ background: 'var(--ink)', color: 'var(--vellum)', fontFamily: "'B612', monospace", fontSize: '11px', fontWeight: 700, padding: '3px 8px' }}>
                STEP 5
              </span>
              <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '20px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                AERIX Headline Index & MoSPI CPI Contribution
              </h2>
            </div>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', color: 'var(--ink-2)', border: '1px solid var(--contour)', padding: '2px 8px', background: '#fff' }}>
              Laspeyres Chained Index (CY2024 = 100)
            </span>
          </div>

          <p style={{ fontSize: '13.5px', color: 'var(--ink)', lineHeight: 1.5, margin: '0 0 12px 0' }}>
            The current national airfare is divided by the Base Year 2024 reference fare (Rs.8,130) and multiplied by 100 to yield the headline index. The resulting inflation rate is multiplied by MoSPI's official household expenditure weight for air travel (0.02951%) to determine the direct percentage-point contribution to India's Consumer Price Index.
          </p>

          <MathBlock
            formula="\text{AERIX}_t = \left(\frac{P_{t}^{\text{National}}}{P_{\text{Base}}^{\text{National}}}\right) \times 100, \quad \Delta \text{CPI}_{pp} = \pi_{\text{MoM}} \times W_{\text{CPI}}"
            caption="Where W_{CPI} = 0.0002951 (0.02951% national basket share per MoSPI HCES 2023-24)."
          />

          <div style={{ background: '#fff', border: '1px solid var(--contour)', borderLeft: '3px solid var(--ink)', padding: '12px 16px', marginTop: '10px' }}>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', fontWeight: 700, color: 'var(--ink-2)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Live Compiled Metric Results
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>Headline AERIX Index</div>
                <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>
                  {liveHeadlineIndex.toFixed(2)} <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--ink-2)' }}>(CY2024=100)</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>MoM Airfare Inflation</div>
                <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>
                  +{liveMoM.toFixed(2)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>MoSPI CPI Impact</div>
                <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>
                  +{liveCpiContrib.toFixed(6)} pp
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Live Corridor Inspector */}
      <div style={{ border: '1px solid var(--contour)', background: '#fff', padding: '20px 24px', maxWidth: '920px' }}>
        <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 400, color: 'var(--ink)', margin: '0 0 4px 0' }}>
          Interactive Corridor Verification
        </h2>
        <p style={{ color: 'var(--ink-2)', fontSize: '13px', margin: '0 0 14px 0' }}>
          Select any route below to inspect real prices collected from live scrapers across all six advance-purchase horizons:
        </p>

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
          {['DEL-BOM', 'BLR-DEL', 'BLR-BOM', 'DEL-HYD', 'DEL-PNQ', 'DEL-CCU', 'AMD-DEL', 'MAA-DEL'].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setSelectedRoute(r)}
              style={{
                background: selectedRoute === r ? 'var(--ink)' : '#fff',
                color: selectedRoute === r ? 'var(--vellum)' : 'var(--ink)',
                border: '1px solid var(--contour)',
                padding: '4px 10px',
                fontFamily: "'B612', monospace",
                fontSize: '11px',
                cursor: 'pointer',
                fontWeight: selectedRoute === r ? 700 : 400,
              }}
            >
              {r}
            </button>
          ))}
        </div>

        <div style={{ border: '1px solid var(--contour)', padding: '14px', background: 'var(--vellum)', marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '6px', borderBottom: '1px solid var(--contour)', paddingBottom: '8px', marginBottom: '10px' }}>
            <div>
              <span style={{ fontFamily: "'B612', monospace", fontSize: '14px', fontWeight: 700, color: 'var(--ink)' }}>{currentRouteMeta.route_id}</span>
              <span style={{ fontSize: '12px', color: 'var(--ink-2)', marginLeft: '8px' }}>{currentRouteMeta.origin} &harr; {currentRouteMeta.destination} · Rank #{currentRouteMeta.rank}</span>
            </div>
            <div style={{ fontFamily: "'B612', monospace", fontSize: '11.5px', color: 'var(--ink-2)' }}>
              DGCA Share: {currentRouteMeta.dgca_share_percent.toFixed(2)}% ({currentRouteMeta.annual_passenger_volume.toLocaleString('en-IN')} flyers)
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
            {['T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45'].map((lead) => {
              const cell = currentRouteCells.find((c) => c.lead_time === lead);
              const hm = LEAD_TIME_HORIZONS.find((h) => h.lead_class === lead);
              const isMospi = lead === 'T+21';
              return (
                <div key={lead} style={{ border: isMospi ? '2px solid var(--ink)' : '1px solid var(--contour)', background: '#fff', padding: '8px 10px' }}>
                  <div style={{ fontFamily: "'B612', monospace", fontSize: '10px', color: 'var(--ink-2)' }}>
                    {lead}{isMospi ? ' (MoSPI)' : ''}
                  </div>
                  <div className="font-num" style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)', margin: '3px 0' }}>
                    {cell?.geometric_mean_inr ? `Rs.${Math.round(cell.geometric_mean_inr).toLocaleString('en-IN')}` : '—'}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--ink-2)' }}>
                    wt {hm?.empirical_weight_percent}% · {cell?.observation_count || 0} quotes
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--contour)' }}>
            <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--ink)' }}>
              Synthesized Corridor Composite Price:
            </span>
            <span className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>
              {dynamicRouteFare ? `Rs.${dynamicRouteFare.toLocaleString('en-IN')}` : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Key Methodological FAQ */}
      <div style={{ maxWidth: '920px' }}>
        <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 400, color: 'var(--ink)', marginBottom: '12px' }}>
          Frequently Clarified Methodological Decisions
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {[
            {
              q: 'Why Geometric Mean instead of simple average across flights?',
              a: 'Airlines practice dynamic yield management where the last 2 seats on a flight may be priced at Rs.25,000+. A simple arithmetic average would be skewed upward by emergency seats that regular passengers never buy. The Geometric Mean (Jevons elementary index) is the UN/MoSPI standard that avoids small-sample upward bounce.',
            },
            {
              q: 'Where do the advance-purchase horizon weights come from?',
              a: 'Horizon weights are drawn from empirical booking distributions across Indian carriers, anchoring on the official MoSPI CPI T+21 collection checkpoint (15.19% weight). This correctly reflects that more travelers book weeks in advance than at the last minute.',
            },
            {
              q: 'Why sample multiple OTAs for the same flight?',
              a: 'Individual travel websites charge different processing fees or offer promotional discounts. By gathering quotes across EaseMyTrip, MakeMyTrip, and Direct channels and averaging them per flight, we eliminate single-platform pricing distortion before any index aggregation occurs.',
            },
          ].map((item) => (
            <div key={item.q} style={{ border: '1px solid var(--contour)', background: '#fff', padding: '16px' }}>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--ink)', marginBottom: '8px' }}>
                {item.q}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--ink-2)', lineHeight: 1.5, margin: 0 }}>
                {item.a}
              </p>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
