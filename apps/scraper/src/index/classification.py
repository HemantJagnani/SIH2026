"""
MoSPI COICOP 2018 Classification and CPI Integration Layer for APIx Phase 29.

Provides formal institutional mappings:
- UN COICOP 2018 classification hierarchy adopted in CPI 2024
- MoSPI CPI 2024 domestic airfare checkpoint specification (21-day advance booking)
- Strict separation between DGCA passenger traffic share proxies and official MoSPI CPI expenditure weights
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional


@dataclass(frozen=True)
class COICOPClassification:
    """
    Formal COICOP 2018 classification hierarchy utilized by MoSPI CPI 2024.
    Reference: MoSPI CPI 2024 National Metadata Structure & UN COICOP 2018.
    """
    division: str = "07"
    division_name: str = "Transport"
    group: str = "07.3"
    group_name: str = "Passenger transport services"
    coicop_class: str = "07.3.3"
    class_name: str = "Passenger transport by air"
    subclass: str = "07.3.3.1"
    subclass_name: str = "Domestic passenger transport by air"
    cpi_item_code: str = "07.3.3.1.01"  # Documented provisional item code; official NSO code pending release
    cpi_item_description: str = "Domestic air travel - economy class one-way"
    classification_authority: str = "Ministry of Statistics and Programme Implementation (MoSPI) / UN COICOP 2018"
    base_year: str = "2024=100"


@dataclass(frozen=True)
class ReferencePeriodTaxonomy:
    """
    Formal reference period taxonomy conforming to MoSPI CPI 2024 and Eurostat HICP standards.

    CRITICAL METHODOLOGICAL DISTINCTION:
    1. PROJECT REFERENCE:
       - reference_type: PROVISIONAL_PROJECT_REFERENCE
       - experimental_project_reference_price: ₹6,632.67 (Option B first complete production run on 2026-09-26)
       - Permits high-frequency experimental series tracking: I_project,t = P_project,t / P_project,ref * 100
       - NEVER describe this as the official MoSPI price reference!
    2. MOSPI INDEX REFERENCE:
       - index_reference_period: 2024=100
    3. MOSPI PRICE REFERENCE:
       - price_reference_period: calendar-year 2024 average
       - Status: PENDING_2024_HISTORICAL_ACTUALS. Must be calculated from actual 2024 observations or
         a separately documented historical reconstruction. DO NOT manufacture 2024 prices from 2026 observations.
    4. MOSPI WEIGHT REFERENCE:
       - weight_reference_period: HCES 2023-24 (Household Consumption Expenditure Survey 2023-24)
    5. EUROSTAT CHAIN-LINKING REFERENCE:
       - chain_link_period: December y-1 (December of the preceding year as the annual linking point)
       - In Eurostat HICP, monthly prices are NOT directly divided by the annual average; short-period
         price relatives are chained, and the long series is subsequently expressed in the index reference period.
    """
    # 1. Project Reference
    reference_type: str = "PROVISIONAL_PROJECT_REFERENCE"
    experimental_project_reference_price: Decimal = Decimal("6632.67")
    experimental_reference_period: str = "2026-09-26"
    reference_price: Decimal = Decimal("6632.67")
    reference_price_method: str = "Option B — first production run weighted representative price"
    reference_price_source: str = "production_run_825fa969"
    reference_index_value: Decimal = Decimal("100.00")

    # 2. MoSPI Index Reference
    index_reference_period: str = "2024=100"

    # 3. MoSPI Price Reference
    price_reference_period: str = "calendar-year 2024 average"
    price_reference_status: str = "PENDING_2024_HISTORICAL_ACTUALS"

    # 4. MoSPI Weight Reference
    weight_reference_period: str = "HCES 2023-24"

    # 5. Eurostat Chain-Linking Reference
    chain_link_period: str = "December y-1"

    methodology_version: str = "APIx v2.0 (MoSPI CPI 2024 + Eurostat HICP Aligned)"


@dataclass
class CPIIntegrationLayer:
    """
    Architectural boundary separating market passenger traffic proxies from official CPI expenditure weights,
    and enforcing the 5 distinct reference tiers.
    
    CRITICAL METHODOLOGICAL INVARIANT:
    - DGCA route passenger traffic shares (W_r) answer: "What share of domestic air travel occurs on route r?"
    - MoSPI CPI household expenditure weights (W_cpi) answer: "What share of total consumer household budget is spent on airfare?"
    These two weights MUST NEVER be conflated or substituted for one another.
    """
    coicop: COICOPClassification = field(default_factory=COICOPClassification)
    taxonomy: ReferencePeriodTaxonomy = field(default_factory=ReferencePeriodTaxonomy)
    
    # Official MoSPI CPI 2024 weighting parameters (from HCES 2023-24)
    # Note: Actual weight is parameterized; provisional value reflects urban transport consumption share
    cpi_airfare_weight_urban: Decimal = Decimal("0.003500")   # ~0.35% of urban consumption basket
    cpi_airfare_weight_rural: Decimal = Decimal("0.000450")   # ~0.045% of rural consumption basket
    cpi_airfare_weight_combined: Decimal = Decimal("0.001850") # ~0.185% of all-India combined basket
    cpi_weight_source: str = "Household Consumption Expenditure Survey (HCES) 2023-24 / MoSPI CPI 2024"
    cpi_weight_status: str = "PROVISIONAL_HCES_2023_24_ESTIMATE"

    # Route representativeness proxies (DGCA passenger traffic shares)
    dgca_passenger_share_del_bom: Decimal = Decimal("1.000000")  # Initially 1.0 for single route pilot, ~0.12 in national matrix
    dgca_traffic_period: str = "DGCA Domestic Air Traffic Monthly Report (May 2026)"
    dgca_traffic_proxy_note: str = "DGCA passenger share serves strictly as a route representativeness proxy, NOT as CPI expenditure weight."

    def calculate_cpi_impact(
        self,
        apix_inflation_rate_percent: Decimal,
        sector: str = "COMBINED"
    ) -> Decimal:
        """
        Calculates the contribution to headline CPI inflation in basis points.
        Contribution (pp) = (W_airfare / 100) * APIx_inflation_rate
        """
        weight_map = {
            "URBAN": self.cpi_airfare_weight_urban,
            "RURAL": self.cpi_airfare_weight_rural,
            "COMBINED": self.cpi_airfare_weight_combined,
        }
        w = weight_map.get(sector.upper(), self.cpi_airfare_weight_combined)
        return (w * apix_inflation_rate_percent)

    def get_reference_taxonomy_meta(self) -> Dict[str, Any]:
        """Returns structured dictionary of the 5 reference tiers."""
        return {
            "project_reference": {
                "reference_type": self.taxonomy.reference_type,
                "experimental_project_reference_price": float(self.taxonomy.experimental_project_reference_price),
                "experimental_reference_period": self.taxonomy.experimental_reference_period,
                "reference_price_method": self.taxonomy.reference_price_method,
                "reference_price_source": self.taxonomy.reference_price_source,
                "reference_index_value": float(self.taxonomy.reference_index_value),
                "status_note": "Provisional project reference for experimental series only; NOT MoSPI price reference.",
            },
            "mospi_index_reference": {
                "index_reference_period": self.taxonomy.index_reference_period,
                "standard": "MoSPI CPI 2024 = 100",
            },
            "mospi_price_reference": {
                "price_reference_period": self.taxonomy.price_reference_period,
                "price_reference_status": self.taxonomy.price_reference_status,
                "rule": "Must be calculated from actual 2024 airfare observations or documented reconstruction. Never manufactured from 2026 data.",
            },
            "mospi_weight_reference": {
                "weight_reference_period": self.taxonomy.weight_reference_period,
                "source": self.cpi_weight_source,
                "combined_basket_weight": float(self.cpi_airfare_weight_combined),
            },
            "eurostat_chain_linking_reference": {
                "chain_link_period": self.taxonomy.chain_link_period,
                "standard": "Eurostat HICP Annual December y-1 Chain Linking",
                "rule": "Monthly prices are not divided directly by annual average; short-period Jevons links are chained recursively.",
            },
        }
