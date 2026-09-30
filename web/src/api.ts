/**
 * Production AERIX Client for Frontend Dashboard.
 * Interacts with FastAPI backend at http://localhost:8000
 */

const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://localhost:8000';
const cleanBase = rawBase.replace(/\/+$/, '');
const BASE = cleanBase.endsWith('/api') ? cleanBase : `${cleanBase}/api`;

export const API_BASE = BASE;
export const API_HOST = cleanBase.endsWith('/api') ? cleanBase.slice(0, -4) : cleanBase;

export interface AERIXIndexResponse {
  index_name: string;
  frequency: string;
  period: string;
  reference_period: string;
  base_value: number;
  index_value: number;
  mom_percent: number | null;
  yoy_percent: number | null;
  route_indices: Record<string, number>;
  lead_time_indices: Record<string, number>;
  methodology_version: string;
  all_india_weighted_fare_inr?: number;
  published_at: string;
}

export type APIxIndexResponse = AERIXIndexResponse;

export interface NSOCPIFeedResponse {
  headline_index: number;
  all_india_weighted_fare_inr: number;
  national_cpi_weight_percent: number;
  collection_date: string;
  aerix_headline_metrics?: {
    headline_index: number;
    mom_inflation_rate_percent: number;
    yoy_inflation_rate_percent: number;
  };
  mospi_cpi_contribution?: {
    mom_contribution_combined_pp: number;
    mom_contribution_urban_pp: number;
    mom_contribution_rural_pp: number;
  };
  route_elementary_indices?: Record<string, number>;
}

export interface QualityMetrics {
  status: string;
  total_observations: number;
  valid_observations: number;
  duplicate_observations: number;
  exact_duplicate_rate_percent: number;
  offer_duplicate_rate_percent: number;
  unique_product_strata_count: number;
  unique_itineraries_count: number;
  routes_covered: string[];
  currency: string;
  methodology_version: string;
  collection_period?: string;
  collection_date?: string;
  evaluated_at: string;
}

export interface LeadCurvePoint {
  lead_time: string;
  lead_days: number;
  average_fare_inr: number;
  median_fare_inr?: number;
  geometric_mean_inr?: number;
  quote_count: number;
  min_fare: number;
  max_fare: number;
  is_real?: boolean;
}

export interface LeadCurveResponse {
  route: string;
  period: string;
  currency: string;
  data_source?: string;
  total_observations?: number;
  curve_points: LeadCurvePoint[];
}

export interface MatrixCell {
  route: string;
  lead_time: string;
  observation_count: number;
  median_fare_inr: number;
  mean_fare_inr: number;
  geometric_mean_inr: number;
  min_fare_inr: number;
  max_fare_inr: number;
  stddev: number;
}

export interface MatrixResponse {
  generated_at: string;
  source: string;
  collection_period?: string;
  observation_period?: string;
  total_cells: number;
  total_observations: number;
  cells: MatrixCell[];
}

export interface CoverageResponse {
  generated_at: string;
  source: string;
  total_target_cells: number;
  populated_cells: number;
  missing_cells: number;
  coverage_percent: number;
  routes_with_data: string[];
  routes_with_data_count: number;
  total_raw_observations: number;
  observations_with_fare: number;
  valid_baseline: number;
  duplicate: number;
  higher_fare_family: number;
  foreign_transit: number;
}

export interface BacktestSummary {
  evaluation_period: string;
  total_days: number;
  base_index_start: number;
  final_index_end: number;
  total_30day_return_percent: number;
  mean_absolute_error_mae: number;
  root_mean_squared_error_rmse: number;
  benchmark_correlation: number;
  apix_daily_volatility_percent: number;
  aerix_daily_volatility_percent?: number;
  naive_scraped_daily_volatility_percent: number;
  volatility_reduction_ratio: number;
  naive_mae: number;
  naive_rmse: number;
  maximum_drawdown_percent: number;
  stratum_coverage_mean: number;
  mospi_t21_checkpoint_present: boolean;
  antigravity_acceptance_passed: boolean;
  target_universe?: string;
  primary_benchmark_route?: string;
  del_bom_macro_benchmark_inr?: number;
  del_bom_apix_monthly_avg_inr?: number;
  del_bom_delta_inr?: number;
  del_bom_mape_percent?: number;
  overall_weighted_mape_percent?: number;
  overall_naive_mape_percent?: number;
  mape_target_threshold_percent?: number;
  mape_acceptance_passed?: boolean;
  top5_mean_spread_inr?: number;
  top5_spread_variance?: number;
  pearson_correlation_r?: number;
  directional_accuracy_percent?: number;
  naive_daily_volatility_percent?: number;
  booking_curve_weights?: Record<string, number>;
  benchmark_line_label?: string;
  acceptance_status?: string;
}

export interface RouteComparison {
  rank: number;
  route_id: string;
  route_name: string;
  origin_code?: string;
  destination_code?: string;
  flight_count?: number;
  distance_km?: number;
  annual_pax: number;
  route_weight: number;
  dgca_monthly_avg_net: number;
  dgca_monthly_avg_gross: number;
  udf_psf_gst: number;
  apix_monthly_avg_net: number;
  apix_monthly_avg_gross: number;
  delta_inr: number;
  abs_delta_inr: number;
  mape_percent: number;
  naive_monthly_avg_net: number;
  naive_delta_inr: number;
  naive_mape_percent: number;
  status: 'EXCELLENT' | 'PASS' | 'INVESTIGATE';
  benchmark_label?: string;
  footnote_notes: string;
}

export interface PairwiseDirectionalAccuracy {
  pair: string;
  route_a: string;
  route_b: string;
  dgca_ratio: number;
  apix_ratio: number;
  dgca_premium_percent: number;
  apix_premium_percent: number;
  ratio_error_percent: number;
  concordant: boolean;
}

export interface BacktestDailyPoint {
  day: number;
  date: string;
  apix_index: number;
  aerix_index?: number;
  apix_composite_fare_inr?: number;
  naive_composite_fare_inr?: number;
  dgca_benchmark_composite_inr?: number;
  del_bom_benchmark?: number;
  daily_mom_inflation_rate: number;
  route_simulated_fares?: Record<string, number>;
  route_naive_fares?: Record<string, number>;
  route_lead_breakdown?: Record<string, Record<string, number>>;
  route_indices?: Record<string, number>;
  lead_time_indices?: Record<string, number>;
  naive_scraped_index?: number;
  ground_truth_benchmark?: number;
  total_observations: number;
  overall_coverage_ratio: number;
}

export interface RealBacktestDailyPoint {
  day: number;
  date: string;
  observation_count: number;
  route_count: number;
  sample_routes: string[];
  collection_sources: string[];
  mean_fare_inr: number;
  median_fare_inr: number;
  geometric_mean_inr: number;
  min_fare_inr: number;
  max_fare_inr: number;
  route_median_fares?: Record<string, number>;
  data_status: string;
}

export interface RealBacktestResponse {
  backtest_type: string;
  data_status: string;
  evaluation_window: string;
  evaluation_start: string;
  evaluation_end: string;
  observation_days: number;
  total_real_observations: number;
  benchmark_source: string;
  provenance_note: string;
  metrics: Record<string, any>;
  summary: Record<string, any>;
  limitations: string[];
  daily_series: RealBacktestDailyPoint[];
  last_updated: string;
}

export interface BacktestResponse {
  backtest_type?: string;
  data_status?: string;
  evaluation_window?: string;
  observation_days?: number;
  total_real_observations?: number;
  summary: BacktestSummary;
  route_comparisons?: RouteComparison[];
  pairwise_directional_accuracy?: PairwiseDirectionalAccuracy[];
  daily_series: BacktestDailyPoint[];
  methodology_notes?: {
    booking_curve_weights_rationale: string;
    dgca_footnote_reconciliation: string;
    microfounded_index_formula: string;
  };
}

export interface SensitivityVariant {
  variant_name: string;
  weight_version: string;
  route_weight_sum: number;
  lead_time_weight_sum: number;
  compiled_index_p1: number;
  compiled_index_p2: number;
  mom_inflation_percent: number;
  route_weights: Record<string, number>;
  lead_time_weights: Record<string, number>;
  route_indices: Record<string, number>;
  lead_time_indices: Record<string, number>;
}

export interface SensitivityResponse {
  analysis_title: string;
  methodology_reference: string;
  baseline_variant: string;
  baseline_index_value: number;
  maximum_divergence_pts: number;
  maximum_divergence_percent: number;
  robustness_status: string;
  divergence_summary: Record<string, {
    index_value: number;
    diff_from_baseline_pts: number;
    abs_diff_pts: number;
    percentage_divergence: number;
  }>;
  variants: Record<string, SensitivityVariant>;
}

export interface Observation {
  route: string;
  origin: string;
  destination: string;
  airline: string;
  airline_code: string;
  flight_number: string;
  cabin: string;
  travel_date: string;
  lead_days: number;
  total_fare: number;
  base_fare: number;
  taxes: number;
  source: string;
  availability: string;
  collected_at: string;
  fare_family: string;
  stops: number;
  price_status: string;
  requires_self_transfer: boolean;
  departure_time_local?: string;
  arrival_time_local?: string;
  collection_mode: string;
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
  observations_count?: number;
  notes: string | null;
}

export interface MethodologyResponse {
  base_value: number;
  reference_period: string;
  methodology_standard: string;
  elementary_formula: string;
  higher_level_formula: string;
  min_coverage: number;
  lead_time_alignment_checkpoint: string;
  route_weights: Record<string, number>;
  lead_time_weights: Record<string, number>;
  methodology_version: string;
  weight_version: string;
}

import {
  DGCA_TOP60_ROUTES,
  LEAD_TIME_HORIZONS,
  DGCA_TOP60_METADATA,
  MOSPI_CPI_EXPENDITURE_WEIGHT,
} from './data/dgcaTop60';

export interface Methodology {
  base_value: number;
  base_date: string | null;
  min_coverage: number;
  item_rules: Record<string, unknown>;
  routes: { id: string; origin: string; destination: string; weight: number; weight_assumption: boolean; rank?: number; annual_pax?: number; dgca_share_percent?: number }[];
  lead_days: { days: number; weight: number; weight_assumption: boolean; is_mospi_checkpoint?: boolean; lead_class?: string; name?: string }[];
  aggregation: Record<string, string>;
  reference: string;
  metadata?: typeof DGCA_TOP60_METADATA;
  cpi_weight?: typeof MOSPI_CPI_EXPENDITURE_WEIGHT;
}

export interface IndexPoint {
  date: string;
  level: number | null;
  coverage: number;
  low_coverage: boolean;
  gap_days: number;
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

export const api = {
  // Official Production AERIX Endpoints
  getAirfareIndex: async (params?: { route?: string; lead_time?: string }): Promise<APIxIndexResponse> => {
    const q = new URLSearchParams();
    if (params?.route) q.set('route', params.route);
    if (params?.lead_time) q.set('lead_time', params.lead_time);
    const res = await fetch(`${BASE}/v1/airfare-index?${q.toString()}`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/airfare-index`);
    return res.json();
  },

  getQualityMetrics: async (): Promise<QualityMetrics> => {
    const res = await fetch(`${BASE}/v1/quality-metrics`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/quality-metrics`);
    return res.json();
  },

  getLeadCurves: async (route = 'DEL-BOM'): Promise<LeadCurveResponse> => {
    const res = await fetch(`${BASE}/v1/lead-curves?route=${encodeURIComponent(route)}`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/lead-curves`);
    return res.json();
  },

  getBacktest: async (mode?: 'synthetic' | 'real'): Promise<BacktestResponse> => {
    const q = new URLSearchParams();
    if (mode) q.set('mode', mode);
    try {
      const res = await fetch(`${BASE}/v1/backtest${mode ? `?${q.toString()}` : ''}`);
      if (res.ok) return await res.json();
    } catch {}
    // Graceful fallback to bundled results if backend is offline or during testing
    const fallback = await import('./data/backtest_results.json');
    return (fallback.default || fallback) as unknown as BacktestResponse;
  },

  getRealBacktest: async (): Promise<RealBacktestResponse> => {
    const res = await fetch(`${BASE}/v1/backtest?mode=real`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/backtest?mode=real`);
    return res.json();
  },


  getSensitivity: async (): Promise<SensitivityResponse> => {
    const res = await fetch(`${BASE}/v1/sensitivity`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/sensitivity`);
    return res.json();
  },

  getMatrix: async (params?: { route?: string; lead_time?: string }): Promise<MatrixResponse> => {
    const q = new URLSearchParams();
    if (params?.route) q.set('route', params.route);
    if (params?.lead_time) q.set('lead_time', params.lead_time);
    const res = await fetch(`${BASE}/v1/matrix?${q.toString()}`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/matrix`);
    return res.json();
  },

  getCoverage: async (): Promise<CoverageResponse> => {
    const res = await fetch(`${BASE}/v1/coverage`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/coverage`);
    return res.json();
  },

  runs: async (): Promise<Run[]> => {
    const res = await fetch(`${BASE}/runs`);
    if (!res.ok) throw new Error(`API error ${res.status}: /runs`);
    return res.json();
  },

  observations: async (): Promise<Observation[]> => {
    const res = await fetch(`${BASE}/observations`);
    if (!res.ok) throw new Error(`API error ${res.status}: /observations`);
    return res.json();
  },

  getNsoCpiFeed: async (): Promise<NSOCPIFeedResponse> => {
    const res = await fetch(`${BASE}/v1/nso/cpi-feed`);
    if (!res.ok) throw new Error(`API error ${res.status}: /v1/nso/cpi-feed`);
    return res.json();
  },

  methodology: async (): Promise<Methodology> => {
    const fallbackRoutes = DGCA_TOP60_ROUTES.map(r => ({
      id: r.route_id,
      origin: r.origin_code,
      destination: r.destination_code,
      weight: r.route_weight,
      weight_assumption: false,
      rank: r.rank,
      annual_pax: r.annual_passenger_volume,
      dgca_share_percent: r.dgca_share_percent,
    }));

    const fallbackLeads = LEAD_TIME_HORIZONS.map(l => ({
      days: l.days,
      weight: l.empirical_weight_decimal,
      weight_assumption: false,
      is_mospi_checkpoint: l.is_mospi_checkpoint,
      lead_class: l.lead_class,
      name: l.name,
    }));

    try {
      const res = await fetch(`${BASE}/methodology`);
      if (res.ok) {
        const raw = await res.json();
        const routes = Object.entries(raw.route_weights || {}).map(([r, w]) => {
          const [orig, dest] = r.split('-');
          const match = DGCA_TOP60_ROUTES.find(x => x.route_id === r);
          return {
            id: r,
            origin: orig || 'DEL',
            destination: dest || 'BOM',
            weight: Number(w),
            weight_assumption: false,
            rank: match?.rank,
            annual_pax: match?.annual_passenger_volume,
            dgca_share_percent: match?.dgca_share_percent,
          };
        });
        const lead_days = Object.entries(raw.lead_time_weights || {}).map(([lt, w]) => {
          const days = parseInt(lt.replace('T+', '')) || 7;
          const match = LEAD_TIME_HORIZONS.find(x => x.days === days);
          return {
            days,
            weight: Number(w),
            weight_assumption: false,
            is_mospi_checkpoint: match?.is_mospi_checkpoint ?? (days === 21),
            lead_class: lt,
            name: match?.name,
          };
        });
        return {
          base_value: raw.base_value || 100,
          base_date: '2024-01-01',
          min_coverage: raw.min_coverage || 0.5,
          item_rules: {},
          routes: routes.length > 0 ? routes : fallbackRoutes,
          lead_days: lead_days.length > 0 ? lead_days : fallbackLeads,
          aggregation: { elementary: raw.elementary_formula, higher: raw.higher_level_formula },
          reference: raw.methodology_standard || 'MoSPI CPI 2024 / Eurostat HICP',
          metadata: DGCA_TOP60_METADATA,
          cpi_weight: MOSPI_CPI_EXPENDITURE_WEIGHT,
        };
      }
    } catch {}

    return {
      base_value: 100,
      base_date: '2024-01-01',
      min_coverage: 0.5,
      item_rules: {},
      routes: fallbackRoutes,
      lead_days: fallbackLeads,
      aggregation: {
        elementary: 'Short-chain Jevons index across matched product strata (M(s,t))',
        higher: 'Young/Laspeyres weighted aggregation across lead times and DGCA passenger share routes',
      },
      reference: 'MoSPI CPI 2024 (Base 2024=100) & Eurostat HICP Methodological Manual 2024',
      metadata: DGCA_TOP60_METADATA,
      cpi_weight: MOSPI_CPI_EXPENDITURE_WEIGHT,
    };
  },

  // Backwards compatibility helpers for legacy views
  index: async (scope: string, route?: string, freq = 'daily'): Promise<IndexPoint[]> => {
    try {
      const bt = await api.getBacktest();
      if (bt && bt.daily_series) {
        return bt.daily_series.map(d => ({
          date: d.date,
          level: d.apix_index,
          coverage: d.overall_coverage_ratio,
          low_coverage: false,
          gap_days: 0,
          is_synthetic: false
        }));
      }
    } catch {}
    return [];
  },

  leadCurve: async (route: string): Promise<LeadCurve[]> => {
    try {
      const lc = await api.getLeadCurves(route);
      return [{
        obs_date: '2026-09-22',
        is_synthetic: false,
        points: lc.curve_points.map(p => ({
          lead_days: p.lead_days,
          dep_band: 'ALL',
          price: p.average_fare_inr
        }))
      }];
    } catch {}
    return [];
  },

  relatives: async (): Promise<Relative[]> => {
    return [];
  }
};
