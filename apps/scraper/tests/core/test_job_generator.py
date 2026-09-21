"""
Tests for Phase 10: Job Generator
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.job_generator import JobGenerator
from adapters.models import CollectionMode
from models.enums import CabinClass, TripType


def test_job_generator_loads_configs(tmp_path: Path):
    """Ensure JobGenerator creates cross product of configurations."""
    
    # Create mock configuration files
    routes_yaml = "routes:\n  - origin: DEL\n    destination: BOM\n  - origin: BLR\n    destination: MAA\n"
    lead_times_yaml = "lead_times:\n  - 1\n  - 7\n"
    sources_yaml = "sources:\n  - name: indigo\n    permitted_method: api\n  - name: makemytrip\n    permitted_method: web\n"
    
    (tmp_path / "routes.yaml").write_text(routes_yaml)
    (tmp_path / "lead_times.yaml").write_text(lead_times_yaml)
    (tmp_path / "sources.yaml").write_text(sources_yaml)
    
    generator = JobGenerator(config_dir=tmp_path)
    test_date = date(2026, 10, 1)
    
    jobs = generator.generate_jobs(
        collection_date=test_date,
        passenger_count=2,
        cabin=CabinClass.BUSINESS,
        trip_type=TripType.ONE_WAY
    )
    
    # 2 routes * 2 lead times * 2 sources = 8 jobs
    assert len(jobs) == 8
    
    # Verify a specific job
    indigo_jobs = [j for j in jobs if j["source"] == "indigo"]
    assert len(indigo_jobs) == 4
    
    # Check date arithmetic
    del_bom_7 = [j for j in indigo_jobs if j["origin"] == "DEL" and j["lead_days"] == 7][0]
    assert del_bom_7["destination"] == "BOM"
    assert del_bom_7["travel_date"] == "2026-10-08"  # Oct 1 + 7 days
    assert del_bom_7["collection_mode"] == CollectionMode.API.value
    
    # Check passenger parameters
    assert del_bom_7["adults"] == 2
    assert del_bom_7["cabin"] == CabinClass.BUSINESS.value
    assert del_bom_7["trip_type"] == TripType.ONE_WAY.value

    # Check web source mapping
    mmt_jobs = [j for j in jobs if j["source"] == "makemytrip"]
    assert mmt_jobs[0]["collection_mode"] == CollectionMode.BROWSER.value
