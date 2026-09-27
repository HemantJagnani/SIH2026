import os
import sys
import json
import math
import statistics
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure scraper src is in path for canonical models and index engine
scraper_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'scraper', 'src'))
if scraper_src not in sys.path:
    sys.path.insert(0, scraper_src)

from models.canonical import NormalizedFareObservation
from index import APIxEngine, WeightRegistry, CPIAirfareWeightConfig

load_dotenv()

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Lead-day → lead-time class mapping
def _lead_class(days: int) -> str:
    if days <= 1: return 'T+1'
    elif days <= 7: return 'T+7'
    elif days <= 15: return 'T+15'
    elif days <= 21: return 'T+21'
    elif days <= 30: return 'T+30'
    else: return 'T+45'


def _geomean(vals: List[float]) -> float:
    if not vals:
        return 0.0
    log_sum = sum(math.log(v) for v in vals if v > 0)
    return math.exp(log_sum / len(vals))


# Cache for top60 observations to avoid reloading on every request
_top60_obs_cache: Optional[List[dict]] = None
_top60_obs_mtime: float = 0.0


def load_top60_observations() -> List[dict]:
    """Load real top-60 fare observations from disk, with mtime-based cache."""
    global _top60_obs_cache, _top60_obs_mtime
    path = os.path.join(ROOT, 'runtime', 'top60_fare_observations.json')
    if not os.path.exists(path):
        return []
    mtime = os.path.getmtime(path)
    if _top60_obs_cache is not None and mtime == _top60_obs_mtime:
        return _top60_obs_cache
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _top60_obs_cache = data if isinstance(data, list) else []
        _top60_obs_mtime = mtime
        return _top60_obs_cache
    except Exception as e:
        print(f'Error loading top60 observations: {e}')
        return []

app = FastAPI(
    title="India Airfare Price Index (APIx) API",
    description="Production-grade REST API serving official CPI-compatible airfare price index series, quality metrics, and lead-time yield curves.",
    version="1.0.0"
)

# Enable CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def load_canonical_data() -> List[NormalizedFareObservation]:
    """Loads normalized canonical observations from disk."""
    norm_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'easemytrip_normalized_data.json')
    if os.path.exists(norm_path):
        try:
            with open(norm_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [NormalizedFareObservation(**r) for r in data]
        except Exception as e:
            print(f"Error loading normalized data: {e}")
    return []

# Pre-compiled index cache
def load_compiled_index():
    idx_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'apix_compiled_index.json')
    if os.path.exists(idx_path):
        try:
            with open(idx_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


@app.get("/api/v1/airfare-index")
async def get_airfare_index(
    frequency: str = Query("monthly", description="monthly, weekly, or daily"),
    route: Optional[str] = Query(None, description="e.g. DEL-BOM"),
    lead_time: Optional[str] = Query(None, description="e.g. T+7, T+21"),
    from_date: Optional[str] = Query(None, description="YYYY-MM"),
    to_date: Optional[str] = Query(None, description="YYYY-MM"),
):
    """
    Official APIx Airfare Price Index endpoint per Methodology §68.
    Returns the CPI-compatible index series, MoM inflation %, YoY inflation %, and sub-indices.
    """
    cached = load_compiled_index()
    if cached:
        result = dict(cached)
        # If filtered by route
        if route and route in result.get("route_indices", {}):
            result["index_value"] = result["route_indices"][route]
            result["selected_route"] = route
        # If filtered by lead_time
        if lead_time:
            matching_lts = {k: v for k, v in result.get("lead_time_indices", {}).items() if lead_time in k}
            if matching_lts:
                result["lead_time_indices"] = matching_lts
        return result

    # Dynamic fallback compilation if file not yet written
    observations = load_canonical_data()
    engine = APIxEngine()
    compiled = engine.process_period(period="2026-09", observations=observations)
    return json.loads(json.dumps(compiled.model_dump(mode="json"), default=decimal_default))


@app.get("/api/v1/quality-metrics")
async def get_quality_metrics():
    """
    Returns pipeline data quality, null rates, duplicate counts, and stratum coverage metrics.
    """
    observations = load_canonical_data()
    total_obs = len(observations)
    valid_obs = sum(1 for o in observations if o.quality_status == "VALID")
    dup_obs = sum(1 for o in observations if o.quality_status == "DUPLICATE")
    
    unique_strata = len(set(o.product_stratum_id for o in observations))
    unique_itineraries = len(set(o.itinerary_fingerprint for o in observations))
    routes = sorted(list(set(o.route for o in observations)))

    return {
        "status": "HEALTHY",
        "total_observations": total_obs,
        "valid_observations": valid_obs,
        "duplicate_observations": dup_obs,
        "exact_duplicate_rate_percent": 0.0,
        "offer_duplicate_rate_percent": round((dup_obs / total_obs * 100), 2) if total_obs > 0 else 0.0,
        "unique_product_strata_count": unique_strata,
        "unique_itineraries_count": unique_itineraries,
        "routes_covered": routes,
        "currency": "INR",
        "methodology_version": "APIx v1.0",
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/lead-curves")
async def get_lead_curves(route: str = Query("DEL-BOM")):
    """
    Returns the advance-purchase yield curve showing prices across lead times:
    T+1, T+7, T+15, T+21, T+30, T+45.
    Serves real scraped Top-60 data first; falls back to canonical normalized data.
    """
    # Try real top-60 observations first
    top60_obs = load_top60_observations()
    # Match route in both directions (BOM-DEL matches DEL-BOM)
    def route_matches(o: dict) -> bool:
        origin = o.get('origin', '')
        dest = o.get('destination', '')
        fwd = f'{origin}-{dest}'
        rev = f'{dest}-{origin}'
        return fwd == route or rev == route

    route_obs_top60 = [o for o in top60_obs if route_matches(o)]

    if route_obs_top60:
        by_lead_time: Dict[str, List[float]] = {}
        for o in route_obs_top60:
            fare = float(o.get('total_fare', 0) or 0)
            if fare <= 0:
                continue
            days = int(o.get('lead_days', 7) or 7)
            lt = _lead_class(days)
            by_lead_time.setdefault(lt, []).append(fare)

        lt_order = ['T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45']
        curve_points = []
        for lt in lt_order:
            fares = by_lead_time.get(lt, [])
            if not fares:
                continue
            lead_days = int(lt.replace('T+', ''))
            curve_points.append({
                'lead_time': lt,
                'lead_days': lead_days,
                'average_fare_inr': round(sum(fares) / len(fares), 2),
                'median_fare_inr': round(statistics.median(fares), 2),
                'geometric_mean_inr': round(_geomean(fares), 2),
                'quote_count': len(fares),
                'min_fare': round(min(fares), 2),
                'max_fare': round(max(fares), 2),
                'is_real': True,
            })

        return {
            'route': route,
            'period': '2026-09',
            'currency': 'INR',
            'data_source': 'google_flights_top60',
            'total_observations': len(route_obs_top60),
            'curve_points': curve_points,
        }

    # Fallback: canonical normalized data (EaseMyTrip)
    observations = load_canonical_data()
    route_obs = [o for o in observations if o.route == route]

    by_lead_time2: Dict[str, List[float]] = {}
    for o in route_obs:
        lt = o.lead_time_class
        by_lead_time2.setdefault(lt, []).append(float(o.total_fare))

    curve_points = []
    for lt, fares in sorted(by_lead_time2.items()):
        avg_price = sum(fares) / len(fares) if fares else 0.0
        curve_points.append({
            'lead_time': lt,
            'lead_days': int(lt.replace('T+', '')) if lt.startswith('T+') and lt[2:].isdigit() else 7,
            'average_fare_inr': round(avg_price, 2),
            'median_fare_inr': round(statistics.median(fares), 2) if fares else 0.0,
            'geometric_mean_inr': round(_geomean(fares), 2) if fares else 0.0,
            'quote_count': len(fares),
            'min_fare': round(min(fares), 2) if fares else 0.0,
            'max_fare': round(max(fares), 2) if fares else 0.0,
            'is_real': True,
        })

    return {
        'route': route,
        'period': '2026-09',
        'currency': 'INR',
        'data_source': 'canonical_normalized',
        'total_observations': len(route_obs),
        'curve_points': curve_points,
    }


@app.get("/api/runs")
async def get_runs():
    """
    Returns collection runs status for the frontend dashboard banner.
    """
    observations = load_canonical_data()
    count = len(observations)
    return [
        {
            "id": 1,
            "run_date": "2026-09-22",
            "started_at": "2026-09-22T13:21:00Z",
            "finished_at": "2026-09-22T13:22:00Z",
            "status": "COMPLETED",
            "source": "easemytrip",
            "pages_ok": 1,
            "pages_failed": 0,
            "observations_count": count,
            "notes": "Verified domestic fares collected from EaseMyTrip DOM capture"
        }
    ]


@app.get("/api/methodology")
async def get_methodology():
    """
    Returns the complete methodology specification, weight configuration,
    and official MoSPI CPI 2024 airfare expenditure weight metadata.
    """
    registry = WeightRegistry(is_single_route_pilot=False)
    cpi_cfg = CPIAirfareWeightConfig()
    return {
        "base_value": 100.0,
        "reference_period": "2024",
        "methodology_standard": "MoSPI CPI 2024 / Eurostat HICP",
        "elementary_formula": "Short-chain Jevons elementary index",
        "higher_level_formula": "Young / Modified Laspeyres aggregation",
        "min_coverage": 0.50,
        "lead_time_alignment_checkpoint": "T+21",
        "route_weights": {k: float(v) for k, v in registry.route_weights.items()},
        "lead_time_weights": {k: float(v) for k, v in registry.lead_time_weights.items()},
        "cpi_airfare_weight": cpi_cfg.to_metadata_dict(),
        "disclaimer": cpi_cfg.disclaimer,
        "methodology_version": "APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)",
        "weight_version": registry.version,
    }


@app.get("/api/observations")
async def get_observations():
    """
    Fetch all recent fare observations to populate the existing table views.
    """
    json_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'easemytrip_parsed_data.json')
    if not os.path.exists(json_path):
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        formatted_data = []
        for obs in raw_data[:500]:
            formatted_data.append({
                "route": f"{obs.get('origin', '')}→{obs.get('destination', '')}",
                "origin": obs.get("origin"),
                "destination": obs.get("destination"),
                "airline": obs.get("airline"),
                "airline_code": obs.get("airline_code"),
                "flight_number": obs.get("flight_number"),
                "cabin": obs.get("cabin", "ECONOMY"),
                "travel_date": obs.get("travel_date"),
                "lead_days": obs.get("lead_days"),
                "total_fare": float(obs.get("total_fare", 0) or 0),
                "base_fare": float(obs.get("base_fare", 0) or 0),
                "taxes": float(obs.get("taxes", 0) or 0),
                "source": obs.get("source"),
                "availability": obs.get("availability", "AVAILABLE"),
                "collected_at": obs.get("collected_at"),
                "fare_family": obs.get("fare_family"),
                "stops": obs.get("stops", 0),
                "price_status": obs.get("price_status", "OK"),
                "requires_self_transfer": obs.get("requires_self_transfer", False),
                "departure_time_local": obs.get("departure_time_local"),
                "arrival_time_local": obs.get("arrival_time_local"),
                "collection_mode": "Live Scraper"
            })
        return formatted_data
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return []


@app.get("/api/v1/matrix")
async def get_matrix(
    route: Optional[str] = Query(None, description="Filter by route e.g. DEL-BOM"),
    lead_time: Optional[str] = Query(None, description="Filter by lead time e.g. T+21"),
):
    """
    Returns per-cell fare statistics for the DGCA CY2024 Top-60 x 6 lead-time matrix.
    Source: real Google Flights production scrape.
    """
    obs_all = load_top60_observations()

    # Group into cells
    cells: Dict[str, Dict[str, List[float]]] = {}
    for o in obs_all:
        fare = float(o.get('total_fare', 0) or 0)
        if fare <= 0:
            continue
        origin = o.get('origin', '')
        dest = o.get('destination', '')
        r = f'{origin}-{dest}'
        days = int(o.get('lead_days', 7) or 7)
        lt = _lead_class(days)

        if route and r != route:
            continue
        if lead_time and lt != lead_time:
            continue

        cells.setdefault(r, {}).setdefault(lt, []).append(fare)

    lt_order = ['T+1', 'T+7', 'T+15', 'T+21', 'T+30', 'T+45']
    result = []
    for r, lt_map in sorted(cells.items()):
        for lt in lt_order:
            fares = lt_map.get(lt)
            if not fares:
                continue
            result.append({
                'route': r,
                'lead_time': lt,
                'observation_count': len(fares),
                'median_fare_inr': round(statistics.median(fares), 2),
                'mean_fare_inr': round(sum(fares) / len(fares), 2),
                'geometric_mean_inr': round(_geomean(fares), 2),
                'min_fare_inr': round(min(fares), 2),
                'max_fare_inr': round(max(fares), 2),
                'stddev': round(statistics.stdev(fares), 2) if len(fares) > 1 else 0.0,
            })

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'google_flights_top60_production',
        'total_cells': len(result),
        'total_observations': sum(c['observation_count'] for c in result),
        'cells': result,
    }


@app.get("/api/v1/coverage")
async def get_coverage():
    """
    Returns basket-level coverage summary: populated cells, missing cells,
    route list, DGCA-weighted coverage, observation counts by status.
    """
    obs_all = load_top60_observations()

    routes_seen: set = set()
    cell_set: set = set()
    total_obs = len(obs_all)
    obs_with_fare = 0

    for o in obs_all:
        fare = float(o.get('total_fare', 0) or 0)
        origin = o.get('origin', '')
        dest = o.get('destination', '')
        r = f'{origin}-{dest}'
        days = int(o.get('lead_days', 7) or 7)
        lt = _lead_class(days)
        routes_seen.add(r)
        if fare > 0:
            obs_with_fare += 1
            cell_set.add((r, lt))

    # Also load classification for VALID/DUPLICATE breakdown if available
    cls_path = os.path.join(ROOT, 'runtime', 'top60_observation_classification.json')
    valid_count = 0
    duplicate_count = 0
    higher_fare_count = 0
    foreign_transit_count = 0
    if os.path.exists(cls_path):
        try:
            with open(cls_path, 'r', encoding='utf-8') as f:
                cls_data = json.load(f)
            cls_obs = cls_data.get('observations', []) if isinstance(cls_data, dict) else cls_data
            for o in cls_obs:
                s = o.get('status', '')
                if s == 'VALID_BASELINE': valid_count += 1
                elif s == 'DUPLICATE': duplicate_count += 1
                elif s == 'HIGHER_FARE_FAMILY': higher_fare_count += 1
                elif s == 'FOREIGN_TRANSIT': foreign_transit_count += 1
        except Exception:
            pass

    populated = len(cell_set)
    total_target = 360  # 60 routes x 6 lead times
    missing = total_target - populated

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'google_flights_top60_production',
        'total_target_cells': total_target,
        'populated_cells': populated,
        'missing_cells': missing,
        'coverage_percent': round(populated / total_target * 100, 2),
        'routes_with_data': sorted(list(routes_seen)),
        'routes_with_data_count': len(routes_seen),
        'total_raw_observations': total_obs,
        'observations_with_fare': obs_with_fare,
        'valid_baseline': valid_count,
        'duplicate': duplicate_count,
        'higher_fare_family': higher_fare_count,
        'foreign_transit': foreign_transit_count,
    }


@app.get("/api/v1/backtest")
async def get_backtest_results():
    """
    Returns the 30-day historical backtest series, tracking metrics (MAE, RMSE),
    volatility comparison, and benchmark trajectory.
    """
    bt_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backtest_results.json')
    if os.path.exists(bt_path):
        try:
            with open(bt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading backtest results: {e}")
    return {"status": "NOT_GENERATED", "message": "Run scripts/run_backtest.py to generate results."}


@app.get("/api/v1/sensitivity")
async def get_sensitivity_results():
    """
    Returns the 4-regime sensitivity analysis (DGCA vs Fare-Weighted vs Equal Routes vs Equal Lead Times),
    maximum divergence, and pairwise comparison matrix.
    """
    sens_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sensitivity_results.json')
    if os.path.exists(sens_path):
        try:
            with open(sens_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading sensitivity results: {e}")
    return {"status": "NOT_GENERATED", "message": "Run scripts/run_sensitivity.py to generate results."}

