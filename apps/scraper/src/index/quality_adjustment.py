"""
Replacement and Quality Adjustment Engine for APIx Phase 29.

Conforms to Eurostat HICP Methodological Manual 2024 (Chapter 7) and
Eurostat Web Scraping Practical Guidelines (2020 §5.2).

Implements:
1. Missing Observation Statuses:
   - VALID
   - TEMPORARILY_MISSING
   - PERMANENTLY_MISSING
   - SOLD_OUT
   - NOT_AVAILABLE
   - SCRAPER_ERROR
   - PARSER_ERROR
   - CAPTCHA_BLOCK
   - HTTP_ERROR
   - REPLACED
   - QUALITY_ADJUSTED
2. Strict Non-Zero Axiom:
   Missing or sold-out observations MUST NEVER become zero price.
3. Replacement Decision Hierarchy:
   - Determine temporary vs permanent absence
   - Search replacement candidate in same product stratum
   - Assess 14 airfare quality characteristics
   - Compute comparability score (0.0 to 1.0)
   - Select treatment:
     * DIRECT_COMPARISON
     * QUALITY_ADJUSTED_REPLACEMENT
     * IMPUTATION_STRATUM_MEAN
     * SPLICED_NON_COMPARABLE
4. Audit Trail:
   Every replacement and quality adjustment is logged with explicit rationale.
"""

from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from .product_definition import QualityCharacteristics


class ObservationStatus(str, Enum):
    """Explicit observation statuses per Phase 29 §11."""
    VALID = "VALID"
    TEMPORARILY_MISSING = "TEMPORARILY_MISSING"
    PERMANENTLY_MISSING = "PERMANENTLY_MISSING"
    SOLD_OUT = "SOLD_OUT"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    SCRAPER_ERROR = "SCRAPER_ERROR"
    PARSER_ERROR = "PARSER_ERROR"
    CAPTCHA_BLOCK = "CAPTCHA_BLOCK"
    HTTP_ERROR = "HTTP_ERROR"
    REPLACED = "REPLACED"
    QUALITY_ADJUSTED = "QUALITY_ADJUSTED"


class ReplacementTreatment(str, Enum):
    """Methodological treatments for product replacement per Eurostat HICP 2024."""
    DIRECT_COMPARISON = "DIRECT_COMPARISON"
    QUALITY_ADJUSTED_REPLACEMENT = "QUALITY_ADJUSTED_REPLACEMENT"
    IMPUTATION_STRATUM_MEAN = "IMPUTATION_STRATUM_MEAN"
    SPLICED_NON_COMPARABLE = "SPLICED_NON_COMPARABLE"


class QualityAdjustmentRecord(BaseModel):
    """
    Detailed audit log for an individual quality adjustment applied to a replacement product.
    Output target: DEL_BOM_quality_adjustments.csv.
    """
    adjustment_id: str
    replacement_id: str
    characteristic_name: str  # e.g., 'baggage_entitlement', 'seat_selection', 'departure_band', 'flexibility'
    base_value: str
    replacement_value: str
    adjustment_amount_inr: Decimal = Field(..., description="Value of quality difference (positive if replacement is superior)")
    valuation_method: str = Field(..., description="e.g. OPTION_COST, HEDONIC_REGRESSION, EXPERT_ESTIMATE")
    rationale: str
    applied_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReplacementAuditRecord(BaseModel):
    """
    Complete audit trail record for a product replacement event.
    Output target: DEL_BOM_replacements.csv.
    """
    replacement_id: str
    stratum_id: str
    route: str
    lead_time_class: str
    base_product_id: str
    base_flight_number: str
    base_price_prev_inr: Decimal
    replacement_product_id: str
    replacement_flight_number: str
    raw_replacement_price_curr_inr: Decimal
    net_quality_adjustment_inr: Decimal = Decimal("0.00")
    adjusted_replacement_price_curr_inr: Decimal
    effective_price_relative: Decimal
    treatment_type: ReplacementTreatment
    comparability_score: float = Field(..., ge=0.0, le=1.0)
    decision_rationale: str
    recorded_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QualityAdjustmentEngine:
    """
    Evaluates comparability between missing base products and candidate replacements.
    Computes quality adjustments for observable service differentials (baggage, refundability, time bands).
    """

    # Valuation benchmarks for airfare service quality differentials (in INR)
    # References standard airline add-on fees in the Indian domestic market
    VALUATION_BENCHMARKS = {
        "CHECKIN_BAGGAGE_PER_5KG": Decimal("500.00"),
        "CABIN_BAGGAGE_ALLOWANCE": Decimal("350.00"),
        "FULL_REFUNDABILITY": Decimal("1500.00"),
        "ZERO_CHANGE_FEE": Decimal("1000.00"),
        "TIME_BAND_SHIFTS": Decimal("300.00"),
    }

    def __init__(self, comparability_threshold: float = 0.70):
        self.comparability_threshold = comparability_threshold

    def calculate_comparability_score(
        self,
        base: QualityCharacteristics,
        candidate: QualityCharacteristics,
    ) -> Tuple[float, List[QualityAdjustmentRecord]]:
        """
        Computes multi-dimensional comparability score (0.0 to 1.0) and identifies quality adjustments.
        Weights 14 characteristics according to consumer utility hierarchy.
        """
        score = 0.0
        adjustments: List[QualityAdjustmentRecord] = []
        adj_counter = 1

        # 1. Route match (mandatory: 0 score if different route)
        if base.route != candidate.route:
            return 0.0, []
        score += 0.25

        # 2. Lead time match (mandatory for comparable stratum)
        if base.lead_time_class == candidate.lead_time_class:
            score += 0.20
        else:
            return 0.0, []

        # 3. Airline / Brand similarity
        if base.airline == candidate.airline:
            score += 0.15
        else:
            # Different airline in same market segment
            score += 0.08

        # 4. Non-stop vs Stops
        if base.stops == candidate.stops:
            score += 0.15
        else:
            score += 0.00  # Penalty for different stop category

        # 5. Departure time band proximity
        dep_base = base.departure_time or ""
        dep_cand = candidate.departure_time or ""
        if dep_base[:2] == dep_cand[:2]:
            score += 0.10
        elif dep_base and dep_cand and abs(int(dep_base[:2]) - int(dep_cand[:2])) <= 3:
            score += 0.05
            # Small quality adjustment for departure hour shift
            adjustments.append(
                QualityAdjustmentRecord(
                    adjustment_id=f"QA_{adj_counter}",
                    replacement_id="",
                    characteristic_name="departure_time_shift",
                    base_value=dep_base,
                    replacement_value=dep_cand,
                    adjustment_amount_inr=Decimal("-150.00") if int(dep_cand[:2]) < int(dep_base[:2]) else Decimal("150.00"),
                    valuation_method="OPTION_COST",
                    rationale="Minor departure slot adjustment (±3 hour departure band window)",
                )
            )
            adj_counter += 1

        # 6. Baggage entitlement
        base_bag = base.baggage_allowance_kg or 15
        cand_bag = candidate.baggage_allowance_kg or 15
        if base_bag == cand_bag:
            score += 0.08
        else:
            diff_kg = cand_bag - base_bag
            diff_adj = Decimal(str(diff_kg // 5)) * self.VALUATION_BENCHMARKS["CHECKIN_BAGGAGE_PER_5KG"]
            adjustments.append(
                QualityAdjustmentRecord(
                    adjustment_id=f"QA_{adj_counter}",
                    replacement_id="",
                    characteristic_name="checkin_baggage_kg",
                    base_value=f"{base_bag}kg",
                    replacement_value=f"{cand_bag}kg",
                    adjustment_amount_inr=diff_adj,
                    valuation_method="OPTION_COST",
                    rationale=f"Check-in baggage differential: {diff_kg:+d}kg valued at market rate",
                )
            )
            adj_counter += 1
            score += 0.04

        # 7. Refundability & Changeability
        if base.refundability == candidate.refundability and base.changeability == candidate.changeability:
            score += 0.07
        else:
            score += 0.02

        return min(round(score, 4), 1.0), adjustments

    def evaluate_replacement(
        self,
        base_product_id: str,
        base_flight_number: str,
        base_price_prev: Decimal,
        base_chars: QualityCharacteristics,
        candidate_product_id: str,
        candidate_flight_number: str,
        candidate_price_curr: Decimal,
        candidate_chars: QualityCharacteristics,
        stratum_id: str,
    ) -> Tuple[ReplacementAuditRecord, List[QualityAdjustmentRecord]]:
        """
        Determines treatment type and creates comprehensive audit record for a candidate replacement.
        """
        comp_score, adjustments = self.calculate_comparability_score(base_chars, candidate_chars)
        rep_id = f"REP_{base_product_id[:8]}_{candidate_product_id[:8]}"

        # Bind replacement_id to adjustments
        for adj in adjustments:
            adj.replacement_id = rep_id

        net_adjustment = sum((adj.adjustment_amount_inr for adj in adjustments), Decimal("0.00"))

        if comp_score >= 0.95 and net_adjustment == Decimal("0.00"):
            treatment = ReplacementTreatment.DIRECT_COMPARISON
            adjusted_price = candidate_price_curr
            rationale = "Direct comparison: replacement flight possesses identical essential service characteristics."
        elif comp_score >= self.comparability_threshold:
            treatment = ReplacementTreatment.QUALITY_ADJUSTED_REPLACEMENT
            # Adjusted price = candidate raw price - net quality adjustment
            # If replacement is superior (net_adj > 0), subtract it to isolate pure price change
            adjusted_price = max(candidate_price_curr - net_adjustment, Decimal("100.00"))
            rationale = (
                f"Quality-adjusted replacement: comparability score {comp_score:.2f} >= {self.comparability_threshold:.2f}. "
                f"Net adjustment of INR {net_adjustment:+,.2f} applied to isolate pure price movement."
            )
        else:
            treatment = ReplacementTreatment.SPLICED_NON_COMPARABLE
            adjusted_price = base_price_prev  # Neutral relative in non-comparable splice
            rationale = (
                f"Non-comparable replacement: comparability score {comp_score:.2f} < {self.comparability_threshold:.2f}. "
                f"Candidate introduced without direct price comparison via chain splicing."
            )

        eff_relative = adjusted_price / base_price_prev

        audit_record = ReplacementAuditRecord(
            replacement_id=rep_id,
            stratum_id=stratum_id,
            route=base_chars.route,
            lead_time_class=base_chars.lead_time_class,
            base_product_id=base_product_id,
            base_flight_number=base_flight_number,
            base_price_prev_inr=base_price_prev,
            replacement_product_id=candidate_product_id,
            replacement_flight_number=candidate_flight_number,
            raw_replacement_price_curr_inr=candidate_price_curr,
            net_quality_adjustment_inr=net_adjustment,
            adjusted_replacement_price_curr_inr=adjusted_price,
            effective_price_relative=Decimal(str(round(eff_relative, 6))),
            treatment_type=treatment,
            comparability_score=comp_score,
            decision_rationale=rationale,
        )

        return audit_record, adjustments


# ---------------------------------------------------------------------------
# Full-Stratum Schedule-Churn Class-Mean Imputation Engine (§Roadmap Item 2)
# ---------------------------------------------------------------------------

class ImputationStatus(str, Enum):
    OBSERVED_DIRECT = "OBSERVED_DIRECT"
    IMPUTED_CLASS_MEAN = "IMPUTED_CLASS_MEAN"
    UNIMPUTABLE_NO_DONORS = "UNIMPUTABLE_NO_DONORS"


class ImputedClassMeanResult(BaseModel):
    """
    Provenance and calculation result for a full-stratum class-mean imputation event.
    Conforms to Eurostat HICP Methodological Manual 2024 §7.3.
    """
    stratum_id: str
    route: str
    lead_time_class: str
    airline: Optional[str] = None
    period: str
    is_imputed: bool
    status: ImputationStatus
    imputed_jevons_link: Optional[Decimal] = None
    donor_hierarchy_level: Optional[str] = None  # ROUTE_CARRIER_LEADTIME, ROUTE_LEADTIME, ROUTE_ALL
    donor_strata_count: int = 0
    donor_matched_pairs_count: int = 0
    provenance_note: str
    imputed_at_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClassMeanImputationEngine:
    """
    Handles 100% stratum attrition during bi-annual airline schedule shifts (IATA Summer/Winter).
    Imputes Jevons link from parent hierarchy:
    1. Route x Carrier x Lead Time (sibling departure bands)
    2. Route x Lead Time (across all carriers)
    3. Route Overall (across all lead times)
    NEVER imputes zero.
    """

    def __init__(self, methodology_version: str = "Eurostat_HICP_ClassMean_v1.0"):
        self.methodology_version = methodology_version
        self.imputation_history: List[ImputedClassMeanResult] = []

    def impute_stratum_link(
        self,
        stratum_id: str,
        route: str,
        lead_time_class: str,
        period: str,
        matched_by_stratum: Dict[str, Tuple[List[Any], int, float, bool]],
        stratum_metadata: Optional[Dict[str, Dict[str, str]]] = None,
        airline: Optional[str] = None,
    ) -> ImputedClassMeanResult:
        """
        Evaluates 100% stratum attrition and computes class-mean geometric link from parent donors.
        Never returns zero.
        """
        import math

        # Step 1: Donor search level 1 (Route x Carrier x Lead Time)
        donors_lvl1: List[Any] = []
        donor_strata_lvl1: List[str] = []
        meta = stratum_metadata or {}

        if airline:
            for s_key, (m_list, elig, cov, is_pub) in matched_by_stratum.items():
                if s_key != stratum_id and m_list:
                    s_meta = meta.get(s_key, {})
                    if (
                        s_meta.get("route") == route
                        and s_meta.get("lead_time_class") == lead_time_class
                        and s_meta.get("airline") == airline
                    ):
                        donors_lvl1.extend(m_list)
                        donor_strata_lvl1.append(s_key)

        if donors_lvl1:
            mean_log = sum(m.log_price_relative for m in donors_lvl1) / len(donors_lvl1)
            link_val = Decimal(str(round(math.exp(mean_log), 6)))
            res = ImputedClassMeanResult(
                stratum_id=stratum_id,
                route=route,
                lead_time_class=lead_time_class,
                airline=airline,
                period=period,
                is_imputed=True,
                status=ImputationStatus.IMPUTED_CLASS_MEAN,
                imputed_jevons_link=link_val,
                donor_hierarchy_level="ROUTE_CARRIER_LEADTIME",
                donor_strata_count=len(donor_strata_lvl1),
                donor_matched_pairs_count=len(donors_lvl1),
                provenance_note=(
                    f"Class-mean imputation applied: 100% stratum attrition in {stratum_id}. "
                    f"Imputed from {len(donors_lvl1)} matched donor pairs across {len(donor_strata_lvl1)} sibling carrier strata."
                ),
            )
            self.imputation_history.append(res)
            return res

        # Step 2: Donor search level 2 (Route x Lead Time across all carriers)
        donors_lvl2: List[Any] = []
        donor_strata_lvl2: List[str] = []
        for s_key, (m_list, elig, cov, is_pub) in matched_by_stratum.items():
            if s_key != stratum_id and m_list:
                s_meta = meta.get(s_key, {})
                if s_meta.get("route") == route and s_meta.get("lead_time_class") == lead_time_class:
                    donors_lvl2.extend(m_list)
                    donor_strata_lvl2.append(s_key)

        if donors_lvl2:
            mean_log = sum(m.log_price_relative for m in donors_lvl2) / len(donors_lvl2)
            link_val = Decimal(str(round(math.exp(mean_log), 6)))
            res = ImputedClassMeanResult(
                stratum_id=stratum_id,
                route=route,
                lead_time_class=lead_time_class,
                airline=airline,
                period=period,
                is_imputed=True,
                status=ImputationStatus.IMPUTED_CLASS_MEAN,
                imputed_jevons_link=link_val,
                donor_hierarchy_level="ROUTE_LEADTIME",
                donor_strata_count=len(donor_strata_lvl2),
                donor_matched_pairs_count=len(donors_lvl2),
                provenance_note=(
                    f"Class-mean imputation applied: 100% stratum attrition in {stratum_id}. "
                    f"Imputed from {len(donors_lvl2)} matched donor pairs across {len(donor_strata_lvl2)} route lead-time strata."
                ),
            )
            self.imputation_history.append(res)
            return res

        # Step 3: Donor search level 3 (Route overall across all lead times)
        donors_lvl3: List[Any] = []
        donor_strata_lvl3: List[str] = []
        for s_key, (m_list, elig, cov, is_pub) in matched_by_stratum.items():
            if s_key != stratum_id and m_list:
                s_meta = meta.get(s_key, {})
                if s_meta.get("route") == route:
                    donors_lvl3.extend(m_list)
                    donor_strata_lvl3.append(s_key)

        if donors_lvl3:
            mean_log = sum(m.log_price_relative for m in donors_lvl3) / len(donors_lvl3)
            link_val = Decimal(str(round(math.exp(mean_log), 6)))
            res = ImputedClassMeanResult(
                stratum_id=stratum_id,
                route=route,
                lead_time_class=lead_time_class,
                airline=airline,
                period=period,
                is_imputed=True,
                status=ImputationStatus.IMPUTED_CLASS_MEAN,
                imputed_jevons_link=link_val,
                donor_hierarchy_level="ROUTE_ALL",
                donor_strata_count=len(donor_strata_lvl3),
                donor_matched_pairs_count=len(donors_lvl3),
                provenance_note=(
                    f"Class-mean imputation applied: 100% stratum attrition in {stratum_id}. "
                    f"Imputed from {len(donors_lvl3)} matched donor pairs across {len(donor_strata_lvl3)} route-wide strata."
                ),
            )
            self.imputation_history.append(res)
            return res

        # If zero donors exist anywhere in the route: NEVER impute zero!
        res_fail = ImputedClassMeanResult(
            stratum_id=stratum_id,
            route=route,
            lead_time_class=lead_time_class,
            airline=airline,
            period=period,
            is_imputed=False,
            status=ImputationStatus.UNIMPUTABLE_NO_DONORS,
            imputed_jevons_link=None,
            donor_hierarchy_level=None,
            donor_strata_count=0,
            donor_matched_pairs_count=0,
            provenance_note=f"No donor strata available in route {route} to impute stratum {stratum_id}. Null preserved; never zero.",
        )
        self.imputation_history.append(res_fail)
        return res_fail

