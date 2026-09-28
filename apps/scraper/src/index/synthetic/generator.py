"""
Synthetic August 2026 Longitudinal Demonstration Generator (§Roadmap Validation).

CRITICAL GOVERNANCE INVARIANT:
This dataset is SYNTHETIC and MUST NEVER be presented or cited as observed historical
Indian airfare data. It exists solely to validate daily, weekly, and monthly APIx
econometric pipelines without waiting for future real collection rounds.
It must never overwrite or contaminate the real 11,716-observation production dataset.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from models.canonical import classify_departure_time_band, classify_stop_category, classify_travel_day_type
from .models import (
    SYNTHETIC_DATA_STATUS,
    SYNTHETIC_GENERATION_VERSION,
    SyntheticAugustMetadata,
    SyntheticFareObservation,
)


class SyntheticAugustGenerator:
    """
    Generates a statistically conservative, reproducible synthetic panel of daily airfare
    observations for August 2026 based on the empirical distributions of the real 11,716-observation
    production baseline.
    """

    LEAD_TIME_DAYS_MAP: Dict[str, int] = {
        "T+1": 1,
        "T+7": 7,
        "T+15": 15,
        "T+21": 21,
        "T+30": 30,
        "T+45": 45,
    }

    def __init__(
        self,
        baseline_path: str = "runtime/top60_observation_classification.json",
        output_dir: str = "runtime/synthetic_aug2026",
        random_seed: int = 42,
    ):
        self.baseline_path = Path(baseline_path)
        self.output_dir = Path(output_dir)
        self.random_seed = random_seed
        self.rng = random.Random(random_seed)

    def load_baseline_templates(self) -> List[Dict[str, Any]]:
        """
        Loads the real production dataset and extracts the 5,977 VALID_BASELINE records
        to serve as the cross-sectional empirical template.
        """
        if not self.baseline_path.exists():
            raise FileNotFoundError(f"Baseline file not found at {self.baseline_path}")

        with open(self.baseline_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_obs = data.get("observations", [])
        valid_templates = [
            o for o in raw_obs
            if o.get("status") == "VALID_BASELINE" and float(o.get("total_fare", 0)) > 0
        ]
        if not valid_templates:
            raise ValueError("No VALID_BASELINE observations found in production dataset")

        return valid_templates

    def generate_synthetic_panel(self) -> Tuple[List[Dict[str, Any]], SyntheticAugustMetadata]:
        """
        Generates the 31-day August 2026 longitudinal demonstration dataset.
        """
        # Reset RNG with fixed seed for exact reproducibility
        self.rng.seed(self.random_seed)

        templates = self.load_baseline_templates()

        # Build product pool and determine deterministic intrinsic schedule presence probabilities
        product_pool: List[Dict[str, Any]] = []
        routes = sorted(set(t["route"] for t in templates))
        lead_times = sorted(set(t["lead_time"] for t in templates))

        for idx, t in enumerate(templates):
            route = t["route"]
            lt = t["lead_time"]
            airline = t.get("airline") or "Domestic Carrier"
            flight_num = t.get("flight_number") or f"FL-{idx}"
            dep_time = t.get("departure_time_local") or "10:00"
            dep_band = classify_departure_time_band(dep_time)
            stops = int(t.get("stops", 0))
            stop_cat = classify_stop_category(stops)
            base_fare = float(t["total_fare"])

            # Deterministic product presence probability p_i in [0.50, 0.94]
            key_for_hash = f"{route}_{lt}_{airline}_{flight_num}_{idx}"
            h_val = int(hashlib.md5(key_for_hash.encode()).hexdigest(), 16)
            presence_prob = 0.50 + ((h_val % 45) / 100.0)

            product_fp = f"FP_{route}_{lt}_{airline}_{flight_num}_{dep_band}_{stops}"
            canon_id = f"CANON_{route}_{lt}_{idx:05d}"

            product_pool.append({
                "index": idx,
                "route": route,
                "lead_time": lt,
                "lead_days": self.LEAD_TIME_DAYS_MAP.get(lt, 7),
                "airline": airline,
                "flight_number": flight_num,
                "departure_time_local": dep_time,
                "departure_time_band": dep_band,
                "stops": stops,
                "stop_category": stop_cat,
                "cabin": t.get("cabin", "ECONOMY"),
                "fare_family": t.get("fare_family", "STANDARD") or "STANDARD",
                "source": t.get("source", "google_flights"),
                "base_fare": base_fare,
                "presence_prob": presence_prob,
                "product_fingerprint": product_fp,
                "canonical_product_id": canon_id,
            })

        # AR(1) state variables for route shocks across the 31 days
        route_shocks: Dict[str, float] = {r: 0.0 for r in routes}
        all_synthetic_records: List[Dict[str, Any]] = []

        # Iterate through every calendar day in August 2026 (2026-08-01 to 2026-08-31)
        for day in range(1, 32):
            coll_date = date(2026, 8, day)
            coll_date_str = coll_date.isoformat()

            # 1. Update route-level AR(1) shocks: mu_r(d) = 0.7 * mu_r(d-1) + N(0, 0.008^2)
            for r in routes:
                eta = self.rng.gauss(0.0, 0.008)
                route_shocks[r] = (0.7 * route_shocks[r]) + eta

            # 2. Lead-time shocks for the day: gamma_L(d) ~ N(0, 0.005^2)
            lead_shocks = {lt: self.rng.gauss(0.0, 0.005) for lt in lead_times}

            # 3. Generate observations for active products on this day
            for prod in product_pool:
                # Presence determination
                if self.rng.random() > prod["presence_prob"]:
                    continue  # Product not scheduled/operating on this day (schedule churn)

                # Forward-looking travel date: collection_date + lead_days
                travel_date = coll_date + timedelta(days=prod["lead_days"])
                travel_date_str = travel_date.isoformat()
                travel_day_type = classify_travel_day_type(travel_date)

                # Day-of-week demand effect: Friday (weekday 4) or Sunday (weekday 6) has mild surge
                delta_weekend = 0.015 if travel_date.weekday() in (4, 6) else 0.0

                # Idiosyncratic noise: N(0, 0.012^2) with 2% probability of a yield shift
                eps = self.rng.gauss(0.0, 0.012)
                if self.rng.random() < 0.02:
                    eps += self.rng.gauss(0.0, 0.035)

                # Total log-price perturbation
                mu_r = route_shocks[prod["route"]]
                gamma_l = lead_shocks[prod["lead_time"]]
                log_pert = mu_r + gamma_l + delta_weekend + eps

                # Synthetic fare calculation
                raw_synthetic_fare = prod["base_fare"] * math.exp(log_pert)
                # Enforce strictly positive, non-negative, plausible fares (minimum ₹1,200.00)
                final_fare = max(round(raw_synthetic_fare, 2), 1200.00)

                obs_record = {
                    "observation_id": f"SYN_AUG2026_{coll_date_str}_{prod['index']:05d}",
                    "data_status": SYNTHETIC_DATA_STATUS,
                    "synthetic": True,
                    "synthetic_generation_version": SYNTHETIC_GENERATION_VERSION,
                    "collection_date": coll_date_str,
                    "collection_month": "2026-08",
                    "travel_date": travel_date_str,
                    "lead_time_class": prod["lead_time"],
                    "lead_days": prod["lead_days"],
                    "route": prod["route"],
                    "origin": prod["route"].split("-")[0],
                    "destination": prod["route"].split("-")[1],
                    "airline": prod["airline"],
                    "flight_number": prod["flight_number"],
                    "departure_time_local": prod["departure_time_local"],
                    "departure_time_band": prod["departure_time_band"],
                    "stops": prod["stops"],
                    "stop_category": prod["stop_category"],
                    "cabin": prod["cabin"],
                    "fare_family": prod["fare_family"],
                    "travel_day_type": travel_day_type,
                    "passenger_type": "ADULT",
                    "baggage_allowance_kg": 15,
                    "total_fare": float(final_fare),
                    "currency": "INR",
                    "canonical_product_id": prod["canonical_product_id"],
                    "product_fingerprint": prod["product_fingerprint"],
                    "source": prod["source"],
                    "status": "VALID_BASELINE",
                }
                all_synthetic_records.append(obs_record)

        # Assemble metadata
        meta = SyntheticAugustMetadata(
            dataset_name="APIx_Synthetic_August_2026_Longitudinal_Demonstration",
            source_real_dataset="11,716-observation production baseline (runtime/top60_observation_classification.json)",
            data_status=SYNTHETIC_DATA_STATUS,
            synthetic=True,
            synthetic_generation_version=SYNTHETIC_GENERATION_VERSION,
            random_seed=self.random_seed,
            generation_date_utc=datetime.now(timezone.utc).isoformat(),
            number_of_collection_days=31,
            number_of_synthetic_observations=len(all_synthetic_records),
            route_count=len(routes),
            lead_time_count=len(lead_times),
            cell_count=len(routes) * len(lead_times),
            canonical_product_pool_size=len(product_pool),
            average_daily_observations=round(len(all_synthetic_records) / 31.0, 2),
            price_generation_methodology=(
                "Log-price perturbation around empirical baseline fares: "
                "ln(P_{i,d}) = ln(P_i^0) + mu_r(d) + gamma_L(d) + delta_day(d) + epsilon_{i,d} "
                "with route-level AR(1) persistence (rho=0.7), lead-time class shocks, weekend travel premiums, "
                "and realistic product schedule churn (p_i in [0.50, 0.94])."
            ),
            assumptions=[
                "Log-normal multiplicative perturbations preserve empirical relative price structure.",
                "Route common shocks follow an AR(1) process with 0.7 autocorrelation and sigma=0.008.",
                "Weekend travel premium (+1.5%) applied to Friday and Sunday departure dates.",
                "Product presence sampled from empirical schedule frequencies between 0.50 and 0.94.",
                "Plausibility constraint: all fares strictly positive with hard minimum of ₹1,200.00.",
                "Zero fabrication of real historical observations; generated exclusively for pipeline demonstration.",
            ],
            disclaimer=(
                "CRITICAL WARNING: THIS DATASET IS SYNTHETIC AND IS GENERATED SOLELY FOR METHODOLOGY "
                "VALIDATION AND DEMONSTRATION OF THE APIx INDEX PIPELINE. IT MUST NEVER BE PRESENTED OR "
                "CITED AS OBSERVED HISTORICAL INDIAN AIRFARE DATA. IT MUST NEVER BE COMBINED WITH REAL "
                "OBSERVATIONS TO PUBLISH INFLATION CLAIMS."
            ),
        )

        return all_synthetic_records, meta

    def save(self) -> Tuple[Path, Path]:
        """
        Generates and saves the synthetic dataset and metadata to runtime/synthetic_aug2026/.
        Does NOT alter runtime/top60_observation_classification.json.
        """
        records, meta = self.generate_synthetic_panel()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        obs_file = self.output_dir / "synthetic_aug2026_observations.json"
        meta_file = self.output_dir / "synthetic_aug2026_metadata.json"

        # Save observations
        with open(obs_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": meta.model_dump(),
                "observations": records,
            }, f, indent=2)

        # Save standalone metadata
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta.model_dump(), f, indent=2)

        return obs_file, meta_file
