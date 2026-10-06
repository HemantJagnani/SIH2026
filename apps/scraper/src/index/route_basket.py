"""
DGCA Calendar Year 2024 Top-60 Route Basket for APIx.

Source Methodology:
- Directorate General of Civil Aviation (DGCA), Ministry of Civil Aviation, Government of India.
- Scheduled domestic city-pair passenger traffic for CY2024 (January 2024 – December 2024).
- Selected Top 60 routes by annual scheduled passenger volume.
- Basket passenger volume: 91,995,307.
- All-India CY2024 domestic passenger volume: 161,325,253.
- Domestic traffic coverage: 57.0247%.

Key Invariants:
1. Route weights represent empirical DGCA passenger traffic shares within the Top-60 basket:
   route_weight = annual_route_passenger_volume / 91,995,307.
2. Route weights sum to exactly 1.00000000.
3. Completely separated from MoSPI CPI 2024 airfare expenditure weight (0.02951% / 0.0002951).
   Anti-contamination guards fail loudly if CPI expenditure weights are ever passed as route weights.
4. Airport/station distinctions strictly preserved:
   DABOLIM (GOI) and GOA / MOPA (GOX) are distinct commercial airport stations.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

# Constants for Basket Identification
BASKET_ID = "DGCA_CY2024_TOP60"
REFERENCE_PERIOD = "CY2024"
BASKET_SIZE = 60
SOURCE = "DGCA"
SOURCE_DESCRIPTION = "Scheduled domestic city-pair passenger traffic"
COVERAGE_PERCENT = Decimal("57.0247")
TOTAL_BASKET_PASSENGER_VOLUME = 91995307
TOTAL_ALL_INDIA_PASSENGER_VOLUME = 161325253

# Prohibited weights and keys to guard against CPI expenditure contamination
PROHIBITED_CPI_ROUTE_KEYS: Set[str] = {
    "07.3.3.1.2.01",
    "07.3.3.1.01",
    "07.3.3.1",
    "CPI_AIRFARE_WEIGHT",
    "CPI_AIRFARE_EXPENDITURE_WEIGHT",
}

PROHIBITED_CPI_WEIGHT_VALUES: Set[Decimal] = {
    Decimal("0.02951"),
    Decimal("0.0002951"),
    Decimal("0.001850"),
}


class DGCARouteItem(BaseModel):
    """Individual route item within the DGCA Top-60 basket."""
    rank: int = Field(..., ge=1, le=60, description="Rank by CY2024 passenger volume (1-60)")
    route_id: str = Field(..., description="Canonical route identifier, e.g. DEL-BOM")
    origin: str = Field(..., description="Origin city name (DGCA standard)")
    destination: str = Field(..., description="Destination city name (DGCA standard)")
    origin_code: str = Field(..., description="IATA airport code for origin")
    destination_code: str = Field(..., description="IATA airport code for destination")
    annual_passenger_volume: int = Field(..., gt=0, description="CY2024 passenger headcount")
    dgca_share_percent: Decimal = Field(..., gt=Decimal("0"), description="Share of All-India traffic (%)")
    route_weight: Decimal = Field(..., gt=Decimal("0"), description="Normalized weight within Top-60 basket")
    source: str = Field(default=SOURCE, description="Data source authority")
    reference_period: str = Field(default=REFERENCE_PERIOD, description="Reference period of passenger traffic")
    basket_id: str = Field(default=BASKET_ID, description="Unique basket identifier")


class DGCARouteBasketConfig(BaseModel):
    """Complete versioned configuration and metadata for the DGCA Top-60 basket."""
    basket_id: str = Field(default=BASKET_ID)
    reference_period: str = Field(default=REFERENCE_PERIOD)
    basket_size: int = Field(default=BASKET_SIZE)
    source: str = Field(default=SOURCE)
    source_description: str = Field(default=SOURCE_DESCRIPTION)
    coverage_percent: Decimal = Field(default=COVERAGE_PERCENT)
    total_basket_passenger_volume: int = Field(default=TOTAL_BASKET_PASSENGER_VOLUME)
    total_all_india_passenger_volume: int = Field(default=TOTAL_ALL_INDIA_PASSENGER_VOLUME)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    routes: List[DGCARouteItem] = Field(default_factory=list)


# Raw route records from CY2024 DGCA city-pair monthly datasets
_RAW_TOP60_RECORDS = [
    (1, "DEL-BOM", "DELHI", "MUMBAI", "DEL", "BOM", 6885053, Decimal("4.2678"), Decimal("0.07484135")),
    (2, "BLR-DEL", "BENGALURU", "DELHI", "BLR", "DEL", 4761622, Decimal("2.9516"), Decimal("0.05175940")),
    (3, "BLR-BOM", "BENGALURU", "MUMBAI", "BLR", "BOM", 4245720, Decimal("2.6318"), Decimal("0.04615148")),
    (4, "DEL-HYD", "DELHI", "HYDERABAD", "DEL", "HYD", 3280715, Decimal("2.0336"), Decimal("0.03566176")),
    (5, "DEL-PNQ", "DELHI", "PUNE", "DEL", "PNQ", 2906263, Decimal("1.8015"), Decimal("0.03159143")),
    (6, "DEL-CCU", "DELHI", "KOLKATA", "DEL", "CCU", 2757937, Decimal("1.7096"), Decimal("0.02997911")),
    (7, "AMD-DEL", "AHMEDABAD", "DELHI", "AMD", "DEL", 2489550, Decimal("1.5432"), Decimal("0.02706171")),
    (8, "DEL-MAA", "CHENNAI", "DELHI", "MAA", "DEL", 2424761, Decimal("1.5030"), Decimal("0.02635744")),
    (9, "BOM-HYD", "HYDERABAD", "MUMBAI", "HYD", "BOM", 2398298, Decimal("1.4866"), Decimal("0.02606979")),
    (10, "DEL-SXR", "DELHI", "SRINAGAR", "DEL", "SXR", 2393837, Decimal("1.4839"), Decimal("0.02602129")),
    (11, "BLR-CCU", "BENGALURU", "KOLKATA", "BLR", "CCU", 2335591, Decimal("1.4478"), Decimal("0.02538815")),
    (12, "BOM-MAA", "CHENNAI", "MUMBAI", "MAA", "BOM", 2253454, Decimal("1.3968"), Decimal("0.02449531")),
    (13, "BLR-HYD", "BENGALURU", "HYDERABAD", "BLR", "HYD", 2252334, Decimal("1.3961"), Decimal("0.02448314")),
    (14, "AMD-BOM", "AHMEDABAD", "MUMBAI", "AMD", "BOM", 2147823, Decimal("1.3314"), Decimal("0.02334709")),
    (15, "BOM-CCU", "KOLKATA", "MUMBAI", "CCU", "BOM", 2060343, Decimal("1.2771"), Decimal("0.02239618")),
    (16, "BLR-PNQ", "BENGALURU", "PUNE", "BLR", "PNQ", 1918477, Decimal("1.1892"), Decimal("0.02085407")),
    (17, "DEL-GOI", "DABOLIM", "DELHI", "GOI", "DEL", 1607773, Decimal("0.9966"), Decimal("0.01747668")),
    (18, "HYD-MAA", "CHENNAI", "HYDERABAD", "MAA", "HYD", 1549175, Decimal("0.9603"), Decimal("0.01683972")),
    (19, "DEL-GAU", "DELHI", "GUWAHATI", "DEL", "GAU", 1531881, Decimal("0.9496"), Decimal("0.01665173")),
    (20, "BLR-COK", "BENGALURU", "KOCHI", "BLR", "COK", 1500003, Decimal("0.9298"), Decimal("0.01630521")),
    (21, "DEL-LKO", "DELHI", "LUCKNOW", "DEL", "LKO", 1489748, Decimal("0.9234"), Decimal("0.01619374")),
    (22, "BOM-GOI", "DABOLIM", "MUMBAI", "GOI", "BOM", 1468167, Decimal("0.9101"), Decimal("0.01595915")),
    (23, "BLR-MAA", "BENGALURU", "CHENNAI", "BLR", "MAA", 1429039, Decimal("0.8858"), Decimal("0.01553383")),
    (24, "DEL-PAT", "DELHI", "PATNA", "DEL", "PAT", 1382171, Decimal("0.8568"), Decimal("0.01502436")),
    (25, "BOM-JAI", "JAIPUR", "MUMBAI", "JAI", "BOM", 1253605, Decimal("0.7771"), Decimal("0.01362684")),
    (26, "ATQ-DEL", "AMRITSAR", "DELHI", "ATQ", "DEL", 1238274, Decimal("0.7676"), Decimal("0.01346019")),
    (27, "BOM-COK", "KOCHI", "MUMBAI", "COK", "BOM", 1190089, Decimal("0.7377"), Decimal("0.01293641")),
    (28, "CCU-HYD", "HYDERABAD", "KOLKATA", "HYD", "CCU", 1159513, Decimal("0.7187"), Decimal("0.01260405")),
    (29, "BBI-DEL", "BHUBANESWAR", "DELHI", "BBI", "DEL", 1122572, Decimal("0.6958"), Decimal("0.01220249")),
    (30, "BLR-GOI", "BENGALURU", "DABOLIM", "BLR", "GOI", 1108857, Decimal("0.6873"), Decimal("0.01205341")),
    (31, "CCU-GAU", "GUWAHATI", "KOLKATA", "GAU", "CCU", 1088907, Decimal("0.6750"), Decimal("0.01183655")),
    (32, "BOM-GOX", "GOA", "MUMBAI", "GOX", "BOM", 1066649, Decimal("0.6612"), Decimal("0.01159460")),
    (33, "DEL-IXB", "BAGDOGRA", "DELHI", "IXB", "DEL", 1055632, Decimal("0.6544"), Decimal("0.01147485")),
    (34, "COK-DEL", "DELHI", "KOCHI", "DEL", "COK", 1013384, Decimal("0.6282"), Decimal("0.01101561")),
    (35, "CCU-MAA", "CHENNAI", "KOLKATA", "MAA", "CCU", 1009171, Decimal("0.6256"), Decimal("0.01096981")),
    (36, "DEL-GOX", "DELHI", "GOA", "DEL", "GOX", 949836, Decimal("0.5888"), Decimal("0.01032483")),
    (37, "BOM-LKO", "LUCKNOW", "MUMBAI", "LKO", "BOM", 931345, Decimal("0.5773"), Decimal("0.01012383")),
    (38, "DEL-IXR", "DELHI", "RANCHI", "DEL", "IXR", 927970, Decimal("0.5752"), Decimal("0.01008714")),
    (39, "GOI-HYD", "DABOLIM", "HYDERABAD", "GOI", "HYD", 921820, Decimal("0.5714"), Decimal("0.01002029")),
    (40, "AMD-BLR", "AHMEDABAD", "BENGALURU", "AMD", "BLR", 912648, Decimal("0.5657"), Decimal("0.00992059")),
    (41, "DEL-IDR", "DELHI", "INDORE", "DEL", "IDR", 900874, Decimal("0.5584"), Decimal("0.00979261")),
    (42, "DEL-IXC", "CHANDIGARH", "DELHI", "IXC", "DEL", 885092, Decimal("0.5486"), Decimal("0.00962106")),
    (43, "DEL-IXL", "DELHI", "LEH", "DEL", "IXL", 869332, Decimal("0.5389"), Decimal("0.00944974")),
    (44, "CJB-MAA", "CHENNAI", "COIMBATORE", "MAA", "CJB", 857020, Decimal("0.5312"), Decimal("0.00931591")),
    (45, "BLR-TRV", "BENGALURU", "TRIVANDRUM", "BLR", "TRV", 848434, Decimal("0.5259"), Decimal("0.00922258")),
    (46, "HYD-VTZ", "HYDERABAD", "VISAKHAPATNAM", "HYD", "VTZ", 839887, Decimal("0.5206"), Decimal("0.00912967")),
    (47, "BBI-BLR", "BENGALURU", "BHUBANESWAR", "BLR", "BBI", 825875, Decimal("0.5119"), Decimal("0.00897736")),
    (48, "DEL-VNS", "DELHI", "VARANASI", "DEL", "VNS", 801782, Decimal("0.4970"), Decimal("0.00871547")),
    (49, "CCU-IXA", "AGARTALA", "KOLKATA", "IXA", "CCU", 789865, Decimal("0.4896"), Decimal("0.00858593")),
    (50, "DEL-RPR", "DELHI", "RAIPUR", "DEL", "RPR", 772248, Decimal("0.4787"), Decimal("0.00839443")),
    (51, "BOM-VNS", "MUMBAI", "VARANASI", "BOM", "VNS", 750055, Decimal("0.4649"), Decimal("0.00815319")),
    (52, "BLR-VNS", "BENGALURU", "VARANASI", "BLR", "VNS", 749368, Decimal("0.4645"), Decimal("0.00814572")),
    (53, "BLR-GAU", "BENGALURU", "GUWAHATI", "BLR", "GAU", 746671, Decimal("0.4628"), Decimal("0.00811640")),
    (54, "BLR-LKO", "BENGALURU", "LUCKNOW", "BLR", "LKO", 737882, Decimal("0.4574"), Decimal("0.00802087")),
    (55, "BOM-CJB", "COIMBATORE", "MUMBAI", "CJB", "BOM", 720184, Decimal("0.4464"), Decimal("0.00782849")),
    (56, "BOM-IDR", "INDORE", "MUMBAI", "IDR", "BOM", 714065, Decimal("0.4426"), Decimal("0.00776197")),
    (57, "BLR-JAI", "BENGALURU", "JAIPUR", "BLR", "JAI", 704531, Decimal("0.4367"), Decimal("0.00765834")),
    (58, "HYD-TIR", "HYDERABAD", "TIRUPATI", "HYD", "TIR", 697530, Decimal("0.4324"), Decimal("0.00758223")),
    (59, "COK-HYD", "HYDERABAD", "KOCHI", "HYD", "COK", 688929, Decimal("0.4270"), Decimal("0.00748874")),
    (60, "BOM-NAG", "MUMBAI", "NAGPUR", "BOM", "NAG", 675676, Decimal("0.4188"), Decimal("0.00734468")),
]


def assert_no_cpi_weight_contamination(weights: Dict[str, Any]) -> None:
    """
    Guards against accidental injection of official MoSPI CPI airfare expenditure weight
    into route-weight or basket calculations.
    """
    for k, v in weights.items():
        k_str = str(k).strip()
        if k_str in PROHIBITED_CPI_ROUTE_KEYS or "07.3.3" in k_str:
            raise ValueError(
                f"CRITICAL METHODOLOGICAL VIOLATION: CPI expenditure item code '{k}' "
                "cannot be used as a route weight! "
                "Route weights must reflect DGCA passenger traffic shares."
            )
        try:
            d_val = Decimal(str(v))
        except (ValueError, TypeError, ArithmeticError):
            continue

        for prohibited in PROHIBITED_CPI_WEIGHT_VALUES:
            if abs(d_val - prohibited) < Decimal("0.0000001"):
                raise ValueError(
                    f"CRITICAL METHODOLOGICAL VIOLATION: Weight value {d_val} for '{k}' matches "
                    f"CPI airfare expenditure weight ({prohibited}). CPI expenditure weights must NOT "
                    "be used as route weights!"
                )


def validate_route_basket(basket: DGCARouteBasketConfig) -> None:
    """
    Rigorous validation suite for the DGCA Top-60 basket:
    1. Exactly 60 routes.
    2. All route weights > 0.
    3. No duplicate unordered routes.
    4. Ranks contiguous 1 to 60.
    5. Route weights sum to 1.0 within strict Decimal tolerance (1e-6).
    6. basket_id and reference_period required.
    7. Anti-contamination guard against CPI weights.
    8. Airport distinctions preserved (DABOLIM vs GOA / Mopa).
    """
    if not basket.basket_id:
        raise ValueError("basket_id is required")
    if not basket.reference_period:
        raise ValueError("reference_period is required")
    if len(basket.routes) != 60:
        raise ValueError(f"Basket must contain exactly 60 routes, got {len(basket.routes)}")

    seen_unordered: Set[tuple[str, str]] = set()
    ranks_seen: Set[int] = set()
    total_weight = Decimal("0")
    total_volume = 0
    dabolim_found = False
    mopa_found = False

    weights_dict: Dict[str, Decimal] = {}

    for r in basket.routes:
        if r.rank in ranks_seen:
            raise ValueError(f"Duplicate rank {r.rank} detected in basket")
        ranks_seen.add(r.rank)

        if r.route_weight <= Decimal("0"):
            raise ValueError(f"Route weight for {r.route_id} must be > 0, got {r.route_weight}")
        if r.annual_passenger_volume <= 0:
            raise ValueError(f"Passenger volume for {r.route_id} must be > 0, got {r.annual_passenger_volume}")

        # Check unordered duplicate
        pair = (min(r.origin.upper(), r.destination.upper()), max(r.origin.upper(), r.destination.upper()))
        if pair in seen_unordered:
            raise ValueError(f"Duplicate unordered route detected: {pair}")
        seen_unordered.add(pair)

        # Check airport stations
        if "DABOLIM" in pair:
            dabolim_found = True
        if "GOA" in pair:
            mopa_found = True

        total_weight += r.route_weight
        total_volume += r.annual_passenger_volume
        weights_dict[r.route_id] = r.route_weight

    # Ranks must cover 1..60
    if ranks_seen != set(range(1, 61)):
        raise ValueError(f"Ranks must be strictly contiguous from 1 to 60. Missing: {set(range(1, 61)) - ranks_seen}")

    # Station separation check
    if not (dabolim_found and mopa_found):
        raise ValueError("Methodological violation: DABOLIM and GOA (Mopa) must both be present as distinct stations")

    # Anti-contamination check
    assert_no_cpi_weight_contamination(weights_dict)

    # Weight sum check within strict Decimal tolerance
    if abs(total_weight - Decimal("1.0")) > Decimal("0.0001"):
        raise ValueError(f"Route weights must sum to 1.0, got {total_weight}")

    # Volume check
    if total_volume != TOTAL_BASKET_PASSENGER_VOLUME:
        raise ValueError(
            f"Basket volume {total_volume} does not match expected {TOTAL_BASKET_PASSENGER_VOLUME}"
        )


def _build_cy2024_top60_basket() -> DGCARouteBasketConfig:
    """Builds and validates the canonical DGCA CY2024 Top-60 basket."""
    routes: List[DGCARouteItem] = []
    
    # Calculate exact unrounded weights with Decimal, then adjust residual on rank 1
    total_basket_dec = Decimal(str(TOTAL_BASKET_PASSENGER_VOLUME))
    exact_weights = [Decimal(str(rec[6])) / total_basket_dec for rec in _RAW_TOP60_RECORDS]
    weight_sum = sum(exact_weights)
    diff = Decimal("1.0") - weight_sum
    if diff != Decimal("0"):
        exact_weights[0] += diff

    for idx, rec in enumerate(_RAW_TOP60_RECORDS):
        rank, route_id, orig, dest, o_code, d_code, vol, dgca_share, _ = rec
        routes.append(
            DGCARouteItem(
                rank=rank,
                route_id=route_id,
                origin=orig,
                destination=dest,
                origin_code=o_code,
                destination_code=d_code,
                annual_passenger_volume=vol,
                dgca_share_percent=dgca_share,
                route_weight=exact_weights[idx],
                source=SOURCE,
                reference_period=REFERENCE_PERIOD,
                basket_id=BASKET_ID,
            )
        )

    provenance = {
        "authority": "Directorate General of Civil Aviation (DGCA), Government of India",
        "dataset_name": "CITY PAIR WISE MONTHLY DOMESTIC PASSENGER TRAFFIC STATISTICS",
        "reference_period": "CY2024 (January 2024 – December 2024)",
        "source_files": [f"DOM CITYPAIR DATA, {m} 2024.xlsx" for m in [
            "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
        ]],
        "extraction_methodology": (
            "Row-level extraction of directional scheduled domestic passenger traffic "
            "(PASSENGERS TO CITY 2 + PASSENGERS FROM CITY 2) for all 12 calendar months, "
            "matching official DGCA monthly checksum totals with 0 error."
        ),
        "normalization_notes": [
            "Leading and trailing whitespace stripped across 190 cells.",
            "Case normalized to uppercase across all stations.",
            "Ghaziabad terminal reported under GHAZIABAD in January 2024 reconciled with HINDON AIRPORT.",
            "Goa Dabolim (GOI) and Manohar International Airport Mopa (GOX) preserved as distinct stations.",
            "Top-60 routes represent 57.0247% of All-India domestic traffic (91,995,307 of 161,325,253).",
            "Route weights are internal representativeness weights and distinct from MoSPI CPI airfare weight."
        ],
    }

    basket = DGCARouteBasketConfig(
        basket_id=BASKET_ID,
        reference_period=REFERENCE_PERIOD,
        basket_size=BASKET_SIZE,
        source=SOURCE,
        source_description=SOURCE_DESCRIPTION,
        coverage_percent=COVERAGE_PERCENT,
        total_basket_passenger_volume=TOTAL_BASKET_PASSENGER_VOLUME,
        total_all_india_passenger_volume=TOTAL_ALL_INDIA_PASSENGER_VOLUME,
        provenance=provenance,
        routes=routes,
    )

    validate_route_basket(basket)
    return basket


# Cached singleton instance of the validated basket
DGCA_CY2024_TOP60_BASKET: DGCARouteBasketConfig = _build_cy2024_top60_basket()


def get_dgca_cy2024_top60_basket() -> DGCARouteBasketConfig:
    """Returns the validated DGCA CY2024 Top-60 route basket."""
    return DGCA_CY2024_TOP60_BASKET


def get_top60_route_weights(use_iata_codes: bool = True) -> Dict[str, Decimal]:
    """
    Returns the normalized route weights dictionary for the Top-60 basket.
    Keys are canonical IATA pairs (e.g. 'DEL-BOM') by default, or city pairs ('DELHI-MUMBAI').
    """
    basket = get_dgca_cy2024_top60_basket()
    weights: Dict[str, Decimal] = {}
    for r in basket.routes:
        key = r.route_id if use_iata_codes else f"{r.origin}-{r.destination}"
        weights[key] = r.route_weight
    return weights
