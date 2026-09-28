"""
Annual December Chain-Linking Engine (§Roadmap Item 7).

Conforms to Eurostat HICP and MoSPI multi-year index continuity:
    Index_(m, y)^(2024=100) = Index_(Dec, y-1)^(2024=100) * [ Index_(m, y)^(Dec y-1=100) / 100 ]

Invariants:
- Versioned annual weights.
- Never retrospectively overwrites previously published index points.
- Remains DATA_DEPENDENT_INACTIVE until multiple annual baskets exist.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional

from .models import AnnualLinkRecord, AnnualChainSeries


class AnnualChainLinkingEngine:
    """
    Manages long-term multi-year chain linking at December of the preceding year.
    """

    def __init__(self, base_year: str = "2024=100"):
        self.base_year = base_year
        self._published_series: Dict[str, Decimal] = {}
        self._annual_links: Dict[int, AnnualLinkRecord] = {}

    @property
    def status(self) -> str:
        """Remains DATA_DEPENDENT_INACTIVE until at least two annual December link points exist."""
        return "ACTIVE" if len(self._annual_links) >= 1 else "DATA_DEPENDENT_INACTIVE"

    def register_december_link(
        self,
        year: int,
        december_index_value: Decimal | float | str,
        weights_version: str,
    ) -> AnnualLinkRecord:
        """
        Registers an immutable annual December link factor.
        Never overwrites previously established annual links.
        """
        if year in self._annual_links:
            return self._annual_links[year]

        d_val = Decimal(str(december_index_value))
        # Cumulative link factor = d_val / 100.0
        link_factor = d_val / Decimal("100.00")

        record = AnnualLinkRecord(
            link_year=year,
            chain_link_factor=Decimal(str(round(link_factor, 6))),
            reference_base_year=self.base_year,
            december_index_value=d_val,
            weights_version=weights_version,
        )
        self._annual_links[year] = record
        return record

    def chain_monthly_index(
        self,
        month_str: str,  # YYYY-MM
        current_year_index_val: Decimal | float | str,
    ) -> Decimal:
        """
        Expresses a monthly index on the historical base year (2024=100):
            Index_(m, y)^(2024=100) = Index_(Dec, y-1)^(2024=100) * [ Index_(m, y) / 100 ]
        """
        y, m = map(int, month_str.split("-"))
        curr_val = Decimal(str(current_year_index_val))

        # Check if previous year December link exists
        prev_year = y - 1
        if prev_year not in self._annual_links:
            # Base year or single-year run: return current value directly
            self._published_series[month_str] = curr_val
            return curr_val

        link_record = self._annual_links[prev_year]
        chained_val = link_record.chain_link_factor * curr_val
        final_val = Decimal(str(round(chained_val, 4)))

        # Store in immutable published history
        self._published_series[month_str] = final_val
        return final_val

    def get_published_series(self) -> AnnualChainSeries:
        """Returns the full published multi-year series."""
        return AnnualChainSeries(
            base_year=self.base_year,
            status=self.status,
            published_links=dict(self._annual_links),
            monthly_indices=dict(self._published_series),
        )
