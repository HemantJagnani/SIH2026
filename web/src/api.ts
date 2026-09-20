/** APIx API client – fetches from the FastAPI backend. */

const BASE = 'http://localhost:8000/api';

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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  index: (scope: string, route?: string, freq = 'daily') => {
    const params = new URLSearchParams({ scope, freq });
    if (route) params.set('route', route);
    return get<IndexPoint[]>(`/index?${params}`);
  },
  items: (date: string) => get<ItemRow[]>(`/items?obs_date=${date}`),
  leadCurve: (route: string, from?: string, to?: string) => {
    const params = new URLSearchParams({ route });
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return get<LeadCurve[]>(`/lead-curve?${params}`);
  },
  relatives: (from?: string, to?: string) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return get<Relative[]>(`/relatives?${params}`);
  },
  runs: () => get<Run[]>('/runs'),
  methodology: () => get<Methodology>('/methodology'),
};
