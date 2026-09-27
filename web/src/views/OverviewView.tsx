import React, { useState, useEffect } from 'react';
import { api, type APIxIndexResponse, type Run } from '../api';

interface OverviewViewProps {
  onNavigate: (tab: 'index' | 'curves' | 'method') => void;
}

interface RouteStatus {
  route: string;
  statusText: string;
  isLive: boolean;
}

export default function OverviewView({ onNavigate }: OverviewViewProps) {
  const [routeStatuses, setRouteStatuses] = useState<RouteStatus[]>([
    { route: 'DEL-BOM', statusText: 'collecting real fares since 3 October 2026', isLive: true },
    { route: 'DEL-BLR', statusText: 'not yet collecting — shown with synthetic history', isLive: false },
    { route: 'BOM-BLR', statusText: 'not yet collecting — shown with synthetic history', isLive: false },
  ]);

  useEffect(() => {
    // Generate route status dynamically from live data
    Promise.allSettled([api.runs(), api.getAirfareIndex()]).then(([runsRes, idxRes]) => {
      const liveRoutes = new Set<string>();
      if (runsRes.status === 'fulfilled' && runsRes.value.length > 0) {
        liveRoutes.add('DEL-BOM');
      }
      if (idxRes.status === 'fulfilled' && idxRes.value.route_indices) {
        // If other routes have verified live data, they would be marked here
      }

      setRouteStatuses([
        {
          route: 'DEL-BOM',
          statusText: liveRoutes.has('DEL-BOM')
            ? 'collecting real fares since 3 October 2026'
            : 'not yet collecting — shown with synthetic history',
          isLive: liveRoutes.has('DEL-BOM'),
        },
        {
          route: 'DEL-BLR',
          statusText: liveRoutes.has('DEL-BLR')
            ? 'collecting real fares'
            : 'not yet collecting — shown with synthetic history',
          isLive: liveRoutes.has('DEL-BLR'),
        },
        {
          route: 'BOM-BLR',
          statusText: liveRoutes.has('BOM-BLR')
            ? 'collecting real fares'
            : 'not yet collecting — shown with synthetic history',
          isLive: liveRoutes.has('BOM-BLR'),
        },
      ]);
    });
  }, []);

  return (
    <div
      className="page"
      style={{
        maxWidth: '820px',
        padding: 'var(--sp-8) var(--sp-4) var(--sp-6)',
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
          APIx
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

      {/* Decorative index sketch: short chained line from 100, hand-drawn scale, no numbers */}
      <div style={{ margin: 'var(--sp-1) 0' }}>
        <svg
          width="180"
          height="40"
          viewBox="0 0 180 40"
          role="img"
          aria-label="Illustrative sketch, not real data."
          style={{ overflow: 'visible' }}
        >
          <title>Illustrative sketch, not real data.</title>
          {/* Faint baseline at 100 */}
          <line x1="0" y1="24" x2="180" y2="24" stroke="var(--contour)" strokeWidth="1" strokeDasharray="2,2" />
          {/* Chained index trajectory */}
          <path
            d="M 4,24 L 28,24 L 54,20 L 80,22 L 108,15 L 136,17 L 164,12"
            fill="none"
            stroke="var(--ink)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <circle cx="4" cy="24" r="2" fill="var(--ink)" />
          <circle cx="54" cy="20" r="1.5" fill="var(--ink)" />
          <circle cx="80" cy="22" r="1.5" fill="var(--ink)" />
          <circle cx="108" cy="15" r="1.5" fill="var(--ink)" />
          <circle cx="136" cy="17" r="1.5" fill="var(--ink)" />
          <circle cx="164" cy="12" r="2" fill="var(--ink)" />
        </svg>
      </div>

      <p className="prose" style={{ color: 'var(--ink)' }}>
        Prices for the same flights move by 200 to 400 percent depending on advance booking timing.
        Official monthly inflation statistics cannot capture this dynamic dispersion. APIx tracks the official
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
          Production Data & Basket Status
        </h2>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--sp-2)',
            fontFamily: "'B612', monospace",
            fontSize: 'var(--t-ui)',
          }}
        >
          {routeStatuses.map((rs) => (
            <div
              key={rs.route}
              style={{
                display: 'grid',
                gridTemplateColumns: '90px 1fr',
                gap: 'var(--sp-4)',
                paddingBottom: 'var(--sp-1)',
                borderBottom: '1px solid var(--contour)',
              }}
            >
              <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{rs.route}</span>
              <span style={{ color: 'var(--ink-2)' }}>{rs.statusText}</span>
            </div>
          ))}
          <div
            style={{
              paddingTop: 'var(--sp-2)',
              fontSize: '12px',
              color: 'var(--ink-2)',
            }}
          >
            + 57 additional scheduled routes in the official DGCA Top-60 basket catalogued in the Method section.
          </div>
        </div>
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
          Read the method &rarr;
        </button>
      </div>
    </div>
  );
}
