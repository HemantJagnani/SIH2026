"""
MoSPI COICOP 2018 Classification and CPI Integration Layer for APIx Phase 29.

Provides formal institutional mappings:
- UN COICOP 2018 classification hierarchy adopted in CPI 2024
- MoSPI CPI 2024 domestic airfare checkpoint specification (21-day advance booking)
- Strict separation between DGCA passenger traffic share proxies and official MoSPI CPI expenditure weights
- Integration of official MoSPI CPI 2024 airfare expenditure weight from Annexure 5.3d
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

# ==============================================================================
# OFFICIAL MOSPI CPI 2024 AIRFARE EXPENDITURE WEIGHT CONFIGURATION
# Source: MoSPI CPI 2024 "Weights of item CPI 2024" (Annexure 5.3d)
# Workbook: announcements_1769773015355_ff9dcdb4-3b64-454c-9810-b07b65600475_Weights_of_itme_CPI_2024.xlsx
# ==============================================================================
CPI_AIRFARE_WEIGHT_PERCENT: Decimal = Decimal("0.02951")
CPI_AIRFARE_WEIGHT_DECIMAL: Decimal = Decimal("0.0002951")
CPI_AIRFARE_ITEM_CODE: str = "07.3.3.1.2.01"
CPI_AIRFARE_ITEM_DESCRIPTION: str = "Passenger transport by air, domestic"
CPI_REFERENCE_YEAR: int = 2024
CPI_WEIGHT_SOURCE: str = "MoSPI CPI 2024 Weights of item CPI 2024"
CPI_RETRIEVAL_DATE: str = "2026-09-27"
CPI_PROVENANCE_REFERENCE: str = "announcements_1769773015355_ff9dcdb4-3b64-454c-9810-b07b65600475_Weights_of_itme_CPI_2024.xlsx"
CPI_METHODOLOGY_VERSION: str = "MoSPI CPI 2024 (Base 2024=100) / HCES 2023-24 Item Level Weights"
CPI_AIRFARE_DISCLAIMER: str = (
    "The MoSPI CPI 2024 airfare expenditure weight is used only for the optional "
    "integration of the experimental Airfare Price Index into CPI. It is not used to construct "
    "the Airfare Price Index itself."
)


@dataclass(frozen=True)
class CPIAirfareWeightConfig:
    """
    Configuration and metadata object for official MoSPI CPI 2024 airfare expenditure weight.

    IMPORTANT:
    This is the CPI expenditure weight for airfare. It must NOT be used as a weight
    when calculating the internal APIx price index.
    """
    source: str = CPI_WEIGHT_SOURCE
    item_code: str = CPI_AIRFARE_ITEM_CODE
    description: str = CPI_AIRFARE_ITEM_DESCRIPTION
    reference_year: int = CPI_REFERENCE_YEAR
    percentage_weight: Decimal = CPI_AIRFARE_WEIGHT_PERCENT
    decimal_weight: Decimal = CPI_AIRFARE_WEIGHT_DECIMAL
    methodology_version: str = CPI_METHODOLOGY_VERSION
    retrieval_date: str = CPI_RETRIEVAL_DATE
    provenance_reference: str = CPI_PROVENANCE_REFERENCE
    disclaimer: str = CPI_AIRFARE_DISCLAIMER

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """
        Validates weight representations and fails loudly if inconsistent or invalid.
        - percentage must equal 0.02951
        - decimal must equal 0.0002951
        - fail loudly if the two representations disagree
        """
        if not isinstance(self.percentage_weight, Decimal) or not isinstance(self.decimal_weight, Decimal):
            raise TypeError("CPI airfare weights must be of type Decimal")

        calculated_decimal = self.percentage_weight / Decimal("100")
        if self.decimal_weight != calculated_decimal:
            raise ValueError(
                f"CPI airfare percentage ({self.percentage_weight}%) and decimal ({self.decimal_weight}) "
                f"disagree! Expected decimal = {calculated_decimal}."
            )

        if self.percentage_weight != Decimal("0.02951"):
            raise ValueError(
                f"Invalid CPI airfare percentage weight: {self.percentage_weight}. "
                "Must equal exactly 0.02951 per official MoSPI CPI 2024 item weights."
            )

        if self.decimal_weight != Decimal("0.0002951"):
            raise ValueError(
                f"Invalid CPI airfare decimal weight: {self.decimal_weight}. "
                "Must equal exactly 0.0002951 per official MoSPI CPI 2024 item weights."
            )

        if self.item_code != "07.3.3.1.2.01":
            raise ValueError(f"Invalid CPI item code: {self.item_code}. Must be '07.3.3.1.2.01'.")

        if self.reference_year != 2024:
            raise ValueError(f"Invalid CPI reference year: {self.reference_year}. Must be 2024.")

    def calculate_cpi_contribution_pp(self, apix_percent_change: Decimal | float | int | str) -> Decimal:
        """
        Given APIx percentage change:
            airfare_contribution_pp = APIx_percent_change * 0.02951 / 100

        Example:
            APIx change = +10%
            contribution = 10 * 0.02951 / 100
                         = +0.002951 percentage points
        """
        if apix_percent_change is None:
            return Decimal("0.000000")
        pct_change = Decimal(str(apix_percent_change))
        contrib = (pct_change * self.percentage_weight) / Decimal("100")
        return contrib.quantize(Decimal("0.00000001"))

    def to_metadata_dict(self) -> Dict[str, Any]:
        """
        Returns structured dictionary for database/methodology metadata storage.
        """
        return {
            "source": self.source,
            "item_code": self.item_code,
            "description": self.description,
            "reference_year": self.reference_year,
            "percentage_weight": float(self.percentage_weight),
            "decimal_weight": float(self.decimal_weight),
            "percentage_weight_str": str(self.percentage_weight),
            "decimal_weight_str": str(self.decimal_weight),
            "methodology_version": self.methodology_version,
            "retrieval_date": self.retrieval_date,
            "provenance_reference": self.provenance_reference,
            "disclaimer": self.disclaimer,
        }


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
    subclass_name: str = "Passenger transport by air, domestic"
    cpi_item_code: str = CPI_AIRFARE_ITEM_CODE            # "07.3.3.1.2.01"
    cpi_item_description: str = CPI_AIRFARE_ITEM_DESCRIPTION  # "Passenger transport by air, domestic"
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
    # 1. Project Reference (Descriptive Diagnostic Only - Prohibited from Index Calculation)
    reference_type: str = "PROVISIONAL_PROJECT_REFERENCE"
    reference_purpose: str = "descriptive/reference-price diagnostic"
    experimental_project_reference_price: Decimal = Decimal("8641.45")
    experimental_reference_period: str = "2026-09-27"
    reference_price: Decimal = Decimal("8641.45")
    reference_price_method: str = "Finalized 60-route x 6-lead-time basket reference price"
    reference_price_source: str = "top60_observation_classification_360cell"
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
    weight_config: CPIAirfareWeightConfig = field(default_factory=CPIAirfareWeightConfig)

    # Official MoSPI CPI 2024 airfare expenditure weight from Annexure 5.3d
    # Item code: 07.3.3.1.2.01, Description: Passenger transport by air, domestic
    cpi_airfare_weight_percent: Decimal = CPI_AIRFARE_WEIGHT_PERCENT    # 0.02951%
    cpi_airfare_weight_decimal: Decimal = CPI_AIRFARE_WEIGHT_DECIMAL    # 0.0002951
    cpi_airfare_weight_combined: Decimal = CPI_AIRFARE_WEIGHT_DECIMAL   # 0.0002951 (All-India Combined)
    
    # Official sector shares within All-India basket (Table 5.3d sum)
    cpi_airfare_weight_rural: Decimal = Decimal("0.00011666")           # 0.011666% of All-India
    cpi_airfare_weight_urban: Decimal = Decimal("0.00017843")           # 0.017843% of All-India
    cpi_weight_source: str = CPI_WEIGHT_SOURCE
    cpi_weight_status: str = "OFFICIAL_MOSPI_CPI_2024_ANNEXURE_5_3D"

    # Route representativeness proxies (DGCA passenger traffic shares)
    dgca_passenger_share_del_bom: Decimal = Decimal("1.000000")
    dgca_traffic_period: str = "DGCA Domestic Air Traffic Monthly Report (May 2026)"
    dgca_traffic_proxy_note: str = "DGCA passenger share serves strictly as a route representativeness proxy, NOT as CPI expenditure weight."

    def __post_init__(self) -> None:
        self.weight_config.validate()

    def calculate_cpi_contribution_pp(
        self,
        apix_percent_change: Decimal | float | int | str,
    ) -> Decimal:
        """
        Calculates the estimated airfare contribution to CPI in percentage points:
            airfare_contribution_pp = APIx_percent_change * 0.02951 / 100
        """
        return self.weight_config.calculate_cpi_contribution_pp(apix_percent_change)

    def calculate_cpi_impact(
        self,
        apix_inflation_rate_percent: Decimal,
        sector: str = "COMBINED"
    ) -> Decimal:
        """
        Calculates the contribution to headline CPI inflation in percentage points:
            Contribution (pp) = APIx_percent_change * weight_decimal
        """
        weight_map = {
            "URBAN": self.cpi_airfare_weight_urban,
            "RURAL": self.cpi_airfare_weight_rural,
            "COMBINED": self.cpi_airfare_weight_combined,
        }
        w = weight_map.get(sector.upper(), self.cpi_airfare_weight_combined)
        return (w * apix_inflation_rate_percent).quantize(Decimal("0.00000001"))

    def get_reference_taxonomy_meta(self) -> Dict[str, Any]:
        """Returns structured dictionary of the 5 reference tiers and official CPI weight metadata."""
        return {
            "project_reference": {
                "reference_type": self.taxonomy.reference_type,
                "reference_purpose": getattr(self.taxonomy, "reference_purpose", "descriptive/reference-price diagnostic"),
                "experimental_project_reference_price": float(self.taxonomy.experimental_project_reference_price),
                "experimental_reference_period": self.taxonomy.experimental_reference_period,
                "reference_price_method": self.taxonomy.reference_price_method,
                "reference_price_source": self.taxonomy.reference_price_source,
                "reference_index_value": float(self.taxonomy.reference_index_value),
                "status_note": "Provisional project reference for descriptive diagnostic only; NEVER enters CPI elementary index formula.",
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
                "source": self.weight_config.source,
                "item_code": self.weight_config.item_code,
                "item_description": self.weight_config.description,
                "reference_year": self.weight_config.reference_year,
                "percentage_weight": float(self.weight_config.percentage_weight),
                "decimal_weight": float(self.weight_config.decimal_weight),
                "retrieval_date": self.weight_config.retrieval_date,
                "provenance_reference": self.weight_config.provenance_reference,
                "disclaimer": self.weight_config.disclaimer,
            },
            "eurostat_chain_linking_reference": {
                "chain_link_period": self.taxonomy.chain_link_period,
                "standard": "Eurostat HICP Annual December y-1 Chain Linking",
                "rule": "Monthly prices are not divided directly by annual average; short-period Jevons links are chained recursively.",
            },
        }
