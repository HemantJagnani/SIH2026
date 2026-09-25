/**
 * indexMath.ts — client-side recompute of the APIx index.
 *
 * Mirrors the Python pipeline exactly:
 *   1. Bands → (route, lead) : geometric mean of relatives within the band
 *   2. Lead windows → route  : weighted geometric mean
 *   3. Routes → overall      : weighted arithmetic mean
 *   4. Chain from 100
 *   5. Weights renormalised over what is present (missing routes/leads excluded)
 */

import type { IndexPoint, Relative } from '../api';

export const ROUTES = ['DEL-BOM', 'DEL-BLR', 'BOM-BLR'] as const;
export type Route = typeof ROUTES[number];

export const DEFAULT_LEAD_WEIGHTS: Record<number, number> = {
  1: 0.25, 7: 0.25, 15: 0.25, 30: 0.25,
};

export const DEFAULT_ROUTE_WEIGHTS: Record<string, number> = {
  'DEL-BOM': 0.5,
  'DEL-BLR': 0.3,
  'BOM-BLR': 0.2,
};

function geometricMean(vals: number[]): number {
  if (vals.length === 0) return 1;
  return Math.exp(vals.reduce((s, v) => s + Math.log(v), 0) / vals.length);
}

function weightedGeometricMean(
  entries: { value: number; weight: number }[],
): number {
  const total = entries.reduce((s, e) => s + e.weight, 0);
  if (total === 0) return 1;
  return Math.exp(
    entries.reduce((s, e) => s + (e.weight / total) * Math.log(e.value), 0),
  );
}

export function recomputeIndex(
  relatives: Relative[],
  routeWeights: Record<string, number> = DEFAULT_ROUTE_WEIGHTS,
  leadWeights: Record<number, number> = DEFAULT_LEAD_WEIGHTS,
  baseValue = 100,
): IndexPoint[] {
  // Group by date
  const byDate = new Map<string, Relative[]>();
  for (const r of relatives) {
    const arr = byDate.get(r.obs_date) ?? [];
    arr.push(r);
    byDate.set(r.obs_date, arr);
  }

  const dates = [...byDate.keys()].sort();
  const result: IndexPoint[] = [];
  let prevLevel = baseValue;

  for (const date of dates) {
    const dayRels = byDate.get(date)!;

    // Step 1: bands → (route, lead) via geometric mean
    const rlJevons = new Map<string, number>();
    const rlGroups = new Map<string, number[]>();
    for (const r of dayRels) {
      const k = `${r.route}|${r.lead_days}`;
      const arr = rlGroups.get(k) ?? [];
      arr.push(r.relative);
      rlGroups.set(k, arr);
    }
    for (const [k, rels] of rlGroups) {
      rlJevons.set(k, geometricMean(rels));
    }

    // Step 2: lead windows → route via weighted geometric mean (renorm over present)
    const routeRelatives = new Map<string, number>();
    for (const route of ROUTES) {
      const present = [...rlJevons.entries()]
        .filter(([k]) => k.startsWith(`${route}|`))
        .map(([k, v]) => ({ lead: Number(k.split('|')[1]), value: v }))
        .filter(({ lead }) => leadWeights[lead] != null && leadWeights[lead] > 0);

      if (present.length === 0) continue;

      const wgm = weightedGeometricMean(
        present.map(({ lead, value }) => ({ value, weight: leadWeights[lead] })),
      );
      routeRelatives.set(route, wgm);
    }

    if (routeRelatives.size === 0) continue;

    // Step 3: routes → overall via weighted arithmetic mean (renorm over present)
    const presentRoutes = [...routeRelatives.entries()].filter(
      ([r]) => routeWeights[r] != null && routeWeights[r] > 0,
    );
    const totalRW = presentRoutes.reduce((s, [r]) => s + routeWeights[r], 0);
    if (totalRW === 0) continue;

    const overallRel = presentRoutes.reduce(
      (s, [r, v]) => s + (routeWeights[r] / totalRW) * v,
      0,
    );

    // Step 4: chain
    const level = prevLevel * overallRel;
    prevLevel = level;

    const isSynthetic = dayRels.every(r => r.is_synthetic);
    const coverage = Math.min(
      1,
      rlGroups.size / (ROUTES.length * Object.keys(leadWeights).length * 3),
    );

    result.push({
      date,
      level,
      coverage,
      low_coverage: false,
      gap_days: 0,
      is_synthetic: isSynthetic,
    });
  }

  return result;
}

/** Compute the max absolute deviation (in index points) between two series. */
export function maxDeviation(
  a: IndexPoint[],
  b: IndexPoint[],
): { maxDev: number; maxDate: string | null } {
  const bMap = new Map(b.map(p => [p.date, p.level]));
  let maxDev = 0;
  let maxDate: string | null = null;

  for (const p of a) {
    if (p.level == null) continue;
    const bLevel = bMap.get(p.date);
    if (bLevel == null) continue;
    const dev = Math.abs(p.level - bLevel);
    if (dev > maxDev) {
      maxDev = dev;
      maxDate = p.date;
    }
  }

  return { maxDev, maxDate };
}
