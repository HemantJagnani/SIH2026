import React, { useState, useEffect } from 'react';
import { api, type CoverageResponse } from '../api';

interface OverviewViewProps {
  onNavigate: (tab: 'index' | 'curves' | 'method' | 'flow') => void;
}

export default function OverviewView({ onNavigate }: OverviewViewProps) {
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);
  const [coverageLoading, setCoverageLoading] = useState(true);

  useEffect(() => {
    api.getCoverage()
      .then(setCoverage)
      .catch(() => setCoverage(null))
      .finally(() => setCoverageLoading(false));
  }, []);

  const routesWithData = coverage?.routes_with_data ?? [];

  return (
    <div
      className="page"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--sp-6)',
      }}
    >
      <div>
        <h1
          style={{
            fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
            fontSize: 'var(--t-headline)',
            lineHeight: 1.15,
            fontWeight: 400,
            color: 'var(--ink)',
            marginBottom: 'var(--sp-2)',
          }}
        >
          AERIX
        </h1>
        <p
          style={{
            fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
            fontSize: 'var(--t-prose)',
            lineHeight: 1.4,
            color: 'var(--ink-2)',
          }}
        >
          A daily airfare price index for Indian domestic routes, built the way the CPI is built.
        </p>
      </div>

      {/* Aeronautical Navigation Chart Banner Illustration */}
      <div
        style={{
          border: '1px solid var(--contour)',
          background: '#fff',
          overflow: 'hidden',
          marginBottom: 'var(--sp-2)',
        }}
      >
        <img
          src="/aeronautical_chart_banner.jpg"
          alt="Aeronautical navigation chart of Indian scheduled domestic airspace"
          style={{
            width: '100%',
            maxHeight: '340px',
            objectFit: 'cover',
            display: 'block',
          }}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '8px 14px',
            background: 'var(--vellum)',
            borderTop: '1px solid var(--contour)',
            fontSize: '11px',
            fontFamily: "'B612', monospace",
            color: 'var(--ink-2)',
          }}
        >
          <span style={{ fontWeight: 700, color: 'var(--ink)' }}>
            FIGURE 1 · AERONAUTICAL NAVIGATION CHART (IND DOMESTIC FIR AIRSPACE)
          </span>
          <span>
            DGCA CY2024 BASKET · 60 CORRIDORS · 91,995,307 SCHEDULED PASSENGERS
          </span>
        </div>
      </div>

      <p className="prose" style={{ color: 'var(--ink)' }}>
        Prices for the same flights move by 200 to 400 percent depending on advance booking timing.
        Official monthly inflation statistics cannot capture this dynamic dispersion. AERIX tracks the official
        <strong> DGCA CY2024 Top-60 Route Basket</strong> (representing 91.99M annual passengers; 57.02% national coverage)
        across <strong>6 advance-purchase horizons</strong> (T+1, T+7, T+15, <strong>T+21 MoSPI Checkpoint</strong>, T+30, and T+45)
        forming a rigorous 360-cell matrix. Price relatives are chained using micro-founded Jevons elementary indices and
        MoSPI Young higher-level aggregation, strictly conforming to MoSPI CPI 2024 (Base 2024=100) and Eurostat HICP standards.
      </p>

      <div>
        <h2
          style={{
            fontSize: 'var(--t-ui)',
            fontWeight: 700,
            color: 'var(--ink)',
            marginBottom: 'var(--sp-3)',
          }}
        >
          Production Data &amp; Basket Status
        </h2>
        {coverageLoading ? (
          <p style={{ fontFamily: "'B612', monospace", fontSize: 'var(--t-ui)', color: 'var(--ink-2)' }}>
            Loading basket coverage...
          </p>
        ) : coverage ? (
          <>
            {/* Summary stats bar */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: 'var(--sp-3)',
                marginBottom: 'var(--sp-4)',
                fontFamily: "'B612', monospace",
                fontSize: 'var(--t-ui)',
              }}
            >
              {[
                { label: 'Routes scraped', val: `${coverage.routes_with_data_count} / 60` },
                { label: 'Cells populated', val: `${coverage.populated_cells} / ${coverage.total_target_cells}` },
                { label: 'Coverage', val: `${coverage.coverage_percent.toFixed(1)}%` },
                { label: 'Raw observations', val: coverage.total_raw_observations.toLocaleString() },
              ].map(({ label, val }) => (
                <div key={label} style={{ borderLeft: '2px solid var(--ink)', paddingLeft: 'var(--sp-3)' }}>
                  <div style={{ fontWeight: 700, color: 'var(--ink)', fontSize: '16px' }}>{val}</div>
                  <div style={{ color: 'var(--ink-2)', fontSize: '12px', marginTop: '2px' }}>{label}</div>
                </div>
              ))}
            </div>
            {/* Route list */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--sp-2)',
                fontFamily: "'B612', monospace",
                fontSize: 'var(--t-ui)',
                maxHeight: '260px',
                overflowY: 'auto',
              }}
            >
              {routesWithData.map((route) => (
                <div
                  key={route}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '90px 1fr',
                    gap: 'var(--sp-4)',
                    paddingBottom: 'var(--sp-1)',
                    borderBottom: '1px solid var(--contour)',
                  }}
                >
                  <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{route}</span>
                  <span style={{ color: 'var(--ink-2)' }}>real fares collected · Sep 2026 production run</span>
                </div>
              ))}
            </div>
            {coverage.routes_with_data_count < 60 && (
              <div
                style={{
                  paddingTop: 'var(--sp-2)',
                  fontSize: '12px',
                  color: 'var(--ink-2)',
                }}
              >
                + {60 - coverage.routes_with_data_count} additional scheduled routes in the DGCA Top-60 basket.
              </div>
            )}
          </>
        ) : (
          <p style={{ fontFamily: "'B612', monospace", fontSize: 'var(--t-ui)', color: 'var(--ink-2)' }}>
            Data unavailable — unable to retrieve the latest result.
          </p>
        )}
      </div>

      <p
        style={{
          fontFamily: "'B612', monospace",
          fontSize: 'var(--t-ui)',
          color: 'var(--ink-2)',
          lineHeight: 1.5,
        }}
      >
        Designed as an experimental, high-frequency index compatible with MoSPI CPI 2024 methodology. Explore the Method section for complete mathematical formulations, weight registry, and validation gates.
      </p>

      {/* In-page navigation links — per §4.1, the only allowed arrows in the app */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--sp-8)',
          marginTop: 'var(--sp-2)',
        }}
      >
        <button
          onClick={() => onNavigate('index')}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            fontFamily: "'B612', monospace",
            fontSize: 'var(--t-ui)',
            fontWeight: 700,
            color: 'var(--ink)',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
        >
          See today's index &rarr;
        </button>

        <button
          onClick={() => onNavigate('flow')}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            fontFamily: "'B612', monospace",
            fontSize: 'var(--t-ui)',
            fontWeight: 700,
            color: 'var(--route-blue)',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
        >
          How it's calculated (Visual Flowchart) &rarr;
        </button>

        <button
          onClick={() => onNavigate('method')}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            fontFamily: "'B612', monospace",
            fontSize: 'var(--t-ui)',
            fontWeight: 700,
            color: 'var(--ink)',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
          onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
        >
          Read full econometric spec &rarr;
        </button>
      </div>
    </div>
  );
}
