"""
Compute real APIx index for DEL-BOM from Phase 28 production data.
Reads APIx_Phase28_Production_Coverage_Report.json, runs the full formula,
and outputs apix_delbom_result.json for the frontend.

Base Period Strategy: Option B
  The base price is the weighted representative price from the FIRST real
  production run (Phase 28, 2026-09-26). Index = 100.00 on that date.
  Future runs compare against this locked base price.
  Override by editing apix_base_delbom.json.
"""
import json
import statistics
from pathlib import Path
from datetime import datetime, timezone

# ── Load Phase 28 report ─────────────────────────────────────────────────────
report_path = Path(__file__).resolve().parent.parent / "APIx_Phase28_Production_Coverage_Report.json"
with open(report_path, "r", encoding="utf-8") as f:
    report = json.load(f)

jobs = report["jobs"]

# ── Configuration ─────────────────────────────────────────────────────────────
LEAD_TIME_WEIGHTS = {1: 1/6, 7: 1/6, 15: 1/6, 21: 1/6, 30: 1/6, 45: 1/6}
ROUTE = "DEL-BOM"
BASE_PERIOD = "2026-09-26"   # Phase 28 collection date = base period

# Option B: base price is loaded from lock file if it exists;
# otherwise we compute it from this run and save it as the lock.
BASE_LOCK_PATH = Path(__file__).resolve().parent.parent / "apix_base_delbom.json"

def load_or_create_base(computed_price: float) -> tuple[float, str, bool]:
    """Returns (base_price, source_description, was_newly_created)."""
    if BASE_LOCK_PATH.exists():
        with open(BASE_LOCK_PATH, "r", encoding="utf-8") as f:
            lock = json.load(f)
        return lock["base_price_inr"], f"Loaded from lock file (set on {lock['locked_on']})", False
    # First run — use today's computed price as base
    lock = {
        "route": ROUTE,
        "base_price_inr": round(computed_price, 2),
        "base_period": BASE_PERIOD,
        "base_method": "Option B — first production run weighted representative price",
        "locked_on": datetime.now(timezone.utc).isoformat(),
        "note": "Delete this file to recompute base from next run, or edit manually to set a different base."
    }
    with open(BASE_LOCK_PATH, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2)
    return computed_price, f"Newly created from Phase 28 run ({BASE_PERIOD}) — index = 100.00", True


# ── Stratum mapping (APIx Product Definition §2.1) ───────────────────────────
STRATUM_MAP = {
    # STANDARD_SAVER
    "Saver": "STANDARD_SAVER", "Value": "STANDARD_SAVER", "SpiceSaver": "STANDARD_SAVER",
    "STANDARD": "STANDARD_SAVER",
    # FLEXIBLE_ECONOMY
    "FlexiPlus": "FLEXIBLE_ECONOMY", "Flex": "FLEXIBLE_ECONOMY", "Classic": "FLEXIBLE_ECONOMY",
    "SpiceFlex": "FLEXIBLE_ECONOMY",
    # OTA_EXCLUSIVE
    "EMTEXCLUSIVE": "OTA_EXCLUSIVE", "Retail": "OTA_EXCLUSIVE",
    # PREMIUM_UPFRONT
    "IndigoUpFront": "PREMIUM_UPFRONT", "SpiceMax": "PREMIUM_UPFRONT",
}

def get_stratum(fare_family):
    if not fare_family:
        return "STANDARD_SAVER"
    return STRATUM_MAP.get(fare_family, "STANDARD_SAVER")

# ── Collect all CORE_ONLY observations across both sources ───────────────────
# For the HEADLINE index: lowest baseline fare per itinerary per lead time
# For stratum sub-indices: group by stratum

all_obs = []   # {lead_days, total_fare, source, fare_family, stratum, airline, flight_number}

for job in jobs:
    mode = job.get("extraction_mode", "")
    state = job.get("state", "")
    if state != "DONE":
        continue
    
    samples = job.get("canonical_samples", [])
    lead_time_str = job.get("lead_time", "T+7")
    lead_days_raw = lead_time_str.replace("T+", "")
    try:
        lead_days = int(lead_days_raw)
    except ValueError:
        continue

    for s in samples:
        fare = s.get("total_fare")
        if fare is None:
            continue
        obs = {
            "lead_days": lead_days,
            "total_fare": float(fare),
            "source": s.get("source", ""),
            "fare_family": s.get("fare_family", "STANDARD"),
            "stratum": get_stratum(s.get("fare_family", "STANDARD")),
            "airline": s.get("airline", ""),
            "flight_number": s.get("flight_number", ""),
            "itinerary_id": s.get("itinerary_id", ""),
            "offer_id": s.get("offer_id", ""),
            "travel_date": s.get("travel_date", ""),
        }
        all_obs.append(obs)

print(f"Total observations loaded: {len(all_obs)}")

# ── HEADLINE INDEX: lowest qualifying fare per itinerary per lead time ────────
# Group by (lead_days, itinerary_id) -> take the minimum fare (baseline saver)
from collections import defaultdict

itin_fares_by_lead = defaultdict(lambda: defaultdict(list))  # lead_days -> itin_id -> [fares]
for obs in all_obs:
    itin_fares_by_lead[obs["lead_days"]][obs["itinerary_id"]].append(obs["total_fare"])

# For each lead time: compute geometric mean of lowest fares across itineraries
import math

def geometric_mean(values):
    if not values:
        return None
    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / len(values))

headline_by_lead = {}  # lead_days -> {median, geo_mean, n_itins, fares}
for lead_days, itin_map in itin_fares_by_lead.items():
    baseline_fares = [min(fares) for fares in itin_map.values()]  # lowest per itin
    headline_by_lead[lead_days] = {
        "n_itineraries": len(baseline_fares),
        "median_fare": statistics.median(baseline_fares),
        "geometric_mean_fare": geometric_mean(baseline_fares),
        "min_fare": min(baseline_fares),
        "max_fare": max(baseline_fares),
        "fares": sorted(baseline_fares),
    }

# ── Weighted representative price using all 6 lead times ─────────────────────
# Normalize weights for available lead times
available_leads = list(headline_by_lead.keys())
total_w = sum(LEAD_TIME_WEIGHTS.get(l, 0) for l in available_leads)

weighted_price = 0.0
lead_time_detail = {}
for lead_days in sorted(available_leads):
    w = LEAD_TIME_WEIGHTS.get(lead_days, 0) / total_w  # renormalized
    p = headline_by_lead[lead_days]["median_fare"]
    weighted_price += w * p
    lead_time_detail[f"T+{lead_days}"] = {
        "lead_days": lead_days,
        "weight": round(w, 6),
        "median_fare_inr": round(p, 2),
        "geometric_mean_fare_inr": round(headline_by_lead[lead_days]["geometric_mean_fare"], 2),
        "n_itineraries": headline_by_lead[lead_days]["n_itineraries"],
        "min_fare_inr": round(headline_by_lead[lead_days]["min_fare"], 2),
        "max_fare_inr": round(headline_by_lead[lead_days]["max_fare"], 2),
        "contribution_inr": round(w * p, 2),
    }

# ── Option B: resolve base price ───────────────────────────────────────────────────────────
BASE_PRICE_DELBOM, base_source, base_is_new = load_or_create_base(weighted_price)
if base_is_new:
    print(f"  [Base] Locked new base price: INR {BASE_PRICE_DELBOM:,.2f} (index will be 100.00)")
else:
    print(f"  [Base] Using locked base: INR {BASE_PRICE_DELBOM:,.2f} — {base_source}")

# ── Route Index ───────────────────────────────────────────────────────────────
route_index = (weighted_price / BASE_PRICE_DELBOM) * 100.0

# ── Stratum Sub-Indices ───────────────────────────────────────────────────────
stratum_fares = defaultdict(lambda: defaultdict(list))  # stratum -> lead -> [fares]
for obs in all_obs:
    stratum_fares[obs["stratum"]][obs["lead_days"]].append(obs["total_fare"])

stratum_indices = {}
for stratum, lead_map in stratum_fares.items():
    s_weighted = 0.0
    s_total_w = sum(LEAD_TIME_WEIGHTS.get(l, 0) for l in lead_map)
    if s_total_w == 0:
        continue
    s_detail = {}
    for lead_days, fares in lead_map.items():
        w = LEAD_TIME_WEIGHTS.get(lead_days, 0) / s_total_w
        med = statistics.median(fares)
        s_weighted += w * med
        s_detail[f"T+{lead_days}"] = {
            "median_fare": round(med, 2),
            "n_obs": len(fares),
            "weight": round(w, 4),
        }
    stratum_indices[stratum] = {
        "weighted_price": round(s_weighted, 2),
        "index_value": round((s_weighted / BASE_PRICE_DELBOM) * 100, 4),
        "lead_breakdown": s_detail,
    }

# ── Source Comparison ─────────────────────────────────────────────────────────
source_fares = defaultdict(lambda: defaultdict(list))
for obs in all_obs:
    source_fares[obs["source"]][obs["lead_days"]].append(obs["total_fare"])

source_comparison = {}
for src, lead_map in source_fares.items():
    s_weighted = 0.0
    s_total_w = sum(LEAD_TIME_WEIGHTS.get(l, 0) for l in lead_map)
    if s_total_w == 0:
        continue
    for lead_days, fares in lead_map.items():
        w = LEAD_TIME_WEIGHTS.get(lead_days, 0) / s_total_w
        s_weighted += w * statistics.median(fares)
    source_comparison[src] = {
        "weighted_price": round(s_weighted, 2),
        "index_value": round((s_weighted / BASE_PRICE_DELBOM) * 100, 4),
        "total_obs": sum(len(f) for f in lead_map.values()),
    }

# ── Airline breakdown ─────────────────────────────────────────────────────────
airline_counts = defaultdict(int)
airline_fare_sum = defaultdict(list)
for obs in all_obs:
    airline_counts[obs["airline"]] += 1
    airline_fare_sum[obs["airline"]].append(obs["total_fare"])

airline_breakdown = {}
for airline, fares in airline_fare_sum.items():
    airline_breakdown[airline] = {
        "n_obs": len(fares),
        "median_fare": round(statistics.median(fares), 2),
        "min_fare": round(min(fares), 2),
        "max_fare": round(max(fares), 2),
    }

# ── Final result ──────────────────────────────────────────────────────────────
result = {
    "meta": {
        "route": ROUTE,
        "base_price_inr": round(BASE_PRICE_DELBOM, 2),
        "base_period": BASE_PERIOD,
        "base_method": "Option B — first production run weighted representative price",
        "base_price_source": base_source,
        "collection_date": "2026-09-26",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_observations": len(all_obs),
        "sources": ["google_flights", "easemytrip"],
        "lead_times_covered": sorted(available_leads),
        "methodology": "APIx v1.0 — Weighted Arithmetic (Laspeyres-type)",
        "formula": "RouteIndex(r,t) = [Σ w_L × Median(fares_{r,L,t})] / BasePrice(r) × 100",
        "disclaimer": "Illustrative POC methodology — subject to validation against MoSPI, DGCA and international price-index standards.",
    },
    "headline": {
        "weighted_representative_price_inr": round(weighted_price, 2),
        "route_index": round(route_index, 4),
        "interpretation": f"DEL-BOM fares are at {route_index:.1f}% of the base-period price ({BASE_PERIOD})",
        "base_price_inr": round(BASE_PRICE_DELBOM, 2),
    },
    "lead_time_breakdown": lead_time_detail,
    "stratum_sub_indices": stratum_indices,
    "source_comparison": source_comparison,
    "airline_breakdown": dict(sorted(airline_breakdown.items(), key=lambda x: -x[1]["n_obs"])),
}

out_path = Path(__file__).resolve().parent.parent / "apix_delbom_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("\n" + "="*60)
print(f"  APIx ROUTE INDEX — {ROUTE}")
print("="*60)
print(f"  Total observations used : {len(all_obs)}")
print(f"  Base price (POC)        : ₹{BASE_PRICE_DELBOM:,.0f}")
print(f"  Weighted rep. price     : ₹{weighted_price:,.2f}")
print(f"  ROUTE INDEX VALUE       : {route_index:.4f}")
print(f"  Interpretation          : {route_index:.1f}% of base-period price")
print("\n  Lead-time breakdown:")
for lt, d in sorted(lead_time_detail.items()):
    print(f"    {lt:6s}  weight={d['weight']:.4f}  median=₹{d['median_fare_inr']:,.0f}  n={d['n_itineraries']}")
print("\n  Stratum sub-indices:")
for stratum, d in stratum_indices.items():
    print(f"    {stratum:20s}  index={d['index_value']:.2f}  price=₹{d['weighted_price']:,.0f}")
print("\n  Source comparison:")
for src, d in source_comparison.items():
    print(f"    {src:20s}  index={d['index_value']:.2f}  price=₹{d['weighted_price']:,.0f}  obs={d['total_obs']}")
print("="*60)
print(f"\nResult saved to: {out_path}")
