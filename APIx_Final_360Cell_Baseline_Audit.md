# AERIX Final 360-Cell Production Baseline Audit & Governance Report

**Audit Date**: September 28, 2026  
**Auditor**: Antigravity Autonomous Reconciliation & Governance Auditor  
**Production Dataset**: `runtime/top60_observation_classification.json` (11,716 observations)  
**Immutable Baseline Snapshot**: `runtime/top60_observation_classification_11430_immutable.json` (11,430 observations)  
**Configuration Reference**: `config/dgca_cy2024_top60.json` (60 routes × 6 lead times = 360 cells)  
**Target Matrix Status**: **360 / 360 Populated Cells (100.00%) | 0 Missing Cells**  
**DGCA-Weighted Route Basket Coverage**: **100.0000%**  

---

## 1. Executive Summary

This formal audit documents the finalization and closure of the AERIX Top-60 Matrix. Following the successful destination resolution fix (`GAU` $\rightarrow$ `"Guwahati"`) and the targeted recollections of the 13 previously missing cells, the 3 targeted outputs were merged into the canonical production classification dataset under strict stratum-aware governance.

### Core Metrics Comparison

| Metric | Pre-Merge Baseline Snapshot (Immutable) | Recollected Additions (13 Cells) | Final Merged 360-Cell Production Matrix |
| :--- | :---: | :---: | :---: |
| **Total Raw Observations** | 11,430 | +286 | **11,716** |
| **Valid AERIX Baseline Observations** | 5,834 | +143 | **5,977** |
| **Duplicate Observations** | 4,772 | +143 | **4,915** |
| **Higher Fare Family Exclusions** | 666 | 0 | **666** |
| **Foreign Transit Exclusions** | 158 | 0 | **158** |
| **Populated Cells** | 347 / 360 (96.39%) | +13 cells | **360 / 360 (100.00%)** |
| **Missing Cells** | 13 / 360 (3.61%) | -13 cells | **0 / 360 (0.00%)** |
| **DGCA-Weighted Coverage** | 97.5232% | +2.4768% | **100.0000%** |
| **Mathematical Discrepancy** | 0 | 0 | **0** |

---

## 2. Ingestion & Merge Provenance

The merge strictly combined three verified source datasets without altering existing observations or duplicating offer signatures:

### 1. Pre-Merge Production Classification Dataset (11,430 observations)
- Preserved immutably as: `runtime/top60_observation_classification_11430_immutable.json`
- Contains ranks 1–60 observations across the 347 previously populated cells.
- Zero existing raw observations were modified or deleted.

### 2. Guwahati Targeted Recollection (270 observations across 12 cells)
- Source file: `runtime/recollection_gau_12cells_observations.json`
- Diagnostics file: `runtime/recollection_gau_12cells_report.json`
- Strata: `DEL-GAU` ($T+1, T+7, T+15, T+21, T+30, T+45$) & `BLR-GAU` ($T+1, T+7, T+15, T+21, T+30, T+45$)
- Yield: 270 raw observations $\rightarrow$ **135 valid baseline offers** + **135 duplicate offers**.

### 3. Indore–Mumbai $T+7$ Transient Glitch Recollection (16 observations across 1 cell)
- Source file: `runtime/recollection_idr_bom_t7_result.json`
- Stratum: `IDR-BOM` at lead time $T+7$ (Travel Date: `2026-10-04`)
- Yield: 16 raw observations $\rightarrow$ **8 valid baseline offers** + **8 duplicate offers**.

### 4. Overlap & Integrity Checks
- **Cell Overlap**: $\emptyset$ (The 13 recollected cells strictly filled the 13 empty matrix coordinates; zero collision with the 347 populated cells).
- **Observation ID Collision**: $\emptyset$ (All 286 new observation UUIDs were confirmed unique against existing records).

---

## 3. Mathematical Classification Invariant

Stratum-aware classification was re-executed across the entire 11,716 observation dataset using `CrossSourceReconciliationPipeline.classify_batch()` and `run()`.

$$\text{VALID\_BASELINE} + \text{DUPLICATE} + \text{HIGHER\_FARE\_FAMILY} + \text{FOREIGN\_TRANSIT} = \text{Total Raw Observations}$$

$$5,977 + 4,915 + 666 + 158 = 11,716$$

$$\text{Discrepancy} = 11,716 - 11,716 = \mathbf{0}$$

- **Valid Economic Fares**: 5,977 ($51.02\%$)
- **Same-Stratum Same-Offer Duplicates**: 4,915 ($41.95\%$)
- **Higher Fare Families Excluded (Flex/Business/Upfront)**: 666 ($5.68\%$)
- **Foreign Transit Excluded (Cabotage Violations)**: 158 ($1.35\%$)

---

## 4. Final 360-Cell Matrix Coverage

Every one of the 60 routes in the DGCA CY2024 top-60 basket is now fully populated across all six lead-time horizons:

| Lead Time Horizon | Days Out | Target Cells | Populated Cells | Missing Cells | Cell Populated Rate |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$T+1$** | 1 day | 60 | 60 | 0 | 100.0% |
| **$T+7$** | 7 days | 60 | 60 | 0 | 100.0% |
| **$T+15$** | 15 days | 60 | 60 | 0 | 100.0% |
| **$T+21$** | 21 days | 60 | 60 | 0 | 100.0% |
| **$T+30$** | 30 days | 60 | 60 | 0 | 100.0% |
| **$T+45$** | 45 days | 60 | 60 | 0 | 100.0% |
| **Total** | — | **360** | **360** | **0** | **100.00%** |

### DGCA-Weighted Basket Coverage

$$\text{Weighted Coverage} = \sum_{r \in \text{Populated Routes}} w_r = \mathbf{1.000000} \quad (\mathbf{100.0000\%})$$

With `DEL-GAU` (Rank 19, weight $0.016652$) and `BLR-GAU` (Rank 53, weight $0.008116$) fully restored, and `IDR-BOM` $T+7$ restored, coverage across the official DGCA passenger volume distribution is complete.

---

## 5. Automated Regression Test Verification

The automated test suite in `tests/reconciliation/` was updated to test both the pre-merge immutable snapshot and the merged 360-cell production matrix concurrently:

```powershell
$env:PYTHONPATH="apps/scraper/src;apps/api/src"; pytest tests/reconciliation/
```
```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Hemant Jagnani\OneDrive\Desktop\SIH2026
plugins: anyio-4.11.0, hypothesis-6.152.2, asyncio-1.4.0, base-url-2.1.0, cov-7.1.0, playwright-0.9.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 37 items

tests\reconciliation\test_cross_source_reconciliation.py .................................. [ 91%]
tests\reconciliation\test_production_regression.py ...                                      [100%]

============================= 37 passed in 2.14s ==============================
```

### Verified Test Cases:
1. `test_production_invariants_11430_immutable_snapshot`: Verifies that `runtime/top60_observation_classification_11430_immutable.json` contains exactly 11,430 observations, 5,834 valid, 4,772 dups, 666 HFF, 158 FT, 347 cells, and 97.5232% coverage. (**PASSED**)
2. `test_production_invariants_360_cells_11716`: Verifies that `runtime/top60_observation_classification.json` contains exactly 11,716 observations, 5,977 valid, 4,915 dups, 666 HFF, 158 FT, 360/360 populated cells, 0 missing cells, and 100.0000% coverage. (**PASSED**)
3. `test_classify_batch_invariants`: Verifies batch classification on the 11,716 observations produces 0 discrepancy. (**PASSED**)
4. `test_cross_source_reconciliation.py` (34 tests): Verifies all product definitions, deduplication scope, and carrier exclusions. (**PASSED**)

---

## 6. Regulatory & Governance Invariants Summary

- **Reference Price ($P_{\text{ref}}$)**: Not calculated.
- **Route Weights & Lead-Time Weights**: Unmodified.
- **CPI Airfare Expenditure Weight**: Unmodified.
- **Product Definition & Classification Rules**: Unmodified.
- **Pre-Merge Immutable Snapshot**: Preserved at `runtime/top60_observation_classification_11430_immutable.json`.
- **Merged Canonical Dataset**: Saved at `runtime/top60_observation_classification.json`.
