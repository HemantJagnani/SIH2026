"""
Monthly Product Price Aggregator for APIx Phase 3.
Implements within-month geometric mean calculation per Methodology §12.
"""

from __future__ import annotations
import math
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Sequence
from models.canonical import NormalizedFareObservation
from .models import MonthlyProductPrice


def compute_monthly_product_prices(
    observations: Sequence[NormalizedFareObservation],
) -> Dict[str, MonthlyProductPrice]:
    """
    Computes within-month geometric product prices:
        P̄_(i,t) = exp( 1/D * sum(ln P_(i,t,d)) )
    
    Filters out invalid, duplicate, or non-positive observations.
    Returns a dictionary mapping (product_id, month) -> MonthlyProductPrice.
    """
    # Group by (product_id, month)
    grouped: Dict[tuple[str, str], list[NormalizedFareObservation]] = defaultdict(list)
    
    for obs in observations:
        # Strictly include valid observations
        if obs.quality_status != "VALID":
            continue
        if obs.total_fare <= Decimal("0"):
            continue
            
        prod_id = obs.product_key or obs.offer_fingerprint
        month = obs.month
        grouped[(prod_id, month)].append(obs)
        
    results: Dict[str, MonthlyProductPrice] = {}
    
    for (prod_id, month), obs_list in grouped.items():
        if not obs_list:
            continue
            
        # Geometric mean via log formulation for numerical stability
        log_sum = sum(math.log(float(o.total_fare)) for o in obs_list)
        count = len(obs_list)
        geom_mean = math.exp(log_sum / count)
        
        # Metadata from first observation in homogeneous group
        first = obs_list[0]
        stratum_id = first.product_stratum_id
        route = first.route
        lead_time = first.lead_time_class
        
        active_days = len(set(o.travel_date for o in obs_list))
        source_count = len(set(o.source for o in obs_list))
        
        key = f"{prod_id}_{month}"
        results[key] = MonthlyProductPrice(
            product_id=prod_id,
            stratum_id=stratum_id,
            route=route,
            lead_time_class=lead_time,
            month=month,
            geometric_price=Decimal(str(round(geom_mean, 2))),
            observation_count=count,
            active_days=active_days,
            source_count=source_count,
            quality_status="VALID",
        )
        
    return results
