/**
 * MethodView — prose-first, no raw config keys.
 * Follows §7 of the revamp brief exactly.
 */
import { useState, useEffect } from 'react';
import { api, type Methodology, type Run, type Relative } from '../api';

const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;
const LEAD_DAYS = [1, 7, 15, 30] as const;

function fmtNum(n: number, dp = 4): string {
  return n.toFixed(dp);
}

function fmtDateShort(s: string): string {
  return new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', timeZone: 'UTC',
  });
}

function fmtDateTime(s: string | null): string {
  if (!s) return '—';
  return new Date(s).toLocaleString('en-GB', {
    day: 'numeric', month: 'short',
    hour: '2-digit', minute: '2-digit',
  });
}

function geometricMean(vals: number[]): number {
  if (vals.length === 0) return 1;
  return Math.exp(vals.reduce((s, v) => s + Math.log(v), 0) / vals.length);
}

/** Build a live worked example from the latest day's relatives. */
function buildWorkedExample(
  relatives: Relative[],
  method: Methodology,
): React.ReactNode {
  if (relatives.length === 0) return null;

  const latestDate = [...new Set(relatives.map(r => r.obs_date))].sort().at(-1);
  if (!latestDate) return null;

  const dayRels = relatives.filter(r => r.obs_date === latestDate);

  // Find the route with the largest contribution
  const routeRelatives: Record<string, number> = {};
  const routeBandData: Record<string, { lead: number; bands: number[]; jevons: number }[]> = {};

  for (const route of ROUTES) {
    const routeRels = dayRels.filter(r => r.route === route);
    const byLead: Record<number, number[]> = {};
    for (const r of routeRels) {
      (byLead[r.lead_days] ??= []).push(r.relative);
    }

    const leadJevons: { lead: number; bands: number[]; jevons: number }[] = [];
    for (const [leadStr, vals] of Object.entries(byLead)) {
      const lead = Number(leadStr);
      const j = geometricMean(vals);
      leadJevons.push({ lead, bands: vals, jevons: j });
    }

    if (leadJevons.length === 0) continue;
    routeBandData[route] = leadJevons;

    const leadWeightMap: Record<number, number> = {};
    for (const ld of method.lead_days) leadWeightMap[ld.days] = ld.weight;
    const presentLeads = leadJevons.filter(lj => leadWeightMap[lj.lead] > 0);
    const totalW = presentLeads.reduce((s, lj) => s + leadWeightMap[lj.lead], 0);
    if (totalW === 0) continue;
    const wgm = Math.exp(
      presentLeads.reduce((s, lj) => s + (leadWeightMap[lj.lead] / totalW) * Math.log(lj.jevons), 0),
    );
    routeRelatives[route] = wgm;
  }

  if (Object.keys(routeRelatives).length === 0) return null;

  // Route weights
  const rwMap: Record<string, number> = {};
  for (const r of method.routes) rwMap[r.id] = r.weight;
  const totalRW = Object.entries(routeRelatives).reduce((s, [r]) => s + (rwMap[r] ?? 0), 0);

  const contributions = Object.entries(routeRelatives).map(([route, rel]) => ({
    route,
    rel,
    contrib: (rwMap[route] ?? 0) / totalRW * (rel - 1),
  }));

  const biggestRoute = contributions.reduce((best, c) =>
    Math.abs(c.contrib) > Math.abs(best.contrib) ? c : best,
  );

  const exampleData = routeBandData[biggestRoute.route] ?? [];

  return (
    <div className="worked-example">
      <h3>Worked example — {fmtDateShort(latestDate)}, route {biggestRoute.route}</h3>
      <p style={{ fontSize: 'var(--t-ui)', color: 'var(--ink-2)', marginBottom: 'var(--sp-4)' }}>
        This route had the largest contribution to the day's change.
        Each step below uses the actual numbers from the index.
      </p>

      <div className="worked-example-rows">
        <div className="worked-row" style={{ fontWeight: 700, color: 'var(--ink-2)' }}>
          <span>Step</span>
          <span>Value</span>
          <span>Note</span>
        </div>

        {exampleData.sort((a, b) => a.lead - b.lead).map(({ lead, bands, jevons }) => (
          <div key={lead} className="worked-row">
            <span className="worked-row-label">{lead === 1 ? '1 day' : `${lead} days`} bands</span>
            <span className="font-num">{fmtNum(jevons, 4)}</span>
            <span style={{ color: 'var(--ink-2)', fontSize: 'var(--t-axis)' }}>
              geom. mean of {bands.length} relative{bands.length !== 1 ? 's' : ''} ({bands.map(b => fmtNum(b, 3)).join(', ')})
            </span>
          </div>
        ))}

        <div className="worked-row">
          <span className="worked-row-label">{biggestRoute.route} route relative</span>
          <span className="font-num">{fmtNum(biggestRoute.rel, 4)}</span>
          <span style={{ color: 'var(--ink-2)', fontSize: 'var(--t-axis)' }}>
            weighted geom. mean of lead-window Jevons
          </span>
        </div>

        <div className="worked-row">
          <span className="worked-row-label">Contribution to day's change</span>
          <span className="font-num">{biggestRoute.contrib >= 0 ? '+' : ''}{fmtNum(biggestRoute.contrib * 100, 2)} pp</span>
          <span style={{ color: 'var(--ink-2)', fontSize: 'var(--t-axis)' }}>
            route weight × (relative − 1)
          </span>
        </div>
      </div>
    </div>
  );
}

interface Props { runs: Run[] }

export default function MethodView({ runs }: Props) {
  const [method, setMethod] = useState<Methodology | null>(null);
  const [relatives, setRelatives] = useState<Relative[]>([]);

  useEffect(() => {
    api.methodology().then(setMethod).catch(() => {});
    api.relatives().then(setRelatives).catch(() => {});
  }, []);

  return (
    <div className="page">
      <h1>Method</h1>

      <div className="method-prose">

        {/* §7.1 What this measures */}
        <h2>What this measures</h2>
        <p>
          The APIx index tracks displayed economy fares for a fixed set of nonstop flights on three
          Indian domestic routes, not what travellers actually paid. Each day, the cheapest nonstop
          economy fare for a departure at each lead time is recorded. The index measures how these
          displayed fares move over time.
        </p>
        <p>
          The base date is the first day with sufficient coverage; the index starts at 100 on that date.
        </p>

        {/* §7.2 How the index is built */}
        <h2>How the index is built</h2>
        <ol>
          <li>
            Each flight group (route, days ahead, departure time band) is priced at its cheapest
            nonstop economy fare each day.
          </li>
          <li>
            Each group's price is compared with its previous price. The change is a ratio
            (today's fare divided by yesterday's fare).
          </li>
          <li>
            Ratios for the departure bands within a lead window are combined with a geometric mean
            (Jevons method), giving one ratio per route and lead window.
          </li>
          <li>
            Lead windows are combined into a route relative with a weighted geometric mean, using
            the lead-window weights below.
          </li>
          <li>
            Route relatives are combined into the overall figure with a weighted arithmetic mean,
            using the route weights below. The result is chained forward from 100.
          </li>
        </ol>

        {/* §7.3 Live worked example */}
        {method && relatives.length > 0 && buildWorkedExample(relatives, method)}

        {/* §7.4 Rules used */}
        <h2>Rules used</h2>
        <dl className="method-dl">
          <dt>Fare class</dt>
          <dd>Economy</dd>
          <dt>Flights counted</dt>
          <dd>Nonstop only</dd>
          <dt>Price used for each group</dt>
          <dd>Lowest available fare</dd>
          <dt>Unusual fares</dt>
          <dd>Kept in the index and flagged for review</dd>
        </dl>

        {/* §7.5 Weights */}
        <h2>Weights</h2>
        {method ? (
          <>
            <p style={{ marginBottom: 'var(--sp-4)' }}>Route weights:</p>
            <table className="method-table" aria-label="Route weights">
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Weight</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {method.routes.map(r => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td className="font-num">{(r.weight * 100).toFixed(0)}%</td>
                    <td>
                      {r.weight_assumption
                        ? <span className="assumed-word">assumed</span>
                        : 'DGCA city-pair data'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p style={{ marginBottom: 'var(--sp-4)', marginTop: 'var(--sp-6)' }}>Lead-window weights:</p>
            <table className="method-table" aria-label="Lead-window weights">
              <thead>
                <tr>
                  <th>Days before departure</th>
                  <th>Weight</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {method.lead_days.map(ld => (
                  <tr key={ld.days}>
                    <td className="font-num">{ld.days === 1 ? '1 day' : `${ld.days} days`}</td>
                    <td className="font-num">{(ld.weight * 100).toFixed(0)}%</td>
                    <td>
                      {ld.weight_assumption
                        ? <span className="assumed-word">assumed</span>
                        : 'measured'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="method-footnote">
              Route weights are placeholders until replaced with passenger shares from DGCA city-pair data.
              Lead-window weights are equal by assumption; the what-if bar on the Index page shows how much they matter.
            </p>
          </>
        ) : (
          <div className="loading">Loading…</div>
        )}

        {/* §7.6 Limits */}
        <h2>Limits</h2>
        <p>
          This index measures displayed fares, not what travellers actually paid. Seat availability,
          loyalty pricing, and ancillary fees are all excluded.
        </p>
        <p>
          A short real history cannot be meaningfully compared with official monthly series such
          as the CPI Transport component. Validation rests on the synthetic recovery test, which
          confirms the aggregation pipeline is internally consistent.
        </p>
        <p>
          The index currently uses one data source. A production system would use data-sharing
          agreements with airlines or GDS providers, not web scraping.
        </p>
        <p>
          Day-over-day relatives include weekday effects because the departure date moves by
          one day each day — Saturday departures are priced differently from Tuesday departures.
          A holiday-adjusted version is not yet implemented.
        </p>

        {/* §7.7 Collection record */}
        <details className="run-log-details">
          <summary>All runs ({runs.length})</summary>
          {runs.length === 0 ? (
            <p style={{ marginTop: 'var(--sp-4)', color: 'var(--ink-2)', fontSize: 'var(--t-ui)' }}>
              No runs recorded yet. The first run is scheduled for 05:00 IST.
            </p>
          ) : (
            <table className="run-log-table" aria-label="All collection runs">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Finished</th>
                  <th>Pages ok</th>
                  <th>Pages failed</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {runs.map(r => (
                  <tr key={r.id}>
                    <td className="font-num">{r.run_date}</td>
                    <td>{r.status}</td>
                    <td className="font-num">{fmtDateTime(r.started_at)}</td>
                    <td className="font-num">{fmtDateTime(r.finished_at)}</td>
                    <td className="font-num">{r.pages_ok}</td>
                    <td className="font-num">{r.pages_failed}</td>
                    <td style={{ color: 'var(--ink-2)' }}>{r.notes ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </details>
      </div>
    </div>
  );
}
