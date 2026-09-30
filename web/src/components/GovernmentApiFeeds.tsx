import React, { useState } from 'react';
import { API_BASE, API_HOST } from '../api';
import { MoSPILogo, DGCALogo } from './SovereignLogos';

interface EndpointSpec {
  id: string;
  name: string;
  authority: string;
  authorityLogo?: 'mospi' | 'dgca' | 'generic';
  method: 'GET' | 'POST';
  path: string;
  formats: string[];
  description: string;
  sampleParams?: string;
  intendedConsumer: string;
  coicopOrStandard?: string;
}

const ENDPOINTS: EndpointSpec[] = [
  {
    id: 'mospi-cpi-feed',
    name: 'MoSPI / NSO Official CPI Ingestion Feed',
    authority: 'Ministry of Statistics & Programme Implementation',
    authorityLogo: 'mospi',
    method: 'GET',
    path: '/api/v1/nso/cpi-feed',
    formats: ['JSON', 'CSV (MoSPI Young Spec)'],
    description:
      'Official monthly airfare index feed under COICOP 07.3.3.1.2.01. Implements Young aggregation using DGCA passenger volume weights and fixed base 2024 = 100 with T+21 isolated checkpoint.',
    sampleParams: '?format=json',
    intendedConsumer: 'MoSPI Price Statistics Division (PSD) / National Statistical Office (NSO)',
    coicopOrStandard: 'COICOP: 07.3.3.1.2.01 · Weight: 0.02951%',
  },
  {
    id: 'rbi-nowcast',
    name: 'Reserve Bank of India (RBI) Inflation Nowcast Feed',
    authority: 'Monetary Policy & Macroeconomic Research',
    authorityLogo: 'generic',
    method: 'GET',
    path: '/api/v1/rbi/nowcast',
    formats: ['JSON'],
    description:
      'Daily high-frequency airfare inflation momentum, rolling 7-day and 30-day annualized rates, and advance-booking yield elasticity for inflation nowcasting and macro modeling.',
    sampleParams: '',
    intendedConsumer: 'RBI Monetary Policy Committee (MPC) & Department of Economic and Policy Research',
    coicopOrStandard: 'High-Frequency Leading Indicator',
  },
  {
    id: 'airfare-index',
    name: 'AERIX All-India Headline & 60-Route Indices',
    authority: 'DGCA Economic Planning & Aviation Registry',
    authorityLogo: 'dgca',
    method: 'GET',
    path: '/api/v1/airfare-index',
    formats: ['JSON'],
    description:
      'Full composite index timeseries with MoM/YoY growth rates, All-India weighted average fare (INR), and individual indices for all 60 monitored domestic corridors.',
    sampleParams: '',
    intendedConsumer: 'Directorate General of Civil Aviation & Ministry of Civil Aviation',
    coicopOrStandard: 'DGCA Top-60 Route Basket (91.99M Pax Coverage)',
  },
  {
    id: 'observations',
    name: 'Flight-Level Micro-Data Forensic Audit Trail',
    authority: 'Quality Assurance & Regulatory Audit',
    authorityLogo: 'generic',
    method: 'GET',
    path: '/api/observations',
    formats: ['JSON'],
    description:
      'Granular micro-data evidence table showing individual flight quotes, airline codes, flight numbers, base fares, taxes, collection timestamps, and 14-point validation flags.',
    sampleParams: '?limit=10',
    intendedConsumer: 'Statisticians, Regulatory Auditors & Academic Researchers',
    coicopOrStandard: '14-Point Validation & Cryptographic Fingerprints',
  },
];

export function GovernmentApiFeeds() {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResponse, setTestResponse] = useState<{
    id: string;
    status: number;
    latencyMs: number;
    data: any;
  } | null>(null);
  const [isTestingLoading, setIsTestingLoading] = useState(false);

  // Compute full endpoint URL
  const getFullUrl = (path: string, params = '') => {
    // If path starts with /api and API_BASE already ends with /api, avoid double /api
    const base = API_HOST;
    return `${base}${path}${params}`;
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => {
      setCopiedId(null);
    }, 2000);
  };

  const runLiveTest = async (ep: EndpointSpec) => {
    if (testingId === ep.id && testResponse) {
      // Toggle close
      setTestingId(null);
      setTestResponse(null);
      return;
    }

    setTestingId(ep.id);
    setIsTestingLoading(true);
    setTestResponse(null);

    const start = performance.now();
    try {
      const url = getFullUrl(ep.path, ep.sampleParams);
      const res = await fetch(url, { headers: { Accept: 'application/json' } });
      const latency = Math.round(performance.now() - start);
      const data = await res.json();
      setTestResponse({
        id: ep.id,
        status: res.status,
        latencyMs: latency,
        data,
      });
    } catch (err: any) {
      const latency = Math.round(performance.now() - start);
      setTestResponse({
        id: ep.id,
        status: 500,
        latencyMs: latency,
        data: { error: err?.message || 'Failed to fetch live endpoint' },
      });
    } finally {
      setIsTestingLoading(false);
    }
  };

  return (
    <section
      aria-label="Government API Ingestion Layer"
      style={{
        marginTop: 'var(--sp-8)',
        padding: 'var(--sp-6)',
        border: '1px solid var(--contour)',
        borderRadius: '6px',
        background: 'rgba(255, 255, 255, 0.02)',
      }}
    >
      {/* ── Section Header ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 'var(--sp-4)',
          marginBottom: 'var(--sp-5)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)',
              }}
            />
            <span
              style={{
                fontFamily: "'B612', monospace",
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--accent, #38bdf8)',
                fontWeight: 700,
              }}
            >
              Institutional Data Feeds & Government Ingestion APIs
            </span>
          </div>
          <h2
            style={{
              fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
              fontSize: '24px',
              fontWeight: 400,
              color: 'var(--ink)',
              margin: '0 0 6px 0',
            }}
          >
            Direct Integration Feeds for MoSPI, RBI & Aviation Planning
          </h2>
          <p
            style={{
              fontFamily: "'Newsreader Variable', 'Newsreader', Georgia, serif",
              fontSize: '15px',
              color: 'var(--ink-2)',
              margin: 0,
              maxWidth: '80ch',
              lineHeight: 1.45,
            }}
          >
            Automated, read-only REST endpoints configured for national statistical ingestion. Standardized to eliminate
            sampling delays, delivering instant JSON and MoSPI-compliant CSV feeds backed by dual-tier Redis caching.
          </p>
        </div>

        {/* Documentation & Sandbox Jump Links */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <a
            href={`${API_HOST}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid var(--contour)',
              background: 'var(--card-bg, rgba(255, 255, 255, 0.04))',
              color: 'var(--ink)',
              fontFamily: "'B612', monospace",
              fontSize: '12px',
              textDecoration: 'none',
              fontWeight: 600,
              transition: 'border-color 0.2s, background 0.2s',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Interactive Swagger UI (/docs) &rarr;
          </a>

          <a
            href={`${API_HOST}/redoc`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid var(--contour)',
              background: 'var(--card-bg, rgba(255, 255, 255, 0.04))',
              color: 'var(--ink-2)',
              fontFamily: "'B612', monospace",
              fontSize: '12px',
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            ReDoc Specification (/redoc)
          </a>
        </div>
      </div>

      {/* ── Architecture SLA Strip ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--sp-3)',
          padding: 'var(--sp-3) var(--sp-4)',
          background: 'rgba(0, 0, 0, 0.2)',
          border: '1px solid var(--contour)',
          borderRadius: '4px',
          marginBottom: 'var(--sp-5)',
          fontFamily: "'B612', monospace",
          fontSize: '11px',
          color: 'var(--ink-2)',
        }}
      >
        <div>
          <span style={{ color: 'var(--ink)', fontWeight: 700 }}>Latency SLA:</span> &lt;15ms (Render Redis L2 Cache)
        </div>
        <div>
          <span style={{ color: 'var(--ink)', fontWeight: 700 }}>Persistence:</span> Neon Serverless PostgreSQL
        </div>
        <div>
          <span style={{ color: 'var(--ink)', fontWeight: 700 }}>Access Rule:</span> Read-Only · Zero PII
        </div>
        <div>
          <span style={{ color: 'var(--ink)', fontWeight: 700 }}>Data Standard:</span> COICOP 07.3.3.1.2.01
        </div>
      </div>

      {/* ── Endpoint Grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 'var(--sp-4)' }}>
        {ENDPOINTS.map((ep) => {
          const fullUrl = getFullUrl(ep.path, ep.sampleParams);
          const curlSnippet = `curl -s "${fullUrl}" | jq .`;
          const isTestingThis = testingId === ep.id;

          return (
            <div
              key={ep.id}
              style={{
                border: '1px solid var(--contour)',
                borderRadius: '6px',
                padding: 'var(--sp-4)',
                background: 'var(--card-bg, rgba(255, 255, 255, 0.02))',
                transition: 'border-color 0.2s',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                  gap: 'var(--sp-3)',
                  marginBottom: 'var(--sp-2)',
                }}
              >
                {/* Method & Route */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '3px',
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: '#10b981',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                    }}
                  >
                    {ep.method}
                  </span>
                  <code
                    style={{
                      fontFamily: "'B612', monospace",
                      fontSize: '14px',
                      fontWeight: 700,
                      color: 'var(--ink)',
                      background: 'rgba(0, 0, 0, 0.3)',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: '1px solid var(--contour)',
                    }}
                  >
                    {ep.path}
                    {ep.sampleParams && (
                      <span style={{ color: 'var(--accent, #38bdf8)', fontWeight: 400 }}>{ep.sampleParams}</span>
                    )}
                  </code>

                  {/* Formats pill */}
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {ep.formats.map((fmt) => (
                      <span
                        key={fmt}
                        style={{
                          fontFamily: "'B612', monospace",
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '3px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          color: 'var(--ink-2)',
                          border: '1px solid var(--contour)',
                        }}
                      >
                        {fmt}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Target Stakeholder Badge */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {ep.authorityLogo === 'mospi' && <MoSPILogo size={16} />}
                  {ep.authorityLogo === 'dgca' && <DGCALogo size={16} />}
                  <span
                    style={{
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      color: 'var(--ink-2)',
                      fontWeight: 600,
                    }}
                  >
                    {ep.authority}
                  </span>
                </div>
              </div>

              {/* Title & Description */}
              <div style={{ marginBottom: 'var(--sp-3)' }}>
                <div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '14px', marginBottom: '4px' }}>
                  {ep.name}
                </div>
                <p style={{ margin: 0, fontSize: '13px', color: 'var(--ink-2)', lineHeight: 1.45 }}>
                  {ep.description}
                </p>
              </div>

              {/* Metadata strip */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 'var(--sp-2)',
                  paddingTop: 'var(--sp-2)',
                  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                  fontFamily: "'B612', monospace",
                  fontSize: '11px',
                  color: 'var(--ink-2)',
                }}
              >
                <div>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>Consumer:</span> {ep.intendedConsumer}
                  {ep.coicopOrStandard && (
                    <span style={{ marginLeft: '8px', color: 'var(--route-blue, #60a5fa)' }}>
                      [{ep.coicopOrStandard}]
                    </span>
                  )}
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(curlSnippet, `${ep.id}-curl`)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--contour)',
                      borderRadius: '3px',
                      padding: '4px 8px',
                      color: 'var(--ink-2)',
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {copiedId === `${ep.id}-curl` ? '✓ Copied cURL' : 'Copy cURL'}
                  </button>

                  <button
                    type="button"
                    onClick={() => copyToClipboard(fullUrl, `${ep.id}-url`)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--contour)',
                      borderRadius: '3px',
                      padding: '4px 8px',
                      color: 'var(--ink-2)',
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {copiedId === `${ep.id}-url` ? '✓ Copied URL' : 'Copy URL'}
                  </button>

                  <button
                    type="button"
                    onClick={() => runLiveTest(ep)}
                    style={{
                      background: isTestingThis ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.06)',
                      border: isTestingThis ? '1px solid var(--accent, #38bdf8)' : '1px solid var(--contour)',
                      borderRadius: '3px',
                      padding: '4px 10px',
                      color: isTestingThis ? 'var(--accent, #38bdf8)' : 'var(--ink)',
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    {isTestingThis ? 'Hide Live Preview' : '⚡ Test Live Response'}
                  </button>

                  <a
                    href={fullUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'none',
                      border: 'none',
                      padding: '4px 6px',
                      color: 'var(--accent, #38bdf8)',
                      fontFamily: "'B612', monospace",
                      fontSize: '11px',
                      textDecoration: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    Open &rarr;
                  </a>
                </div>
              </div>

              {/* ── Expandable Live Preview Drawer ── */}
              {isTestingThis && (
                <div
                  style={{
                    marginTop: 'var(--sp-3)',
                    padding: 'var(--sp-3)',
                    background: '#090d14',
                    border: '1px solid var(--contour)',
                    borderRadius: '4px',
                    fontFamily: "'B612', monospace",
                    fontSize: '11px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px',
                      paddingBottom: '4px',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ color: 'var(--ink-2)' }}>Live Query Response:</span>
                      {isTestingLoading ? (
                        <span style={{ color: 'var(--accent, #38bdf8)' }}>Executing GET request...</span>
                      ) : (
                        <span
                          style={{
                            color: testResponse?.status === 200 ? '#10b981' : '#f87171',
                            fontWeight: 700,
                          }}
                        >
                          HTTP {testResponse?.status} OK
                        </span>
                      )}
                    </div>
                    {testResponse && (
                      <span style={{ color: 'var(--ink-2)' }}>Response Time: {testResponse.latencyMs} ms</span>
                    )}
                  </div>

                  {isTestingLoading ? (
                    <div style={{ padding: '12px 0', color: 'var(--ink-2)' }}>Connecting to backend feed...</div>
                  ) : testResponse?.data ? (
                    <pre
                      style={{
                        margin: 0,
                        maxHeight: '220px',
                        overflowY: 'auto',
                        color: '#93c5fd',
                        lineHeight: 1.4,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {JSON.stringify(testResponse.data, null, 2)}
                    </pre>
                  ) : null}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
