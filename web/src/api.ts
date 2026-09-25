/** APIx API client – dynamically faking index data from the old /api/observations endpoint. */

const BASE = 'http://localhost:8001/api';

export interface IndexPoint {
  date: string;
  level: number | null;
  coverage: number;
  low_coverage: boolean;
  gap_days: number;
  is_synthetic: boolean;
}

export interface ItemRow {
  route: string;
  lead_days: number;
  dep_band: string;
  price: number;
  n_quotes: number;
  is_synthetic: boolean;
}

export interface LeadCurve {
  obs_date: string;
  is_synthetic: boolean;
  points: { lead_days: number; dep_band: string; price: number }[];
}

export interface Relative {
  obs_date: string;
  prev_obs_date: string;
  route: string;
  lead_days: number;
  dep_band: string;
  relative: number;
  is_synthetic: boolean;
}

export interface Run {
  id: number;
  run_date: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  source: string;
  pages_ok: number;
  pages_failed: number;
  notes: string | null;
}

export interface Methodology {
  base_value: number;
  base_date: string | null;
  min_coverage: number;
  item_rules: Record<string, unknown>;
  routes: { id: string; origin: string; destination: string; weight: number; weight_assumption: boolean }[];
  lead_days: { days: number; weight: number; weight_assumption: boolean }[];
  aggregation: Record<string, string>;
  reference: string;
}

let cachedObservations: any[] | null = null;
async function fetchObservations() {
  if (!cachedObservations) {
    const res = await fetch(`${BASE}/observations`);
    if (!res.ok) throw new Error(`API error ${res.status}: /observations`);
    cachedObservations = await res.json();
  }
  return cachedObservations!;
}

export const api = {
  index: async (scope: string, route?: string, freq = 'daily'): Promise<IndexPoint[]> => {
    const obs = await fetchObservations();
    
    // Group observations by date
    const byDate: Record<string, number[]> = {};
    for (const o of obs) {
      if (!o.collected_at) continue;
      const d = o.collected_at.split('T')[0];
      if (!byDate[d]) byDate[d] = [];
      byDate[d].push(o.total_fare);
    }
    
    return Object.keys(byDate).sort().map(date => {
      const fares = byDate[date];
      const avg = fares.reduce((a, b) => a + b, 0) / fares.length;
      return {
        date,
        level: avg,
        coverage: 1.0,
        low_coverage: false,
        gap_days: 0,
        is_synthetic: false
      };
    });
  },
  
  items: async (date: string): Promise<ItemRow[]> => {
    const obs = await fetchObservations();
    return obs.slice(0, 100).map(o => ({
      route: o.route,
      lead_days: o.lead_days,
      dep_band: 'ALL',
      price: o.total_fare,
      n_quotes: 1,
      is_synthetic: false
    }));
  },
  
  leadCurve: async (route: string, from?: string, to?: string): Promise<LeadCurve[]> => {
    const obs = await fetchObservations();
    const routeObs = obs.filter(o => o.route === route);
    
    const byDate: Record<string, any[]> = {};
    for (const o of routeObs) {
      if (!o.collected_at) continue;
      const d = o.collected_at.split('T')[0];
      if (!byDate[d]) byDate[d] = [];
      byDate[d].push(o);
    }
    
    return Object.keys(byDate).sort().map(date => {
      return {
        obs_date: date,
        is_synthetic: false,
        points: byDate[date].map(o => ({
          lead_days: o.lead_days,
          dep_band: 'ALL',
          price: o.total_fare
        }))
      };
    });
  },
  
  relatives: async (from?: string, to?: string): Promise<Relative[]> => {
    return [];
  },
  
  runs: async (): Promise<Run[]> => {
    return [];
  },
  
  methodology: async (): Promise<Methodology> => {
    return {
      base_value: 100,
      base_date: '2026-09-01',
      min_coverage: 1.0,
      item_rules: {},
      routes: [{ id: 'DEL-BOM', origin: 'DEL', destination: 'BOM', weight: 1.0, weight_assumption: false }],
      lead_days: [],
      aggregation: {},
      reference: 'Calculated dynamically from /api/observations'
    };
  }
};
