"""
Urban/Rural Sectoral CPI Contribution Engine (§Roadmap Item 9).

Calculates percentage-point contributions of domestic airfare to headline CPI inflation
using official MoSPI CPI 2024 Annexure 5.3d weights:
- Combined All-India airfare weight: 0.02951% (0.0002951)
- Urban airfare weight: 0.017843% (0.00017843)
- Rural airfare weight: 0.011666% (0.00011666)

Formula:
    Contribution (pp) = APIx_percent_change * weight_percent / 100
                      = APIx_percent_change * weight_decimal
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional, Union

from .models import SectoralCPIContribution


class CPIContributionEngine:
    """
    Computes sector-disaggregated CPI percentage-point contributions.
    """

    # Official MoSPI CPI 2024 item-level weights (Annexure 5.3d Item 07.3.3.1.2.01)
    WEIGHT_COMBINED_PERCENT = Decimal("0.02951")
    WEIGHT_URBAN_PERCENT = Decimal("0.017843")
    WEIGHT_RURAL_PERCENT = Decimal("0.011666")

    WEIGHT_COMBINED_DECIMAL = Decimal("0.0002951")
    WEIGHT_URBAN_DECIMAL = Decimal("0.00017843")
    WEIGHT_RURAL_DECIMAL = Decimal("0.00011666")

    @classmethod
    def calculate_sectoral_contributions(
        cls,
        apix_inflation_rate_percent: Union[Decimal, float, int, str],
        period: str = "2026-09",
    ) -> SectoralCPIContribution:
        """
        Calculates sectoral contributions in percentage points (pp).
        Must be applied to inflation rate (percentage change), NEVER absolute index level.
        """
        pct_change = Decimal(str(apix_inflation_rate_percent))

        # pp = pct_change * weight / 100
        contrib_comb = (pct_change * cls.WEIGHT_COMBINED_PERCENT) / Decimal("100")
        contrib_urb = (pct_change * cls.WEIGHT_URBAN_PERCENT) / Decimal("100")
        contrib_rur = (pct_change * cls.WEIGHT_RURAL_PERCENT) / Decimal("100")

        return SectoralCPIContribution(
            period=period,
            apix_inflation_rate_percent=pct_change,
            cpi_combined_contribution_pp=contrib_comb.quantize(Decimal("0.00000001")),
            cpi_urban_contribution_pp=contrib_urb.quantize(Decimal("0.00000001")),
            cpi_rural_contribution_pp=contrib_rur.quantize(Decimal("0.00000001")),
            cpi_airfare_weight_combined_percent=cls.WEIGHT_COMBINED_PERCENT,
            cpi_airfare_weight_urban_percent=cls.WEIGHT_URBAN_PERCENT,
            cpi_airfare_weight_rural_percent=cls.WEIGHT_RURAL_PERCENT,
        )

    @classmethod
    def assert_valid_inflation_input(cls, val: Union[Decimal, float, str]) -> None:
        """
        Guards against accidentally supplying index level (e.g., 105.4) instead of
        percentage change (e.g., +5.4%).
        """
        d = Decimal(str(val))
        if d > Decimal("75.0") or d < Decimal("-75.0"):
            # Extreme value check: inflation rate > 75% in a single period is almost certainly an index level
            raise ValueError(
                f"Value {d} appears to be an index level, not an inflation rate! "
                "CPI contribution must be computed from APIx percentage change."
            )
