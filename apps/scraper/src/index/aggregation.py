"""
Index Aggregation Engine for APIx Phase 29.

Implements:
1. Lead-time aggregation using PROVISIONAL EQUAL LEAD-TIME WEIGHTS (w_L = 1/6):
   I_(r,l,t) = unweighted mean across product strata within lead-time class l
   I_(r,t) = sum_l [ W_l * I_(r,l,t) ]
2. Route aggregation using DGCA passenger traffic share proxies:
   APIx_t = sum_r [ W_r * I_(r,t) ] (where W_DELBOM = 1.0000 for single route)
3. Source Diagnostic Handling:
   Separate source calculations for Google Flights, EaseMyTrip, etc.
   Records: source_overlap, source_coverage, source_divergence.
   Never weights by scraped row counts.
4. Retains DEL_BOM_PROTOTYPE_MEDIAN_INDICATOR as an explicit diagnostic indicator.
"""

from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional
from .models import (
    ElementaryIndexResult,
    LeadTimeIndexResult,
    RouteIndexResult,
    APIxSeriesResult,
)
from .weights import WeightRegistry
from .classification import CPIIntegrationLayer
from .cpi_contribution import CPIContributionEngine



class IndexAggregationEngine:
    """
    Higher-level weighted aggregation engine conforming to MoSPI Young/Laspeyres framework.
    """

    def __init__(
        self,
        weight_registry: Optional[WeightRegistry] = None,
        weights: Optional[WeightRegistry] = None,
        methodology_version: str = "APIx v1.0",
    ):
        self.weights = weight_registry or weights or WeightRegistry()
        self.methodology_version = methodology_version
        self.cpi_layer = CPIIntegrationLayer()

    def aggregate_elementary_to_lead_time(
        self,
        elementary_results: List[ElementaryIndexResult],
        period: str,
    ) -> Dict[tuple[str, str], LeadTimeIndexResult]:
        """
        Aggregates elementary strata within (route, lead_time_class):
            I_(r,l,t) = mean over strata q of I_(r,l,q,t)
        Returns:
            Dict mapping (route, lead_time_class) -> LeadTimeIndexResult
        """
        grouped: Dict[tuple[str, str], list[ElementaryIndexResult]] = defaultdict(list)
        for el in elementary_results:
            if el.is_published and el.period == period:
                grouped[(el.route, el.lead_time_class)].append(el)

        lead_time_results: Dict[tuple[str, str], LeadTimeIndexResult] = {}
        for (route, lead_time), el_list in sorted(grouped.items()):
            if not el_list:
                continue
            # Arithmetic average across homogeneous product strata within lead-time class
            avg_index = sum(e.chained_index for e in el_list) / Decimal(str(len(el_list)))
            mean_coverage = sum(e.coverage_ratio for e in el_list) / len(el_list)
            w = self.weights.get_lead_time_weight(lead_time)

            lead_time_results[(route, lead_time)] = LeadTimeIndexResult(
                route=route,
                lead_time_class=lead_time,
                period=period,
                index_value=Decimal(str(round(avg_index, 4))),
                strata_count=len(el_list),
                coverage_ratio=round(mean_coverage, 4),
                weight=w,
                weight_label=getattr(self.weights, "lead_time_weight_type", "EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS"),
            )

        return lead_time_results

    def aggregate_lead_time_to_route(
        self,
        lead_time_results: Dict[tuple[str, str], LeadTimeIndexResult],
        period: str,
        prototype_median_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, RouteIndexResult]:
        """
        Aggregates lead-time indices into route-level index:
            I_(r,t) = sum_l [ W_l * I_(r,l,t) ]
        Retains prototype median indicator as a diagnostic benchmark.
        """
        by_route: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        for (route, lead_time), res in lead_time_results.items():
            if res.period == period:
                by_route[route][lead_time] = res.index_value

        route_results: Dict[str, RouteIndexResult] = {}
        for route, lt_dict in sorted(by_route.items()):
            if not lt_dict:
                continue
            available_lts = sorted(lt_dict.keys())
            cond_weights = self.weights.get_normalized_sub_weights(
                available_lts, self.weights.lead_time_weights
            )
            route_index = sum(cond_weights[lt] * lt_dict[lt] for lt in available_lts)

            proto_index = None
            proto_price = None
            if prototype_median_data and route in prototype_median_data:
                p_info = prototype_median_data[route]
                proto_index = Decimal(str(p_info.get("route_index", 100.0)))
                proto_price = Decimal(str(p_info.get("weighted_representative_price_inr", 0.0)))

            tax = self.cpi_layer.taxonomy
            route_results[route] = RouteIndexResult(
                route=route,
                period=period,
                index_value=Decimal(str(round(route_index, 4))),
                lead_times_included=available_lts,
                lead_time_weights=cond_weights,
                lead_time_weight_type=getattr(self.weights, "lead_time_weight_type", "EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS"),
                elementary_indices_by_lead_time=lt_dict,
                prototype_median_indicator=proto_index,
                prototype_representative_price_inr=proto_price,
                index_reference_period=tax.index_reference_period,
                price_reference_period=tax.price_reference_period,
                weight_reference_period=tax.weight_reference_period,
                chain_link_period=tax.chain_link_period,
                reference_type=tax.reference_type,
                experimental_project_reference_price=tax.experimental_project_reference_price,
                experimental_reference_period=tax.experimental_reference_period,
                reference_price=tax.reference_price,
                reference_price_method=tax.reference_price_method,
                reference_price_source=tax.reference_price_source,
                reference_index_value=tax.reference_index_value,
                cpi_item_code=self.cpi_layer.weight_config.item_code,
                cpi_airfare_weight_percent=self.cpi_layer.weight_config.percentage_weight,
                cpi_airfare_weight_decimal=self.cpi_layer.weight_config.decimal_weight,
                cpi_weight_disclaimer=self.cpi_layer.weight_config.disclaimer,
                methodology_version=self.methodology_version,
            )

        return route_results

    def aggregate_routes_to_apix(
        self,
        route_results: Dict[str, RouteIndexResult],
        period: str,
        prev_apix_val: Optional[Decimal] = None,
        source_diagnostics: Optional[Dict[str, Any]] = None,
        prototype_median_summary: Optional[Dict[str, Any]] = None,
    ) -> APIxSeriesResult:
        """
        Aggregates route indices into All-India APIx using DGCA passenger traffic proxies.
        Keeps APIx level and CPI contribution as strictly separate outputs.
        """
        available_routes = sorted(route_results.keys())
        cond_route_weights = self.weights.get_normalized_sub_weights(
            available_routes, self.weights.route_weights
        )

        apix_val = sum(cond_route_weights[r] * route_results[r].index_value for r in available_routes)
        final_val = Decimal(str(round(apix_val, 4)))

        mom_pct = None
        if prev_apix_val and prev_apix_val > Decimal("0"):
            mom_pct = Decimal(str(round(((final_val / prev_apix_val) - Decimal("1.0")) * Decimal("100"), 4)))

        # Format COICOP and CPI integration metadata
        coicop_meta = {
            "division": self.cpi_layer.coicop.division,
            "group": self.cpi_layer.coicop.group,
            "class": self.cpi_layer.coicop.coicop_class,
            "subclass": self.cpi_layer.coicop.subclass,
            "cpi_item_code": self.cpi_layer.coicop.cpi_item_code,
            "cpi_item_description": self.cpi_layer.coicop.cpi_item_description,
            "base_year": self.cpi_layer.coicop.base_year,
            "index_reference_period": self.cpi_layer.taxonomy.index_reference_period,
        }

        ref_tax_meta = self.cpi_layer.get_reference_taxonomy_meta()
        tax = self.cpi_layer.taxonomy
        cfg = self.cpi_layer.weight_config

        # CPI Contribution Calculation:
        # airfare_contribution_pp = APIx_percent_change * 0.02951 / 100
        contrib_pp = None
        cpi_combined_pp = None
        cpi_urban_pp = None
        cpi_rural_pp = None
        if mom_pct is not None:
            contrib_pp = self.cpi_layer.calculate_cpi_contribution_pp(mom_pct)
            sec = CPIContributionEngine.calculate_sectoral_contributions(mom_pct)
            cpi_combined_pp = sec.cpi_combined_contribution_pp
            cpi_urban_pp = sec.cpi_urban_contribution_pp
            cpi_rural_pp = sec.cpi_rural_contribution_pp

        cpi_integration_meta = {
            "source": cfg.source,
            "item_code": cfg.item_code,
            "description": cfg.description,
            "reference_year": cfg.reference_year,
            "percentage_weight": float(cfg.percentage_weight),
            "decimal_weight": float(cfg.decimal_weight),
            "percentage_weight_str": str(cfg.percentage_weight),
            "decimal_weight_str": str(cfg.decimal_weight),
            "cpi_airfare_weight_urban": str(self.cpi_layer.cpi_airfare_weight_urban),
            "cpi_airfare_weight_rural": str(self.cpi_layer.cpi_airfare_weight_rural),
            "cpi_airfare_weight_combined": str(self.cpi_layer.cpi_airfare_weight_combined),
            "cpi_weight_source": self.cpi_layer.cpi_weight_source,
            "retrieval_date": cfg.retrieval_date,
            "provenance_reference": cfg.provenance_reference,
            "methodology_version": cfg.methodology_version,
            "disclaimer": cfg.disclaimer,
            "estimated_cpi_contribution_pp": float(contrib_pp) if contrib_pp is not None else None,
            "cpi_combined_contribution_pp": float(cpi_combined_pp) if cpi_combined_pp is not None else None,
            "cpi_urban_contribution_pp": float(cpi_urban_pp) if cpi_urban_pp is not None else None,
            "cpi_rural_contribution_pp": float(cpi_rural_pp) if cpi_rural_pp is not None else None,
            "dgca_proxy_note": self.cpi_layer.dgca_traffic_proxy_note,
            "reference_taxonomy": ref_tax_meta,
        }

        route_indices_map = {r: route_results[r].index_value for r in available_routes}

        return APIxSeriesResult(
            index_name="India Airfare Price Index",
            series_type="MONTHLY_CPI_COMPATIBLE",
            period=period,

            # Explicit Reference Period Taxonomy Fields
            index_reference_period=tax.index_reference_period,
            price_reference_period=tax.price_reference_period,
            weight_reference_period=tax.weight_reference_period,
            chain_link_period=tax.chain_link_period,
            reference_type=tax.reference_type,
            experimental_project_reference_price=tax.experimental_project_reference_price,
            experimental_reference_period=tax.experimental_reference_period,
            reference_price=tax.reference_price,
            reference_price_method=tax.reference_price_method,
            reference_price_source=tax.reference_price_source,
            reference_index_value=tax.reference_index_value,

            # Backward compatibility aliases
            reference_period=period,
            base_value=Decimal("100.00"),
            base_price=tax.experimental_project_reference_price,
            base_period=tax.experimental_reference_period,

            index_value=final_val,
            mom_percent=mom_pct,
            route_indices=route_indices_map,
            lead_time_indices={},  # Populated by engine
            source_diagnostics=source_diagnostics or {},
            prototype_median_indicator=prototype_median_summary,
            coicop_classification=coicop_meta,
            cpi_integration=cpi_integration_meta,

            # Separate CPI Weight and Contribution Outputs (Requirements 5 & 6)
            cpi_airfare_weight_percent=cfg.percentage_weight,
            cpi_airfare_weight_decimal=cfg.decimal_weight,
            cpi_airfare_item_code=cfg.item_code,
            cpi_airfare_item_description=cfg.description,
            cpi_reference_year=cfg.reference_year,
            cpi_weight_source=cfg.source,
            estimated_cpi_contribution_pp=contrib_pp,
            cpi_combined_contribution_pp=cpi_combined_pp,
            cpi_urban_contribution_pp=cpi_urban_pp,
            cpi_rural_contribution_pp=cpi_rural_pp,
            cpi_weight_disclaimer=cfg.disclaimer,

            methodology_version=self.methodology_version,
            product_definition_version="APIx_PRODUCT_DEF_v2.0_FROZEN",
            weight_version=self.weights.version,

            # DGCA Route Basket Integration
            route_basket_id=getattr(self.weights, "basket_id", "DGCA_CY2024_TOP60"),
            route_basket_reference_period=getattr(self.weights, "reference_period", "CY2024"),
            route_basket_coverage_percent=getattr(self.weights, "coverage_percent", Decimal("57.0247")),
            route_weights_used={r: float(cond_route_weights[r]) for r in available_routes},

            # Lead-Time Weights Specification
            lead_time_weight_type=getattr(self.weights, "lead_time_weight_type", "EMPIRICAL_DATASET_DERIVED_LEAD_TIME_WEIGHTS"),
            lead_time_weights_used={k: float(v) for k, v in self.weights.lead_time_weights.items()},
        )
