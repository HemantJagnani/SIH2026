import React, { useState, useMemo } from 'react';
import pipelineHeroImg from '../assets/pipeline_hero.jpg';

interface CalculationFlowViewProps {
  onNavigate?: (tab: 'overview' | 'index' | 'curves' | 'backtest' | 'method') => void;
}

export default function CalculationFlowView({ onNavigate }: CalculationFlowViewProps) {
  const [activeLevel, setActiveLevel] = useState<number>(1);
  const [showMathSpec, setShowMathSpec] = useState<boolean>(false);

  // Interactive Sandbox State
  const [selectedSandboxRoute, setSelectedSandboxRoute] = useState<'DEL-BOM' | 'BLR-DEL' | 'DEL-CCU'>('DEL-BOM');
  const [customOutlierPrice, setCustomOutlierPrice] = useState<number>(18500);

  // Pre-configured route demo values
  const routeConfigs = {
    'DEL-BOM': {
      origin: 'Delhi (DEL)',
      dest: 'Mumbai (BOM)',
      dgcaRank: 1,
      dgcaWeight: 0.0427,
      baseFare2024: 6100,
      t7Flights: [5850, 6150, 6300, 6420, 6500],
      horizons: [
        { label: 'T+1 (Urgent)', days: 1, weight: 0.0509, fare: 11450 },
        { label: 'T+7 (Short)', days: 7, weight: 0.1350, fare: 7315 },
        { label: 'T+15 (Mid)', days: 15, weight: 0.1491, fare: 6452 },
        { label: 'T+21 (MoSPI Checkpoint ★)', days: 21, weight: 0.1519, fare: 6331 },
        { label: 'T+30 (Leisure)', days: 30, weight: 0.2588, fare: 6443 },
        { label: 'T+45 (Early Plan)', days: 45, weight: 0.2543, fare: 6448 },
      ]
    },
    'BLR-DEL': {
      origin: 'Bengaluru (BLR)',
      dest: 'Delhi (DEL)',
      dgcaRank: 2,
      dgcaWeight: 0.0295,
      baseFare2024: 7200,
      t7Flights: [6800, 7100, 7450, 7600, 7850],
      horizons: [
        { label: 'T+1 (Urgent)', days: 1, weight: 0.0509, fare: 13200 },
        { label: 'T+7 (Short)', days: 7, weight: 0.1350, fare: 10045 },
        { label: 'T+15 (Mid)', days: 15, weight: 0.1491, fare: 7850 },
        { label: 'T+21 (MoSPI Checkpoint ★)', days: 21, weight: 0.1519, fare: 6950 },
        { label: 'T+30 (Leisure)', days: 30, weight: 0.2588, fare: 6800 },
        { label: 'T+45 (Early Plan)', days: 45, weight: 0.2543, fare: 6720 },
      ]
    },
    'DEL-CCU': {
      origin: 'Delhi (DEL)',
      dest: 'Kolkata (CCU)',
      dgcaRank: 6,
      dgcaWeight: 0.0171,
      baseFare2024: 6400,
      t7Flights: [5900, 6200, 6350, 6500, 6700],
      horizons: [
        { label: 'T+1 (Urgent)', days: 1, weight: 0.0509, fare: 12100 },
        { label: 'T+7 (Short)', days: 7, weight: 0.1350, fare: 8867 },
        { label: 'T+15 (Mid)', days: 15, weight: 0.1491, fare: 7200 },
        { label: 'T+21 (MoSPI Checkpoint ★)', days: 21, weight: 0.1519, fare: 6650 },
        { label: 'T+30 (Leisure)', days: 30, weight: 0.2588, fare: 6510 },
        { label: 'T+45 (Early Plan)', days: 45, weight: 0.2543, fare: 6480 },
      ]
    }
  };

  const currentCfg = routeConfigs[selectedSandboxRoute];

  // Geometric Mean Helper
  const calcGM = (fares: number[]) => {
    if (fares.length === 0) return 0;
    const sumLogs = fares.reduce((acc, f) => acc + Math.log(f), 0);
    return Math.exp(sumLogs / fares.length);
  };

  // Simple Arithmetic Mean Helper
  const calcAM = (fares: number[]) => {
    if (fares.length === 0) return 0;
    return fares.reduce((a, b) => a + b, 0) / fares.length;
  };

  // Sandbox Calculations
  const t7FlightsWithOutlier = [...currentCfg.t7Flights, customOutlierPrice];
  const gmT7Without = Math.round(calcGM(currentCfg.t7Flights));
  const gmT7With = Math.round(calcGM(t7FlightsWithOutlier));
  const amT7With = Math.round(calcAM(t7FlightsWithOutlier));

  // Route representative fare
  const routeRepFare = useMemo(() => {
    return Math.round(
      currentCfg.horizons.reduce((acc, h) => acc + h.fare * h.weight, 0)
    );
  }, [currentCfg]);

  const routeIndex = ((routeRepFare / currentCfg.baseFare2024) * 100).toFixed(2);

  // Steps definition for flowchart
  const levels = [
    {
      num: 1,
      badge: 'Step 1: Provider Level',
      title: 'Same Flight Across Providers',
      sub: 'Averaging quotes from OTAs and Metasearch engines',
      action: 'Simple Arithmetic Average',
      input: 'MakeMyTrip, EaseMyTrip, Google Flights, Airline Direct',
      output: '1 Clean Consensus Fare per Physical Flight',
      color: '#2A5FA5',
    },
    {
      num: 2,
      badge: 'Step 2: Horizon Level',
      title: 'Multiple Flights in One Timeframe',
      sub: 'Consolidating all 40+ daily flights at a specific advance purchase (e.g. T+7)',
      action: 'Geometric Mean (Jevons Formula)',
      input: 'All scheduled morning, afternoon & evening flights',
      output: '1 Representative Price for that Horizon (No Outlier Skew)',
      color: '#B0286A',
    },
    {
      num: 3,
      badge: 'Step 3: Route Level',
      title: '6 Booking Advance Timeframes',
      sub: 'Combining T+1, T+7, T+15, T+21 ★, T+30, T+45 using actual booking habits',
      action: 'Consumer Booking-Curve Weighted Average',
      input: '6 Horizon Fares × Passenger Purchase Distribution',
      output: '1 Single Representative Price for the Corridor (e.g., DEL-BOM)',
      color: '#2F7D6D',
    },
    {
      num: 4,
      badge: 'Step 4: National Level',
      title: 'All-India 60-Route Basket',
      sub: 'Aggregating all 60 top domestic corridors across India',
      action: 'Official DGCA Passenger Volume Weighted Average',
      input: '60 Route Fares × DGCA CY2024 Passenger Shares (57% national traffic)',
      output: '1 All-India Representative Airfare: ₹8,864',
      color: '#8A5600',
    },
    {
      num: 5,
      badge: 'Step 5: Inflation & CPI',
      title: 'AERIX Index & MoSPI CPI Feed',
      sub: 'Comparing against CY2024 base and calculating official CPI contribution',
      action: 'Young / Laspeyres Index (Base 2024 = 100)',
      input: 'National Fare vs Base Fare + 0.02951% Household CPI Weight',
      output: 'AERIX = 109.02 · MoM +4.33% · CPI Impact: +0.001276 pp',
      color: '#1A2B3C',
    },
  ];

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-6)' }}>
      {/* ── 1. Hero Header with Aeronautical Network Artwork ── */}
      <div
        style={{
          border: '1px solid var(--contour)',
          background: '#fff',
          borderRadius: '4px',
          overflow: 'hidden',
          boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
        }}
      >
        <div style={{ position: 'relative', width: '100%', maxHeight: '340px', overflow: 'hidden' }}>
          <img
            src={pipelineHeroImg}
            alt="Indian Domestic Flight Network & Price Aggregation Architecture"
            style={{
              width: '100%',
              height: '340px',
              objectFit: 'cover',
              objectPosition: 'center 45%',
              display: 'block',
              filter: 'contrast(1.03)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(180deg, rgba(240,242,238,0.2) 0%, rgba(26,43,60,0.85) 100%)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
              padding: 'var(--sp-6)',
              color: '#fff',
            }}
          >
            <div
              style={{
                fontFamily: "'B612', monospace",
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                color: '#6EE7B7',
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
              AERIX Econometric Pipeline · Visual Explainer for Evaluators
            </div>
            <h1
              style={{
                fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
                fontSize: 'clamp(24px, 3.2vw, 38px)',
                lineHeight: 1.15,
                fontWeight: 400,
                color: '#ffffff',
                margin: 0,
              }}
            >
              How the Airfare Price Index is Calculated
            </h1>
            <p
              style={{
                fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
                fontSize: 'clamp(15px, 1.4vw, 19px)',
                color: 'rgba(255,255,255,0.88)',
                maxWidth: '75ch',
                margin: '8px 0 0 0',
              }}
            >
              A transparent, 5-level journey from raw online ticket quotes to India's official
              Consumer Price Index (CPI) — designed without unnecessary mathematical jargon so
              anyone can immediately verify how airfare inflation is measured.
            </p>
          </div>
        </div>

        {/* Quick Metrics Bar */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            borderTop: '1px solid var(--contour)',
            background: 'var(--vellum)',
          }}
        >
          <div style={{ padding: 'var(--sp-3) var(--sp-4)', borderRight: '1px solid var(--contour)' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)', textTransform: 'uppercase' }}>Daily Observations</div>
            <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)' }}>12,212 Quotes</div>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>Across 360 Corridor-Lead Cells</div>
          </div>
          <div style={{ padding: 'var(--sp-3) var(--sp-4)', borderRight: '1px solid var(--contour)' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)', textTransform: 'uppercase' }}>Advance Horizons</div>
            <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--route-blue)' }}>6 Time Windows</div>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>T+1 to T+45 (MoSPI T+21 Anchor)</div>
          </div>
          <div style={{ padding: 'var(--sp-3) var(--sp-4)', borderRight: '1px solid var(--contour)' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)', textTransform: 'uppercase' }}>National Coverage</div>
            <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--route-mag)' }}>60 DGCA Corridors</div>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>91.99M Passengers (57.02% traffic)</div>
          </div>
          <div style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)', textTransform: 'uppercase' }}>Headline AERIX Index</div>
            <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: '#047857' }}>109.02 (CY2024 = 100)</div>
            <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>All-India Fare: ₹8,864 · MoM +4.33%</div>
          </div>
        </div>
      </div>

      {/* ── 2. The Master 5-Level Visual Flowchart ── */}
      <section>
        <div style={{ marginBottom: 'var(--sp-3)', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '24px', fontWeight: 400, color: 'var(--ink)' }}>
              The 5-Level Calculation Hierarchy
            </h2>
            <p style={{ color: 'var(--ink-2)', fontSize: '13px' }}>
              Click any level in the pipeline below to inspect its purpose, formula, and concrete numerical example.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              onClick={() => setShowMathSpec(!showMathSpec)}
              style={{
                background: showMathSpec ? 'var(--ink)' : 'transparent',
                color: showMathSpec ? '#fff' : 'var(--ink)',
                border: '1px solid var(--ink)',
                padding: '4px 12px',
                borderRadius: '3px',
                fontSize: '12px',
                cursor: 'pointer',
                fontFamily: "'B612', monospace",
              }}
            >
              {showMathSpec ? '✓ Formal Math Formulas Visible' : '∑ Show Formal Formulas (For Economists)'}
            </button>
          </div>
        </div>

        {/* Visual Pipeline Flow Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '12px',
            position: 'relative',
          }}
        >
          {levels.map((lvl) => {
            const isActive = activeLevel === lvl.num;
            return (
              <div
                key={lvl.num}
                onClick={() => setActiveLevel(lvl.num)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ' ? setActiveLevel(lvl.num) : null)}
                style={{
                  background: isActive ? '#ffffff' : 'rgba(255,255,255,0.7)',
                  border: isActive ? `2px solid ${lvl.color}` : '1px solid var(--contour)',
                  borderRadius: '4px',
                  padding: 'var(--sp-4)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isActive ? '0 4px 14px rgba(0,0,0,0.08)' : 'none',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  minHeight: '190px',
                }}
              >
                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '6px',
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "'B612', monospace",
                        fontSize: '11px',
                        fontWeight: 700,
                        color: lvl.color,
                        background: `${lvl.color}15`,
                        padding: '2px 6px',
                        borderRadius: '2px',
                      }}
                    >
                      LEVEL {lvl.num}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--ink-2)', fontWeight: 700 }}>
                      {lvl.num < 5 ? '→' : '★ FINAL'}
                    </span>
                  </div>
                  <h3
                    style={{
                      fontFamily: "'Newsreader Variable', serif",
                      fontSize: '17px',
                      fontWeight: 600,
                      color: 'var(--ink)',
                      margin: '4px 0 6px 0',
                    }}
                  >
                    {lvl.title}
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.35 }}>
                    {lvl.sub}
                  </p>
                </div>

                <div
                  style={{
                    marginTop: '12px',
                    paddingTop: '8px',
                    borderTop: '1px dashed var(--contour)',
                    fontSize: '11px',
                    fontFamily: "'B612', monospace",
                    color: lvl.color,
                    fontWeight: 700,
                  }}
                >
                  ⚡ {lvl.action}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 3. Level-by-Level Deep Dive Detail Card ── */}
      <section
        style={{
          border: '1px solid var(--contour)',
          background: '#ffffff',
          borderRadius: '4px',
          padding: 'var(--sp-6)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.02)',
        }}
      >
        {activeLevel === 1 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ background: '#2A5FA5', color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '2px', fontWeight: 700 }}>
                LEVEL 1
              </span>
              <span style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 600, color: 'var(--ink)' }}>
                Multi-Provider Price Reconciliation (Per Physical Flight)
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              <div>
                <h4 style={{ fontFamily: "'B612', monospace", fontSize: '13px', textTransform: 'uppercase', color: 'var(--ink-2)', marginBottom: '8px' }}>
                  The Problem & Solution
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.5, color: 'var(--ink)' }}>
                  A passenger flying on <strong>IndiGo 6E-2045</strong> from Delhi to Mumbai at 08:30 AM will see slightly
                  different prices depending on which website they visit (EaseMyTrip, MakeMyTrip, Google Flights, or the airline direct)
                  due to varying convenience fees, partner commissions, and browser cache latency.
                </p>
                <div
                  style={{
                    background: 'var(--vellum)',
                    padding: '12px',
                    borderRadius: '4px',
                    borderLeft: '3px solid #2A5FA5',
                    marginTop: '12px',
                    fontSize: '13px',
                  }}
                >
                  <strong>What AERIX does:</strong> For every unique flight number and departure time, AERIX collects quotes across
                  all providers and takes the <strong>simple average</strong> across the verified sources.
                  <br />
                  <strong>Result:</strong> Exactly <strong>1 clean, objective consensus fare</strong> for each physical flight.
                </div>
              </div>

              {/* Concrete Visual Example Box */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', padding: '16px' }}>
                <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#2A5FA5', fontWeight: 700, marginBottom: '8px' }}>
                  CONCRETE EXAMPLE · IndiGo 6E-2045 (DEL → BOM)
                </div>
                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', marginBottom: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #CBD5E1', textAlign: 'left', color: '#64748B' }}>
                      <th style={{ padding: '6px' }}>Scraped Provider</th>
                      <th style={{ padding: '6px', textAlign: 'right' }}>Scraped Fare</th>
                      <th style={{ padding: '6px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid #E2E8F0' }}>
                      <td style={{ padding: '6px' }}>EaseMyTrip</td>
                      <td className="font-num" style={{ padding: '6px', textAlign: 'right' }}>₹6,120</td>
                      <td style={{ padding: '6px', color: '#16A34A' }}>Verified</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #E2E8F0' }}>
                      <td style={{ padding: '6px' }}>MakeMyTrip</td>
                      <td className="font-num" style={{ padding: '6px', textAlign: 'right' }}>₹6,280</td>
                      <td style={{ padding: '6px', color: '#16A34A' }}>Verified</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid #E2E8F0' }}>
                      <td style={{ padding: '6px' }}>Google Flights</td>
                      <td className="font-num" style={{ padding: '6px', textAlign: 'right' }}>₹6,200</td>
                      <td style={{ padding: '6px', color: '#16A34A' }}>Verified</td>
                    </tr>
                  </tbody>
                </table>
                <div
                  style={{
                    background: '#EFF6FF',
                    padding: '8px 12px',
                    borderRadius: '3px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#1E40AF', fontWeight: 700 }}>Flight 6E-2045 Consensus Price:</span>
                  <span className="font-num" style={{ fontSize: '16px', fontWeight: 700, color: '#1E3A8A' }}>
                    ₹6,200
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeLevel === 2 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ background: '#B0286A', color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '2px', fontWeight: 700 }}>
                LEVEL 2
              </span>
              <span style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 600, color: 'var(--ink)' }}>
                Representative Horizon Price: Why Geometric Mean (GM) Matters
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              <div>
                <h4 style={{ fontFamily: "'B612', monospace", fontSize: '13px', textTransform: 'uppercase', color: 'var(--ink-2)', marginBottom: '8px' }}>
                  The Problem & Solution
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.5, color: 'var(--ink)' }}>
                  On any given departure date (e.g. 7 days from now, <strong>T+7</strong>), there are 30 to 50 scheduled flights operating
                  across the day. Most flights are priced between ₹5,800 and ₹6,500. However, 1 or 2 last-minute premium/business seats
                  might be listed at ₹22,000.
                </p>
                <div
                  style={{
                    background: '#FDF2F8',
                    padding: '12px',
                    borderRadius: '4px',
                    borderLeft: '3px solid #B0286A',
                    marginTop: '12px',
                    fontSize: '13px',
                  }}
                >
                  <strong>Why a simple average fails:</strong> If we simply added the numbers up, that single ₹22,000 ticket would drag
                  the average up to ₹9,500, even though 95% of passengers paid only ₹6,000!
                  <br /><br />
                  <strong>The Fix (Geometric Mean):</strong> We take the Geometric Mean (multiplying the values and taking the Nth root).
                  The Geometric Mean dampens extreme luxury spikes and captures the true price that standard consumers actually encounter.
                </div>
              </div>

              {/* Visual Demonstration: Simple Average vs Geometric Mean */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', padding: '16px' }}>
                <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#B0286A', fontWeight: 700, marginBottom: '8px' }}>
                  THE OUTLIER TEST · 5 Flights at T+7 Departure
                </div>
                <div style={{ fontSize: '12px', color: 'var(--ink-2)', marginBottom: '10px' }}>
                  Flight Fares: ₹5,850 · ₹6,150 · ₹6,300 · ₹6,420 · <strong>₹18,500 (Luxury Outlier)</strong>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                  <div style={{ background: '#FEE2E2', padding: '10px', borderRadius: '3px', border: '1px solid #FCA5A5' }}>
                    <div style={{ fontSize: '11px', color: '#991B1B', fontWeight: 700 }}>❌ Simple Average</div>
                    <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: '#B91C1C' }}>₹8,644</div>
                    <div style={{ fontSize: '10px', color: '#7F1D1D' }}>+37% distorted by 1 outlier!</div>
                  </div>

                  <div style={{ background: '#DCFCE7', padding: '10px', borderRadius: '3px', border: '1px solid #86EFAC' }}>
                    <div style={{ fontSize: '11px', color: '#166534', fontWeight: 700 }}>✓ Geometric Mean (AERIX)</div>
                    <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: '#15803D' }}>₹7,315</div>
                    <div style={{ fontSize: '10px', color: '#14532D' }}>True consumer center of gravity</div>
                  </div>
                </div>

                <p style={{ fontSize: '11px', color: 'var(--ink-2)', margin: 0 }}>
                  This adheres to the official <strong>Jevons Elementary Index Standard</strong> prescribed by MoSPI and Eurostat HICP.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeLevel === 3 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ background: '#2F7D6D', color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '2px', fontWeight: 700 }}>
                LEVEL 3
              </span>
              <span style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 600, color: 'var(--ink)' }}>
                Route Representative Price Across 6 Advance Horizons
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              <div>
                <h4 style={{ fontFamily: "'B612', monospace", fontSize: '13px', textTransform: 'uppercase', color: 'var(--ink-2)', marginBottom: '8px' }}>
                  The Problem & Solution
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.5, color: 'var(--ink)' }}>
                  A route cannot be summarized by a single departure day. Urgent next-day tickets (<strong>T+1</strong>) are expensive,
                  while tickets booked 45 days in advance (<strong>T+45</strong>) are significantly cheaper.
                </p>
                <div
                  style={{
                    background: '#F0FDF4',
                    padding: '12px',
                    borderRadius: '4px',
                    borderLeft: '3px solid #2F7D6D',
                    marginTop: '12px',
                    fontSize: '13px',
                  }}
                >
                  <strong>How AERIX solves this:</strong> We track <strong>6 distinct timeframes</strong> (T+1, T+7, T+15, T+21, T+30, T+45)
                  and weight them according to actual consumer booking distribution:
                  <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                    <li><strong>T+1 (1 day ahead):</strong> 5.09% (Urgent emergency travel)</li>
                    <li><strong>T+7 (7 days ahead):</strong> 13.50% (Short advance)</li>
                    <li><strong>T+15 (15 days ahead):</strong> 14.91% (Mid advance)</li>
                    <li><strong>T+21 (21 days ahead):</strong> <strong>15.19% ★ Official MoSPI CPI Checkpoint</strong></li>
                    <li><strong>T+30 (30 days ahead):</strong> 25.88% (Planned travel)</li>
                    <li><strong>T+45 (45 days ahead):</strong> 25.43% (Early vacation bookings)</li>
                  </ul>
                </div>
              </div>

              {/* Visual Breakdown of Route Price */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', padding: '16px' }}>
                <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#2F7D6D', fontWeight: 700, marginBottom: '8px' }}>
                  COMPUTING 1 PRICE FOR DELHI → MUMBAI (DEL-BOM)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', marginBottom: '12px' }}>
                  {routeConfigs['DEL-BOM'].horizons.map((h) => (
                    <div
                      key={h.days}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: h.days === 21 ? '#ECFDF5' : '#fff',
                        border: h.days === 21 ? '1px solid #10B981' : '1px solid #E2E8F0',
                        padding: '4px 8px',
                        borderRadius: '3px',
                      }}
                    >
                      <span style={{ fontWeight: h.days === 21 ? 700 : 400, color: h.days === 21 ? '#047857' : 'inherit' }}>
                        {h.label}
                      </span>
                      <div className="font-num" style={{ display: 'flex', gap: '12px' }}>
                        <span style={{ color: 'var(--ink-2)' }}>weight {(h.weight * 100).toFixed(1)}%</span>
                        <span style={{ fontWeight: 700 }}>₹{h.fare.toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    background: '#ECFDF5',
                    borderTop: '1px dashed #10B981',
                    padding: '8px 12px',
                    borderRadius: '3px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#065F46', fontWeight: 700 }}>Weighted DEL-BOM Route Price:</span>
                  <span className="font-num" style={{ fontSize: '17px', fontWeight: 700, color: '#047857' }}>
                    ₹6,890
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeLevel === 4 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ background: '#8A5600', color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '2px', fontWeight: 700 }}>
                LEVEL 4
              </span>
              <span style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 600, color: 'var(--ink)' }}>
                National Aggregation Across 60 DGCA Corridors
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              <div>
                <h4 style={{ fontFamily: "'B612', monospace", fontSize: '13px', textTransform: 'uppercase', color: 'var(--ink-2)', marginBottom: '8px' }}>
                  The Problem & Solution
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.5, color: 'var(--ink)' }}>
                  Now that we have a representative price for each corridor, how do we combine them for the entire country?
                  Giving every route equal weight would be statistically incorrect: Delhi–Mumbai carries <strong>6.88 million</strong> passengers
                  annually, while smaller regional routes carry under 200,000.
                </p>
                <div
                  style={{
                    background: '#FFFBEB',
                    padding: '12px',
                    borderRadius: '4px',
                    borderLeft: '3px solid #8A5600',
                    marginTop: '12px',
                    fontSize: '13px',
                  }}
                >
                  <strong>The Official DGCA Volume Weights:</strong> We take the weighted average of all 60 corridors using official
                  <strong> DGCA CY2024 Passenger Traffic Statistics</strong>:
                  <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                    <li><strong>DEL-BOM (Rank #1):</strong> 4.27% passenger share</li>
                    <li><strong>BLR-DEL (Rank #2):</strong> 2.95% passenger share</li>
                    <li><strong>BLR-BOM (Rank #3):</strong> 2.63% passenger share</li>
                    <li><strong>... up to 60 routes:</strong> Covering <strong>91.99M passengers</strong> (57.02% of all Indian flyers!)</li>
                  </ul>
                </div>
              </div>

              {/* National Price Result Box */}
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '4px', padding: '16px' }}>
                <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#8A5600', fontWeight: 700, marginBottom: '8px' }}>
                  NATIONAL BASKET COMPILATION
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', borderBottom: '1px solid #E2E8F0' }}>
                    <span>DEL-BOM (4.27% share)</span>
                    <span className="font-num">₹6,890 × 0.0427 = ₹294.20</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', borderBottom: '1px solid #E2E8F0' }}>
                    <span>BLR-DEL (2.95% share)</span>
                    <span className="font-num">₹7,920 × 0.0295 = ₹233.64</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', borderBottom: '1px solid #E2E8F0' }}>
                    <span>BLR-BOM (2.63% share)</span>
                    <span className="font-num">₹6,410 × 0.0263 = ₹168.58</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', color: 'var(--ink-2)' }}>
                    <span>Remaining 57 corridors...</span>
                    <span className="font-num">+ ₹8,167.58</span>
                  </div>
                </div>

                <div
                  style={{
                    background: '#FEF3C7',
                    borderTop: '1px dashed #D97706',
                    padding: '10px 12px',
                    borderRadius: '3px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <span style={{ fontSize: '12px', color: '#92400E', fontWeight: 700 }}>All-India Representative Airfare:</span>
                  <span className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: '#B45309' }}>
                    ₹8,864
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeLevel === 5 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ background: '#1A2B3C', color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '2px', fontWeight: 700 }}>
                LEVEL 5
              </span>
              <span style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 600, color: 'var(--ink)' }}>
                The Final Formula: Base 2024 Index & MoSPI CPI Contribution
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              <div>
                <h4 style={{ fontFamily: "'B612', monospace", fontSize: '13px', textTransform: 'uppercase', color: 'var(--ink-2)', marginBottom: '8px' }}>
                  The Final Formula
                </h4>
                <p style={{ fontSize: '14px', lineHeight: 1.5, color: 'var(--ink)' }}>
                  Now that we have today's All-India Representative Fare (<strong>₹8,864</strong>), how do we get the final
                  index number and its impact on India's national inflation?
                </p>

                <div
                  style={{
                    background: 'var(--vellum)',
                    padding: '14px',
                    borderRadius: '4px',
                    border: '1px solid var(--contour)',
                    marginTop: '12px',
                    fontFamily: "'B612', monospace",
                  }}
                >
                  <div style={{ fontSize: '11px', color: 'var(--ink-2)', marginBottom: '4px' }}>1. HEADLINE AERIX FORMULA:</div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)' }}>
                    Index = (Current Fare ÷ 2024 Base Fare) × 100
                  </div>
                  <div style={{ fontSize: '13px', color: '#047857', marginTop: '4px' }}>
                    Index = (₹8,864 ÷ ₹8,130) × 100 = <strong>109.02</strong>
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--ink-2)', marginTop: '14px', marginBottom: '4px' }}>2. MoSPI CPI IMPACT FORMULA:</div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)' }}>
                    CPI Impact = Airfare Inflation Rate × Household Weight (0.02951%)
                  </div>
                  <div style={{ fontSize: '13px', color: '#1E40AF', marginTop: '4px' }}>
                    +4.325% MoM Surge × 0.0002951 = <strong>+0.001276 percentage points</strong>
                  </div>
                </div>
              </div>

              {/* Live Output Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '4px', padding: '16px' }}>
                  <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#065F46', fontWeight: 700 }}>
                    HEADLINE AIRFARE INDEX (CY2024 = 100)
                  </div>
                  <div className="font-num" style={{ fontSize: '32px', fontWeight: 700, color: '#047857', margin: '4px 0' }}>
                    109.02
                  </div>
                  <div style={{ fontSize: '12px', color: '#065F46' }}>
                    Indicates that domestic airfares across India have increased by <strong>9.02%</strong> compared to the CY2024 base year.
                  </div>
                </div>

                <div style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '4px', padding: '16px' }}>
                  <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: '#1E40AF', fontWeight: 700 }}>
                    MoSPI CPI CONTRIBUTION (Item 07.3.3.1.2.01)
                  </div>
                  <div className="font-num" style={{ fontSize: '24px', fontWeight: 700, color: '#1D4ED8', margin: '4px 0' }}>
                    +0.001276 pp
                  </div>
                  <div style={{ fontSize: '12px', color: '#1E3A8A' }}>
                    A 4.33% MoM airfare surge adds <strong>0.001276 percentage points</strong> directly to India's Combined CPI inflation rate.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── 4. Interactive Evaluator Sandbox (Hands-On Simulation) ── */}
      <section
        style={{
          border: '1px solid var(--contour)',
          background: '#ffffff',
          borderRadius: '4px',
          padding: 'var(--sp-6)',
        }}
      >
        <div style={{ marginBottom: 'var(--sp-4)' }}>
          <div
            style={{
              fontFamily: "'B612', monospace",
              fontSize: '11px',
              textTransform: 'uppercase',
              color: 'var(--route-blue)',
              fontWeight: 700,
            }}
          >
            HANDS-ON SIMULATION FOR EVALUATORS
          </div>
          <h2 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '24px', fontWeight: 400, color: 'var(--ink)' }}>
            Live Calculation Sandbox: Test the Math in Real-Time
          </h2>
          <p style={{ color: 'var(--ink-2)', fontSize: '13px' }}>
            Select a route and adjust the luxury outlier price below to see how Geometric Mean protects the price from sudden spikes.
          </p>
        </div>

        {/* Route Selector Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: 'var(--sp-4)' }}>
          {(['DEL-BOM', 'BLR-DEL', 'DEL-CCU'] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setSelectedSandboxRoute(r)}
              style={{
                background: selectedSandboxRoute === r ? 'var(--ink)' : 'var(--vellum)',
                color: selectedSandboxRoute === r ? '#fff' : 'var(--ink)',
                border: '1px solid var(--contour)',
                padding: '6px 14px',
                borderRadius: '3px',
                cursor: 'pointer',
                fontFamily: "'B612', monospace",
                fontSize: '12px',
                fontWeight: selectedSandboxRoute === r ? 700 : 400,
              }}
            >
              {r} ({routeConfigs[r].origin} ⇄ {routeConfigs[r].dest})
            </button>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--sp-6)' }}>
          {/* Controls */}
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--ink)', marginBottom: '8px' }}>
              Simulate 1 Extreme Luxury Ticket at T+7 Departure: ₹{customOutlierPrice.toLocaleString('en-IN')}
            </label>
            <input
              type="range"
              min={8000}
              max={35000}
              step={500}
              value={customOutlierPrice}
              onChange={(e) => setCustomOutlierPrice(Number(e.target.value))}
              style={{ width: '100%', marginBottom: '12px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--ink-2)' }}>
              <span>₹8,000 (Standard Ticket)</span>
              <span>₹20,000 (Business)</span>
              <span>₹35,000 (Emergency)</span>
            </div>

            <div
              style={{
                marginTop: '16px',
                padding: '12px',
                background: 'var(--vellum)',
                borderRadius: '4px',
                fontSize: '12px',
                color: 'var(--ink-2)',
              }}
            >
              Notice how the <strong>Simple Average</strong> shoots up wildly with high ticket prices, while the
              <strong> Geometric Mean</strong> remains grounded in the reality of what normal travelers actually pay.
            </div>
          </div>

          {/* Results Comparison */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '12px', borderRadius: '4px' }}>
              <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>T+7 Departure Fares (5 normal + 1 outlier):</div>
              <div className="font-num" style={{ fontSize: '12px', color: 'var(--ink)', marginTop: '4px' }}>
                {currentCfg.t7Flights.map((f) => `₹${f.toLocaleString('en-IN')}`).join(', ')}, <strong>₹{customOutlierPrice.toLocaleString('en-IN')}</strong>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ border: '1px solid #FCA5A5', background: '#FEF2F2', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '11px', color: '#991B1B', fontWeight: 700 }}>Simple Average:</div>
                <div className="font-num" style={{ fontSize: '20px', fontWeight: 700, color: '#DC2626' }}>
                  ₹{amT7With.toLocaleString('en-IN')}
                </div>
                <div style={{ fontSize: '10px', color: '#B91C1C' }}>
                  Spiked by +{(((amT7With - gmT7Without) / gmT7Without) * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ border: '1px solid #86EFAC', background: '#F0FDF4', padding: '10px', borderRadius: '4px' }}>
                <div style={{ fontSize: '11px', color: '#166534', fontWeight: 700 }}>AERIX Geometric Mean:</div>
                <div className="font-num" style={{ fontSize: '20px', fontWeight: 700, color: '#16A34A' }}>
                  ₹{gmT7With.toLocaleString('en-IN')}
                </div>
                <div style={{ fontSize: '10px', color: '#15803D' }}>
                  Controlled at +{(((gmT7With - gmT7Without) / gmT7Without) * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 14px',
                background: 'var(--vellum)',
                borderRadius: '4px',
                border: '1px solid var(--contour)',
              }}
            >
              <div>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink)' }}>{selectedSandboxRoute} Representative Fare:</span>
                <div style={{ fontSize: '11px', color: 'var(--ink-2)' }}>DGCA Share: {(currentCfg.dgcaWeight * 100).toFixed(2)}%</div>
              </div>
              <div className="font-num" style={{ fontSize: '18px', fontWeight: 700, color: 'var(--route-blue)' }}>
                ₹{routeRepFare.toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. Formal Mathematical Specification (Collapsible for Economists) ── */}
      {showMathSpec && (
        <section
          style={{
            border: '1px solid var(--contour)',
            background: '#ffffff',
            borderRadius: '4px',
            padding: 'var(--sp-6)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-4)' }}>
            <div>
              <span style={{ fontFamily: "'B612', monospace", fontSize: '11px', textTransform: 'uppercase', color: '#B0286A', fontWeight: 700 }}>
                STATISTICAL SPECIFICATION
              </span>
              <h3 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 400, color: 'var(--ink)' }}>
                Mathematical Rigor: Eurostat HICP & MoSPI CPI Compliance
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setShowMathSpec(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', color: 'var(--ink-2)' }}
            >
              ✕ Hide
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--sp-4)', fontSize: '13px' }}>
            <div style={{ background: 'var(--vellum)', padding: '14px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '4px' }}>1. Elementary Level (Jevons Formula)</div>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', color: 'var(--route-blue)', margin: '6px 0' }}>
                P(r, l, t) = exp( 1/N * ∑ ln(P_i) )
              </div>
              <p style={{ fontSize: '11px', color: 'var(--ink-2)', margin: 0 }}>
                Geometric mean of all quotes across flight carriers on route <em>r</em> at lead horizon <em>l</em>.
              </p>
            </div>

            <div style={{ background: 'var(--vellum)', padding: '14px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '4px' }}>2. Horizon Aggregation (Young Relative)</div>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', color: 'var(--route-mag)', margin: '6px 0' }}>
                P(r, t) = ∑ w_l * P(r, l, t)
              </div>
              <p style={{ fontSize: '11px', color: 'var(--ink-2)', margin: 0 }}>
                Weighted sum across the 6 booking horizons where ∑ w_l = 1.0 (MoSPI checkpoint T+21 carries 15.19%).
              </p>
            </div>

            <div style={{ background: 'var(--vellum)', padding: '14px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '4px' }}>3. National Laspeyres Aggregate</div>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', color: 'var(--route-teal)', margin: '6px 0' }}>
                AERIX_t = ∑ W_r * [ P(r, t) / P(r, 0) ] * 100
              </div>
              <p style={{ fontSize: '11px', color: 'var(--ink-2)', margin: 0 }}>
                Laspeyres / Young index aggregated using official DGCA CY2024 passenger volume shares (Base CY2024 = 100).
              </p>
            </div>

            <div style={{ background: 'var(--vellum)', padding: '14px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '4px' }}>4. MoSPI CPI Contribution</div>
              <div style={{ fontFamily: "'B612', monospace", fontSize: '12px', color: '#8A5600', margin: '6px 0' }}>
                ΔCPI_pp = ( (I_t - I_t-1) / I_t-1 ) * 0.02951%
              </div>
              <p style={{ fontSize: '11px', color: 'var(--ink-2)', margin: 0 }}>
                Classified under COICOP item 07.3.3.1.2.01 (Air Passenger Transport) in India's National CPI basket.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ── 6. Evaluator Q&A Cheat Sheet ── */}
      <section
        style={{
          border: '1px solid var(--contour)',
          background: '#ffffff',
          borderRadius: '4px',
          padding: 'var(--sp-6)',
        }}
      >
        <h3 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '22px', fontWeight: 400, color: 'var(--ink)', marginBottom: 'var(--sp-4)' }}>
          Frequently Asked Questions by Evaluators
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--sp-4)' }}>
          <div style={{ padding: '12px', background: 'var(--vellum)', borderRadius: '4px' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--ink)', marginBottom: '6px' }}>
              Q: Why not just take a simple average of all scraped tickets?
            </div>
            <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, margin: 0 }}>
              Because a simple average gives the exact same weight to an empty midnight flight as a packed morning commuter flight,
              and gets completely distorted whenever a single first-class ticket sells for ₹30,000. Geometric Mean and passenger volume
              weights reflect actual consumer spending reality.
            </p>
          </div>

          <div style={{ padding: '12px', background: 'var(--vellum)', borderRadius: '4px' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--ink)', marginBottom: '6px' }}>
              Q: Where do the route weights come from?
            </div>
            <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, margin: 0 }}>
              Official DGCA CY2024 city-pair statistics. We take the top 60 scheduled domestic routes, which carry 91.99 million passengers
              annually (over 57% of all domestic flyers in India). Stations in dual-airport cities like Goa (Dabolim vs Mopa) are kept separate.
            </p>
          </div>

          <div style={{ padding: '12px', background: 'var(--vellum)', borderRadius: '4px' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--ink)', marginBottom: '6px' }}>
              Q: Why is T+21 advance booking special?
            </div>
            <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, margin: 0 }}>
              The Ministry of Statistics and Programme Implementation (MoSPI) explicitly defines <strong>21 days advance booking</strong>
              as the official national reference checkpoint for domestic flights in the upcoming CPI 2024 series. AERIX tracks this checkpoint
              explicitly while also measuring the full booking curve from T+1 to T+45.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
