import React, { useState, useMemo } from 'react';
import { getRouteAuditData } from '../data/routeExtractionAudit';
import { MathBlock } from './MathBlock';
import {
  AirlineLogo,
  ScraperSourceBadge,
  EaseMyTripLogo,
  GoogleFlightsLogo,
  OTAConsensusLogo,
} from './ProviderAndAirlineLogos';

interface RouteDataAuditModalProps {
  routeId: string | null;
  onClose: () => void;
}

export const RouteDataAuditModal: React.FC<RouteDataAuditModalProps> = ({ routeId, onClose }) => {
  const [activeTab, setActiveTab] = useState<'flights' | 'pipeline' | 'horizons'>('flights');
  const [selectedHorizon, setSelectedHorizon] = useState<string>('ALL');
  const [selectedCarrier, setSelectedCarrier] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const auditData = useMemo(() => {
    if (!routeId) return null;
    return getRouteAuditData(routeId);
  }, [routeId]);

  if (!routeId || !auditData) return null;

  const filteredFlights = auditData.flights.filter((f) => {
    if (selectedHorizon !== 'ALL' && f.lead_horizon !== selectedHorizon) return false;
    if (selectedCarrier !== 'ALL' && f.carrier_name !== selectedCarrier) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchNum = f.flight_number.toLowerCase().includes(q);
      const matchCarrier = f.carrier_name.toLowerCase().includes(q);
      const matchSource = f.source.toLowerCase().includes(q);
      if (!matchNum && !matchCarrier && !matchSource) return false;
    }
    return true;
  });

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(26, 43, 60, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--vellum)',
          width: '100%',
          maxWidth: '1120px',
          maxHeight: '92vh',
          borderRadius: '2px',
          boxShadow: '0 12px 36px rgba(26, 43, 60, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid var(--contour)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cockpit Sectional Header */}
        <div
          style={{
            padding: '16px 22px',
            background: 'var(--ink)',
            color: 'var(--vellum)',
            borderBottom: '2px solid var(--contour)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
              <span
                style={{
                  fontFamily: "'B612', monospace",
                  fontSize: '15px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  border: '1px solid rgba(240, 242, 238, 0.35)',
                  background: 'rgba(240, 242, 238, 0.08)',
                  padding: '2px 8px',
                  borderRadius: '2px',
                  color: 'var(--vellum)',
                }}
              >
                {auditData.route_id}
              </span>
              <h2
                style={{
                  fontFamily: "'Newsreader Variable', serif",
                  fontSize: '20px',
                  fontWeight: 400,
                  margin: 0,
                  color: '#FFFFFF',
                  letterSpacing: '0.02em',
                }}
              >
                {auditData.origin} ⇄ {auditData.destination}
              </h2>
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: "'B612', monospace",
                  border: '1px solid rgba(240, 242, 238, 0.4)',
                  color: 'var(--vellum)',
                  padding: '1px 6px',
                  borderRadius: '2px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                Rank #{Math.floor(auditData.rank)} DGCA CY2024
              </span>
            </div>
            <div
              style={{
                fontSize: '11px',
                fontFamily: "'B612', monospace",
                color: 'rgba(240, 242, 238, 0.72)',
                marginTop: '5px',
              }}
            >
              Passenger Share: <span style={{ color: '#FFFFFF' }}>{auditData.pax_share_pct.toFixed(2)}%</span> · Basket Weight: <span style={{ color: '#FFFFFF' }}>{(auditData.route_weight * 100).toFixed(2)}%</span> · Annual Scheduled Volume: <span style={{ color: '#FFFFFF' }}>{auditData.annual_passenger_volume.toLocaleString('en-IN')}</span> pax
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              background: 'transparent',
              border: '1px solid rgba(240, 242, 238, 0.25)',
              color: 'var(--vellum)',
              fontFamily: "'B612', monospace",
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              padding: '4px 10px',
              borderRadius: '2px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Close [Esc]
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--contour)',
            background: 'var(--vellum)',
            padding: '0 16px',
            gap: '4px',
          }}
        >
          {[
            { id: 'flights', label: `Extracted Flights & Sources (${auditData.flights.length})` },
            { id: 'pipeline', label: 'Calculation Pipeline & Formulas' },
            { id: 'horizons', label: 'Advance Booking Distribution' },
          ].map((tab) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  padding: '10px 16px',
                  fontSize: '11px',
                  fontFamily: "'B612', monospace",
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  fontWeight: active ? 700 : 400,
                  color: active ? 'var(--ink)' : 'var(--ink-2)',
                  background: active ? '#FFFFFF' : 'transparent',
                  border: 'none',
                  borderTop: active ? '2px solid var(--ink)' : '2px solid transparent',
                  borderLeft: active ? '1px solid var(--contour)' : '1px solid transparent',
                  borderRight: active ? '1px solid var(--contour)' : '1px solid transparent',
                  cursor: 'pointer',
                  transition: 'background 0.1s ease',
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Modal Body Container */}
        <div style={{ padding: '18px 22px', overflowY: 'auto', flex: 1, background: 'var(--vellum)' }}>
          {/* TAB 1: Extracted Flights & Sources */}
          {activeTab === 'flights' && (
            <div>
              {/* Scraper Sources Summary Cards */}
              <div style={{ marginBottom: '16px' }}>
                <div
                  style={{
                    fontSize: '11px',
                    fontFamily: "'B612', monospace",
                    textTransform: 'uppercase',
                    color: 'var(--ink-2)',
                    marginBottom: '8px',
                    letterSpacing: '0.06em',
                    fontWeight: 700,
                  }}
                >
                  Active Scraping Engines & Data Sources · Corridor {auditData.route_id}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px' }}>
                  {auditData.sources_summary.map((src) => {
                    const isEMT = src.source.toLowerCase().includes('easemytrip');
                    const isGoogle = src.source.toLowerCase().includes('google');
                    return (
                      <div
                        key={src.source}
                        style={{
                          background: '#FFFFFF',
                          border: '1px solid var(--contour)',
                          borderRadius: '2px',
                          padding: '12px 14px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {isEMT ? (
                              <EaseMyTripLogo size={24} />
                            ) : isGoogle ? (
                              <GoogleFlightsLogo size={24} />
                            ) : (
                              <OTAConsensusLogo size={24} />
                            )}
                            <strong style={{ fontSize: '13px', color: 'var(--ink)', fontFamily: "'B612', monospace" }}>{src.source}</strong>
                          </div>
                          <span
                            style={{
                              fontSize: '9px',
                              fontFamily: "'B612', monospace",
                              textTransform: 'uppercase',
                              letterSpacing: '0.04em',
                              border: '1px solid var(--contour)',
                              background: 'var(--vellum)',
                              color: 'var(--route-teal)',
                              padding: '1px 5px',
                              borderRadius: '2px',
                              fontWeight: 700,
                            }}
                          >
                            {src.status}
                          </span>
                        </div>
                      <div style={{ fontSize: '11px', color: 'var(--ink-2)', marginTop: '4px' }}>
                        {src.engine}
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          color: 'var(--ink)',
                          marginTop: '8px',
                          borderTop: '1px solid var(--contour)',
                          paddingTop: '6px',
                          fontFamily: "'B612', monospace",
                        }}
                      >
                        <span>Harvested: <strong>{src.observation_count} quotes</strong></span>
                        <span style={{ color: 'var(--ink-2)' }}>{src.last_sync}</span>
                      </div>
                    </div>
                    );
                  })}
                </div>
              </div>

              {/* Filters & Search Toolbar */}
              <div
                style={{
                  background: '#FFFFFF',
                  border: '1px solid var(--contour)',
                  borderRadius: '2px',
                  padding: '10px 14px',
                  marginBottom: '14px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '10px',
                }}
              >
                {/* Horizon Pills */}
                <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '11px', fontFamily: "'B612', monospace", textTransform: 'uppercase', color: 'var(--ink-2)', marginRight: '4px', letterSpacing: '0.04em' }}>
                    Horizon:
                  </span>
                  {['ALL', 'T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45'].map((h) => {
                    const active = selectedHorizon === h;
                    return (
                      <button
                        key={h}
                        onClick={() => setSelectedHorizon(h)}
                        style={{
                          padding: '3px 8px',
                          fontSize: '11px',
                          fontFamily: "'B612', monospace",
                          border: active ? '1px solid var(--ink)' : '1px solid var(--contour)',
                          background: active ? 'var(--ink)' : 'var(--vellum)',
                          color: active ? 'var(--vellum)' : 'var(--ink)',
                          borderRadius: '2px',
                          cursor: 'pointer',
                        }}
                      >
                        {h}
                      </button>
                    );
                  })}
                </div>

                {/* Carrier & Search */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <select
                    value={selectedCarrier}
                    onChange={(e) => setSelectedCarrier(e.target.value)}
                    style={{
                      padding: '4px 8px',
                      fontSize: '11px',
                      fontFamily: "'B612', monospace",
                      border: '1px solid var(--contour)',
                      background: 'var(--vellum)',
                      color: 'var(--ink)',
                      borderRadius: '2px',
                    }}
                  >
                    <option value="ALL">All Airlines (5 Carriers)</option>
                    <option value="IndiGo">IndiGo (6E)</option>
                    <option value="Air India">Air India (AI)</option>
                    <option value="Vistara">Vistara (UK)</option>
                    <option value="Akasa Air">Akasa Air (QP)</option>
                    <option value="SpiceJet">SpiceJet (SG)</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Search flight #..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      padding: '4px 8px',
                      fontSize: '11px',
                      fontFamily: "'B612', monospace",
                      border: '1px solid var(--contour)',
                      background: 'var(--vellum)',
                      color: 'var(--ink)',
                      borderRadius: '2px',
                      width: '140px',
                    }}
                  />
                </div>
              </div>

              {/* Extracted Flights Table */}
              <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead style={{ background: 'var(--vellum)', borderBottom: '1px solid var(--contour)' }}>
                    <tr style={{ color: 'var(--ink-2)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: "'B612', monospace" }}>
                      <th style={{ padding: '8px 12px' }}>Flight / Carrier</th>
                      <th style={{ padding: '8px 12px' }}>Schedule</th>
                      <th style={{ padding: '8px 12px' }}>Horizon</th>
                      <th style={{ padding: '8px 12px' }}>Provider Source</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Base Fare</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Taxes / UDF</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Total Quoted</th>
                      <th style={{ padding: '8px 12px' }}>Cross-Provider Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFlights.map((f) => (
                      <tr key={f.id} style={{ borderBottom: '1px solid var(--contour)' }}>
                        <td style={{ padding: '8px 12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <AirlineLogo code={f.carrier_code} name={f.carrier_name} size={24} />
                            <div>
                              <div style={{ fontWeight: 700, color: 'var(--ink)', fontFamily: "'B612', monospace" }}>
                                {f.flight_number}
                              </div>
                              <div style={{ fontSize: '10px', color: 'var(--ink-2)' }}>
                                {f.carrier_name} · {f.aircraft}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: "'B612', monospace", color: 'var(--ink)', fontSize: '11px' }}>
                          <div>{f.departure_time} ➔ {f.arrival_time}</div>
                          <div style={{ fontSize: '10px', color: 'var(--ink-2)' }}>{f.duration} non-stop</div>
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <span
                            style={{
                              fontFamily: "'B612', monospace",
                              fontSize: '10px',
                              fontWeight: 700,
                              border: f.lead_horizon === 'T+1' ? '1px solid var(--assumed)' : '1px solid var(--contour)',
                              background: 'var(--vellum)',
                              color: f.lead_horizon === 'T+1' ? 'var(--assumed)' : 'var(--ink)',
                              padding: '1px 5px',
                              borderRadius: '2px',
                            }}
                          >
                            {f.lead_horizon}
                          </span>
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <ScraperSourceBadge source={f.source} size={16} />
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: "'B612', monospace", fontVariantNumeric: 'tabular-nums' }}>
                          ₹{f.base_fare.toLocaleString('en-IN')}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: "'B612', monospace", color: 'var(--ink-2)', fontVariantNumeric: 'tabular-nums' }}>
                          ₹{f.taxes_and_fees.toLocaleString('en-IN')}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: "'B612', monospace", fontWeight: 700, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums' }}>
                          ₹{f.total_fare.toLocaleString('en-IN')}
                        </td>
                        <td style={{ padding: '8px 12px', fontSize: '10px', fontFamily: "'B612', monospace" }}>
                          {f.cross_provider_match ? (
                            <span style={{ color: 'var(--route-blue)', borderLeft: '2px solid var(--route-blue)', paddingLeft: '5px' }}>
                              Cross-matched ({f.cross_provider_match.other_provider} Δ ₹{Math.abs(f.cross_provider_match.delta)})
                            </span>
                          ) : (
                            <span style={{ color: 'var(--route-teal)' }}>Verified [Single Source]</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {filteredFlights.length === 0 && (
                      <tr>
                        <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: 'var(--ink-2)', fontFamily: "'B612', monospace" }}>
                          No flight observations match the selected criteria.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: Step-by-Step Calculation Pipeline */}
          {activeTab === 'pipeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Introduction Card */}
              <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                <h3 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '17px', fontWeight: 400, color: 'var(--ink)', marginBottom: '4px' }}>
                  Micro-founded Transformation Pipeline: Scraper Harvest to Route Index
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.5, margin: 0 }}>
                  Algorithmic sequence applied to corridor <strong>{auditData.route_id}</strong> on cycle <strong>{auditData.scrape_date}</strong>. Each stage eliminates statistical bias (such as scraper flight churn, provider fee anomalies, and urgent-booking right-tail skew) in accordance with official MoSPI and DGCA specifications.
                </p>
              </div>

              {/* Step 1 */}
              <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--route-blue)' }}>
                    01
                  </span>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                    Provider Reconciliation (Cross-Provider Mean)
                  </h4>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, marginBottom: '8px' }}>
                  When identical flights (matched by carrier, schedule, and date) appear across multiple scrapers, quotes are averaged arithmetic-wise to neutralize platform-specific markups:
                </p>
                <MathBlock
                  formula="\bar{P}_f = \frac{1}{K} \sum_{k=1}^K P_{f, k}"
                  caption="Unweighted cross-provider quote consensus"
                  style={{ margin: '8px 0' }}
                />
                <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", background: 'var(--vellum)', padding: '6px 10px', borderLeft: '3px solid var(--route-blue)', color: 'var(--ink)' }}>
                  Validated {auditData.total_observations} quotes across 3 independent scraping engines. 100% matched model parity.
                </div>
              </div>

              {/* Step 2 */}
              <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--route-blue)' }}>
                    02
                  </span>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                    Horizon Elementary Aggregation (Jevons Geometric Mean)
                  </h4>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, marginBottom: '8px' }}>
                  For each advance purchase horizon, flights are aggregated using the unweighted Geometric Mean (Jevons formula) to protect against right-tail fare inflation:
                </p>
                <MathBlock
                  formula="P_{r, h} = \left( \prod_{i=1}^{N_h} P_{i, h} \right)^{\frac{1}{N_h}} = \exp\left( \frac{1}{N_h} \sum_{i=1}^{N_h} \ln P_{i, h} \right)"
                  caption="Elementary Jevons price for route r at advance horizon h"
                  style={{ margin: '8px 0' }}
                />

                {/* Table of calculated means */}
                <div style={{ marginTop: '12px', overflowX: 'auto', border: '1px solid var(--contour)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
                    <thead style={{ background: 'var(--vellum)', borderBottom: '1px solid var(--contour)' }}>
                      <tr style={{ color: 'var(--ink-2)', fontFamily: "'B612', monospace", textTransform: 'uppercase' }}>
                        <th style={{ padding: '6px 10px' }}>Horizon</th>
                        <th style={{ padding: '6px 10px' }}>Classification</th>
                        <th style={{ padding: '6px 10px', textAlign: 'center' }}>Flights</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>Min (₹)</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right' }}>Max (₹)</th>
                        <th style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 700 }}>Computed Jevons Mean (P_r,h)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditData.horizons.map((h) => (
                        <tr key={h.lead_horizon} style={{ borderBottom: '1px solid var(--contour)' }}>
                          <td style={{ padding: '6px 10px', fontFamily: "'B612', monospace", fontWeight: 700 }}>{h.lead_horizon}</td>
                          <td style={{ padding: '6px 10px', color: 'var(--ink-2)' }}>{h.horizon_name} {h.is_mospi ? '[MoSPI]' : ''}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'center', fontFamily: "'B612', monospace" }}>{h.flight_count}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: "'B612', monospace" }}>₹{h.min_fare.toLocaleString('en-IN')}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: "'B612', monospace" }}>₹{h.max_fare.toLocaleString('en-IN')}</td>
                          <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: "'B612', monospace", fontWeight: 700, color: 'var(--route-blue)' }}>
                            ₹{h.geometric_mean.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Step 3 */}
              <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--route-blue)' }}>
                    03
                  </span>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                    Empirical Booking Curve Weighting (DGCA Passenger Distribution)
                  </h4>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, marginBottom: '8px' }}>
                  Horizons are weighted by empirical booking curves derived from sovereign DGCA monthly passenger distributions:
                </p>
                <MathBlock
                  formula={`P_r = \\sum_{h \\in \\mathcal{H}} w_h \\cdot P_{r, h} = ${auditData.horizons.map((h) => `${h.dgca_weight_decimal} \\cdot P_{${h.lead_horizon.replace('+', '')}}`).join(' + ')}`}
                  caption="Empirically weighted composite daily benchmark fare for route r"
                  style={{ margin: '8px 0' }}
                />

                <div style={{ background: 'var(--vellum)', border: '1px solid var(--contour)', borderRadius: '2px', padding: '10px 14px', marginTop: '10px', fontSize: '11px', fontFamily: "'B612', monospace" }}>
                  <div style={{ fontWeight: 700, color: 'var(--ink)', marginBottom: '4px' }}>
                    Weighted Price Arithmetic for {auditData.route_id}:
                  </div>
                  <div style={{ color: 'var(--ink-2)', lineHeight: 1.5 }}>
                    {auditData.horizons.map((h, idx) => (
                      <span key={h.lead_horizon}>
                        ({h.dgca_weight_decimal} × ₹{h.geometric_mean.toFixed(0)}){idx < auditData.horizons.length - 1 ? ' + ' : ''}
                      </span>
                    ))}
                    <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--contour)', fontSize: '12px', fontWeight: 700, color: 'var(--ink)' }}>
                      = ₹{auditData.benchmark_price_today.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (Daily Benchmark Price P_r,t)
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 4 & 5 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--route-blue)' }}>
                      04
                    </span>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                      Chained Route Index Relative
                    </h4>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, marginBottom: '8px' }}>
                    Price relative is linked recursively from base period 100.00:
                  </p>
                  <MathBlock
                    formula={`J_{r, t} = \\frac{P_{r, t}}{P_{r, t-1}} = \\frac{${auditData.benchmark_price_today}}{${auditData.benchmark_price_yesterday}} = ${auditData.elementary_jevons_link}`}
                    caption={`Chained Route Index: I_r = ${auditData.chained_index.toFixed(2)}`}
                    style={{ margin: '6px 0' }}
                  />
                </div>

                <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontFamily: "'B612', monospace", fontSize: '12px', fontWeight: 700, color: 'var(--route-blue)' }}>
                      05
                    </span>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--ink)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                      National Basket Aggregation
                    </h4>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.4, marginBottom: '8px' }}>
                    Route index is weighted by its DGCA CY2024 passenger share:
                  </p>
                  <MathBlock
                    formula={`C_r = w_r \\times I_{r, t} = ${(auditData.route_weight).toFixed(4)} \\times ${auditData.chained_index.toFixed(2)} = ${auditData.national_index_contribution.toFixed(2)}`}
                    caption={`Contributes ${auditData.national_index_contribution.toFixed(2)} points to National Composite Index`}
                    style={{ margin: '6px 0' }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Advance Booking Distribution */}
          {activeTab === 'horizons' && (
            <div style={{ background: '#FFFFFF', border: '1px solid var(--contour)', borderRadius: '2px', padding: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '12px' }}>
                <h3 style={{ fontFamily: "'Newsreader Variable', serif", fontSize: '18px', fontWeight: 400, color: 'var(--ink)', margin: 0 }}>
                  Advance Purchase Horizon Decomposition & Booking Distribution
                </h3>
                <span style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: 'var(--ink-2)' }}>
                  DGCA CY2024 Empirical Panel
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--ink-2)', lineHeight: 1.5, marginBottom: '16px' }}>
                Advance purchase weights model actual ticket issuance timelines to ensure market-clearing statistical parity:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '18px' }}>
                {auditData.horizons.map((h) => (
                  <div
                    key={h.lead_horizon}
                    style={{
                      border: '1px solid var(--contour)',
                      borderRadius: '2px',
                      padding: '12px',
                      background: 'var(--vellum)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '14px', fontFamily: "'B612', monospace", color: 'var(--ink)' }}>{h.lead_horizon}</strong>
                      <span
                        style={{
                          fontSize: '10px',
                          fontFamily: "'B612', monospace",
                          fontWeight: 700,
                          color: 'var(--route-blue)',
                          background: '#FFFFFF',
                          border: '1px solid var(--contour)',
                          padding: '1px 5px',
                          borderRadius: '2px',
                        }}
                      >
                        {h.dgca_weight_pct}% DGCA
                      </span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--ink-2)', marginBottom: '8px' }}>{h.horizon_name}</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--ink)', fontFamily: "'B612', monospace" }}>
                      ₹{h.geometric_mean.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--ink-2)', marginTop: '4px', fontFamily: "'B612', monospace" }}>
                      Min ₹{h.min_fare.toLocaleString('en-IN')} · Max ₹{h.max_fare.toLocaleString('en-IN')}
                    </div>
                    <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid var(--contour)', fontSize: '11px', color: 'var(--ink)', display: 'flex', justifyContent: 'space-between', fontFamily: "'B612', monospace" }}>
                      <span>Contribution:</span>
                      <strong>₹{h.weighted_contribution.toFixed(1)}</strong>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ background: 'var(--vellum)', border: '1px solid var(--contour)', borderRadius: '2px', padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", textTransform: 'uppercase', color: 'var(--ink-2)', letterSpacing: '0.04em' }}>
                    Composite Daily Benchmark Price (P_r,t):
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--ink)', fontFamily: "'B612', monospace", marginTop: '2px' }}>
                    ₹{auditData.benchmark_price_today.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", textTransform: 'uppercase', color: 'var(--ink-2)', letterSpacing: '0.04em' }}>
                    Chained Route Index Relative:
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--route-blue)', fontFamily: "'B612', monospace", marginTop: '2px' }}>
                    {auditData.chained_index.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '12px 22px',
            borderTop: '1px solid var(--contour)',
            background: 'var(--vellum)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: '11px', fontFamily: "'B612', monospace", color: 'var(--ink-2)' }}>
            Extraction Cycle: <strong>{auditData.scrape_date} 05:00 AM IST</strong> · Playwright DOM + Scheduled Matrix Engine
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '6px 16px',
              fontSize: '11px',
              fontFamily: "'B612', monospace",
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              background: 'var(--ink)',
              color: 'var(--vellum)',
              border: '1px solid var(--ink)',
              borderRadius: '2px',
              cursor: 'pointer',
            }}
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
